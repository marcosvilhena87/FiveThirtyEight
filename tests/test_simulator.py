import csv
import math
import tempfile
import unittest
from pathlib import Path

from src.brasileirao_spi import (
    expected_goals, match_probabilities, poisson, rank, ratings,
    read_standings, read_fixtures, simulate, validate_schedule,
)


def synthetic_league():
    clubs = {}
    for i in range(20):
        name = f"Clube {i:02d}"
        clubs[name] = dict(played=36, wins=12, draws=12, losses=12,
                           gf=40 + i, ga=45 - i, points=48)
    # Rodada completa em turno e returno, mantendo 38 partidas por clube.
    fixtures = []
    for i in range(0, 20, 2):
        a, b = f"Clube {i:02d}", f"Clube {i+1:02d}"
        fixtures.extend(((a, b), (b, a)))
    return clubs, fixtures


class SimulatorTests(unittest.TestCase):
    def test_probabilities_sum(self):
        p = match_probabilities(1.6, 1.1)
        self.assertTrue(all(0 <= x <= 1 for x in p))
        self.assertAlmostEqual(sum(p), 1.0, places=10)

    def test_symmetric_match(self):
        h, d, a = match_probabilities(1.3, 1.3)
        self.assertAlmostEqual(h, a, places=10)
        self.assertGreater(d, 0)

    def test_home_advantage(self):
        clubs, _ = synthetic_league()
        avg, strength = ratings(clubs)
        x, y = expected_goals("Clube 00", "Clube 01", avg, strength)
        self.assertGreater(x, 0)
        self.assertGreater(y, 0)

    def test_poisson_nonnegative_and_repeatable(self):
        import random
        a, b = random.Random(10), random.Random(10)
        self.assertEqual([poisson(a, 1.5) for _ in range(100)],
                         [poisson(b, 1.5) for _ in range(100)])

    def test_schedule_missing_fixture_fails(self):
        clubs, fixtures = synthetic_league()
        with self.assertRaises(ValueError):
            validate_schedule(clubs, fixtures[:-1])

    def test_reproducibility_probability_totals(self):
        clubs, fixtures = synthetic_league()
        x = simulate(clubs, fixtures, runs=120, seed=9)
        y = simulate(clubs, fixtures, runs=120, seed=9)
        self.assertEqual(x, y)
        self.assertEqual(len(x), 20)
        self.assertAlmostEqual(sum(r["title_probability"] for r in x), 1.0)
        self.assertAlmostEqual(sum(r["relegation_probability"] for r in x), 4.0)
        self.assertAlmostEqual(sum(r["top4_probability"] for r in x), 4.0)
        self.assertTrue(all(r["expected_points"] >= 48 for r in x))

    def test_standings_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "table.csv"
            p.write_text("team,played,wins,draws,losses,gf,ga\nA,2,1,1,0,3,1\nA,2,1,1,0,3,1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_standings(p)

    def test_fixture_unknown_team_rejected(self):
        clubs, _ = synthetic_league()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fixtures.csv"
            p.write_text("home,away\nClube 00,Inexistente\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_fixtures(p, clubs)


if __name__ == "__main__":
    unittest.main()
