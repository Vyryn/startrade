import unittest
from unittest.mock import patch

from tests.support import basics, database, googleapi
from utils import hit_calculator as combat


class ActivityRules(unittest.TestCase):
    def test_activity_requires_three_distinct_long_words(self):
        for message, points in [
            ("", 0),
            ("hi", 0),
            ("blue BLUE moon", 0),
            ("blue moon rises", 1),
            ("blue moon rises over us", 2),
            ("/blue moon rises", 0),
            ("(blue moon rises", 0),
            ("blue moon rises)", 0),
        ]:
            with self.subTest(message=message):
                self.assertEqual(basics.get_activity_worth(message), points)

    def test_wealth_brackets(self):
        brackets = [
            (100, 4),
            (250, 3),
            (400, 2.5),
            (650, 2),
            (1000, 1.8),
            (1200, 1.6),
            (1400, 1.4),
            (1600, 1.2),
            (1800, 1.1),
            (2000, 1),
        ]
        previous = 5
        for millions, multiplier in brackets:
            boundary = millions * 1_000_000
            with self.subTest(boundary=boundary):
                self.assertEqual(database.activity_multiplier(boundary - 1), previous)
                self.assertEqual(database.activity_multiplier(boundary), multiplier)
            previous = multiplier

    def test_sheet_numeric_cells(self):
        for cell, expected in [
            ("$1,234.50", 1234.5),
            ("-12", -12),
            ("", 0),
            ("N/A", 0),
        ]:
            with self.subTest(cell=cell):
                self.assertEqual(googleapi.clean(cell), expected)


class CombatRules(unittest.TestCase):
    def test_damage_falloff(self):
        for setting, distance, expected in [
            ("m20", 20, 100),
            ("m20", 21, 10),
            ("$1,000", 1000, 50),
            ("10", 20, 25),
            ("unknown", 20, 100),
            ("0", 20, 100),
        ]:
            with self.subTest(setting=setting, distance=distance):
                self.assertEqual(combat.attenuate(100, setting, distance), expected)

    def test_shield_and_hull_damage(self):
        for shields, pierce, expected in [
            (40, 0, (30, 0)),
            (50, 0.5, (20, 30)),
            (20, 0, (20, 0)),
            (0, 0, (10, 0)),
            (50, 1, (10, 50)),
        ]:
            with self.subTest(shields=shields, pierce=pierce):
                self.assertEqual(
                    combat.damage_determine(30, shields, 40, 20, pierce, "0", 0),
                    expected,
                )

    def test_lethal_damage_stops_at_zero(self):
        self.assertEqual(combat.damage_determine(1, 0, 40, 20, 0, "0", 0), (0, 0))

    def test_hit_limits(self):
        self.assertEqual(combat.hit_chance(0, 2000, 60, 100, 1), 99)
        self.assertEqual(combat.hit_chance(1000, 0, 60, 1, 60), 0.01)

    def test_evasion_and_bonus(self):
        args = (100, 2000, 60, 30, 60)
        ordinary = combat.hit_chance(*args)
        self.assertAlmostEqual(
            combat.hit_chance(*args, evading=True, bonus=2), ordinary - 8
        )

    def test_advantage_doubles_hit_threshold(self):
        args = (100, 2000, 60, 30, 60)
        with patch.object(
            combat.random, "random", return_value=combat.hit_chance(*args) / 100 + 0.001
        ):
            self.assertFalse(combat.hit_determine(*args))
            self.assertTrue(combat.hit_determine(*args, clear_advantage=True))
