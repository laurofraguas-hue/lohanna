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
