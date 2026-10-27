# Ingestão automática — Série A 2026

O workflow [auto-update-brasileirao.yml](../.github/workflows/auto-update-brasileirao.yml) executa diariamente às 09:20 UTC (06:20 UTC-3), e também manualmente via **Actions > Brasileirão — atualização automática > Run workflow**.

## Configuração obrigatória

1. Cadastre chave em https://www.football-data.org/ e confirme disponibilidade da competição **BSA** para 2026 em seu plano.
2. Em **Settings > Secrets and variables > Actions**, registre `FOOTBALL_DATA_API_KEY`.
3. Autorize escrita do GitHub Actions (`contents: write`) conforme as regras do repositório.

**Sem token, a rotina falha explicitamente e não publica dados.**

## Como funciona

- Obtém partidas da API football-data.org v4.
- Usa como âncora o calendário e classificação preservados em 26/10/2026.
- Incorpora somente resultados com status `FINISHED` e placares válidos, cruzando mandos e adversários.
- Nunca repete jogos já concluídos na âncora. Detecta conflitos, duplicidades e nomes de clubes desconhecidos.
- Audita os 38 jogos por clube, roda 200 mil simulações com o mesmo motor NumPy, salva CSVs e metadados datados.
- Sem novas partidas confirmadas, não altera arquivos.

## Limitações e controles

O processamento depende da cobertura, da atualização e da nomenclatura da API, que podem variar. Teste primeiro via `--dry-run`. Datas da grade-base ainda são provisórias e a classificação de 26/10 deriva de fotografia anterior provisória. O modelo é Poisson inspirado no SPI, **não** o algoritmo oficial FiveThirtyEight nem calibrado por xG. A automação atual faz snapshots incrementais desde 26/10; não reconcilia retroativamente retificações em partidas anteriores à âncora. Para corrigir placares históricos, revise a base e execute uma reconstrução auditada. O agendamento pode ser desativado no GitHub Actions.
