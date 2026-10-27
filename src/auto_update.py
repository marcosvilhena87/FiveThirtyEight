"""Incremental Brasileirão updater from football-data.org v4.

Requires FOOTBALL_DATA_API_KEY. Never invents scores or pending fixtures.
The frozen 2026-10-26 snapshot anchors incremental updates.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from collections import Counter

from src.brasileirao_spi import read_standings, read_fixtures, validate_schedule
from src.simulate_numpy import simulate_numpy

BASE = Path("data/brasileirao_2026")
OUT = Path("results/brasileirao_2026")
BASE_DATE = "2026-10-26"
API = "https://api.football-data.org/v4/competitions/BSA/matches?season=2026"
ALIASES = {
    "Flamengo": "Flamengo", "Palmeiras": "Palmeiras",
    "Athletico-PR": "Athletico-PR", "Athletico Paranaense": "Athletico-PR",
    "Athletico": "Athletico-PR", "Cruzeiro": "Cruzeiro",
    "Fluminense": "Fluminense", "Atlético-MG": "Atlético-MG",
    "Atlético Mineiro": "Atlético-MG", "Atletico Mineiro": "Atlético-MG",
    "Bahia": "Bahia", "Santos": "Santos", "São Paulo": "São Paulo",
    "Bragantino": "Bragantino", "Red Bull Bragantino": "Bragantino",
    "RB Bragantino": "Bragantino", "Botafogo": "Botafogo",
    "Coritiba": "Coritiba", "Vitória": "Vitória", "Vitoria": "Vitória",
    "Mirassol": "Mirassol", "Vasco": "Vasco", "Vasco da Gama": "Vasco",
    "Corinthians": "Corinthians", "Internacional": "Internacional",
    "Grêmio": "Grêmio", "Gremio": "Grêmio", "Remo": "Remo",
    "Chapecoense": "Chapecoense",
}

def identify(team):
    name = team.get("shortName") or team.get("name") or ""
    if name in ALIASES:
        return ALIASES[name]
    full = team.get("name") or ""
    simplified = full.replace(" FC", "").replace(" SAF", "").replace(" EC", "")
    if simplified in ALIASES:
        return ALIASES[simplified]
    raise ValueError(f"Nome de clube não mapeado: {team!r}")

def load_api():
    token = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not token:
        raise RuntimeError("FOOTBALL_DATA_API_KEY não configurada")
    req = Request(API, headers={"X-Auth-Token": token, "Accept": "application/json",
                                "User-Agent": "FiveThirtyEight-Brasileirao-2026/1.0"})
    with urlopen(req, timeout=30) as response:
        raw = response.read(3_000_000)
    obj = json.loads(raw)
    if not isinstance(obj.get("matches"), list):
        raise ValueError("Resposta da API sem lista matches")
    return obj["matches"]

def rows_as_csv(rows, fields):
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue()

def run(matches, *, runs=200000, seed=42, dry_run=False):
    prev = read_standings(BASE / f"standings_{BASE_DATE}.csv")
    with (BASE / f"fixtures_{BASE_DATE}.csv").open(encoding="utf-8", newline="") as f:
        pending = list(csv.DictReader(f))
    expected = {(r["home"], r["away"]): r for r in pending}
    if len(expected) != len(pending):
        raise ValueError("Calendário base tem jogos duplicados")
    finalized = {}
    for item in matches:
        home, away = identify(item["homeTeam"]), identify(item["awayTeam"])
        key = home, away
        if key not in expected:
            continue  # matches prior to the baseline must not be replayed
        if item.get("status") != "FINISHED":
            continue
        score = item.get("score", {}).get("fullTime", {})
        hg, ag = score.get("home"), score.get("away")
        if not isinstance(hg, int) or not isinstance(ag, int) or min(hg, ag) < 0:
            raise ValueError(f"Placar inválido: {key}")
        if key in finalized and finalized[key] != (hg, ag):
            raise ValueError(f"Placar conflitante: {key}")
        finalized[key] = hg, ag
    if not finalized:
        print("Nenhum novo resultado confirmado; sem atualização")
        return False
    for (h, a), (hg, ag) in finalized.items():
        for team, gf, ga in ((h, hg, ag), (a, ag, hg)):
            s = prev[team]
            s["played"] += 1
            s["gf"] += gf
            s["ga"] += ga
            s["wins" if gf > ga else "draws" if gf == ga else "losses"] += 1
            s["points"] = s["wins"] * 3 + s["draws"]
    fixtures = [r for r in pending if (r["home"], r["away"]) not in finalized]
    validate_schedule(prev, [(r["home"], r["away"]) for r in fixtures])
    # Every final recognized by the provider must appear in the frozen pending schedule.
    # Do not publish if provider has incomplete or inconsistent league coverage.
    as_of = datetime.now(timezone.utc).date().isoformat()
    base = BASE / f"standings_{as_of}.csv"
    fixture_path = BASE / f"fixtures_{as_of}.csv"
    probability_path = OUT / f"probabilities_{as_of}.csv"
    metadata_path = OUT / f"metadata_{as_of}.json"
    if any(p.exists() for p in (base, fixture_path, probability_path, metadata_path)):
        raise RuntimeError("Data-base já existe; não sobrescrever: " + as_of)
    if dry_run:
        print(f"DRY RUN: {len(finalized)} finais novos, {len(fixtures)} jogos pendentes")
        return True
    result = simulate_numpy(prev, [(r["home"], r["away"]) for r in fixtures], runs=runs, seed=seed)
    standings_rows = [{"team": team, **{k: s[k] for k in
                      ("played", "wins", "draws", "losses", "gf", "ga")}}
                      for team, s in prev.items()]
    BASE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    base.write_text(rows_as_csv(standings_rows,
                    ["team", "played", "wins", "draws", "losses", "gf", "ga"]), encoding="utf-8")
    fixture_path.write_text(rows_as_csv(fixtures, list(pending[0])), encoding="utf-8")
    probability_path.write_text(rows_as_csv(result, list(result[0])), encoding="utf-8")
    metadata_path.write_text(json.dumps({
        "as_of": as_of, "previous_snapshot": BASE_DATE,
        "provider": API, "confirmed_new_results": [
            {"home": h, "away": a, "home_goals": hg, "away_goals": ag}
            for (h, a), (hg, ag) in sorted(finalized.items())
        ], "remaining_fixtures": len(fixtures), "runs": runs, "seed": seed,
        "model": "Independent Poisson; shrink=8; home=1.246; away=0.803",
        "warning": "SPI-inspired experimental estimate, not official FiveThirtyEight"
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Atualização {as_of}: {len(finalized)} finais, {len(fixtures)} pendentes")
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=200000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--input-json", type=Path, help="Offline fixture for auditing/tests")
    args = p.parse_args()
    matches = json.loads(args.input_json.read_text(encoding="utf-8"))["matches"] if args.input_json else load_api()
    run(matches, runs=args.runs, seed=args.seed, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
