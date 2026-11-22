"""Versioned numeric card inputs shared by tactical proposals and future planning.

Metadata is NOT an executable rule catalogue or a legal draw pool. otherParams
remain ordered parameters of a particular effect, not universally named stats.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'tactical-card-values-v1'
FIELDS = ('level', 'anima', 'attack', 'randomAttack', 'attackCount', 'def',
          'randomDef', 'damage', 'randomDamage', 'jianYi', 'guaXiang',
          'hpCost', 'physique', 'chargeQi', 'actionAgain', 'rarity')
PARAMETERS = 8
FEATURE_DIM = 2 * (len(FIELDS) + PARAMETERS)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def card_features(row):
    params = row.get('otherParams')
    if params is not None and (not isinstance(params, list) or len(params) > PARAMETERS):
        raise ValueError('Unsupported parameter layout; version the input contract')
    values = [row.get(key) for key in FIELDS]
    values += [(params[i] if params is not None and i < len(params) else None)
               for i in range(PARAMETERS)]
    result = []
    for value in values:
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError('Non-finite/non-numeric card parameter')
        result += [math.asinh(float(value)) if value is not None else 0., float(value is not None)]
    return result


def effect_key(row):
    # Stable across numeric-only patches; template and categorical changes differ.
    return digest({key: row.get(key) for key in
                   ('desc', 'sect', 'career', 'cardType', 'subcategory', 'owner', 'linkageId')})


class TacticalCatalogue:
    def __init__(self, rows, *, rules_version, source_sha256):
        self.rows = {}
        for row in rows:
            key = row['id']
            if type(key) is not int or key in self.rows:
                raise ValueError('Duplicate or invalid card ID')
            card_features(row)
            self.rows[key] = dict(row)
        self.contract = {'schema': SCHEMA, 'rules_version': rules_version,
                         'source_sha256': source_sha256, 'feature_fields': list(FIELDS),
                         'parameter_slots': PARAMETERS, 'numeric_transform': 'asinh; paired known mask',
                         'metadata_only': True, 'executable_or_legal_pool': False,
                         'rows_digest': digest(rows)}
        self.fingerprint = digest(self.contract)

    @classmethod
    def load(cls, path, *, rules_version, expected_sha256):
        data = Path(path).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected_sha256:
            raise ValueError('Card table hash mismatch')
        return cls(json.loads(data.decode('utf-8-sig')), rules_version=rules_version,
                   source_sha256=expected_sha256)

    def matrix(self, vocabulary):
        if len(set(vocabulary)) != len(vocabulary):
            raise ValueError('Duplicate vocabulary')
        missing = set(vocabulary) - self.rows.keys()
        if missing:
            raise ValueError(f'Missing explicit card metadata: {sorted(missing)[:8]}')
        return [[0.] * FEATURE_DIM] + [card_features(self.rows[c]) for c in vocabulary]

    def describe_route(self, *, transition, target, counters):
        """Same current numerical metadata reaches ALL route evaluation inputs.

        Target cards are a hypothetical proposal, not a claim of acquisition,
        legality, completion probability or measured future battle strength.
        """
        return {'rules_fingerprint': self.fingerprint, 'scope': 'hypothetical_route_features',
                **{role: [{'card_id': c, 'features': card_features(self.rows[c]),
                          'effect_key': effect_key(self.rows[c])} for c in cards]
                   for role, cards in [('transition', transition), ('target', target), ('counters', counters)]}}
