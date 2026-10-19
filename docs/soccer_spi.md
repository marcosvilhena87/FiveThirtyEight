# Dados de futebol — FiveThirtyEight SPI

## Escopo e proveniência

Fonte primária: [fivethirtyeight/data — soccer-spi](https://github.com/fivethirtyeight/data/blob/master/soccer-spi/README.md).

O SPI (Soccer Power Index) produzia avaliações de força e previsões probabilísticas por partida. Segundo a fonte oficial, a atualização de previsões esportivas terminou em **13 de junho de 2023**. Os CSVs são históricos; nem o funcionamento atual dos links nem a integridade de um download foram testados nesta documentação.

## Esquema dos arquivos de partidas

| Campo | Interpretação |
| --- | --- |
| `season`, `date` | Temporada e data da partida |
| `league_id`, `league` | Identificação da competição |
| `team1`, `team2` | Mandante e visitante |
| `spi1`, `spi2` | SPI pré-jogo de cada equipe |
| `prob1`, `prob2`, `probtie` | Probabilidades de vitória mandante, visitante e empate |
| `proj_score1`, `proj_score2` | Projeções de gols de cada equipe |
| `importance1`, `importance2` | Importância estimada (escala 0–100) |
| `score1`, `score2` | Gols efetivamente marcados |
| `xg1`, `xg2` | Expected goals (xG) |
| `nsxg1`, `nsxg2` | Non-shot expected goals |
| `adj_score1`, `adj_score2` | Gols ajustados por contexto de jogo |

### Arquivos de ranking

`rank`, `prev_rank`, `name`, `league`, `off`, `def` e `spi`.

**Cuidado:** `off` e `def` são indicadores de força ofensiva e defensiva do SPI, não contagens de gols. `proj_score` descreve expectativa pré-jogo; `xg` e `nsxg` descrevem informações observadas da partida, não devem entrar como preditores pré-jogo para esse mesmo confronto.

## Requisitos para reconstruir um simulador de classificação

Os CSVs SPI fornecem principalmente previsões **por jogo**, não constituem, isoladamente, um motor completo de probabilidade de classificação final. Para um campeonato com jogos restantes:

1. Registrar data de corte e tabela oficial naquele momento.
2. Usar somente informação disponível nessa data na estimativa de `P(casa)`, `P(empate)`, `P(fora)` e, se necessário, distribuição de placares.
3. Validar `P(casa) + P(empate) + P(fora) ≈ 1` e tratar valores ausentes.
4. Simular o calendário restante com sorteios reproduzíveis; gerar placares coerentes se forem necessários saldo de gols e gols pró como desempates.
5. Aplicar o regulamento oficial de classificação e desempate da edição.
6. Para cada equipe, dividir as ocorrências do evento pelo número de simulações: campeão, vaga internacional ou rebaixado.
7. Informar margem de erro Monte Carlo, dados de entrada, calibração e hipóteses; 100 mil simulações reduzem o erro amostral, mas **não eliminam erro de modelo**.

### Validação recomendada

- Separação temporal treino/teste e backtest por rodada, sem vazamento de informação futura.
- Brier score, log loss e gráficos de calibração das probabilidades 1–X–2.
- Verificação de desempenho versus Elo simples e Poisson mandante/visitante.
- Avaliação separada de previsão de partidas e previsão dos eventos finais (título/rebaixamento).
- Documentação de fonte, licença, versão e data de extração.

## Referências

- [Dados oficiais](https://github.com/fivethirtyeight/data/tree/master/soccer-spi)
- [Metodologia original](https://fivethirtyeight.com/methodology/how-our-club-soccer-predictions-work/)
- [Histórico da descontinuação e licença](https://github.com/fivethirtyeight/data)
- [Projeto comunitário](https://github.com/rvdmaazen/FiveThirtyEight-Soccer-Predictions)
