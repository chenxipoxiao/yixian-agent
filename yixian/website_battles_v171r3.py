"""Validate newer paired original-case bindings before legacy projection.

The four v168 paired inputs already own an explicit normalization sequence.
Keep that sequence and source guard intact. Other exact old receipts use r2.
"""
from . import website_battles_v171r2 as legacy
from . import website_battles_v171 as stance
from . import website_battles_v168 as paired

UnresolvedBattle=legacy.UnresolvedBattle
compiler=legacy.compiler
extension_contract=legacy.extension_contract

def compile_case(case,view,tables):
    if case['row']['id'] in paired.extension_contract()['bindings']:
        return stance.compile_case(case,view,tables)
    return legacy.compile_case(case,view,tables)
