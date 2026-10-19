# FiveThirtyEight — Futebol / Soccer Power Index (SPI)

Repositório de pesquisa sobre dados históricos, variáveis e metodologia de previsão de futebol do **FiveThirtyEight**, com foco em uma futura aplicação ao **Campeonato Brasileiro Série A**.

> **Arquivo histórico:** segundo o repositório oficial, as previsões esportivas deixaram de ser atualizadas em **13/06/2023**. Os arquivos SPI **não representam avaliações de força atualizadas para 2026**. Os links dos CSVs são os endereços publicados pelo FiveThirtyEight; sua disponibilidade atual deve ser verificada antes de qualquer ingestão.

## Fontes

| Fonte | Endereço | Uso |
| --- | --- | --- |
| FiveThirtyEight — dados oficiais | https://github.com/fivethirtyeight/data/tree/master/soccer-spi | Dicionário de dados e links dos CSVs |
| FiveThirtyEight — repositório principal | https://github.com/fivethirtyeight/data | Status do acervo, licença e fontes |
| FiveThirtyEight — metodologia SPI | https://fivethirtyeight.com/methodology/how-our-club-soccer-predictions-work/ | Referência da metodologia |
| FiveThirtyEight-Soccer-Predictions (comunitário) | https://github.com/rvdmaazen/FiveThirtyEight-Soccer-Predictions | Pesquisa sobre histórico de probabilidades |
| Espelho comunitário da documentação | https://github.com/datasets/five-thirty-eight-datasets/tree/main/datasets/soccer-spi | Consulta alternativa |

## CSVs oficiais documentados

| Arquivo | URL original | Conteúdo |
| --- | --- | --- |
| `spi_matches.csv` | https://projects.fivethirtyeight.com/soccer-api/club/spi_matches.csv | SPI e previsões por partida desde 2016 |
| `spi_matches_latest.csv` | https://projects.fivethirtyeight.com/soccer-api/club/spi_matches_latest.csv | Última temporada registrada por liga |
| `spi_global_rankings.csv` | https://projects.fivethirtyeight.com/soccer-api/club/spi_global_rankings.csv | Ranking e ratings de clubes |
| `spi_matches_intl.csv` | https://projects.fivethirtyeight.com/soccer-api/international/spi_matches_intl.csv | Previsões internacionais |
| `spi_global_rankings_intl.csv` | https://projects.fivethirtyeight.com/soccer-api/international/spi_global_rankings_intl.csv | Ranking internacional |

**Importante:** este repositório, nesta etapa, documenta fontes; **não contém cópias dos CSVs**, nem apresenta resultados simulados para 2026.

## Dicionário de dados e plano de modelagem

Consulte [docs/soccer_spi.md](docs/soccer_spi.md) para definições, limitações e roteiro de reprodução das probabilidades por campeonato.

## Aplicação futura ao Brasileirão

1. Obter resultados, classificação, calendário e critérios de desempate da Série A 2026 de fontes atuais e verificáveis.
2. Calibrar estimativas de forças ofensiva e defensiva, mando de campo e gols esperados com resultados históricos disponíveis **antes de cada jogo**.
3. Calcular as probabilidades de vitória/empate/derrota e validar calibração probabilística.
4. Simular os jogos restantes (por exemplo, 100.000 temporadas), atualizando pontos e desempates em cada simulação.
5. Contar frequências de título, vagas internacionais e rebaixamento; registrar data-base, versões, sementes e incertezas.
6. Realizar backtest cronológico e comparar com linhas de base simples (Elo, Poisson e frequência histórica).

Nenhum resultado do SPI histórico deve ser apresentado como probabilidade atual do Brasileirão 2026.

## Atribuição e licenças

A documentação oficial do FiveThirtyEight indica, salvo nota contrária, **CC BY 4.0 para datasets** e **MIT para código**. Atribuir a fonte e revisar a licença específica antes de redistribuir arquivos de terceiros.

Este repositório é um projeto de pesquisa independente, sem afiliação com o FiveThirtyEight.
