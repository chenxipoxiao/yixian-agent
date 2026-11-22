"""Carry the source-bound neutral vase reader through the season compiler view.

The first candidate installed the reader before v124's per-call override and
therefore did not reach an eligible new battle. Both old entrypoints remain
unchanged; unrelated season projections retain their original implementation.
"""
import inspect
from . import website_battles_v135 as candidate
from . import full_battle_v124 as season
from .combat_season_vase_v124 import vase_projection as season_projection
from .combat_compiler_view_v81 import compiler_modules

ORIGIN = candidate.ORIGIN
METADATA_ID = candidate.METADATA_ID
UnresolvedBattle = candidate.UnresolvedBattle
compile_case = candidate.compile_case


def compiler():
    view = candidate.compiler()
    modules = compiler_modules(view)
    neutral = modules['yixian.full_battle_v80']._vase_projection
    legacy_season = season.rebind(season_projection, modules['yixian.full_battle_v80'])

    def projection(row, context, tables, facts):
        affected = any(199 in p['candidate_start']['talents'] and
                       METADATA_ID in candidate.web_params(ctx, 'privateTalentDatas', '199')
                       for p, ctx in zip(row['players'], context['players']))
        return (neutral if affected else legacy_season)(row, context, tables, facts)

    module = modules['yixian.full_battle_v124']
    module._website_vase_projection = projection
    source = inspect.getsource(season.compile_owned_start)
    replacements = [
        ('from .full_battle_v13 import _params',
         'from .website_battles_v132 import web_params as _params'),
        ("modules['yixian.full_battle_v80']._vase_projection=rebind(vase_projection,modules['yixian.full_battle_v80'])",
         "modules['yixian.full_battle_v80']._vase_projection=_website_vase_projection"),
    ]
    for before, after in replacements:
        if source.count(before) != 1:
            raise UnresolvedBattle('website_vase_metadata:season_source_anchor_changed')
        source = source.replace(before, after)
    exec(compile(source, __file__, 'exec'), vars(module))
    return view
