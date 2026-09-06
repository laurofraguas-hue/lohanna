# Inventário de dados e plano — Painéis de candidatos aliados

Data: 2026-09-06 · Branch: `claude/electoral-panel-allied-candidates-wfput7`

---

## 1. Painel de referência (lido integralmente)

`referencia/Painel_Estrategico_Unificado_Lohanna_BH_7_.html` — 1.386.583 bytes, 694 linhas, 100% offline.

| Componente | Conteúdo |
|---|---|
| Linha 7 | CSS do Leaflet (10.880 B) |
| Linha 8 | **Leaflet 1.9.4** minificado inline (147.172 B) |
| Linha 9 | **Chart.js** minificado inline (200.808 B) |
| Linhas 10–140 | `<style>` do painel (10.577 B) — identidade visual |
| Linhas 143–307 | Corpo HTML (header, cards, controles, seções) |
| Linha 310 | `const DATA = {...}` — 973.032 B de JSON |
| Linhas 311–694 | Lógica de renderização (~31 KB) |

Extraídos para reuso em `lib/`: `leaflet-1.9.4.min.js`, `chartjs.min.js`, `leaflet.min.css`, `painel.css`.

**Zero requisições externas confirmado** — nenhum tile provider, nenhum CDN.

### Identidade visual (confirmada na linha 11)
`--navy:#1B2A55` · `--pink:#C13B7E` · `--bg:#f4f5f9` · `--card:#ffffff` · `--txt:#22283b` · `--muted:#6b7390`

### Faixas de cor do índice (linhas 317–324)
`≥65 → #8f1f57` · `≥57 → #C13B7E` · `≥50 → #d97fae` · `≥43 → #aeb6d0` · `<43 → #5b6a99` · nulo → `#cfd3df`

### Esquema real do objeto `DATA` (verificado)

| Chave | Tipo | Tamanho no BH |
|---|---|---|
| `mk` | lista | 12 chaves: `educ, sup, univ, ig, lgbt, gen, rac, e0..e4` |
| `edu_vars` | lista | 5 rótulos de educação |
| `geojson` | FeatureCollection | 9 features (regionais), métricas nas `properties` |
| `regionais` | lista | 9 objetos: métricas + `votos`, `setores`, `regional` |
| `bairros` | lista | 415 objetos: métricas + `votos`, `setores`, `Bairro`, `regional` |
| `setores` | lista | 3.743 arrays `[lat, lon, ?, bairro, ...12 métricas]` |
| `tops` | dict | 4 pautas × top-10 `{b, i, s, reg}` |
| `votes` | dict | `total`=87.162 · `regionais[]` com `bairros[{b,v,s}]` · `top_regional` · `top_bairro` · `circ[]` (439 círculos) |
| `edu_break` | dict | `regionais[9]`, `vars[5]`, `values[9][5]` |
| `mob` | dict | `cons[12]`, `exp[12]` — com `lat/lon/score` |
| `cand` | dict | 16 chaves (concorrência 2022: `bairros[20]`, `fed_city`, `est_city`, `campo`, `bairros_geo`, `reg_geo`, …) |
| `crs` | string | nota de projeção |

O esquema pedido no comando (`votos24`/`votos22`, `votes24`/`votes22`, `overlap`, `mob.recip`) é uma **extensão coerente** deste — confirmo que é implementável sem quebrar a lógica existente.

---

## 2. Planilha de candidatos — `Mapeamento candidatos 2026.xlsx`

ID `1bqGTJtt955cmUAGwS4UK5ylKUIT-ZCbl` · 9.311 bytes · 1 aba (`Planilha1`) · **11 linhas × 4 colunas**.

Colunas: **`Nome`, `Municípios`, `Interesses`, `Votos`**

| # | Nome | Municípios | Coluna `Votos` (texto literal) |
|---|---|---|---|
| 1 | Professor Gabriel Mendes | Betim, Belo Horizonte | `Votação lohanna 2022` |
| 2 | Fabão | Uberlândia | `Votação lohanna 2022; votação Fabão 2024` |
| 3 | Kell Silva | Divinópolis | `Votação lohanna 2022; kell 2024` |
| 4 | Sara Vitral | Belo Horizonte | `Votos lohanna 2022; votos sara vitral 2024` |
| 5 | Sinara Campos | São João Del-Rei | `Votos Lohanna 2022; votos sinara 2024` |
| 6 | Irene Melo Franco | Pará de Minas | `Votos Lohanna 2022; votos irene 2024` |
| 7 | Marcelo Monteiro | Lagoa Santa | `Votos Lohanna 2022; votos marcelo 2024` |
| 8 | Pedro Sousa | Mariana | `Votos lohanna 2022; votos pedro 2024` |
| 9 | Damires Rinarlly | Conselheiro Lafaiete | `votos lohanna 2022; votos damires 2024` |
| 10 | Douglas Verissimo | Curvelo | `votos lohanna 2022; votos douglas verissimo 2024` |

### RESPOSTA EXPLÍCITA SOBRE A GRANULARIDADE DA COLUNA `votos`

**A coluna `Votos` não contém votos.** Verificado no XML bruto da planilha (`xl/worksheets/sheet1.xml`):

```
cells with content: 44
NUMERIC CELLS: 0    STRING CELLS: 44
```

As 44 células (11 linhas × 4 colunas) são **todas** do tipo `t="s"` (shared string). **Não existe uma única célula numérica no arquivo.**

A coluna `Votos` é uma **coluna de especificação**, não de dados: ela descreve *quais camadas de votação cada painel deve ter* ("Votos lohanna 2022; votos sara vitral 2024"). Não é total municipal, não é por bairro, não é por zona — não é número nenhum.

**Consequência:** a regra de precedência do §3.1 ("se a coluna `votos` divergir do TSE, a planilha prevalece") fica sem objeto, e a camada Lohanna 2022 precisa vir de outra fonte. Ver §5.

---

## 3. Pasta do Drive — `1RQWYvnDU2ef_5yqWRdERtJQ0PFLN6Uju`

Inventário completo (3 arquivos, ~307 MB):

| Arquivo | Tipo | Tamanho | Papel previsto |
|---|---|---|---|
| `tabela_oportunidades_lohanna_franca_mg_2022.xlsx` | xlsx | **60.777.486 B (58 MB)** | Aderência a pautas por município |
| `votacao_secao_2024_MG.zip` | zip | **201.366.815 B (192 MB)** | TSE 2024 por seção — camada do candidato aliado |
| `eleitorado_local_votacao_2024.zip` | zip | **45.276.803 B (43 MB)** | Perfil do eleitorado / geocodificação dos locais |

**Abas, nº de linhas e nomes de colunas: não foi possível obter.** Ver §4.

---

## 4. BLOQUEIO — os três arquivos de dados não são acessíveis neste ambiente

### 4.1 Rede externa totalmente fechada

O gateway de rede desta sessão nega CONNECT para todos os hosts testados:

```
docs.google.com            000   (gateway: 403 ao CONNECT)
drive.google.com           000
overpass-api.de            000
servicodados.ibge.gov.br   000
dadosabertos.tse.jus.br    000
cdn.jsdelivr.net           000
raw.githubusercontent.com  000
```

Testado também **sem proxy** (`curl --noproxy '*'`): `docs.google.com` → **HTTP 403**. Não é problema de configuração de proxy; é política de rede do ambiente.

Portanto: **`curl .../export?format=xlsx` e `gdown` não funcionam aqui** — as duas rotas indicadas no comando estão indisponíveis. (`gdown` foi instalado, mas não tem como alcançar o Drive.)

### 4.2 O conector do Drive não dá conta do volume

O conector do Google Drive funciona (foi como li a planilha de candidatos), mas:

- `download_file_content` devolve o arquivo **em base64 dentro da resposta da ferramenta**, ou seja, dentro do meu contexto. 58 MB → ~81 milhões de caracteres base64 → ~23 milhões de tokens. O orçamento total da sessão é de ~15 milhões. O zip de 192 MB daria ~77 milhões de tokens. **Fisicamente impossível**, e não há parâmetro de faixa/range para baixar em pedaços.
- `read_file_content` (que devolve texto em vez de base64) foi testado no xlsx de 58 MB e **retornou vazio** (`{"fileContent":""}`) — é o comportamento documentado para arquivos muito grandes.
- Os dois `.zip` são binários: o conector nem sequer suporta esse mime type para leitura em texto.

**Conclusão:** neste ambiente eu consigo ler apenas a planilha de candidatos (9 KB). Os 307 MB que contêm *toda* a substância dos painéis — aderência a pautas, resultados do TSE 2024 por seção e eleitorado — estão inalcançáveis.

---

## 5. O que isso impede, seção a seção

| Seção do painel | Depende de | Status |
|---|---|---|
| 2. Cards de resumo | TSE 2024 + Lohanna 2022 | bloqueada |
| 3. Leituras estratégicas | dados reais | bloqueada |
| 4. Mapa + ranking por região | tabela de aderência (58 MB) | bloqueada |
| 5. Desempenho do candidato 2024 | `votacao_secao_2024_MG.zip` | bloqueada |
| 6. Desempenho Lohanna 2022 | fonte inexistente (coluna `Votos` é texto) | bloqueada |
| 7. Sobreposição das duas bases | 5 + 6 | bloqueada |
| 8. Plano de mobilização | 4 + 5 | bloqueada |
| 9–10. Pautas e ranking de bairros | tabela de aderência | bloqueada |
| 11. Inteligência competitiva 2024 | `votacao_secao_2024_MG.zip` | bloqueada |
| 1 / 12. Header e rodapé | metadados | única parte viável |

Construir o painel agora significaria inventar números — expressamente vedado pelo §3.2.4.

---

## 6. Achados que independem do bloqueio (valem para quando os dados chegarem)

### 6.1 O pleito é 2024, não 2022 — divergência do comando resolvida

O §3.1 pediu para avisar se houvesse divergência. **Há, e os dados a resolvem a favor de 2024:**
- A própria coluna `Votos` da planilha diz "2024" em 9 dos 10 candidatos (`votos sara vitral 2024`, `kell 2024`, …).
- O arquivo do TSE na pasta é `votacao_secao_2024_MG.zip`.
- Eleições municipais no Brasil ocorreram em 2020 e 2024; não houve vereança em 2022.

**Nenhuma ação corretiva necessária** — a camada do candidato aliado é 2024, como o comando já previa em §3.1.

### 6.2 O candidato nº 1 não tem camada 2024

**Professor Gabriel Mendes** — o primeiro da planilha, e portanto o painel-piloto — tem na coluna `Votos` apenas **`Votação lohanna 2022`**, sem camada própria de 2024. É o único dos dez nessa situação.

Se isso for literal, o painel dele **não tem duas camadas** e as seções 5, 7 e a frente de Reciprocidade (8) não existem — vira um painel de camada única, mais próximo do original de BH. Preciso saber se ele não disputou 2024 ou se é lacuna de preenchimento.

### 6.3 Gabriel Mendes tem dois municípios

`Betim, Belo Horizonte` — é o único com dois. Isso muda a unidade geográfica (§6 do comando): ou são dois painéis, ou um painel com recorte de dois municípios (BH tem 9 regionais, Betim não tem regionais oficiais — as duas metades não se agregam na mesma unidade).

### 6.4 As pautas da planilha não batem com as do painel de referência

O painel de BH tem eixos de **educação, ensino superior, universitários, LGBT, gênero, antirracismo**. A coluna `Interesses` traz eixos novos: **saúde todos, família e cuidados, demografia e sexo todos, meio ambiente, predominância de instagram / consumo visual / influenciadores**.

O seletor de métrica da seção 4 terá de mudar por município (ex.: Uberlândia = saúde; Lagoa Santa = meio ambiente). Só a tabela de aderência de 58 MB dirá quais dessas colunas de fato existem — por isso não vou presumir nomes de coluna, como o comando exige.

---

## 7. Como destravar — opções

Em ordem de preferência:

**A. Reduzir os arquivos na origem e reenviar** *(mais rápido)*
Filtrar antes de subir, guardando só o necessário:
- `votacao_secao_2024_MG.zip` → apenas cargo **Vereador** (e Prefeito para contexto) nos **10 municípios** da planilha. Deve cair de 192 MB para poucos MB.
- `eleitorado_local_votacao_2024.zip` → apenas os mesmos 10 municípios.
- `tabela_oportunidades_...xlsx` → apenas as linhas desses municípios, salvo em **CSV** (xlsx de 58 MB vira CSV de poucos MB).

Depois é só anexar os arquivos direto nesta conversa (como foi feito com o painel de referência) — esse caminho não passa pela rede e funciona.

**B. Anexar direto na conversa, sem filtrar**
Funciona para arquivos na casa de poucos MB. Os 58 MB provavelmente não passam; os zips de 192/43 MB certamente não.

**C. Liberar a rede do ambiente**
Habilitar saída para `docs.google.com` / `drive.google.com` na política de rede desta sessão. Aí `curl` e `gdown` funcionam como o comando previu, e eu baixo tudo sozinho.

**D. Rodar em ambiente com internet aberta**
Claude Code local, onde `gdown --folder` alcança o Drive.

### E ainda falta resolver, independente da rota:

1. **De onde vêm os votos da Lohanna em 2022?** A coluna `Votos` não os tem. Alternativas: (a) `tabela_oportunidades_lohanna_franca_mg_2022.xlsx` — o nome sugere que sim, e viabilizaria granularidade por bairro; (b) um arquivo do TSE 2022 por seção, que **não está na pasta**; (c) você informa os totais municipais e a Lohanna 2022 vira card de resumo, não camada de mapa (§3.1 já prevê esse caso).

2. **Geometria dos municípios.** O comando pede limites via Overpass/OSM ou malha do IBGE — ambos inalcançáveis pela mesma barreira de rede. Precisarei que os GeoJSON/shapefiles venham junto, ou que a rede seja liberada. Sem geometria, os mapas coropléticos das seções 4, 7 e 8 não existem.

3. **Gabriel Mendes:** dois municípios e sem camada 2024 (§6.2 e §6.3).

---

## 8. Plano de execução (assim que os dados chegarem)

1. Inventário real: abas, nº de linhas, nomes de coluna de cada arquivo — impresso antes de qualquer código.
2. Reconstruir os totais de 2024 a partir das seções do TSE, contando cada seção **uma única vez**; validar contra o total oficial do candidato no município **antes** de renderizar (§3.2.1).
3. Definir a unidade geográfica por município na ordem do §6 (regionais → clusters de bairros → zonas eleitorais → locais agrupados), a mesma para as duas camadas.
4. `gerar_painel.py` + `template_painel.html`, parametrizados por candidato/município, consumindo `lib/` já extraído. Índice percentílico 0–100 e faixas de cor idênticas; filtro `≥5` setores configurável.
5. Mapas em **SVG inline** projetado no próprio HTML (o comando pede isso explicitamente por causa do desalinhamento canvas/SVG do Leaflet no original).
6. Painel-piloto → **PARO** para validação, com totais conferidos e decisões metodológicas listadas.
7. Aprovado, os demais um a um, salvando em `paineis/Painel_<Nome>_<Municipio>.html` e atualizando `PROGRESSO.md` a cada painel.
8. QA do §9 rodado em cada arquivo antes da entrega.

---

# ADENDO — 2ª tentativa de acesso (2026-09-06)

Você adicionou os dados de 2022 e pediu para eu tentar de novo. Tentei por **três rotas
independentes**. Todas falharam, e agora tenho os limites exatos, medidos e não deduzidos.

## A.1 Pasta do Drive agora — 5 arquivos, ~679 MB

| Arquivo | Tamanho | Situação |
|---|---|---|
| `votacao_secao_2022_MG.zip` | **295.129.070 B (281 MB)** | **novo** |
| `votacao_secao_2024_MG.zip` | 201.366.815 B (192 MB) | |
| `eleitorado_local_votacao_2022.zip` | **76.463.224 B (73 MB)** | **novo** |
| `tabela_oportunidades_lohanna_franca_mg_2022.xlsx` | 60.777.486 B (58 MB) | |
| `eleitorado_local_votacao_2024.zip` | 45.276.803 B (43 MB) | |

Os arquivos foram **acrescentados**, não reduzidos: o total subiu de ~307 MB para ~679 MB.
O menor deles tem 43 MB.

## A.2 As três rotas testadas

**1. Rede do contêiner** — segue fechada:
```
docs.google.com   000     drive.google.com (sem proxy)  403
```

**2. `WebFetch`** (busca pelo servidor, não pelo contêiner) — também barrada:
```json
{"error_type":"EGRESS_BLOCKED","domain":"docs.google.com",
 "message":"Access to docs.google.com is blocked by the network egress proxy."}
```
Isso descarta a hipótese de que só o contêiner estivesse bloqueado: a política de egress
vale para o ambiente inteiro.

**3. Conector do Drive** — testado no menor arquivo (43 MB). O próprio conector respondeu:
```
File too large for download, over limit of 10 MB.
```

## A.3 O limite exato, agora medido

**Teto rígido de 10 MB por arquivo no conector do Drive.** O menor dos cinco arquivos tem
43 MB — 4,3× o teto. Nenhum passa.

Há ainda um segundo teto, independente: o conector devolve o arquivo em base64 **dentro do
meu contexto**. Mesmo um arquivo de 10 MB viraria ~13,3 milhões de caracteres ≈ 3,8 milhões
de tokens — um quarto do orçamento da sessão gasto num único arquivo, sem sobrar espaço para
construir os painéis.

**A rota que funciona é outra: anexar o arquivo direto na conversa.** Aí ele é gravado em
disco no contêiner sem passar pelo meu contexto — foi exatamente assim que o painel de
referência de 1,4 MB chegou até mim. É por isso que a solução é reduzir os arquivos antes de
enviar, e não tentar outro caminho de download.

## A.4 O que os dados de 2022 destravam (quando chegarem)

`votacao_secao_2022_MG.zip` responde a pergunta que ficou em aberto no §7-E1: **os votos da
Lohanna em 2022 saem do TSE por seção**, e não da coluna `Votos` da planilha (que é texto).

Isso é a melhor notícia desta rodada, porque muda o teto do produto: a camada 2022 deixa de
ser um card de resumo e passa a ser **camada geográfica de verdade**, comparável à de 2024 na
mesma unidade. Ou seja, a **seção 7 (Sobreposição das duas bases)** — scatter com Spearman e
os quatro quadrantes — e a frente de **Reciprocidade** da seção 8 são viáveis. Elas eram o
principal risco do projeto e deixaram de ser.

## A.5 `preparar_dados.py` — o desbloqueio

Escrevi e testei `preparar_dados.py`, que roda **na sua máquina** e faz a redução:

1. filtra tudo para os 10 municípios da planilha;
2. agrega os votos de **seção → local de votação** (soma `QT_VOTOS` por município + zona +
   local + candidato), o que corta o tamanho em cerca de uma ordem de grandeza e já entrega a
   granularidade que o painel usa — cada seção contada **uma única vez**, atendendo o §3.2.1;
3. mantém 2024 (Vereador + Prefeito) e 2022 (Dep. Estadual + Federal) em **arquivos
   separados**, para as camadas nunca se misturarem (§3.1);
4. extrai bairro, latitude, longitude e eleitorado de cada local de votação;
5. filtra a tabela de aderência pelos mesmos municípios;
6. **imprime o inventário** de cada arquivo — abas, nº de linhas e nomes de coluna — que é
   justamente o que o §7.1 exige e o que eu não posso levantar sozinho.

Testado de ponta a ponta com dados sintéticos no formato do TSE (CSV `;`, latin-1, dentro de
zip). Conferências que passaram: totais por município exatos, seções deduplicadas via
`QT_SECOES`, cargos e municípios corretamente filtrados, detecção de colunas tolerante a
variação de nome (nada é presumido — se não encontra, avisa em vez de adivinhar).

---

# ADENDO 2 — Tabelas de oportunidade (aderência a pautas), 5 municípios

Recebidas por anexo: Lagoa Santa, Mariana, Pará de Minas, São João del-Rei, Uberlândia.
Total 9,3 MB. Schema **idêntico nos cinco**: 1 aba por município, **52 colunas**.

## B.1 O que a tabela é

É a mesma estrutura que gerou o painel de referência (`Lohanna_BH.xlsx`). Colunas que
importam:

| Grupo | Colunas |
|---|---|
| Identificação | `Município`, `UF`, **`Ano`**, **`Candidato`** |
| Pauta | **`Variável`**, `Classificação` |
| Geografia | `CD_setor`, `CD_MUN`, `Bairro`, **`Bairro_Censo`**, `Latitude_Setor`, `Longitude_Setor`, `Latitude`, `Longitude` |
| Índice | `Valor_Bruto`, `Peso_Moradores`, **`Valor_Ajustado`**, `Quartil_Fundo`, `XG` |
| Votos | **`Votos_Candidato`**, `Q1/Q2/Q3_Votos_Base`, `Distancia_Urna_Setor_m` |
| Endereço/CNEFE | `CEP`, `Rua`, `Numero_Endereco`, `Codigo_Unico_Endereco_CNEFE`, `Metodo_Correspondencia`, `Nivel_Geocodificacao_CNEFE`, `Status_Endereco`, `Fonte_Endereco` |
| Contexto municipal | `Total_Setores_Município`, `Qtd/Percentual_Ideal/Subideal/Base_Município` |

`Valor_Ajustado` é o insumo do índice — o rodapé do painel de referência diz
"Índice = percentil médio do valor ajustado, normalizado por pauta". A normalização
percentílica 0–100 do §3.2.2 se aplica sobre ele.

## B.2 A camada da Lohanna 2022 tem fonte — e é esta

`Candidato` = **LOHANNA SOUZA FRANÇA MOREIRA DE OLIVEIRA** · `Ano` = **2022**, em todos.

Com `Votos_Candidato` por **setor censitário**, a camada 2022 é geográfica de verdade e
agregável a bairro. Isso confirma, por uma segunda fonte independente, o que o
`votacao_secao_2022_MG.zip` já indicava — e torna a **seção 7 (Sobreposição das duas
bases)** e a frente de **Reciprocidade** plenamente viáveis.

## B.3 A armadilha do §3.2.1 — confirmada, medida, pior que o previsto

`Votos_Candidato` **repete o mesmo valor em cada linha do setor**. Verificado: em todos
os municípios, **zero setores** têm mais de um valor distinto de `Votos_Candidato`.

Como há uma linha por (setor, variável) — 22 pautas —, somar ingenuamente multiplica o
total por ~20×. Medido:

| Município | Soma ingênua | **Soma correta** (1 setor = 1 vez) | Inflação |
|---|---:|---:|---:|
| Lagoa Santa | 14.514 | **772** | 18,8× |
| Mariana | 15.543 | **637** | 24,4× |
| Pará de Minas | 77.749 | **3.830** | 20,3× |
| São João del-Rei | 42.064 | **1.737** | 24,2× |
| Uberlândia | 113.987 | **5.173** | 22,0× |

O comando alertava para ~11× em BH; aqui é **19× a 24×**. A regra vale integralmente:
**deduplicar por `CD_setor` antes de qualquer soma.**

Esses totais ainda precisam ser conferidos contra o total oficial do TSE de 2022 por
município (item do QA §9), o que depende dos dados eleitorais ainda não recebidos.

## B.4 As 22 pautas são as mesmas nos cinco municípios

**8 eixos, 22 pautas, idênticos em todos** — ao contrário do que a coluna `Interesses` da
planilha de candidatos sugeria. Aquela coluna diz quais pautas **enfatizar** em cada
painel, não quais existem. Isso simplifica: o seletor de métrica da seção 4 é o mesmo
para todos, e o recorte por candidato vira ordenação/destaque, não estrutura.

| Eixo | Pautas |
|---|---|
| **Educação** | 5 — alta escolaridade · escolaridade média · universitários/campus · pós-graduação · técnico e superior |
| **Saúde** | 5 — atenção primária/UBS · pré-natal/parto/pediatria · diferenças de acesso · queixa de falta de médico · alta demanda por UBS |
| **Demografia por Sexo e Idade** | 4 — mulheres 15–19 · 20–24 · 25–29 · 30–34 |
| **Igualdade e Direitos** | 3 — LGBT/tolerância · igualdade de gênero · antirracismo/equidade racial |
| **Família e Cuidado** | 2 — lares chefiados por mulheres · alta demanda por creche |
| **Comportamento e Rotina** | 1 — predominância de Instagram, consumo visual, influenciadores |
| **Meio Ambiente e Qualidade Urbana** | 1 — pressão ambiental, arborização, lixo |
| **Comunidade e Cultura** | 1 — cultura local, tradição popular, pertencimento |

As 5 de Educação e as 3 de Igualdade e Direitos são **exatamente** as do painel de
referência (`edu_vars` e `ig/lgbt/gen/rac`). Os outros 6 eixos são novos e ampliam o
seletor — e cobrem os `Interesses` pedidos (saúde, família e cuidados, demografia,
meio ambiente, Instagram).

## B.5 Chave de junção com a malha do IBGE: `Bairro_Censo`

Testado contra os GeoJSON gerados em `dados/geo/`:

| Município | `Bairro` (bruto) ∩ IBGE | **`Bairro_Censo` ∩ IBGE** |
|---|---:|---:|
| São João del-Rei | 8 de 24 | **8 de 8 — 100%** |
| Uberlândia | 69 de 91 | **69 de 69 — 100%** |

**`Bairro_Censo` casa perfeitamente com o `NM_BAIRRO` do shapefile; `Bairro` (bruto) não.**
Decisão fechada: a junção geográfica usa `Bairro_Censo`.

Linhas sem `Bairro_Censo` (marcadas `—`): 2,3% em SJDR e 1,4% em Uberlândia — vão para um
agrupamento "Não classificado" ou "Zona Rural", nunca descartadas em silêncio.

Em Uberlândia, 6 bairros do IBGE não têm dado na tabela (Aclimação, Jardim Inconfidência,
Jardim Ipanema, Lagoinha, Morada dos Pássaros, Panorama). Serão desenhados em cinza
("sem dado"), como o painel de referência faz com `colorFor(null)` → `#cfd3df`.

## B.6 Os 3 municípios sem malha do IBGE

Lagoa Santa, Mariana e Pará de Minas têm **`Bairro_Censo` vazio em 100% das linhas** —
coerente: o IBGE não delimitou bairros ali, então a tabela não tem o campo.

Mas têm alternativa boa: **`Bairro` (bruto) com ~50 valores** e
**`Latitude_Setor`/`Longitude_Setor` preenchidos em 100% das linhas**. Ou seja, cada setor
tem nome de bairro e coordenada.

Isso é melhor do que o fallback previsto no §6 (zonas eleitorais): dá para usar o **bairro
bruto como unidade** e desenhar o mapa como **pontos proporcionais** por setor — o mesmo
recurso que o painel de referência já usa em `votes.circ` — ou gerar polígonos por
envoltória convexa dos setores de cada bairro. Decisão a tomar no painel-piloto do
primeiro desses municípios.

## B.7 Robustez (§3.2.3)

Setores por bairro, contando cada setor uma vez:

| Município | Mediana | Máx | Bairros com ≥5 setores |
|---|---:|---:|---|
| São João del-Rei | 14 | 34 | 8 de 8 |
| Uberlândia | 13 | 88 | 57 de 69 |

O filtro `≥5` do painel original é adequado e será mantido, configurável.

## B.8 O que ainda falta

- As tabelas de oportunidade dos **5 municípios restantes** (anunciadas para o próximo envio).
- Os **dados eleitorais do TSE**: `votacao_secao_2024_MG.zip` (camada do candidato aliado,
  2024) e o total oficial de 2022 por município, para validar os números da B.3.
- A malha do IBGE **não cobre** Divinópolis, Pará de Minas, Lagoa Santa, Mariana,
  Conselheiro Lafaiete e Curvelo — ver B.6 para o caminho.
