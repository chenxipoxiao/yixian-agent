from copy import deepcopy
import unittest

from yixian.death_fates import apply_death_prevention
from yixian.effects import EffectEngine
from yixian.effect_battle import simulate_effect_battle
from yixian.simulator import is_available


def fixture(turns=1):
    return {"seed": 73, "max_turns": turns, "first_player": 0, "players": [
        {"character": "sw1", "hp": 40, "max_hp": 40, "cultivation": 10,
         "round_number": 10, "destiny": 100, "cards": ["111021"] * 8},
        {"character": "sw2", "hp": 40, "max_hp": 40, "cultivation": 9,
         "round_number": 10, "destiny": 100, "cards": ["601011"] * 8},
    ]}


def states(engine, *, fates=(), season=()):
    return [engine.initialize_player({"life": 100, "rerolls": 0, "fates": list(fates),
                                      "season_choices": list(season)}, talent_counters={}),
            engine.initialize_player({"life": 100, "rerolls": 0, "fates": [], "season_choices": []})]


def explicit_terminal(request):
    players = deepcopy(request["players"])
    players[0]["hp"], players[1]["hp"] = 20, -1
    return {"terminated": True, "truncated": False, "winner": 0, "players": players}


class ExpandedEffectBoundaryTests(unittest.TestCase):
    def test_multiple_season_start_components_need_interaction_dispatch(self):
        engine = EffectEngine()
        result = simulate_effect_battle(fixture(), states(engine,season=[1004,7036]),
                                       engine=engine,simulator=explicit_terminal)
        self.assertFalse(result['label_usable'])
        self.assertTrue(result['missing_cross_effect_dispatch'])

    def test_unknown_native_or_season_effect_never_yields_eligible_label(self):
        engine = EffectEngine()
        for fates, season in (([153], []), ([987654321], []), ([], [987654321]), ([], [3002])):
            with self.subTest(fates=fates, season=season):
                result = simulate_effect_battle(fixture(), states(engine, fates=fates, season=season),
                                               engine=engine, simulator=explicit_terminal)
                self.assertFalse(result["label_usable"])
                self.assertTrue(result["unimplemented_effects_present"])

    def test_native_activation_and_season_start_need_dispatch_before_training(self):
        engine = EffectEngine()
        initial = states(engine, fates=[138, 202], season=[7066])
        result = simulate_effect_battle(fixture(), initial, engine=engine, simulator=explicit_terminal)
        # Directly assigning initial activation layers does not call yisim's
        # activation event; neither damage nor first-activation Qi is executed.
        # Such a mixed battle remains diagnostic until event dispatch is wired.
        self.assertFalse(result["label_usable"])

    def test_pending_death_draw_blocks_next_battle_even_if_owner_would_win(self):
        engine = EffectEngine()
        actor = engine.initialize_player({"life": 10, "rerolls": 0, "exp": 20,
            "hand_cards": [], "fates": [83], "season_choices": []}, talent_counters={"83": 1})
        pending = apply_death_prevention(actor, 10)["player"]
        pending["life"] = 1
        battle = fixture()
        battle["players"][0]["destiny"] = 1
        other = states(engine)[1]
        with self.assertRaises(ValueError):
            simulate_effect_battle(battle, [pending, other], engine=engine, simulator=explicit_terminal)

    def test_temporary_native_and_season_health_never_overwrites_match_health(self):
        engine = EffectEngine()
        initial = states(engine, fates=[139], season=[1003])
        for player in initial:
            player.update(max_hp=40, extra_max_hp=0)
        before = deepcopy(initial)
        result = simulate_effect_battle(fixture(), initial, engine=engine, simulator=explicit_terminal)
        self.assertEqual(result["match_players"][0]["max_hp"], 40)
        self.assertEqual(result["match_players"][1]["max_hp"], 40)
        self.assertEqual(initial, before)


@unittest.skipUnless(is_available(), "Pinned legacy simulator is not installed")
class ExpandedEffectActualBattleTests(unittest.TestCase):
    def test_native_passives_reach_actual_battle_once_and_leave_match_state_clean(self):
        engine = EffectEngine()
        initial = states(engine, fates=[14, 15, 69])
        before = deepcopy(initial)
        boosted = simulate_effect_battle(fixture(), initial, engine=engine)
        plain = simulate_effect_battle(fixture(), states(engine), engine=engine)
        self.assertEqual(plain["combat"]["players"][1]["hp"] - boosted["combat"]["players"][1]["hp"], 3)
        self.assertEqual(boosted["combat"]["players"][0]["qi"], 1)
        self.assertEqual(boosted["combat"]["players"][0]["def"], 1)
        self.assertEqual(initial, before)
        self.assertEqual(boosted["match_players"], before)
        self.assertFalse(boosted["regular_fate_components"][0]["unsupported"])

    def test_pure_native_terminal_can_be_legacy_label_but_never_current_verified(self):
        engine = EffectEngine()
        result = simulate_effect_battle(fixture(64), states(engine, fates=[14, 15, 69]), engine=engine)
        self.assertTrue(result["label_usable"])
        self.assertFalse(result["current_season_verified"])
        self.assertEqual(result["combat"]["winner"], 0)
        self.assertNotIn("destiny", result["combat"]["players"][1])

    def test_existing_season_qi_plus_native_start_qi_is_added_once(self):
        engine = EffectEngine()
        battle = fixture()
        battle["players"][0]["cards"] = ["111071"] * 8
        native = simulate_effect_battle(battle, states(engine, fates=[13], season=[1001]), engine=engine)
        plain = simulate_effect_battle(battle, states(engine, season=[1001]), engine=engine)
        self.assertEqual(native["starting_qi"], [2, 2])
        self.assertEqual(native["combat"]["players"][0]["qi"] - plain["combat"]["players"][0]["qi"], 1)


if __name__ == "__main__":
    unittest.main()
