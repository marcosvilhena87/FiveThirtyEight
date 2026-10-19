# Calibração temporal de ataque, defesa e mando

Implementação: [src/calibration.py](../src/calibration.py). Modelo **independente inspirado no FiveThirtyEight**, não reprodução da engenharia proprietária SPI.

## CSV por jogo

`date,home,away,home_goals,away_goals,home_xg,away_xg`

- `date`: ISO `YYYY-MM-DD`, data real da disputa.
- `home`/`away`: mesma grafia de clubes da tabela.
- `home_goals`/`away_goals`: gols reais, inteiros não negativos.
- `home_xg`/`away_xg`: xG **pré-definido por provedor identificado**, não estimativa inventada. Ambos vazios se indisponíveis.
- Nunca incluir jogos futuros ou resultados além do instante de referência; partidas adiadas são ordenadas pela data jogada.
- Fontes devem registrar URL, provedor, licença, data de obtenção, versão e cobertura. Não inferir xG de gols.
- Não misturar provedores de xG sem mapear definições; marcar eventuais mudanças metodológicas.

Exemplo **sintético, não histórico**: [matches_example.csv](../data/examples/matches_example.csv).

## Treinamento e validação

```bash
python -m src.calibration --matches dados_verificados.csv --cutoff 2026-10-19 --min-train 100 --output-dir results/calibration
python -m src.brasileirao_spi --standings data/brasileirao_2026/standings_2026-10-18.csv --fixtures data/brasileirao_2026/fixtures_2026-10-18.csv --as-of 2026-10-18 --calibrated-model results/calibration/model.json --runs 200000 --seed 42
python -m unittest discover -s tests -v
```

**Atenção à data-base:** para prever ao fim de 18/10/2026, o parâmetro `--cutoff` deve ser `2026-10-19` (exclusivo), cobrindo partidas jogadas até 18/10. O CLI do simulador permite modelos cuja data de corte seja no máximo igual à data-base; para um corte exclusivo no dia seguinte, esta verificação deve ser ajustada para confirmar que a última partida do treino não excede a data-base. Até isso ser feito, não usar a integração automática para o corte do dia seguinte.

O programa usa regressão Poisson log-linear com:
- `log(lambda_home) = mu + mando + ataque_home - defesa_away`
- `log(lambda_away) = mu + ataque_away - defesa_home`
- Alvo = `(1-w)*gols + w*xG` quando xG disponível; somente gols se ausente.
- Meia-vida temporal em dias para ponderar jogos históricos, por padrão 365.
- Regularização L2 para reduzir sobreajuste; parâmetros configuráveis.
- Rolling-origin por **dia completo**: previsão de partidas no dia D usa apenas partidas anteriores a D.
- Brier multiclasse e log-loss médios em holdout cronológico.
- Sem otimização dos hiperparâmetros no período de avaliação: testar valores em janela de validação anterior e só depois avaliar em janela futura separada.

**Limitações:** modelo não representa os adjusted goals nem non-shot xG do SPI original; otimização iterativa e hiperparâmetros iniciais não foram calibrados empiricamente; em equipes promovidas sem dados anteriores o histórico precisa incluir temporadas anteriores. As probabilidades precisam ser avaliadas contra baselines de Elo/Poisson antes de produção. O código ainda não baixa jogos ou xG automaticamente.
