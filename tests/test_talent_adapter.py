from copy import deepcopy
import re
import unittest

from yixian.simulator import is_available, simulate_battle
from yixian.talent_adapter import (
    ROOT, TABLE, LOCALIZATION, SCOPE, SUPPORTED_TALENT_IDS,
    compile_talents, talent_adapter_contract,
)


LOCAL_DATA = TABLE.is_file() and LOCALIZATION.is_file()


def fixture(card="601011", *, turns=1):
    return {"seed": 73, "max_turns": turns, "first_player": 0, "players": [
        {"character": "sw1", "hp": 60, "max_hp": 80, "cultivation": 10,
         "round_number": 10, "destiny": 100, "cards": [card] * 8},
        {"character": "sw2", "hp": 80, "max_hp": 80, "cultivation": 9,
         "round_number": 10, "destiny": 100, "cards": ["601011"] * 8},
    ]}


def play(battle, fates, *, counters=None):
    request = deepcopy(battle)
    compiled = compile_talents(fates, counters, player=request["players"][0])
    if compiled["unsupported"]:
        raise AssertionError(compiled["unsupported"])
    for field, value in compiled["player_fields"].items():
        request["players"][0][field] = request["players"][0].get(field, 0) + value
    return simulate_battle(request)


@unittest.skipUnless(LOCAL_DATA, "Audited local talent snapshot is not installed")
class TalentAdapterTests(unittest.TestCase):
    def test_raw_grades_and_forging_branches_do_not_collapse(self):
        result = compile_talents([13, 10013, 20013, 30013, 10093, 20093])
        self.assertFalse(result["unsupported"])
        self.assertEqual(result["player_fields"]["p5_store_qi_stacks"], 1)
        self.assertIn("blade_forging_sharpness_stacks", result["player_fields"])
        self.assertIn("blade_forging_stable_stacks", result["player_fields"])
        self.assertEqual([x["parameters"][0] for x in result["coverage"][:4]], [1, 1, 2, 3])

    def test_unknown_and_proven_mismatches_are_not_silent_noops(self):
        result = compile_talents([10094, 10127, 153, 209, 987654321])
        self.assertFalse(result["player_fields"])
        self.assertEqual(len(result["unsupported"]), 5)
        self.assertIn("6 extra attack", result["unsupported"][0]["reason"])
        self.assertIn("physique", result["unsupported"][2]["reason"])

    def test_context_cannot_be_guessed_from_untyped_replay_counters(self):
        unknown = compile_talents([92, 110], {"92": 4, "110": 2})
        self.assertEqual(len(unknown["unsupported"]), 2)
        supplied = compile_talents([92, 110], {
            "92": {"swordsmith_attack_bonus": 4}, "110": {"innate_element": "metal"}})
        self.assertFalse(supplied["unsupported"])
        self.assertEqual(supplied["player_fields"], {
            "swordsmith_stacks": 4, "innate_mark_stacks": 1, "innate_metal_stacks": 1})

    def test_physique_needs_explicit_starting_state(self):
        self.assertEqual(len(compile_talents([149, 176, 183, 184])["unsupported"]), 4)
        result = compile_talents([149, 176, 183, 184], player={"physique": 12, "max_physique": 20})
        self.assertFalse(result["unsupported"])

    def test_conflicting_coral_upgrade_and_match_settlement_are_excluded(self):
        result = compile_talents([25, 222, 45, 105])
        self.assertFalse(result["player_fields"])
        self.assertEqual(len(result["unsupported"]), 4)
        self.assertIn("2-attack", result["unsupported"][0]["reason"])

    def test_duplicates_invalid_types_and_mutation_do_not_corrupt_mapping(self):
        for ids in ([13, 13], [True], ["13"], "13"):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                compile_talents(ids)
        original = [13]
        result = compile_talents(original)
        result["coverage"][0]["parameters"][0] = 99
        self.assertEqual(compile_talents(original)["coverage"][0]["parameters"], [1])
        self.assertEqual(original, [13])

    def test_every_registered_field_exists_in_actual_engine_and_has_evidence(self):
        source = (ROOT / "external/yisim/gamestate.jscpp").read_text(encoding="utf-8")
        fields = set(re.findall(r"this\.([a-z0-9_]+)\s*=", source))
        all_ids = sorted(SUPPORTED_TALENT_IDS)
        result = compile_talents(all_ids, {
            "92": {"swordsmith_attack_bonus": 0}, "110": {"innate_element": "wood"}},
            player={"physique": 0, "max_physique": 0})
        self.assertFalse(result["unsupported"])
        self.assertTrue(set(result["player_fields"]).issubset(fields))
        for entry in result["coverage"]:
            self.assertTrue(entry["name"])
            self.assertTrue(entry["description"])
            self.assertTrue(entry["implementation"])
            self.assertEqual(entry["scope"], SCOPE)
            self.assertFalse(entry["current_server_verified"])
        contract = talent_adapter_contract()
        self.assertTrue(contract["combat_component_only"])
        self.assertFalse(contract["acquisition_and_persistent_growth_implemented"])


@unittest.skipUnless(LOCAL_DATA and is_available(), "Pinned simulator and local snapshot required")
class TalentAdapterBattleTests(unittest.TestCase):
    def test_coral_pierces_defense_and_fire_blade_reduces_max_hp(self):
        battle = fixture()
        battle["players"][1]["def"] = 20
        plain = play(battle, [])
        coral = play(battle, [25])
        flame = play(battle, [67])
        self.assertEqual(plain["players"][1]["hp"], 80)
        self.assertEqual(coral["players"][1]["hp"], 77)
        self.assertEqual(coral["players"][1]["def"], 20)
        self.assertEqual(flame["players"][1]["max_hp"], 79)

    def test_cloud_combo_activates_without_preceding_cloud_and_gains_qi_def(self):
        battle = fixture("111021")
        plain = play(battle, [])
        combined = play(battle, [14, 15, 69])
        self.assertEqual(plain["players"][1]["hp"] - combined["players"][1]["hp"], 3)
        self.assertEqual(combined["players"][0]["qi"], 1)
        self.assertEqual(combined["players"][0]["def"], 1)
        self.assertTrue(combined["truncated"])
        self.assertIsNone(combined["winner"])

    def test_heal_expands_max_hp_and_hp_change_gains_def(self):
        battle = fixture("131011")
        plain = play(battle, [])
        boosted = play(battle, [120, 64])
        self.assertEqual(boosted["players"][0]["hp"], 64)
        self.assertEqual(boosted["players"][0]["max_hp"] - plain["players"][0]["max_hp"], 3)
        self.assertEqual(boosted["players"][0]["def"], 1)

    def test_element_activation_triggers_explosion_and_first_only_qi(self):
        battle = fixture("131011", turns=3)
        plain = play(battle, [])
        boosted = play(battle, [138, 202])
        self.assertEqual(boosted["players"][0]["qi"] - plain["players"][0]["qi"], 1)
        self.assertEqual(plain["players"][1]["max_hp"] - boosted["players"][1]["max_hp"], 6)

    def test_guard_and_revive_really_prevent_the_first_death(self):
        battle = fixture(turns=2)
        battle["players"][0]["hp"] = 2
        plain = play(battle, [])
        guard = play(battle, [134])
        revived = play(battle, [139])
        self.assertTrue(plain["terminated"])
        self.assertFalse(guard["terminated"])
        self.assertEqual(guard["players"][0]["hp"], 2)
        self.assertFalse(revived["terminated"])
        self.assertEqual((revived["players"][0]["hp"], revived["players"][0]["max_hp"]), (15, 15))

    def test_swordsmith_counter_and_actual_forging_card_change_damage(self):
        battle = fixture("611033")
        plain = play(battle, [])
        forged = play(battle, [92, 10093, 20094, 10095],
                      counters={"92": {"swordsmith_attack_bonus": 4}})
        self.assertEqual(plain["players"][1]["hp"] - forged["players"][1]["hp"], 7)
        self.assertEqual(forged["players"][0]["qi"], 2)

    def test_start_qi_adds_to_existing_season_qi_without_overwriting(self):
        battle = fixture("111071")
        battle["players"][0]["qi"] = 2
        plain = play(battle, [])
        boosted = play(battle, [13, 20013])
        self.assertEqual(boosted["players"][0]["qi"] - plain["players"][0]["qi"], 3)
        self.assertEqual(boosted["players"][1]["hp"], plain["players"][1]["hp"])
        self.assertEqual(battle["players"][0]["qi"], 2)

    def test_physique_card_triggers_resonance_and_extra_attack(self):
        battle = fixture("141041")
        battle["players"][0].update(physique=12, max_physique=20)
        plain = play(battle, [])
        boosted = play(battle, [173, 184])
        self.assertEqual(plain["players"][1]["hp"] - boosted["players"][1]["hp"], 3)
        self.assertEqual(boosted["players"][0]["def"], 1)


if __name__ == "__main__":
    unittest.main()
