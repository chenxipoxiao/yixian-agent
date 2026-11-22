"""Compare complete case content across the documented v77 JSON key boundary.

Only preparation_v77_context.bindings[*].values may contain integer keys in
memory. Nothing else is dropped or coerced, and ambiguous keys are rejected.
This is a report comparator, not a battle/runtime or model contract change.
"""
from copy import deepcopy
import json
import math


def _json_domain(value):
    if isinstance(value, dict):
        if any(type(k) is not str for k in value):
            raise ValueError('Unexpected non-string JSON key')
        for v in value.values():
            _json_domain(v)
    elif isinstance(value, list):
        for v in value:
            _json_domain(v)
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError('Non-finite report number')
    elif value is not None and type(value) not in (str, int, bool):
        raise ValueError('Unsupported report value')


def canonical_case(case):
    value = deepcopy(case)
    metadata = value.get('compiled', {}).get('preparation_v77_context', {})
    for binding in metadata.get('bindings', []):
        old = binding['values']
        converted = {}
        for k, v in old.items():
            if type(k) not in (str, int) or not str(k).isdigit():
                raise ValueError('Unexpected preparation key')
            key = str(k)
            if key in converted:
                raise ValueError('Preparation key collision')
            converted[key] = v
        binding['values'] = converted
    _json_domain(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False)


def cases_equal(previous, current):
    return canonical_case(previous) == canonical_case(current)
