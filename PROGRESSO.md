# PROGRESSO — Painéis de candidatos aliados

Atualizado: 2026-09-06 (2ª rodada) · Branch `claude/electoral-panel-allied-candidates-wfput7`

## Estado: PAUSADO no passo 1 — bloqueio de acesso confirmado por 3 rotas

2ª tentativa feita a pedido do usuário. Os dados de 2022 foram adicionados à pasta,
mas os arquivos continuam grandes demais: o conector do Drive tem **teto medido de
10 MB por arquivo** e o menor dos cinco tem 43 MB. Ver `INVENTARIO.md`, ADENDO.

Desbloqueio pronto para uso: **`preparar_dados.py`** (roda na máquina do usuário,
reduz os ~679 MB a poucos MB anexáveis). Testado end-to-end.

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

1. **Os 5 arquivos de dados são inalcançáveis neste ambiente** (~679 MB; eram 3/~307 MB).
   - Rede externa fechada: `docs.google.com`, `drive.google.com`, Overpass, IBGE e TSE todos negados no CONNECT (403), inclusive sem proxy. `curl .../export` e `gdown` não funcionam aqui.
   - Conector do Drive: `download_file_content` devolve base64 no contexto (58 MB → ~23 M tokens; orçamento total ~15 M) e não tem download por faixa. `read_file_content` no xlsx de 58 MB retornou vazio. Os `.zip` são binários e não suportados em leitura de texto.
   - Rotas para destravar em `INVENTARIO.md` §7 (a mais rápida: filtrar por município/cargo na origem e anexar direto na conversa).
2. ~~Origem dos votos da Lohanna 2022 indefinida~~ — **RESOLVIDO**: saem de
   `votacao_secao_2022_MG.zip` (TSE por seção). A camada 2022 passa a ser geográfica de
   verdade, o que viabiliza a seção 7 (Sobreposição) e a frente de Reciprocidade.
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

---

## Atualização da 2ª rodada (2026-09-06)

### Testado, com resultado medido

| Rota | Resultado |
|---|---|
| Rede do contêiner (`curl`, com e sem proxy) | `000` / `403` — bloqueada |
| `WebFetch` (busca pelo servidor) | `EGRESS_BLOCKED` — bloqueada também fora do contêiner |
| Conector do Drive, menor arquivo (43 MB) | `File too large for download, over limit of 10 MB` |

Teto do conector: **10 MB por arquivo**. Menor arquivo da pasta: **43 MB**.

### Entregue nesta rodada

- **`preparar_dados.py`** — reduz os ~679 MB ao recorte dos 10 municípios, agregando
  seção → local de votação. Testado com dados sintéticos no formato do TSE; conferidos
  totais por município, deduplicação de seções (`QT_SECOES`), separação estrita das
  camadas 2024/2022 e detecção tolerante de nomes de coluna.

### COMO RETOMAR — atualizado

Na sua máquina, com os 5 arquivos numa pasta:

```bash
pip install pandas openpyxl
python3 preparar_dados.py --entrada /caminho/da/pasta/do/drive
```

Ele grava em `./dados_filtrados/` e imprime o inventário (abas, linhas, colunas).
Depois: **anexe os CSVs direto nesta conversa** — esse canal grava em disco sem passar
pelo meu contexto, e é o único que funciona. Cole também o inventário que o script
imprimir; é o que me permite escrever o pipeline sem presumir nomes de coluna.

Se algum CSV ainda passar de ~25 MB, rode em duas levas editando a lista `MUNICIPIOS`
no topo do script.

Continua faltando decidir:
- **Geometria dos municípios** (Overpass e IBGE também bloqueados) — precisa vir junto
  como GeoJSON/shapefile de bairros, ou a rede ser liberada. Sem isso, os mapas
  coropléticos das seções 4, 7 e 8 não existem; o resto do painel sim.
- **Gabriel Mendes**: painel de camada única? Betim, BH, ou os dois?
