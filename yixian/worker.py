"""Persistent, single-request-at-a-time CPU battle process for training rollouts."""
from __future__ import annotations
import json
import math
import queue
import shutil
import subprocess
import threading
from collections.abc import Mapping
from .research import canonical_json, contract_digest
from .simulator import BRIDGE, ROOT, SimulatorError, engine_contract


class BattleWorker:
    def __init__(self, timeout: float = 15):
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('Worker timeout must be positive and finite.')
        node = shutil.which('node')
        if node is None:
            raise SimulatorError('Node.js is required to start the battle worker.')
        self.timeout = timeout
        self.contract = engine_contract()
        self.digest = contract_digest(self.contract)
        self._lock = threading.RLock()
        self._lines = queue.Queue()
        self._closed = False
        try:
            self._process = subprocess.Popen(
                [node, '--experimental-default-type=module', str(BRIDGE), '--serve'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding='utf-8', bufsize=1, cwd=ROOT,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        except OSError as error:
            raise SimulatorError(f'Cannot start the battle worker: {error}') from error
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self):
        try:
            for line in self._process.stdout:
                self._lines.put(line)
        except (OSError, UnicodeError):
            pass  # A missing response is an error, never a battle label.
        finally:
            self._lines.put(None)

    @staticmethod
    def _validate_result(result, battle):
        if not isinstance(result, dict) or type(result.get('schema_version')) is not int or result['schema_version'] != 1:
            raise ValueError('schema mismatch')
        terminated, truncated = result.get('terminated'), result.get('truncated')
        if type(terminated) is not bool or type(truncated) is not bool or terminated == truncated:
            raise ValueError('invalid terminal flags')
        winner = result.get('winner')
        if winner is not None and (type(winner) is not int or winner not in (0, 1)):
            raise ValueError('invalid winner')
        expected_outcome = 'truncated' if truncated else 'simultaneous_death_unresolved' if winner is None else 'win'
        if result.get('outcome') != expected_outcome or (truncated and winner is not None):
            raise ValueError('inconsistent outcome')
        if result.get('seed') != battle.get('seed') or result.get('first_player') != battle.get('first_player'):
            raise ValueError('response belongs to a different battle')
        turns = result.get('turns')
        if type(turns) is not int or not 1 <= turns <= battle.get('max_turns', 0):
            raise ValueError('invalid turn count')
        players = result.get('players')
        if not isinstance(players, list) or len(players) != 2 or not all(isinstance(p, dict) for p in players):
            raise ValueError('invalid player results')
        for player in players:
            for field in ('hp', 'max_hp', 'qi', 'def', 'destiny', 'cultivation', 'next_card_index'):
                value = player.get(field)
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError('nonfinite player result')
        alive = [player['hp'] > 0 for player in players]
        if terminated and ((winner is None and any(alive)) or
                           (winner is not None and (not alive[winner] or alive[1-winner]))):
            raise ValueError('winner contradicts final health')

    def __call__(self, battle):
        if not isinstance(battle, Mapping):
            raise ValueError('battle must be a JSON object')
        payload = canonical_json(dict(battle))
        with self._lock:
            if self._closed or self._process.poll() is not None:
                raise SimulatorError('Battle worker is closed; no result was produced.')
            try:
                self._process.stdin.write(payload + '\n')
                self._process.stdin.flush()
                line = self._lines.get(timeout=self.timeout)
            except (queue.Empty, OSError) as error:
                self.close()
                raise SimulatorError('Battle worker timed out or stopped; rollout must be discarded.') from error
            if line is None:
                self.close()
                raise SimulatorError('Battle worker exited unexpectedly.')
            try:
                packet = json.loads(line)
                if not isinstance(packet, dict) or type(packet.get('ok')) is not bool:
                    raise ValueError('invalid response envelope')
                if not packet['ok']:
                    if not isinstance(packet.get('error'), str) or type(packet.get('recoverable')) is not bool:
                        raise ValueError('invalid error response')
                else:
                    result = packet['result']
                    self._validate_result(result, battle)
            except (KeyError, ValueError, TypeError, OverflowError) as error:
                self.close()
                raise SimulatorError('Invalid response from battle worker.') from error
            if not packet['ok']:
                if not packet['recoverable']:
                    self.close()
                raise SimulatorError(packet['error'])
            result['engine_contract'] = self.digest
            return result

    def close(self):
        with self._lock:
            if not self._closed:
                self._closed = True
                if self._process.poll() is None:
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                        self._process.wait(timeout=3)
                if self._process.stdin:
                    try:
                        self._process.stdin.close()
                    except OSError:
                        pass
                self._reader.join(timeout=1)
                self._process.stdout.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
