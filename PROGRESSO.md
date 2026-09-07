# PROGRESSO — Painéis de candidatos aliados

Atualizado: 2026-09-07 (Rota A executada) · Branch `claude/electoral-panel-allied-candidates-wfput7`

## Estado: CONCLUÍDO — 10 painéis entregues, com as duas camadas e a sobreposição

> **Leia primeiro a última seção, "ROTA A EXECUTADA" (2026-09-07).** A rede foi liberada,
> todos os dados chegaram, e a camada de votos de 2022 de **todos os dez painéis** foi
> reconstruída: a coluna da planilha que vinha sendo usada não era o voto do setor
> censitário, e inflava a votação de 3× a 11×. As seções abaixo ficam como registro
> histórico; onde divergirem da última, vale a última.

<details><summary>Histórico das rodadas anteriores (2026-09-03 a 06)</summary>

## Estado (2ª rodada): PAUSADO no passo 1 — bloqueio de acesso confirmado por 3 rotas

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

---

## Camada de 2024 por local de votação — 5 painéis atualizados (2026-09-07)

Com os arquivos do TSE por seção já colhidos, cinco painéis ganharam a camada de 2024
que antes não tinham (ou tinham só o total municipal):

| Candidato | Município | Votos 2024 | Posição | Locais | Vence em |
|---|---|---:|---|---:|---:|
| Sinara Campos | São João del-Rei | 2.355 | **1º de 197** | 54 | **7** |
| Marcelo Monteiro | Lagoa Santa | 1.156 | 6º de 214 | 31 | 2 |
| Douglas Veríssimo | Curvelo | 1.058 | 7º de 204 | 30 | 3 |
| Pedro Sousa | Mariana | 620 | 25º de 155 | 35 | 0 |
| Irene Melo Franco | Pará de Minas | 619 | 21º de 224 | 36 | 0 |

Validado: para os cinco, o total do painel bate com a soma das seções na fonte **e** com
a soma dos locais no próprio painel.

### O que a seção de 2024 passou a mostrar

- **desempenho local a local**, ordenado, com endereço e zona de cada local;
- selo **"1º no local"** onde o candidato lidera;
- os **três mais votados em cada local**, com o aliado destacado — inteligência
  competitiva de verdade, no nível em que a campanha age;
- **concentração**: quanto os oito melhores locais representam da votação total;
- **capilaridade**: em quantos dos locais do município teve ao menos um voto.

### Ferramentas novas

- `colher.py` — decodifica os downloads que o harness grava em disco.
- `agregar_2024.py` — consolida os CSVs por seção em agregados por local, sem dupla
  contagem. Validado contra os totais municipais conhecidos.

### O que ainda falta

- **Coordenada dos locais de votação.** É o único item que separa o projeto da seção de
  sobreposição por bairro e da frente de Reciprocidade. O bloco no painel agora explica
  exatamente isso, em vez de dizer genericamente que a camada de 2024 não existe.
- **29 arquivos do TSE** (Belo Horizonte, Uberlândia, Betim, Divinópolis e Conselheiro
  Lafaiete), todos acima do teto prático de ~6 MB do conector.

</details>

---

# ROTA A EXECUTADA — rede liberada, dados completos (2026-09-07)

A allowlist do ambiente foi ajustada e o Drive passou a responder. Os cinco arquivos
foram baixados com `gdown` direto para o disco do contêiner, sem passar pelo contexto
do modelo. **Todos os bloqueios de dados caíram.**

```
https://drive.google.com          -> 302   (antes: 403)
https://docs.google.com           -> 302
https://drive.usercontent.google  -> 404 (host responde; o 404 é da raiz)
```

## O achado que mudou os dez painéis

**A coluna `Votos_Candidato` da tabela de aderência não é o voto do setor censitário.**
É o total do **local de votação mais próximo**, repetido em cada setor que aquele local
atende. Somá-la sobre os setores multiplica a votação pelo número de setores por local.

Como foi verificado — três testes independentes, não uma suspeita:

1. **Contra a fonte.** No `votacao_secao_2022_MG` do TSE, a Lohanna disputou 2022 como
   **Deputada Estadual**. Em Uberlândia teve **476** votos; a soma da planilha dava 5.173.
   Em Belo Horizonte, **7.849** contra 87.255.
2. **O teto bate exatamente.** O maior valor por setor na planilha de Uberlândia é 25 —
   e o maior total por local de votação no TSE é 25, no mesmo município.
3. **Setor a setor.** Atribuindo cada setor ao local de votação mais próximo pela
   coordenada, o valor da planilha é **exatamente** o total daquele local em **96,8%**
   dos setores de Uberlândia, 91,4% de Divinópolis e 81,7% de Mariana. As diferenças são
   onde o "mais próximo" calculado aqui difere do critério da planilha, não o mecanismo.

### O que isso corrigiu

| Município | Painéis antigos | Real (TSE) | Inflação |
|---|---:|---:|---:|
| Belo Horizonte | 87.255 | **7.849** | 11,1× |
| Uberlândia | 5.173 | **476** | 10,9× |
| Betim | 5.711 | **632** | 9,0× |
| Pará de Minas | 3.830 | **542** | 7,1× |
| Conselheiro Lafaiete | 1.923 | **576** | 3,3× |
| São João del-Rei | 1.737 | **482** | 3,6× |
| Lagoa Santa | 772 | **129** | 6,0× |
| Curvelo | 745 | **130** | 5,7× |
| Mariana | 637 | **188** | 3,4× |
| Divinópolis | *suprimida* | **24.045** | — |

A camada de 2022 dos dez painéis foi **inteiramente reconstruída** a partir do TSE, por
local de votação — a mesma unidade da camada de 2024. O índice de aderência, as 22 pautas
e tudo o que deriva delas não mudam: `Valor_Ajustado` é outra coluna e continua por setor.

### Divinópolis: a supressão era falso positivo

A camada de 2022 de Divinópolis tinha sido suprimida por "escala incompatível" — mediana de
387 votos por setor contra 3 a 18 nos outros. Com o mecanismo entendido, a explicação é
outra: **Divinópolis é a cidade da Lohanna**, onde ela foi a 2ª mais votada do município
com **24.045 votos**, e o valor por local é grande de fato. A supressão foi removida e o
painel da Kell Silva passa a ter a camada de 2022 completa, com o maior volume dos dez.

## Seção 7 (Sobreposição) e Frente 3 (Reciprocidade): entregues

Era o que faltava desde o começo, e o que faltava era a **coordenada dos locais de votação**.
Ela está em `eleitorado_local_votacao_<ano>.csv` (`NR_LATITUDE`/`NR_LONGITUDE`), agora baixado.

Com ela, cada local de votação é situado num bairro — dentro do polígono do IBGE onde há
malha, pelo centroide mais próximo (até 3 km) no resto —, e as duas camadas passam a existir
na mesma unidade geográfica. **Nada é estimado: são duas contagens reais somadas por bairro.**

O que o painel passou a mostrar:

- **Scatter 2022 × 2024** por bairro, eixos em raiz quadrada, com as medianas como corte;
- **ρ de Spearman** entre as duas bases, com a leitura em texto;
- **os quatro quadrantes** — base comum, território do aliado, território da Lohanna, vazio
  compartilhado — em lista e **no mapa**;
- **Frente 3 – Reciprocidade**: quem leva voto para quem, medido pela diferença de *fatia do
  município* entre as camadas (cada ano normalizado pelo seu próprio total);
- **inteligência competitiva bairro a bairro**: os três mais votados em cada bairro, com o
  aliado destacado, e em quantos bairros ele é o primeiro.

## Estado final dos dez painéis

| Candidato | Município | Lohanna 2022 | Candidato 2024 | ρ | Base comum |
|---|---|---:|---|---:|---:|
| Sara Vitral | Belo Horizonte | 7.849 | 2.136 (139º de 877) | 0,687 | sim |
| Fabão | Uberlândia | 476 | **14.596 (1º de 548)** | 0,698 | sim |
| Kell Silva | Divinópolis | **24.045** | 2.195 (9º de 267) | 0,880 | sim |
| Sinara Campos | São João del-Rei | 482 | **2.355 (1º de 218)** | 0,881 | sim |
| Damires Rinarlly | Conselheiro Lafaiete | 576 | **3.406 (2º de 221)** | 0,897 | sim |
| Marcelo Monteiro | Lagoa Santa | 129 | 1.156 (6º de 214) | 0,761 | sim |
| Douglas Veríssimo | Curvelo | 130 | 1.058 (7º de 222) | 0,829 | sim |
| Pedro Sousa | Mariana | 188 | 620 (25º de 155) | 0,813 | sim |
| Irene Melo Franco | Pará de Minas | 542 | 619 (21º de 242) | 0,626 | sim |
| Professor Gabriel Mendes | Betim | 632 | não disputou | — | camada única |

**Damires Rinarlly** aparece aqui com número novo: 3.406 votos e **2º lugar** em Conselheiro
Lafaiete. Nas rodadas anteriores o município não tinha arquivo do TSE.

Nove dos dez painéis têm agora as duas camadas e a sobreposição completa. O de Gabriel Mendes
segue de camada única — ele não disputou 2024 —, e a seção de sobreposição aparece com a
explicação, não preenchida.

### Conferência (todos os dez)

Os totais de 2022 batem **exatamente** com o TSE nos dez municípios, e os de 2024 nos nove
que têm candidato. Dentro de cada painel, a soma dos bairros e a soma das regiões batem entre
si; ficam abaixo do total municipal apenas pelos locais de votação sem coordenada na fonte do
TSE, que **não são rateados** — cada painel diz no rodapé quantos são.

### QA (§9) — os dez aprovados

`qa_lote.py`, em Chromium sobre cada arquivo, agora cobrindo também as seções novas:
**0 erros de JavaScript, 0 requisições de rede, 0 ocorrências de NaN/undefined/Infinity**,
seletor de métrica movendo mapa + ranking + legenda juntos, sem estouro horizontal em 900 e
380 px, e scatter, mapa de quadrantes, listas de reciprocidade e tabela competitiva por bairro
renderizando em todos os que têm as duas camadas.

Tamanhos: 0,37 MB a 1,95 MB — todos abaixo do teto de ~2 MB.

## Ferramentas novas desta rodada

| Script | O que faz |
|---|---|
| `filtrar_bruto.py` | recorta os CSVs do TSE (1–2 GB) para os 10 municípios, lendo em fluxo de dentro do `.zip` |
| `geo_locais.py` | extrai lat/lon, bairro e eleitorado dos locais de votação (`--ano 2022` / `2024`) |
| `agregar_2022.py` | votos da Lohanna em 2022 por local de votação, direto da fonte |

`agregar_2024.py`, `preparar_geo.py`, `gerar_painel.py`, `montar_painel.py` e `qa_lote.py`
continuam válidos. `preparar_dados.py` e `colher.py` viraram legado: existiam para contornar
o bloqueio de rede, que não existe mais.

## Como reproduzir do zero

```bash
pip install gdown pandas openpyxl playwright
mkdir -p dados/bruto
gdown 1JHxAAszjaIZDR2AG4paIZwEZrrzrSeuJ -O dados/bruto/votacao_secao_2024_MG.zip
gdown 17xnxWXMqL-aFoIH952-3_Lr5w6GGeoiA -O dados/bruto/votacao_secao_2022_MG.zip
gdown 1JUUZVHt-2E3AxjElOL5BY3ErlNHpuUNN -O dados/bruto/eleitorado_local_votacao_2024.zip
gdown 13xLTneLip4kv0fPXb4Ev74MvqeX3xxrm -O dados/bruto/eleitorado_local_votacao_2022.zip
(cd dados/bruto && unzip -o eleitorado_local_votacao_2024.zip eleitorado_local_votacao_2024.csv \
                && unzip -o eleitorado_local_votacao_2022.zip eleitorado_local_votacao_2022.csv)

python3 filtrar_bruto.py --ano 2024 && python3 filtrar_bruto.py --ano 2022
python3 geo_locais.py   --ano 2024 && python3 geo_locais.py   --ano 2022
python3 agregar_2024.py            && python3 agregar_2022.py
./gerar_todos.sh
python3 qa_lote.py
```

Pico de disco ~3 GB. `dados/geo/locais_*.csv` e `dados/tse2022_locais/` estão commitados
(250 KB no total), então quem só quiser regerar os painéis de 2022 pula os dois maiores
downloads. `dados/tse2024_locais/` tem 36 MB e ficou de fora.

## O que continua em aberto

1. **Locais de votação sem coordenada na fonte do TSE.** São 36 de 1.040 em 2024 e 45 de
   1.028 em 2022, concentrados em São João del-Rei (21 de 66) e Belo Horizonte (10 de 439).
   Esses locais entram nos totais municipais, mas ficam fora do recorte por bairro — o
   rodapé de cada painel diz quantos são. Resolver exige geocodificar os endereços, o que
   pede um serviço externo.
2. **Seis municípios sem malha de bairros do IBGE** (Divinópolis, Pará de Minas, Lagoa
   Santa, Mariana, Conselheiro Lafaiete, Curvelo). Neles o bairro vem do campo de endereço
   e o mapa é de pontos, não coroplético. Com a rede aberta, a malha de setores censitários
   do IBGE passou a ser alcançável e permitiria construir bairros por agregação — não foi
   feito nesta rodada.
3. **Professor Gabriel Mendes em Belo Horizonte.** A planilha o lista em Betim *e* BH; o
   painel entregue é o de Betim. O de BH sai com um comando, se for o caso.
4. **Ordem de leitura dos painéis** — a planilha sugere Gabriel Mendes primeiro; segue sem
   confirmação.
