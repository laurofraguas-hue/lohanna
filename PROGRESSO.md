# PROGRESSO — Painéis de candidatos aliados

Atualizado: 2026-09-06 · Branch `claude/electoral-panel-allied-candidates-wfput7`

## Estado: PAUSADO no passo 1 — aguardando dados e validação

Nenhum painel gerado. O passo 1 (inventário) foi concluído até onde o ambiente permite:
ver `INVENTARIO.md` para o relatório completo.

## Concluído

- Painel de referência lido integralmente e destrinchado (estrutura, CSS, esquema real do `DATA`, faixas de cor, bibliotecas embutidas).
- Bibliotecas e estilos extraídos para `lib/` (Leaflet 1.9.4, Chart.js, CSS do Leaflet, CSS do painel) — prontos para embutir nos novos painéis, mantendo o requisito 100% offline.
- Planilha de candidatos baixada e auditada célula a célula: 10 candidatos, 10 municípios, 4 colunas.
- Granularidade da coluna `Votos` respondida em definitivo (ver abaixo).
- Pasta do Drive inventariada: 3 arquivos, ~307 MB.

## Em andamento

Nada. Bloqueado.

## Pendências / bloqueios

1. **Os 3 arquivos de dados são inalcançáveis neste ambiente** (~307 MB).
   - Rede externa fechada: `docs.google.com`, `drive.google.com`, Overpass, IBGE e TSE todos negados no CONNECT (403), inclusive sem proxy. `curl .../export` e `gdown` não funcionam aqui.
   - Conector do Drive: `download_file_content` devolve base64 no contexto (58 MB → ~23 M tokens; orçamento total ~15 M) e não tem download por faixa. `read_file_content` no xlsx de 58 MB retornou vazio. Os `.zip` são binários e não suportados em leitura de texto.
   - Rotas para destravar em `INVENTARIO.md` §7 (a mais rápida: filtrar por município/cargo na origem e anexar direto na conversa).
2. **Origem dos votos da Lohanna 2022 indefinida** — a coluna `Votos` não tem números.
3. **Geometria dos municípios** — Overpass e IBGE também bloqueados; precisa vir junto ou a rede ser liberada.
4. **Professor Gabriel Mendes** (candidato-piloto): dois municípios (Betim + BH) e sem camada 2024 na planilha.

## Decisões metodológicas registradas

- **Pleito da camada do candidato aliado = 2024** (não 2022). Confirmado por três evidências independentes: a coluna `Votos` diz "2024" em 9 dos 10 candidatos; o arquivo do TSE na pasta é `votacao_secao_2024_MG.zip`; não houve eleição de vereador em 2022. A divergência apontada no comando (§3.1) fica resolvida a favor de 2024, sem ação corretiva.
- **A coluna `Votos` da planilha de candidatos é especificação, não dado.** Verificado no XML bruto: 44 células, todas `t="s"` (string), zero células numéricas. Ela lista quais camadas cada painel deve ter. A regra de precedência do §3.1 fica sem objeto.
- **Nada será renderizado sem dado real** (§3.2.4): bloco sem dado é omitido e a ausência registrada no rodapé e aqui.
- Convenção de cor fixada: **navy `#1B2A55` = candidato 2024**, **pink `#C13B7E` = Lohanna 2022**.

## COMO RETOMAR

**Pré-requisito:** destravar o acesso aos dados por uma das rotas do `INVENTARIO.md` §7.

Rota recomendada (A) — filtrar na origem e anexar nesta conversa:

1. `votacao_secao_2024_MG.zip` → só cargo Vereador (+ Prefeito p/ contexto), só os 10 municípios da planilha → CSV.
2. `eleitorado_local_votacao_2024.zip` → só os 10 municípios → CSV.
3. `tabela_oportunidades_lohanna_franca_mg_2022.xlsx` → só as linhas dos 10 municípios → CSV.
4. Se existirem, juntar os limites geográficos (GeoJSON/shapefile de bairros ou distritos) desses municípios.
5. Anexar os arquivos direto na conversa.

E responder às três perguntas em aberto:
- de onde vêm os votos da Lohanna 2022 (e em que granularidade);
- Gabriel Mendes: painel de camada única? Betim, BH, ou os dois?
- confirmar a ordem dos painéis (a planilha sugere Gabriel Mendes primeiro).

**Próximo passo exato ao retomar:** imprimir o inventário real dos arquivos recebidos
(abas, nº de linhas, nomes de colunas — sem presumir nada), e só então escrever
`gerar_painel.py` + `template_painel.html` e gerar o painel-piloto, parando para validação.
