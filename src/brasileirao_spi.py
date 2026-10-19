"""Simulador independente inspirado no Soccer Power Index do FiveThirtyEight.

Usa apenas a biblioteca padrão. Não implementa os ratings proprietários oficiais.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter
from pathlib import Path


def read_table(path, required):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or not set(required).issubset(rows[0]):
        raise ValueError(f"{path}: cabeçalhos obrigatórios: {required}")
    return rows


def read_standings(path):
    rows = read_table(path, ["team", "played", "wins", "draws", "losses", "gf", "ga"])
    clubs = {}
    for row in rows:
        name = row["team"].strip()
        if not name or name in clubs:
            raise ValueError("Nome de clube vazio ou duplicado")
        stats = {key: int(row[key]) for key in ("played", "wins", "draws", "losses", "gf", "ga")}
        if any(x < 0 for x in stats.values()):
            raise ValueError(f"{name}: estatística negativa")
        if stats["played"] != stats["wins"] + stats["draws"] + stats["losses"]:
            raise ValueError(f"{name}: J != V+E+D")
        stats["points"] = 3 * stats["wins"] + stats["draws"]
        clubs[name] = stats
    return clubs


def read_fixtures(path, teams):
    fixtures = []
    seen = set()
    for row in read_table(path, ["home", "away"]):
        home, away = row["home"].strip(), row["away"].strip()
        if home not in teams or away not in teams or home == away:
            raise ValueError(f"Partida inválida: {home} x {away}")
        key = (home, away)
        if key in seen:
            raise ValueError(f"Jogo duplicado: {home} x {away}")
        seen.add(key)
        fixtures.append((home, away))
    return fixtures


def validate_schedule(clubs, fixtures, season_games=38):
    if len(clubs) != 20:
        raise ValueError("Série A requer exatamente 20 clubes")
    remaining = Counter()
    for home, away in fixtures:
        remaining[home] += 1
        remaining[away] += 1
    for name, s in clubs.items():
        if s["played"] + remaining[name] != season_games:
            raise ValueError(f"{name}: {s['played']} disputados + {remaining[name]} pendentes != {season_games}")
    expected = sum(season_games - s["played"] for s in clubs.values()) // 2
    if len(fixtures) != expected:
        raise ValueError(f"Esperados {expected} confrontos restantes; recebidos {len(fixtures)}")


def ratings(clubs, shrink=8.0):
    if shrink < 0:
        raise ValueError("shrink deve ser não negativo")
    games = sum(s["played"] for s in clubs.values())
    if games == 0:
        raise ValueError("Não há partidas disputadas")
    avg = sum(s["gf"] for s in clubs.values()) / games
    if avg <= 0:
        raise ValueError("Média de gols inválida")
    return avg, {
        name: ((s["gf"] + shrink * avg) / (s["played"] + shrink),
               (s["ga"] + shrink * avg) / (s["played"] + shrink))
        for name, s in clubs.items()
    }


def expected_goals(home, away, avg, strength, home_multiplier=1.246, away_multiplier=0.803):
    h_attack, h_defense = strength[home]
    a_attack, a_defense = strength[away]
    return (max(0.001, h_attack * a_defense / avg * home_multiplier),
            max(0.001, a_attack * h_defense / avg * away_multiplier))


def poisson(rng, lam):
    """Amostragem Poisson de Knuth: adequada a médias de gols pequenas."""
    threshold = math.exp(-lam)
    k, product = 0, 1.0
    while product > threshold:
        k += 1
        product *= rng.random()
    return k - 1


def match_probabilities(lam_home, lam_away, max_goals=20):
    """Matriz Poisson com caudas agregadas à última faixa."""
    def pmf(lam):
        vals = [math.exp(-lam)]
        for i in range(1, max_goals):
            vals.append(vals[-1] * lam / i)
        vals.append(max(0.0, 1.0 - sum(vals)))
        return vals
    h, a = pmf(lam_home), pmf(lam_away)
    win = sum(p * q for i, p in enumerate(h) for j, q in enumerate(a) if i > j)
    draw = sum(p * q for i, p in enumerate(h) for j, q in enumerate(a) if i == j)
    return win, draw, 1 - win - draw


def rank(s):
    # Brasileirão: pontos, vitórias, saldo e gols marcados.
    # Empates remanescentes usam sorteio determinístico do RNG.
    return (s["points"], s["wins"], s["gf"] - s["ga"], s["gf"])


def simulate(clubs, fixtures, runs=100_000, seed=42, shrink=8.0,
             home_multiplier=1.246, away_multiplier=0.803):
    if runs <= 0:
        raise ValueError("runs deve ser positivo")
    validate_schedule(clubs, fixtures)
    avg, strength = ratings(clubs, shrink)
    match_lambdas = [
        (h, a, *expected_goals(h, a, avg, strength, home_multiplier, away_multiplier))
        for h, a in fixtures
    ]
    rng = random.Random(seed)
    counts = {name: {"champion": 0, "relegated": 0, "top4": 0, "points_sum": 0,
                      "position_sum": 0} for name in clubs}
    for _ in range(runs):
        state = {name: s.copy() for name, s in clubs.items()}
        for home, away, lh, la in match_lambdas:
            gh, ga = poisson(rng, lh), poisson(rng, la)
            hs, aws = state[home], state[away]
            hs["played"] += 1
            aws["played"] += 1
            hs["gf"] += gh
            hs["ga"] += ga
            aws["gf"] += ga
            aws["ga"] += gh
            if gh > ga:
                hs["wins"] += 1
                hs["points"] += 3
                aws["losses"] += 1
            elif gh < ga:
                aws["wins"] += 1
                aws["points"] += 3
                hs["losses"] += 1
            else:
                hs["draws"] += 1
                aws["draws"] += 1
                hs["points"] += 1
                aws["points"] += 1
        # Ordem aleatória apenas no último nível não modelado dos desempates.
        ordering = list(state)
        rng.shuffle(ordering)
        ordering.sort(key=lambda name: rank(state[name]), reverse=True)
        for pos, name in enumerate(ordering, 1):
            c = counts[name]
            c["champion"] += pos == 1
            c["relegated"] += pos >= 17
            c["top4"] += pos <= 4
            c["points_sum"] += state[name]["points"]
            c["position_sum"] += pos
    return sorted(
        [{"team": name,
          "title_probability": c["champion"] / runs,
          "relegation_probability": c["relegated"] / runs,
          "top4_probability": c["top4"] / runs,
          "expected_points": c["points_sum"] / runs,
          "expected_position": c["position_sum"] / runs}
         for name, c in counts.items()],
        key=lambda x: x["expected_position"]
    )



def simulate_calibrated(clubs, fixtures, model, runs=100_000, seed=42):
    """Simula temporada usando lambdas ajustados pelo histórico jogo a jogo."""
    from src.calibration import forecast
    if runs <= 0:
        raise ValueError("runs deve ser positivo")
    validate_schedule(clubs, fixtures)
    fixtures_lambda = [(h, a, *forecast(model, h, a)[:2]) for h, a in fixtures]
    rng = random.Random(seed)
    counts = {t: {"title": 0, "relegation": 0, "top4": 0,
                  "points": 0, "position": 0} for t in clubs}
    for _ in range(runs):
        state = {t: dict(stats) for t, stats in clubs.items()}
        for h, a, lh, la in fixtures_lambda:
            gh, ga = poisson(rng, lh), poisson(rng, la)
            x, y = state[h], state[a]
            x["gf"] += gh
            x["ga"] += ga
            y["gf"] += ga
            y["ga"] += gh
            if gh > ga:
                x["wins"] += 1
                x["points"] += 3
            elif gh < ga:
                y["wins"] += 1
                y["points"] += 3
            else:
                x["points"] += 1
                y["points"] += 1
        order = list(state)
        rng.shuffle(order)
        order.sort(key=lambda t: rank(state[t]), reverse=True)
        for i, team in enumerate(order):
            c = counts[team]
            c["title"] += i == 0
            c["relegation"] += i >= 16
            c["top4"] += i < 4
            c["points"] += state[team]["points"]
            c["position"] += i+1
    return sorted(({"team": t, "title_probability": c["title"]/runs,
                    "relegation_probability": c["relegation"]/runs,
                    "top4_probability": c["top4"]/runs,
                    "expected_points": c["points"]/runs,
                    "expected_position": c["position"]/runs}
                   for t,c in counts.items()), key=lambda d: d["expected_position"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Monte Carlo Brasileirão 2026 — SPI aproximado")
    parser.add_argument("--standings", required=True, type=Path)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--runs", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("results/probabilities.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("results/metadata.json"))
    parser.add_argument("--as-of", required=True, help="Data-base YYYY-MM-DD")
    parser.add_argument("--calibrated-model", type=Path, help="JSON gerado por src.calibration; anterior à data-base")
    args = parser.parse_args(argv)
    clubs = read_standings(args.standings)
    fixtures = read_fixtures(args.fixtures, clubs)
    if args.calibrated_model:
        from datetime import date, timedelta
        from src.calibration import forecast
        payload = json.loads(args.calibrated_model.read_text(encoding="utf-8"))
        if date.fromisoformat(payload["cutoff"]) > date.fromisoformat(args.as_of) + timedelta(days=1):
            raise ValueError("Modelo posterior à data-base: risco de vazamento temporal")
        model = payload["model"]
        missing = set(clubs) - set(model["attack"])
        if missing:
            raise ValueError(f"Modelo sem histórico para clubes: {sorted(missing)}")
        result = simulate_calibrated(clubs, fixtures, model, args.runs, args.seed)
    else:
        result = simulate(clubs, fixtures, args.runs, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)
    meta = {"as_of": args.as_of, "calibrated_model": str(args.calibrated_model) if args.calibrated_model else None, "standings": str(args.standings),
            "fixtures": str(args.fixtures), "runs": args.runs, "seed": args.seed,
            "model": "SPI-inspired Poisson independent-goals, shrink=8, home=1.246, away=0.803",
            "caveat": "Não é um modelo oficial FiveThirtyEight; ratings não se atualizam jogo a jogo."}
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in result:
        print(f"{row['team']:<18} titulo={row['title_probability']:.2%} queda={row['relegation_probability']:.2%} pts={row['expected_points']:.1f}")


if __name__ == "__main__":
    main()
