# Brasileirão 2026 — simulador Monte Carlo

O módulo `src/brasileirao_spi.py` é uma aproximação independente do FiveThirtyEight SPI, e **não** o modelo oficial. Modela gols marcados e sofridos suavizados em direção à média da liga por oito partidas; combinação multiplicativa ataque/defesa e ajuste de mando; gols independentes via Poisson. Não usa xG, atletas, ligas internacionais, fatores de importância ou evolução dos ratings jogo a jogo.

## Dados / proveniência

- `standings_2026-10-18.csv` é uma transcrição da classificação discutida em 18/10/2026, **provisória e sujeita a auditoria com ge/CBF**.
- O arquivo `fixtures_template.csv` contém apenas o cabeçalho **intencionalmente**. É necessário reunir e verificar o calendário restante na fonte original antes de gerar qualquer probabilidade. O programa não cria jogos automaticamente.
- Cada linha dos fixtures deve ter `home,away`, com os nomes exatamente iguais à coluna `team` da classificação; adicionar somente jogos ainda não disputados na data-base. Não duplicar partidas. Para 18/10/2026, há 72 partidas pendentes segundo a transcrição: 16 times com 31 jogos e quatro com 30.
- O script rejeita uma entrada quando um clube não atinge 38 jogos somando realizados e pendentes. Isso verifica **quantidades**, não comprova que os adversários ou mandos estejam corretos. Verificar também cada confronto na fonte.
- Os critérios de desempate simulados são pontos, vitórias, saldo e gols pró. Os critérios seguintes são aproximados por sorteio em caso de igualdade; por isso um empate completo nos quatro critérios não reproduz integralmente o regulamento da CBF.

## Executar

Requer Python 3.10+; nenhuma dependência externa.

```bash
python -m unittest discover -s tests -v
python -m src.brasileirao_spi \
  --standings data/brasileirao_2026/standings_2026-10-18.csv \
  --fixtures data/brasileirao_2026/fixtures_2026-10-18.csv \
  --as-of 2026-10-18 --runs 200000 --seed 42
```

O comando gera `results/probabilities.csv` e `results/metadata.json` quando um calendário auditado existir. Até que o arquivo de fixtures seja preenchido, ele deve **falhar com erro**, e não produzir probabilidades fictícias.

## Fórmulas

- Gols médios por clube = `(GF + 8 * media_liga)/(J + 8)`; mesma expressão para os gols sofridos.
- `lambda_casa = ataque_casa * defesa_visitante / media_liga * 1.246`
- `lambda_fora = ataque_fora * defesa_casa / media_liga * 0.803`
- Gols amostrados de Poisson independente, sem inflação de empate. A probabilidade exata de cada placar pode ser consultada via `match_probabilities`.
- Percentuais estimados = proporção das simulações que produzem o evento. Não equivalem às previsões oficiais históricas do FiveThirtyEight.

Os multiplicadores são hipóteses explícitas a calibrar com jogos históricos (sem vazamento de dados futuros). Recomendam-se: calibração temporal de mando, xG, validação com Brier/log-loss e registro de CSV e checksums das fontes.
