"""Offline checks for API ingestion and refusal to publish incomplete data."""
import unittest
from unittest.mock import patch
from src.auto_update import identify, run

class AutoUpdateTests(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(identify({"shortName": "RB Bragantino"}), "Bragantino")
        with self.assertRaises(ValueError):
            identify({"name": "Time Desconhecido"})

    def test_empty_feed_is_noop(self):
        self.assertFalse(run([], runs=1, dry_run=True))

    def test_one_known_final_dry_run(self):
        match = {
            "status": "FINISHED",
            "homeTeam": {"shortName": "Fluminense"},
            "awayTeam": {"shortName": "Internacional"},
            "score": {"fullTime": {"home": 2, "away": 0}},
        }
        # Frozen fixture for round 33; no output should be produced in dry-run.
        self.assertTrue(run([match], runs=1, dry_run=True))

    def test_invalid_goal_rejected(self):
        match = {
            "status": "FINISHED",
            "homeTeam": {"shortName": "Fluminense"},
            "awayTeam": {"shortName": "Internacional"},
            "score": {"fullTime": {"home": None, "away": 0}},
        }
        with self.assertRaises(ValueError):
            run([match], runs=1, dry_run=True)

if __name__ == "__main__":
    unittest.main()
