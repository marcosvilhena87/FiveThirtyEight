import csv
import unittest
from collections import Counter
from pathlib import Path

from src.brasileirao_spi import read_standings, read_fixtures, validate_schedule

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data/brasileirao_2026"


class FixtureAuditTests(unittest.TestCase):
    def setUp(self):
        self.clubs = read_standings(DIR / "standings_2026-10-18.csv")
        self.path = DIR / "fixtures_2026-10-18.csv"
        self.fixtures = read_fixtures(self.path, self.clubs)

    def test_72_pending_and_all_38_games(self):
        self.assertEqual(len(self.fixtures), 72)
        validate_schedule(self.clubs, self.fixtures)

    def test_exactly_one_delayed_fixture(self):
        with self.path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(Counter(x["round"] for x in rows),
                         {"21": 1, "31": 1, "32": 10, "33": 10,
                          "34": 10, "35": 10, "36": 10, "37": 10, "38": 10})
        self.assertEqual([(x["home"], x["away"]) for x in rows if x["round"] == "21"],
                         [("Chapecoense", "Vasco")])
        self.assertEqual([(x["home"], x["away"]) for x in rows if x["round"] == "31"],
                         [("Corinthians", "Vitória")])

    def test_date_source_metadata(self):
        with self.path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            self.assertTrue(r["source"].startswith("https://"))
            if int(r["round"]) >= 35:
                self.assertEqual(r["date_status"], "data_basica_nao_confirmada")
            elif r["round"] == "21":
                self.assertEqual(r["date"], "")
                self.assertEqual(r["date_status"], "data_a_definir")
            else:
                self.assertEqual(r["date_status"], "detalhada")

    def test_published_probabilities_total(self):
        with (ROOT / "results/brasileirao_2026/probabilities_2026-10-18.csv").open(
            encoding="utf-8", newline=""
        ) as f:
            data = list(csv.DictReader(f))
        self.assertEqual(len(data), 20)
        for key, total in [("title_probability", 1), ("relegation_probability", 4), ("top4_probability", 4)]:
            self.assertAlmostEqual(sum(float(row[key]) for row in data), total, places=6)


if __name__ == "__main__":
    unittest.main()
