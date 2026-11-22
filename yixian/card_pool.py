"""Independent explicit card pools; no inferred server eligibility catalogue.

All operations copy JSON state, including its random-generator state. The pool
is a count by card family, not a player hand. Generating/refining a held card
therefore does not debit it. Replacement-specific card effects remain outside
this module. Replacements exclude every card with the outgoing display name;
removing its family before or after those draws is therefore equivalent.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random

from .research import canonical_json

FALLBACK_CARD_ID = -1  # Local CardConfig: 走火入魔, "没有其他牌了！"
CATEGORIES = frozenset({'sect', 'profession', 'other'})
REMOVAL_TIMINGS = frozenset({'before_draw', 'after_draw'})
ALCHEMY_THREE_COPY_NAMES = frozenset({'洗髓丹', '锻体玄丹', '悟道丹'})
SAME_NAME_REPLACEMENT_IDS = frozenset({6000002})  # 画师·练笔.
NONEXEMPT_REPLACE_EFFECT_IDS = frozenset({7000109})  # 五行璞玉.


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def _card_id(value):
    if type(value) is not int or value <= 0 and value != FALLBACK_CARD_ID:
        raise ValueError('Card IDs must be positive raw IDs or the confirmed fallback -1')
    return value


def _metadata(row):
    if not isinstance(row, Mapping):
        raise ValueError('Card metadata must be an object')
    row = deepcopy(dict(row))
    _integer(row.get('card_id'), 'pool card_id', 1)
    for field in ('family', 'name'):
        if not isinstance(row.get(field), str) or not row[field]:
            raise ValueError(f'Metadata requires explicit {field}')
    _integer(row.get('realm'), 'card realm', 1)
    _integer(row.get('copy_count'), 'family copy_count')
    if row.get('category') not in CATEGORIES or type(row.get('replace_effect')) is not bool:
        raise ValueError('Metadata needs category and boolean replace_effect')
    row.setdefault('allow_same_name_replace', False)
    row.setdefault('replacement_depletion_exempt', row['replace_effect'])
    for field in ('allow_same_name_replace', 'replacement_depletion_exempt'):
        if type(row[field]) is not bool:
            raise ValueError(f'{field} must be boolean')
    if 'refine_effect' in row and type(row['refine_effect']) is not bool:
        raise ValueError('refine_effect must be boolean when supplied')
    return row


def _json_rng_state(rng):
    return json.loads(json.dumps(rng.getstate()))


def _rng(pool):
    state = pool.get('rng_state')
    if not isinstance(state, list) or len(state) != 3 or not isinstance(state[1], list):
        raise ValueError('Missing JSON random-generator state')
    rng = random.Random()
    try:
        rng.setstate((state[0], tuple(state[1]), state[2]))
    except (ValueError, TypeError) as error:
        raise ValueError('Invalid random-generator state') from error
    return rng


def create_pool(metadata, *, removal_timing='before_draw', seed=None, rng=None, season_extra_removal=True):
    """Create one player/match pool. ``rng`` is cloned, never mutated.

    Metadata may contain upgrade aliases sharing a family; those aliases share
    one count. A particular draw may nominate only one raw ID per family.
    """
    if removal_timing not in REMOVAL_TIMINGS:
        raise ValueError('removal_timing must be before_draw or after_draw')
    if type(season_extra_removal) is not bool:
        raise ValueError('season_extra_removal must be boolean')
    if (seed is None) == (rng is None):
        raise ValueError('Supply exactly one explicit seed or random.Random instance')
    if seed is not None:
        if type(seed) is not int:
            raise ValueError('seed must be an integer')
        local_rng = random.Random(seed)
    else:
        if not isinstance(rng, random.Random):
            raise ValueError('rng must be random.Random')
        local_rng = random.Random()
        local_rng.setstate(rng.getstate())
    if not isinstance(metadata, (list, tuple)):
        raise ValueError('metadata must be an explicit card whitelist')
    entries, families = {}, {}
    for source in metadata:
        row = _metadata(source)
        key, family = str(row['card_id']), row['family']
        if key in entries:
            raise ValueError('Duplicate raw card ID')
        entries[key] = row
        signature = {field: row[field] for field in ('name', 'realm', 'category', 'copy_count')}
        if family in families and families[family]['metadata'] != signature:
            raise ValueError('Aliases in one family must agree on realm, category and total count')
        families[family] = {'remaining': row['copy_count'], 'metadata': signature}
    result = {'schema_version': 1, 'cards': entries, 'families': families,
              'rng_algorithm': 'python_random_MT19937', 'rng_state': _json_rng_state(local_rng),
              'rules': {'removal_timing': removal_timing, 'season_extra_removal': season_extra_removal},
              'replacement_counts_by_round': {}, 'last_replacement_round': 0}
    canonical_json(result)
    return result


def snapshot(pool):
    """Validate and copy a pool, suitable for JSON persistence and branching."""
    if not isinstance(pool, Mapping):
        raise ValueError('Pool state must be an object')
    canonical_json(pool)
    result = deepcopy(dict(pool))
    if type(result.get('schema_version')) is not int or result['schema_version'] != 1:
        raise ValueError('Unsupported pool schema')
    entries, families = result.get('cards'), result.get('families')
    if not isinstance(entries, dict) or not isinstance(families, dict):
        raise ValueError('Missing pool metadata or family counts')
    expected_families = set()
    for key, source in entries.items():
        row = _metadata(source)
        entries[key] = row
        if key != str(row['card_id']):
            raise ValueError('Noncanonical raw-card key')
        family = row['family']
        expected_families.add(family)
        family_state = families.get(family)
        if not isinstance(family_state, dict):
            raise ValueError('Missing family state')
        remaining = _integer(family_state.get('remaining'), 'remaining family count')
        if remaining > row['copy_count']:
            raise ValueError('Remaining count exceeds initial family count')
        if family_state.get('metadata') != {field: row[field] for field in ('name', 'realm', 'category', 'copy_count')}:
            raise ValueError('Family metadata does not match its raw card')
    if set(families) != expected_families:
        raise ValueError('Unknown family count')
    rules = result.get('rules', {})
    if rules.get('removal_timing') not in REMOVAL_TIMINGS or type(rules.get('season_extra_removal')) is not bool:
        raise ValueError('Missing explicit pool rules')
    ledger = result.get('replacement_counts_by_round')
    last_round = _integer(result.get('last_replacement_round'), 'last_replacement_round')
    if not isinstance(ledger, dict):
        raise ValueError('Missing first-replacement ledger')
    for key, count in ledger.items():
        if not isinstance(key, str) or not key.isdecimal() or str(int(key)) != key or int(key) < 1:
            raise ValueError('Invalid round key in replacement ledger')
        _integer(count, 'replacement count', 1)
    if max((int(x) for x in ledger), default=0) != last_round:
        raise ValueError('Replacement ledger and last round disagree')
    if result.get('rng_algorithm') != 'python_random_MT19937':
        raise ValueError('Unsupported random algorithm')
    _rng(result)
    return result


def _eligible(pool, eligible_ids):
    if not isinstance(eligible_ids, (list, tuple)):
        raise ValueError('Supply an explicit list of legal raw card IDs for this draw')
    rows, seen_ids, seen_families = [], set(), set()
    for card_id in eligible_ids:
        _integer(card_id, 'eligible raw card ID', 1)
        if card_id in seen_ids:
            raise ValueError('Duplicate eligible raw card ID')
        row = pool['cards'].get(str(card_id))
        if row is None:
            raise ValueError(f'Eligible card {card_id} is absent from explicit pool metadata')
        if row['family'] in seen_families:
            raise ValueError('Nominate only one raw-card alias per eligible family')
        seen_ids.add(card_id)
        seen_families.add(row['family'])
        rows.append(row)
    # Canonical order makes a whitelist a set, not an accidental source of bias.
    return sorted(rows, key=lambda row: row['card_id'])


def _draw(pool, rows, rng):
    total = sum(pool['families'][row['family']]['remaining'] for row in rows)
    if not total:
        return FALLBACK_CARD_ID, {'kind': 'empty_legal_pool', 'card_id': FALLBACK_CARD_ID}
    ticket = rng.randrange(total)
    for row in rows:
        family_state = pool['families'][row['family']]
        copies = family_state['remaining']
        if ticket < copies:
            family_state['remaining'] -= 1
            return row['card_id'], {'kind': 'pool_draw', 'card_id': row['card_id'],
                                    'family': row['family'], 'remaining_before': copies,
                                    'remaining_after': copies - 1}
        ticket -= copies
    raise AssertionError('Weighted draw exhausted its tickets')


def _result(pool, card_id, events, **extra):
    return {'pool': pool, 'card_id': card_id, 'events': events,
            'complete_pool_accounting': True, 'complete_current_season_rules': False, **extra}


def draw_card(pool, eligible_ids):
    """Consume one physical copy from the caller's explicit legal candidates."""
    result = snapshot(pool)
    rows = _eligible(result, eligible_ids)
    rng = _rng(result)
    card_id, event = _draw(result, rows, rng)
    result['rng_state'] = _json_rng_state(rng)
    return _result(result, card_id, [event])


def replace_card(pool, outgoing_id, eligible_ids, *, round_number, realm):
    """Account for one replacement, without spending rerolls or editing a hand.

    At realms 2/3/4, only the round's first replacement may return its first
    off-realm draw and draw once again from the same pool. The second result is
    accepted regardless of realm. No repeated search for a current-realm card.
    """
    result = snapshot(pool)
    _integer(round_number, 'round_number', 1)
    _integer(realm, 'player realm', 1)
    if round_number < result['last_replacement_round']:
        raise ValueError('Cannot rewind the replacement-round ledger')
    _card_id(outgoing_id)
    outgoing = result['cards'].get(str(outgoing_id))
    if outgoing is None and outgoing_id != FALLBACK_CARD_ID:
        raise ValueError('Outgoing card needs explicit pool metadata, even if it was generated')
    rows = _eligible(result, eligible_ids)
    outgoing_name = outgoing['name'] if outgoing is not None else '走火入魔'
    allow_same_name = outgoing is not None and outgoing['allow_same_name_replace']
    excluded_ids = ([] if allow_same_name else
                    [row['card_id'] for row in rows if row['name'] == outgoing_name])
    # The user confirmed that replacing a name never yields that same name,
    # including upgrade variants and separate families with the same name.
    # Use this identical filtered whitelist for both the first and second draw.
    if not allow_same_name:
        rows = [row for row in rows if row['name'] != outgoing_name]
    round_key = str(round_number)
    previous = result['replacement_counts_by_round'].get(round_key, 0)
    first = previous == 0
    events = [{'kind': 'replace_same_name_exclusion', 'name': outgoing_name,
               'excluded_card_ids': excluded_ids, 'allow_same_name_exception': allow_same_name}]
    requested = (0 if outgoing is None or outgoing['replacement_depletion_exempt'] else
                 3 if result['rules']['season_extra_removal'] and outgoing['category'] == 'sect' else 2)

    def remove():
        if outgoing is None:
            return
        family_state = result['families'][outgoing['family']]
        before = family_state['remaining']
        removed = min(before, requested)
        family_state['remaining'] -= removed
        events.append({'kind': 'replace_pool_removal', 'card_id': outgoing_id, 'family': outgoing['family'],
                       'requested': requested, 'removed': removed, 'remaining_before': before,
                       'remaining_after': before - removed, 'timing': result['rules']['removal_timing'],
                       'replace_effect_exempt': outgoing['replacement_depletion_exempt']})

    if result['rules']['removal_timing'] == 'before_draw':
        remove()
    rng = _rng(result)
    card_id, event = _draw(result, rows, rng)
    events.append(event)
    redrawn = False
    if first and realm in (2, 3, 4) and card_id != FALLBACK_CARD_ID and result['cards'][str(card_id)]['realm'] != realm:
        family = result['cards'][str(card_id)]['family']
        result['families'][family]['remaining'] += 1
        events.append({'kind': 'first_replace_return', 'card_id': card_id, 'family': family,
                       'reason': 'off_current_realm', 'returned_copies': 1})
        card_id, event = _draw(result, rows, rng)
        events.append(event)
        redrawn = True
    if result['rules']['removal_timing'] == 'after_draw':
        remove()
    result['rng_state'] = _json_rng_state(rng)
    result['replacement_counts_by_round'][round_key] = previous + 1
    result['last_replacement_round'] = round_number
    events.append({'kind': 'replacement_ledger', 'round': round_number, 'count_before': previous,
                   'count_after': previous + 1, 'first_replacement': first})
    return _result(result, card_id, events, redrawn=redrawn, first_replacement=first,
                   replacement_card_effects_executed=False)


def generate_card(pool, card_id):
    """Record a caller-authorized generated card without debiting the pool."""
    _card_id(card_id)
    return _result(snapshot(pool), card_id, [{'kind': 'generated_card', 'card_id': card_id, 'pool_delta': 0}])


def refine_card(pool, card_id):
    """Return the basic +1 cultivation receipt, with extra effects unresolved.

    The caller edits the hand/resource account. The pool is unchanged. Local
    Tips_8 and CardKeywordDesc_炼化 establish the basic +1 for each card.
    """
    _card_id(card_id)
    result = snapshot(pool)
    metadata = result['cards'].get(str(card_id), {})
    effect = metadata.get('refine_effect')
    pending = ([] if effect is False else
               [{'kind': 'extra_refinement_effect', 'card_id': card_id,
                 'reason': 'not_implemented' if effect is True else 'missing_effect_metadata'}])
    return _result(result, None, [{'kind': 'refined_card', 'card_id': card_id,
                                  'pool_delta': 0, 'cultivation_gain': 1}],
                   cultivation_gain=1, pending_actions=pending,
                   complete_refinement=not pending, refinement_effects_executed=False)


def metadata_from_local(card_ids, *, local_root='data/local/2026-11-06', copy_count_overrides=None):
    """Read metadata for only the explicit whitelist; do not infer eligibility.

    Upgrade variants share namespaced families. The namespace distinguishes the
    alchemist 洗髓丹 from an unrelated hidden card of the same display name.
    """
    if not isinstance(card_ids, (list, tuple)) or len(set(card_ids)) != len(card_ids):
        raise ValueError('Provide unique explicit raw card IDs')
    path = Path(local_root) / 'tables/CardConfig.json'
    raw = path.read_bytes()
    catalog = {row['id']: row for row in json.loads(raw)}
    overrides = copy_count_overrides or {}
    if not isinstance(overrides, Mapping):
        raise ValueError('copy_count_overrides must map whitelisted raw IDs to counts')
    if any(key not in card_ids for key in overrides):
        raise ValueError('A copy-count override must refer to a whitelisted raw ID')
    result = []
    for card_id in card_ids:
        _integer(card_id, 'whitelisted raw card ID', 1)
        if card_id not in catalog:
            raise ValueError(f'Unknown local raw card ID {card_id}')
        row = catalog[card_id]
        realm = row['level']
        career, sect, owner = row.get('career', 0), row.get('sect', 0), row.get('owner', 0)
        if career and sect:
            raise ValueError('Ambiguous local card category; provide explicit metadata')
        category = 'profession' if career else 'sect' if sect else 'other'
        if card_id in overrides:
            copies = _integer(overrides[card_id], 'copy_count override')
        elif career == 1 and row['name'] in ALCHEMY_THREE_COPY_NAMES:
            copies = 3
        elif realm in (1, 2, 3, 4, 5):
            copies = 6 if realm == 5 else 8
        else:
            raise ValueError('No confirmed copy-count rule for this realm; provide an override')
        result.append({'card_id': card_id, 'name': row['name'], 'realm': realm, 'category': category,
                       'family': f"sect={sect};career={career};owner={owner};realm={realm};name={row['name']}",
                       'replace_effect': '[置换]' in row.get('desc', ''), 'copy_count': copies,
                       'allow_same_name_replace': card_id in SAME_NAME_REPLACEMENT_IDS,
                       'replacement_depletion_exempt': ('[置换]' in row.get('desc', '')
                                                        and card_id not in NONEXEMPT_REPLACE_EFFECT_IDS),
                       'refine_effect': '[炼化]' in row.get('desc', ''),
                       'no_upgrade': row.get('noUpgrade', False),
                       'source': {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}})
    return result


def contract(pool=None):
    result = {'schema_version': 1, 'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'confirmed_rule_source': 'user_confirmation_in_current_conversation',
              'fallback_card_id': FALLBACK_CARD_ID,
              'fallback_source': 'data/local/2026-11-06/tables/CardConfig.json: id=-1, name=走火入魔',
              'realm_copy_counts': {'1': 8, '2': 8, '3': 8, '4': 8, '5': 6},
              'alchemist_three_copy_names': sorted(ALCHEMY_THREE_COPY_NAMES),
              'first_replace_redraw_realms': [2, 3, 4], 'maximum_first_replace_redraws': 1,
              'replacement_excludes_same_display_names_except_explicit_metadata_exceptions': True,
              'same_name_replacement_exception_raw_ids': sorted(SAME_NAME_REPLACEMENT_IDS),
              'replacement_effect_nonexempt_raw_ids': sorted(NONEXEMPT_REPLACE_EFFECT_IDS),
              'default_removal_timing': 'before_draw',
              'removal_timing_affects_draw_given_same_name_exclusion': False,
              'basic_refinement_cultivation_gain': 1,
              'refinement_source': 'Localization Tips_8 and CardKeywordDesc_炼化',
              'sampling_model': 'uniform_among_remaining_eligible_physical_copies',
              'sampling_distribution_server_verified': False,
              'removal_timing_server_verified': False, 'server_eligible_pool_verified': False,
              'replacement_card_effects_executed': False, 'full_current_season_rules': False}
    if pool is not None:
        checked = snapshot(pool)
        result['rules'] = deepcopy(checked['rules'])
        result['explicit_metadata_sha256'] = hashlib.sha256(canonical_json(checked['cards']).encode()).hexdigest()
    return result
