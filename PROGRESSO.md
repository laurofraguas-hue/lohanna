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

### COMO RETOMAR — Rota B (sem mexer em configuração)

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
  como GeoJSON/shapefile de bairros, ou a rede ser liberada (Rota A abaixo resolve isso
  de quebra). Sem geometria, os mapas coropléticos das seções 4, 7 e 8 não existem;
  o resto do painel sim.
- **Gabriel Mendes**: painel de camada única? Betim, BH, ou os dois?

---

## COMO RETOMAR — Rota A (liberar a rede) — RECOMENDADA

Esta é a rota mais limpa: com a rede aberta, o download e todo o processamento acontecem
dentro da sessão, sem intermediário e sem passar pelo contexto do modelo.

### Diagnóstico

Esta sessão roda no ambiente **"Default"** (`env_011CUVqrkKzKo11Hg8FNTmsn`, Anthropic
cloud), cujo nível de rede é **Trusted** — allowlist fixa com registries de pacotes,
GitHub e SDKs de nuvem. Google Drive não está nela. Por isso `pip install` funciona e
`curl docs.google.com` não.

Níveis disponíveis: **None**, **Trusted** (atual), **Full** (qualquer domínio),
**Custom** (allowlist própria).

### Passo a passo

1. Em **claude.ai/code**, clicar no **ícone de nuvem com o nome do ambiente** ("Default"),
   na linha logo acima da caixa de mensagem. Não há página de configurações nem URL direta
   para esse seletor.
2. Passar o mouse sobre o ambiente e clicar na **engrenagem** à direita — ou escolher
   **Add cloud environment** para criar um ambiente novo e deixar o Default intacto
   (preferível, já que o Default é o padrão de todas as outras sessões).
3. Em **Network access**, escolher **Custom**.
4. Em **Allowed domains**, uma linha por domínio:

```
drive.google.com
docs.google.com
drive.usercontent.google.com
*.googleusercontent.com
accounts.google.com
overpass-api.de
servicodados.ibge.gov.br
geoftp.ibge.gov.br
```

5. Marcar **"Also include default list of common package managers"** — senão pip, npm etc.
   param de funcionar.
6. Salvar.

Alternativa: escolher **Full** e pular a lista.

Os três primeiros domínios são os que o `gdown` usa (o download de arquivo grande do Drive
redireciona para `drive.usercontent.google.com`). Os três últimos destravam a **geometria
dos municípios** — Overpass e IBGE estão barrados pela mesma política, e sem eles não há
mapa coroplético.

### Duas ressalvas

- **A sessão atual não pega a mudança.** A configuração do ambiente é lida uma única vez,
  na largada da sessão. Depois de salvar, **abrir uma sessão nova** no ambiente ajustado,
  no mesmo repositório e branch (`claude/electoral-panel-allied-candidates-wfput7`). Tudo
  já está commitado, então a sessão nova encontra `INVENTARIO.md`, `PROGRESSO.md`, `lib/`
  e `preparar_dados.py` prontos.
- **Liberar a rede não muda o teto de 10 MB do conector do Drive** — esse limite é do
  conector, não da rede (tráfego de conectores MCP nem passa pela allowlist da sessão).
  O que a liberação destrava é `gdown`/`curl`, que gravam direto no disco do contêiner
  sem passar pelo contexto do modelo. É disso que precisamos.

### Primeiros comandos da sessão nova

```bash
# 1. confirmar que a rede abriu
curl -sS -o /dev/null -w "%{http_code}\n" https://drive.google.com

# 2. baixar UM arquivo por vez (o disco da sessão é cota fixa)
pip install gdown pandas openpyxl
gdown --id 1JHxAAszjaIZDR2AG4paIZwEZrrzrSeuJ -O dados/votacao_secao_2024_MG.zip

# 3. reduzir e APAGAR o bruto antes de baixar o próximo
python3 preparar_dados.py --entrada dados --saida dados_filtrados
rm dados/votacao_secao_2024_MG.zip
```

IDs dos arquivos na pasta `1RQWYvnDU2ef_5yqWRdERtJQ0PFLN6Uju`:

| Arquivo | ID | Tamanho |
|---|---|---|
| `votacao_secao_2022_MG.zip` | `17xnxWXMqL-aFoIH952-3_Lr5w6GGeoiA` | 281 MB |
| `votacao_secao_2024_MG.zip` | `1JHxAAszjaIZDR2AG4paIZwEZrrzrSeuJ` | 192 MB |
| `eleitorado_local_votacao_2022.zip` | `13xLTneLip4kv0fPXb4Ev74MvqeX3xxrm` | 73 MB |
| `eleitorado_local_votacao_2024.zip` | `1JUUZVHt-2E3AxjElOL5BY3ErlNHpuUNN` | 43 MB |
| `tabela_oportunidades_lohanna_franca_mg_2022.xlsx` | `1n34KJU_XvcanQ3A3LSAhE_Xn9k6DOrI1` | 58 MB |
| `Mapeamento candidatos 2026.xlsx` (já em `dados/`) | `1bqGTJtt955cmUAGwS4UK5ylKUIT-ZCbl` | 9 KB |

**Atenção ao disco:** são ~679 MB comprimidos, vários GB descompactados, contra uma cota
fixa por sessão. Baixar e processar um por vez, apagando o bruto a cada etapa. Se aparecer
"no space left on device", apagar os brutos já processados libera espaço na hora.

### Depois do download, o fluxo é o mesmo das duas rotas

1. Imprimir o inventário real (abas, nº de linhas, nomes de coluna) — **sem presumir nada**.
2. Reconstruir os totais de 2024 a partir das seções, cada seção contada uma única vez;
   validar contra o total oficial do candidato no município **antes** de renderizar.
3. Definir a unidade geográfica por município (regionais → clusters de bairros → zonas
   eleitorais → locais agrupados), a mesma para as duas camadas.
4. `gerar_painel.py` + `template_painel.html`, consumindo `lib/`.
5. Painel-piloto → **PARAR** para validação.
6. Aprovado, os demais um a um, atualizando este arquivo a cada painel.

---

## Atualização — malha de bairros do IBGE recebida (2026-09-06)

`MG_bairros_CD2022.zip` (2,3 MB) chegou por anexo na conversa e está em
`dados/geo/`. **Bloqueio de geometria parcialmente resolvido.**

### O que é

Malha de bairros do **Censo 2022 do IBGE**, Minas Gerais. Shapefile de polígonos,
**1.994 bairros em 55 municípios** (de 853 em MG — o IBGE só delimita bairros em
municípios selecionados). Projeção **SIRGAS 2000 (EPSG:4674)**, encoding UTF-8.

Campos: `CD_REGIAO, NM_REGIAO, CD_UF, NM_UF, CD_MUN, NM_MUN, CD_DIST, NM_DIST,
CD_SUBDIST, NM_SUBDIST, CD_BAIRRO, NM_BAIRRO, CD_RGINT, NM_RGINT, CD_RGI, NM_RGI,
CD_CONCURB, NM_CONCURB`.

`CD_MUN` (código IBGE de 7 dígitos) é a chave de junção com o TSE, que usa código
próprio — a ponte se faz por `NM_MUNICIPIO` normalizado, ou por uma tabela
CD_MUN ↔ CD_MUNICIPIO_TSE.

### Cobertura dos 10 municípios do projeto

| Município | Bairros | Situação |
|---|---:|---|
| Belo Horizonte | 476 | OK |
| Betim | 126 | OK |
| Uberlândia | 75 | OK |
| São João del-Rei | 8 | OK, só a área urbana (~10 × 11 km) |
| Divinópolis | — | **sem malha** |
| Pará de Minas | — | **sem malha** |
| Lagoa Santa | — | **sem malha** |
| Mariana | — | **sem malha** |
| Conselheiro Lafaiete | — | **sem malha** |
| Curvelo | — | **sem malha** |

**4 dos 10 municípios têm bairros; 6 não têm.** Para os 6, a unidade geográfica cai
para o nível seguinte do §6 do comando: **zonas eleitorais**, ou **locais de votação
agrupados por proximidade** (lat/lon vêm de `eleitorado_local_votacao_*.csv`). Nesses
municípios o mapa deixa de ser coroplético e passa a ser de pontos proporcionais —
que é, aliás, o mesmo recurso que o painel de referência já usa em `votes.circ`.

Em São João del-Rei os 8 polígonos cobrem só a mancha urbana. Locais de votação
rurais cairão fora de todos eles e precisam de um agrupamento "Zona Rural", como o
§6 prevê.

### Entregue: `preparar_geo.py`

Extrai a malha por município e gera GeoJSON simplificado (Douglas-Peucker,
tolerância 0,00015° ≈ 17 m) com coordenadas arredondadas a 5 casas (~1 m).
Gera também o contorno do município (união dos bairros), útil como moldura.

Resultado — bem dentro do orçamento de ~2 MB por painel:

| Município | Bairros | Vértices orig. → simpl. | GeoJSON |
|---|---:|---:|---:|
| Belo Horizonte | 476 | 58.145 → 11.882 | 320 KB |
| Betim | 126 | 26.669 → 4.938 | 122 KB |
| Uberlândia | 75 | 5.778 → 1.475 | 42 KB |
| São João del-Rei | 8 | 3.399 → 735 | 17 KB |

Conferido: **zero polígonos inválidos**, zero nomes de bairro vazios, nenhum nome
duplicado, e os bounding boxes batem com a localização real de cada município.
O script sanea topologia em três níveis (direto → `buffer(0)` → `make_valid`) e
revalida após o arredondamento, porque encostar vértices pode invalidar polígono.

Referência cruzada: o painel de BH trabalha com 415 bairros; o IBGE traz 476. As
duas fontes são compatíveis em ordem de grandeza — a diferença vem de o painel
original ter agregado setores censitários, não de erro de recorte.

### Sobre a projeção

SIRGAS 2000 e WGS 84 diferem por menos de 1 m no Brasil — irrelevante na escala de
um mapa de bairros. As coordenadas vão para o GeoJSON como lon/lat sem reprojeção,
e o rodapé do painel registra isso, como faz o painel de referência.

### O que ainda falta

Só os **dados eleitorais e de aderência** (Rota A ou Rota B acima). A geometria
deixou de ser bloqueio para 4 municípios e tem caminho definido para os outros 6.

---

## PAINEL-PILOTO ENTREGUE — Fabão / Uberlândia (2026-09-06)

`paineis/Painel_Fabao_Uberlandia.html` — 0,68 MB, 100% offline. **Aguardando validação.**

### Por que Uberlândia como piloto

É o primeiro candidato da planilha que tem de fato as duas camadas (Gabriel Mendes é o
caso degenerado, sem 2024), tem malha do IBGE com 75 bairros, e Fabão foi o vereador mais
votado — cidade grande o bastante para ser representativa, pequena o bastante para iterar.

### Ferramentas criadas (reutilizáveis para os demais)

- `gerar_painel.py` — monta o objeto DATA de qualquer município/candidato.
- `template_painel.html` + `painel.js` — estrutura e lógica, parametrizadas.
- `montar_painel.py` — junta template + CSS + Chart.js + DATA num arquivo só.
- `qa_painel.py` — roda a checklist do §9 em navegador real.

Gerar outro painel são dois comandos:
```bash
python3 gerar_painel.py --municipio "<Município>" --candidato "<Apelido>" --numero <nº urna>
python3 montar_painel.py --data dados/DATA_<cand>_<mun>.json
```

### Números conferidos

| | Fonte | Painel |
|---|---:|---:|
| Lohanna 2022 (dedup por setor) | 5.173 | 5.173 |
| Soma das regiões no acordeão | — | 5.173 |
| Soma dos bairros na tabela | — | 5.173 |
| Fabão vereador 2024 (TSE) | 14.596 | 14.596 |

Camadas em objetos separados (`votes22` / `votes24`); nenhum campo soma as duas.

### QA (§9)

| Item | Resultado |
|---|---|
| Sem dependência externa | apenas o namespace XML do SVG |
| Erros de JavaScript | 0 |
| Requisições de rede ao abrir | 0 |
| NaN / undefined / null / Infinity | 0 |
| Seletor atualiza mapa + ranking + legenda | sim |
| Mapa e tabela concordam sobre líderes | conferido em 3 pautas |
| Responsivo ≤ 900 px | sem estouro horizontal em 900 e 380 px |
| Rodapé com fontes por ano, data e ressalvas | sim |

### Decisões metodológicas deste painel

- **Unidade geográfica:** bairros do IBGE (Censo 2022), via `Bairro_Censo`, que casa 69/69.
- **Regiões:** Uberlândia não tem regionais oficiais, então os bairros foram agrupados em
  Centro/Norte/Sul/Leste/Oeste por ângulo e distância ao centroide da cidade (§6, opção 2).
- **Índice:** percentil de `Valor_Ajustado` calculado dentro de cada pauta, 0–100, com as
  faixas de cor do painel de referência. Cada par (setor, pauta) entra uma vez.
- **Votos 2022:** deduplicados por `CD_setor` — a inflação seria de 22× sem isso.
- **Mapa:** SVG inline puro, projeção equirretangular com correção de cosseno. Sem Leaflet,
  o que elimina a defasagem entre camadas e economiza 147 KB.
- **80 setores sem bairro** viraram "Não classificado" (63 votos) — preservados, não descartados.
- **6 bairros do IBGE sem dado** ficam cinza no mapa.
- **Cobertura:** 1.352 de 1.924 setores (70,3%) — registrado no rodapé.

### O que está vazio por falta de dado

- **Seção 7 (Sobreposição)** e **Frente 3 (Reciprocidade)**: exigem a camada 2024 por local
  de votação. O bloco aparece com a explicação, em vez de ser preenchido por estimativa.
- **Inteligência competitiva por bairro**: idem; só o recorte municipal está montado.

Ambas entram sem outra mudança quando o arquivo por local de votação chegar — o painel já
está construído sobre a unidade geográfica correta.

---

## OS 10 PAINÉIS ENTREGUES (2026-09-06)

Todos em `paineis/`, um arquivo `.html` autocontido por candidato, 100% offline.
Reproduzíveis com `./gerar_todos.sh`.

| Candidato | Município | Bairros | Regiões | Malha IBGE | Lohanna 2022 | Candidato 2024 | Corte |
|---|---|---:|---:|---|---:|---|---:|
| Sara Vitral | Belo Horizonte | 423 | 9 oficiais | sim | 87.255 | 2.136 (131º) | ≥5 |
| Professor Gabriel Mendes | Betim | 98 | 11 oficiais | sim | 5.711 | não concorreu | ≥5 |
| Fabão | Uberlândia | 69 | 6 clusters | sim | 5.173 | **14.596 (1º)** | ≥5 |
| Sinara Campos | São João del-Rei | 8 | 6 clusters | sim | 1.737 | **2.355 (1º)** | ≥5 |
| Kell Silva | Divinópolis | 138 | 5 clusters | não | **suprimida** | 2.195 (9º) | ≥5 |
| Irene Melo Franco | Pará de Minas | 53 | 5 clusters | não | 3.830 | sem arquivo TSE | ≥3 |
| Damires Rinarlly | Conselheiro Lafaiete | 69 | 5 clusters | não | 1.923 | sem arquivo TSE | ≥2 |
| Marcelo Monteiro | Lagoa Santa | 51 | 5 clusters | não | 772 | sem arquivo TSE | ≥2 |
| Douglas Verissimo | Curvelo | 43 | 5 clusters | não | 745 | sem arquivo TSE | ≥2 |
| Pedro Sousa | Mariana | 50 | 5 clusters | não | 637 | sem arquivo TSE | ≥2 |

Tamanhos: 0,32 MB a 1,74 MB — todos abaixo do teto de ~2 MB.

### QA (§9) — os 10 aprovados

Rodado em Chromium sobre cada arquivo (`qa_lote.py`): **0 erros de JavaScript, 0
requisições de rede, 0 ocorrências de NaN/undefined/Infinity**, seletor de métrica
atualizando mapa + ranking + legenda em conjunto, e sem estouro horizontal em 900 e
380 px. Todos os totais conferidos contra as fontes: os votos de 2022 batem entre o
card, a soma das regiões e a soma dos bairros, e os de 2024 batem com o TSE.

### Três decisões novas, que o piloto não exercitou

**1. Regionais oficiais quando existem.** O shapefile do IBGE traz `NM_DIST` e
`NM_SUBDIST`. Em Belo Horizonte, os dois combinados dão exatamente as **9 regionais**
do painel de referência (Barreiro e Venda Nova como distritos, mais as 7 internas);
Betim tem as suas. Onde o IBGE não subdivide (Uberlândia, São João del-Rei e os seis
sem malha), permanecem os clusters cardeais. Isso segue a ordem de preferência do §6:
oficial primeiro, cluster só como recurso.

**2. Mapa de pontos onde não há malha.** Seis municípios não têm bairros delimitados
pelo IBGE. Neles o mapa deixa de ser coroplético e passa a ser de círculos — um por
bairro, no centroide dos seus setores, colorido pelo índice e, na seção de 2022,
dimensionado pelos votos. Mantém a leitura espacial sem inventar fronteira.

**3. Filtro de robustez calibrado ao município.** O corte de 5 setores pressupõe
bairros grandes. Onde a unidade vem do campo de endereço, a mediana cai para 1 ou 2
setores e o corte de 5 esvaziaria o ranking (Mariana ficaria com 4 bairros). O corte
passou a ser o maior de {5, 3, 2} que preserva massa crítica, e o rodapé de cada
painel diz qual foi usado e por quê. Continua ajustável pelo seletor na tela e por
`--min-setores`.

### Divinópolis — camada de 2022 suprimida

O painel da Kell Silva sai **sem a contagem de votos de 2022**, com a justificativa
no card, nas leituras estratégicas e no rodapé. O índice de aderência, as 22 pautas,
o mapa, os rankings e a camada de 2024 continuam íntegros — o que saiu foi só o número
que seria enganoso. Os pesos do plano de mobilização foram renormalizados sobre as
pautas, em vez de tratar dado ausente como ausência de voto.

Para restaurar: regerar o arquivo de Divinópolis com o mesmo procedimento dos outros
nove, ou reconstruir a camada a partir do `votacao_secao_2022_MG`. Depois é só rodar
`gerar_todos.sh` sem o `--suprimir-votos22`.

### O que continua pendente em todos

- **Seção 7 (Sobreposição das duas bases)** e **Frente 3 (Reciprocidade)**: dependem do
  TSE 2024 por local de votação. O bloco aparece com a explicação, não preenchido.
- **Inteligência competitiva por bairro**: idem.
- **Cinco municípios sem nenhum arquivo do TSE 2024** (Pará de Minas, Lagoa Santa,
  Mariana, Conselheiro Lafaiete, Curvelo): esses painéis são de camada única.
- **Professor Gabriel Mendes**: painel feito para **Betim**. Ele consta na planilha com
  Betim e Belo Horizonte; o de BH sai com um comando, se quiser os dois.

### Como regerar tudo

```bash
./gerar_todos.sh     # dados + montagem dos 10
python3 qa_lote.py   # checklist do §9 em navegador real
```
