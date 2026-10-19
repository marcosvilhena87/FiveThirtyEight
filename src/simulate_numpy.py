"""Reprodução vetorizada do cenário publicado para o Brasileirão 2026.

Requer numpy. Usa os mesmos lambdas Poisson do simulador básico.
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np

from src.brasileirao_spi import read_standings, read_fixtures, validate_schedule, ratings, expected_goals


def simulate_numpy(standings, fixtures, runs=200000, seed=42):
    validate_schedule(standings, fixtures)
    if runs <= 0:
        raise ValueError("runs deve ser positivo")
    teams = list(standings)
    idx = {t: i for i, t in enumerate(teams)}
    avg, strength = ratings(standings, shrink=8)
    rng = np.random.default_rng(seed)
    points = np.tile(np.array([standings[t]["points"] for t in teams]), (runs, 1))
    wins = np.tile(np.array([standings[t]["wins"] for t in teams]), (runs, 1))
    gf = np.tile(np.array([standings[t]["gf"] for t in teams]), (runs, 1))
    ga = np.tile(np.array([standings[t]["ga"] for t in teams]), (runs, 1))
    for home, away in fixtures:
        h, a = idx[home], idx[away]
        lh, la = expected_goals(home, away, avg, strength)
        gh, ag = rng.poisson(lh, runs), rng.poisson(la, runs)
        points[:, h] += 3*(gh > ag) + (gh == ag)
        points[:, a] += 3*(ag > gh) + (gh == ag)
        wins[:, h] += (gh > ag)
        wins[:, a] += (ag > gh)
        gf[:, h] += gh
        ga[:, h] += ag
        gf[:, a] += ag
        ga[:, a] += gh

    tie = rng.random((runs, len(teams)))
    order = np.lexsort((tie.T, gf.T, (gf-ga).T, wins.T, points.T), axis=0)[::-1].T
    positions = np.empty((runs, len(teams)), dtype=np.uint8)
    row = np.arange(runs)
    for pos in range(len(teams)):
        positions[row, order[:, pos]] = pos + 1
    output = []
    for j, team in enumerate(teams):
        p = positions[:, j]
        output.append(dict(
            team=team,
            title_probability=float(np.mean(p == 1)),
            relegation_probability=float(np.mean(p >= 17)),
            top4_probability=float(np.mean(p <= 4)),
            expected_points=float(points[:, j].mean()),
            expected_position=float(p.mean())
        ))
    return sorted(output, key=lambda r: r["expected_position"])


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--standings", required=True)
    cli.add_argument("--fixtures", required=True)
    cli.add_argument("--runs", type=int, default=200000)
    cli.add_argument("--seed", type=int, default=42)
    cli.add_argument("--output", default="results/brasileirao_2026/probabilities_reproduced.csv")
    args = cli.parse_args()
    standings = read_standings(args.standings)
    fixtures = read_fixtures(args.fixtures, standings)
    results = simulate_numpy(standings, fixtures, args.runs, args.seed)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(results)
    print(f"{len(results)} clubes; {len(fixtures)} partidas; {args.runs} simulações; {output}")


if __name__ == "__main__":
    main()
