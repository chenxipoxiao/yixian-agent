"""Native recorded vase with non-element jade in the first slot, ranked season 10."""
from . import full_battle_v200 as previous
from .combat_compiler_view_v81 import isolated_compiler, compiler_modules
from .full_battle_v45 import digest_json
from .website_battles_v152 import extension_contract, FRAGMENTS

catalogue = previous.catalogue
derive_start_initiative = previous.derive_start_initiative
UnresolvedBattle = previous.UnresolvedBattle
RECORD = 'replay-e40d0b2b2f856b1985d2a2388ac081eeb7fb4e5b2b29678936956920e7035e86-round-8'
SOURCE = ('b55f93961bb9b68d127ff21865f8d68093ba775e0d81f65bb39c8927b31fd501', '8cba39a285f4565eca9fb62a69bb561bc4d1afa4a1f0bfb5a7bf7b8c8b92a637')


def compile_start(row, **kwargs):
    if row.get('id') != RECORD:
        return previous.compile_start(row, **kwargs)
    start = {k: v for k, v in row.items() if k != 'outcome'}
    context = kwargs.get('combat_context')
    if (kwargs.get('game_mode'), kwargs.get('season_mec')) != (3, 10) or (
        digest_json(start), digest_json(context)
    ) != SOURCE:
        raise UnresolvedBattle('jade_vase:unverified_start')
    extension_contract()
    view = isolated_compiler(previous)
    leaf = compiler_modules(view)['yixian.full_battle_v80']

    def project(row, context, tables, facts):
        slots = leaf.vase._params(context['players'][1], 'privateTalentDatas', '199')
        cards, mapping, _, _ = tables
        name = cards[7000109]['name']
        if slots != [7000109, 7000023, 7000109] or name != '五行璞玉' or any(f in name for f in FRAGMENTS):
            raise UnresolvedBattle('jade_vase:metadata_changed')
        return [dict(player_index=1, raw_slots=slots, read_slot_indices=[0],
                     first_slot_known_non_element=True, native_cards=[None, mapping[slots[1]], None],
                     omitted_runtime_slot_indices=[0, 2], card_body_admitted=False)]

    leaf._vase_projection = project
    return view.compile_start(start, **kwargs)
