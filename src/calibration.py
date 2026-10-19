"""Calibração cronológica de ataque/defesa/mando com gols e xG opcionais.

Modelo independente inspirado no SPI, sem dependências externas.
Uma predição de uma data usa exclusivamente jogos de datas anteriores.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path

from src.brasileirao_spi import match_probabilities, read_table


def load_matches(path):
    required = ["date", "home", "away", "home_goals", "away_goals", "home_xg", "away_xg"]
    data = []
    seen = set()
    for row in read_table(path, required):
        day = date.fromisoformat(row["date"])
        home, away = row["home"].strip(), row["away"].strip()
        if not home or not away or home == away:
            raise ValueError("Clubes inválidos")
        key = (day, home, away)
        if key in seen:
            raise ValueError(f"Jogo duplicado: {key}")
        seen.add(key)
        gh, ga = int(row["home_goals"]), int(row["away_goals"])
        if min(gh, ga) < 0:
            raise ValueError("Gols negativos")
        xgs = []
        for field in ("home_xg", "away_xg"):
            raw = (row[field] or "").strip()
            xg = float(raw) if raw else None
            if xg is not None and (not math.isfinite(xg) or xg < 0):
                raise ValueError(f"xG inválido: {field}")
            xgs.append(xg)
        if (xgs[0] is None) != (xgs[1] is None):
            raise ValueError("xG deve existir para ambos os clubes ou nenhum")
        data.append((day, home, away, gh, ga, *xgs))
    return sorted(data, key=lambda r: (r[0], r[1], r[2]))


def fit(matches, cutoff, *, xg_weight=0.7, decay_days=365.0,
        iterations=300, learning_rate=0.025, regularization=1.5):
    """Ajusta Poisson log-linear com efeito de mando e shrinkage L2.

    lam_home = exp(mu + home_adv + attack_home - defense_away)
    lam_away = exp(mu + attack_away - defense_home)
    Observação composta: (1-w)*gols + w*xG quando disponível.
    """
    if not 0 <= xg_weight <= 1 or decay_days <= 0 or regularization < 0:
        raise ValueError("Hiperparâmetros inválidos")
    history = [m for m in matches if m[0] < cutoff]
    teams = sorted({t for m in history for t in (m[1], m[2])})
    if not history:
        return {"mu": math.log(1.25), "home": math.log(1.15),
                "attack": {}, "defense": {}, "trained_games": 0}
    attack = {t: 0.0 for t in teams}
    defense = {t: 0.0 for t in teams}
    # baseline da liga recalculada apenas sobre treinos anteriores ao corte
    mu = math.log(max(0.1, sum(m[3] + m[4] for m in history) / (2 * len(history))))
    home_adv = math.log(1.15)
    for _ in range(iterations):
        grad_a = {t: 0.0 for t in teams}
        grad_d = {t: 0.0 for t in teams}
        grad_mu = grad_h = 0.0
        total_weight = 0.0
        for day, home, away, gh, ga, xh, xa in history:
            w = math.exp(-math.log(2) * (cutoff - day).days / decay_days)
            total_weight += w
            yh = gh if xh is None else (1-xg_weight)*gh + xg_weight*xh
            ya = ga if xa is None else (1-xg_weight)*ga + xg_weight*xa
            lh = math.exp(max(-5, min(5, mu+home_adv+attack[home]-defense[away])))
            la = math.exp(max(-5, min(5, mu+attack[away]-defense[home])))
            eh, ea = w*(yh-lh), w*(ya-la)
            grad_a[home] += eh
            grad_a[away] += ea
            grad_d[away] -= eh
            grad_d[home] -= ea
            grad_mu += eh+ea
            grad_h += eh
        scale = learning_rate / max(1.0, total_weight)
        for t in teams:
            attack[t] += scale*(grad_a[t]-regularization*attack[t])
            defense[t] += scale*(grad_d[t]-regularization*defense[t])
        # Identificabilidade: centralizar os vetores de efeito
        am = sum(attack.values())/len(teams)
        dm = sum(defense.values())/len(teams)
        attack = {t: v-am for t,v in attack.items()}
        defense = {t: v-dm for t,v in defense.items()}
        mu += scale*grad_mu
        home_adv += scale*(grad_h-regularization*home_adv)
        mu = max(-2, min(2, mu))
        home_adv = max(-1, min(1, home_adv))
    return {"mu": mu, "home": home_adv, "attack": attack,
            "defense": defense, "trained_games": len(history)}


def forecast(model, home, away):
    mu, h = model["mu"], model["home"]
    lh = math.exp(mu+h+model["attack"].get(home, 0.0)-model["defense"].get(away,0.0))
    la = math.exp(mu+model["attack"].get(away,0.0)-model["defense"].get(home,0.0))
    return lh, la, match_probabilities(lh, la)


def backtest(matches, min_train=100, **kwargs):
    """Rolling-origin em blocos de dia; nunca treina com partidas do mesmo dia."""
    rows = []
    for day in sorted({m[0] for m in matches}):
        history_count = sum(m[0] < day for m in matches)
        if history_count < min_train:
            continue
        model = fit(matches, day, **kwargs)
        for m in matches:
            if m[0] != day:
                continue
            _, home, away, gh, ga, xh, xa = m
            lh, la, (p1, px, p2) = forecast(model, home, away)
            actual = (1,0,0) if gh > ga else (0,1,0) if gh == ga else (0,0,1)
            probs = (p1,px,p2)
            brier = sum((p-y)**2 for p,y in zip(probs,actual))
            logloss = -math.log(max(1e-12, probs[actual.index(1)]))
            rows.append({"date":day.isoformat(),"home":home,"away":away,
                         "p_home":p1,"p_draw":px,"p_away":p2,
                         "exp_home_goals":lh,"exp_away_goals":la,
                         "actual":("H","D","A")[actual.index(1)],
                         "brier":brier,"logloss":logloss,
                         "trained_games":history_count})
    return rows


def main(argv=None):
    p=argparse.ArgumentParser(description="Calibração e backtest sem vazamento temporal")
    p.add_argument("--matches",type=Path,required=True)
    p.add_argument("--cutoff",required=True,help="YYYY-MM-DD exclusivo")
    p.add_argument("--min-train",type=int,default=100)
    p.add_argument("--xg-weight",type=float,default=0.7)
    p.add_argument("--decay-days",type=float,default=365)
    p.add_argument("--output-dir",type=Path,default=Path("results/calibration"))
    args=p.parse_args(argv)
    games=load_matches(args.matches)
    cutoff=date.fromisoformat(args.cutoff)
    training=[m for m in games if m[0]<cutoff]
    settings={"xg_weight":args.xg_weight,"decay_days":args.decay_days}
    model=fit(games,cutoff,**settings)
    validation=backtest(training,min_train=args.min_train,**settings)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    with (args.output_dir/"model.json").open("w",encoding="utf-8") as f:
        json.dump({"cutoff":str(cutoff),"parameters":settings,"model":model},f,indent=2,ensure_ascii=False)
    if validation:
        with (args.output_dir/"backtest.csv").open("w",newline="",encoding="utf-8") as f:
            wr=csv.DictWriter(f,fieldnames=list(validation[0]))
            wr.writeheader()
            wr.writerows(validation)
    scores={"evaluated":len(validation),
            "mean_brier":sum(x["brier"] for x in validation)/len(validation) if validation else None,
            "mean_logloss":sum(x["logloss"] for x in validation)/len(validation) if validation else None,
            "warning":"Sem jogos suficientes para backtest" if not validation else None}
    (args.output_dir/"metrics.json").write_text(json.dumps(scores,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(scores,indent=2))


if __name__=="__main__":
    main()
