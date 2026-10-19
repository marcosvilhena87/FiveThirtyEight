import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.calibration import backtest, fit, forecast, load_matches
from src.brasileirao_spi import simulate_calibrated


def games():
    # Um calendário sintético para testar o modelo, não dados oficiais.
    records = []
    for i in range(130):
        day = date.fromordinal(date(2025, 1, 1).toordinal() + i)
        h, a = ("A", "B") if i % 2 else ("B", "A")
        gh, ga = (2, 1) if i % 3 else (0, 0)
        records.append((day,h,a,gh,ga,1.7,0.8))
    return records


class CalibrationTests(unittest.TestCase):
    def test_strict_cutoff_no_future_leakage(self):
        data = games()
        cutoff = date(2025, 3, 1)
        m1 = fit(data, cutoff, iterations=30)
        future = [(date(2025, 8, 1), "A", "B", 40, 0, 30., 0.)]
        m2 = fit(data + future, cutoff, iterations=30)
        self.assertEqual(m1, m2)

    def test_cutoff_excludes_same_day(self):
        data = games()
        cutoff = data[50][0]
        a = fit(data, cutoff, iterations=30)
        altered = [(*r[:3], 80, 0, 80., 0.) if r[0] == cutoff else r for r in data]
        self.assertEqual(a, fit(altered, cutoff, iterations=30))

    def test_xg_changes_rating(self):
        data = games()
        day = date(2025, 6, 1)
        x = fit(data, day, xg_weight=1.0, iterations=50)
        g = fit(data, day, xg_weight=0.0, iterations=50)
        self.assertNotEqual(x["attack"], g["attack"])

    def test_probability_normalization(self):
        m = fit(games(), date(2025,6,1), iterations=30)
        home, away, p = forecast(m, "A", "B")
        self.assertGreater(home, 0)
        self.assertGreater(away, 0)
        self.assertAlmostEqual(sum(p), 1.0)

    def test_backtest_prequential(self):
        rows = backtest(games(), min_train=100, iterations=12)
        self.assertTrue(rows)
        self.assertTrue(all(r["trained_games"] >= 100 for r in rows))
        self.assertTrue(all(r["logloss"] >= 0 for r in rows))

    def test_missing_xg_allowed_and_invalid_pair_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "games.csv"
            path.write_text("date,home,away,home_goals,away_goals,home_xg,away_xg\n2025-01-01,A,B,1,0,,\n",encoding="utf-8")
            self.assertEqual(len(load_matches(path)),1)
            path.write_text("date,home,away,home_goals,away_goals,home_xg,away_xg\n2025-01-01,A,B,1,0,1.0,\n",encoding="utf-8")
            with self.assertRaises(ValueError):
                load_matches(path)

    def test_calibrated_simulator(self):
        clubs={}
        fixtures=[]
        for i in range(0,20,2):
            a,b=f"C{i}",f"C{i+1}"
            clubs[a]=dict(played=36,wins=12,draws=12,losses=12,gf=40,ga=40,points=48)
            clubs[b]=dict(played=36,wins=12,draws=12,losses=12,gf=40,ga=40,points=48)
            fixtures.extend(((a,b),(b,a)))
        model={"mu":0.2,"home":0.15,"attack":{t:0.0 for t in clubs},
               "defense":{t:0.0 for t in clubs}}
        x=simulate_calibrated(clubs,fixtures,model,runs=25,seed=42)
        self.assertAlmostEqual(sum(t["title_probability"] for t in x),1)
        self.assertAlmostEqual(sum(t["relegation_probability"] for t in x),4)


if __name__ == "__main__":
    unittest.main()
