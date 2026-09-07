#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_painel.py — monta o objeto DATA de um painel a partir das fontes já inventariadas.

Fontes, por camada (nunca somadas entre si):
  · aderência a pautas + votos da Lohanna 2022 ... dados/aderencia/tabela_oportunidade_<mun>.xlsx
  · malha de bairros (quando existe) ............ dados/geo/bairros_<mun>.geojson
  · totais do candidato aliado em 2024 .......... dados/tse2024/votos_2024_<MUN>.csv

Regras aplicadas:
  · §3.2.1 — votos deduplicados por CD_setor antes de qualquer soma;
  · §3.2.2 — índice percentílico 0–100 por pauta, sobre Valor_Ajustado;
  · §3.2.3 — filtro de robustez configurável (padrão: >= 5 setores);
  · §3.2.4 — bloco sem dado é omitido, nunca preenchido.
"""

import argparse
import json
import math
import os
import re
import unicodedata
from collections import defaultdict

import pandas as pd

# ---------------------------------------------------------------- utilidades

def norm(s):
    s = unicodedata.normalize("NFKD", str(s) if s is not None else "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper().replace("-", " ").strip()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", norm(s).lower()).strip("_")


def pct_rank(serie):
    """Percentil 0–100. Empates recebem o percentil médio, como no painel original."""
    return serie.rank(pct=True, method="average") * 100.0


# ------------------------------------------------------- eixos e rótulos

# Chaves curtas por eixo, na ordem em que aparecem no seletor.
EIXOS = [
    ("educ",  "Educação"),
    ("ig",    "Igualdade e Direitos"),
    ("saude", "Saúde"),
    ("fam",   "Família e Cuidado"),
    ("demo",  "Demografia por Sexo e Idade"),
    ("comp",  "Comportamento e Rotina"),
    ("amb",   "Meio Ambiente e Qualidade Urbana"),
    ("cult",  "Comunidade e Cultura"),
]
EIXO_POR_NOME = {norm(n): k for k, n in EIXOS}

# Pautas que compõem os agregados herdados do painel de referência.
SUP_PAUTAS = [
    "Alta escolaridade, superior/pós, qualificação elevada",
    "Presença de universitários, ensino superior, campus",
    "Pós-graduação, alta qualificação, capital intelectual",
    "Técnico e superior, formação profissional, diplomas",
]
ATALHOS = {
    "univ": "Presença de universitários, ensino superior, campus",
    "lgbt": "Aderência a pautas LGBT, tolerância e direitos",
    "gen":  "Aderência a pautas de igualdade de gênero",
    "rac":  "Sensibilidade a antirracismo, inclusão, equidade racial",
}

CAMPO_PROG = {"PT", "PSOL", "PDT", "PV", "REDE", "PSB", "PCDOB", "UP", "PSTU", "PCB", "PCO"}


# ------------------------------------------------------------ carga

def carregar_aderencia(mun_slug):
    p = f"dados/aderencia/tabela_oportunidade_{mun_slug}.xlsx"
    if not os.path.exists(p):           # são joão del rei foi enviado como "del_rey"
        alt = p.replace("del_rei", "del_rey")
        p = alt if os.path.exists(alt) else p
    if not os.path.exists(p):
        raise SystemExit(f"não encontrei a tabela de aderência: {p}")
    df = pd.read_excel(p)
    df["_eixo"] = df["Variável"].str.split(" - ").str[0].map(norm).map(EIXO_POR_NOME)
    df["_pauta"] = df["Variável"].str.split(" - ", n=1).str[1].str.strip()
    return df, p


def carregar_geo(mun_slug):
    for cand in (mun_slug, mun_slug.replace("del_rey", "del_rei")):
        p = f"dados/geo/bairros_{cand}.geojson"
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8")), p
    return None, None


# --------------------------------------------- locais de votação (geo)

def carregar_geo_locais(mun_nome, ano=2024):
    """Geocodificação dos locais de votação de 2024 (lat/lon, bairro, eleitorado).

    Vem de `eleitorado_local_votacao_2024.csv` do TSE, colapsado para uma linha
    por (município, zona, local) por `geo_locais.py`. É esta coordenada que
    permite dizer a que bairro cada local pertence — e, com isso, cruzar a camada
    de 2024 com a de 2022 na mesma unidade geográfica."""
    p = f"dados/geo/locais_{ano}.csv"
    if not os.path.exists(p):
        return None, None
    d = pd.read_csv(p, dtype=str)
    d = d[d["NM_MUNICIPIO"].map(norm) == norm(mun_nome)].copy()
    if d.empty:
        return None, None
    for c in ("NR_LATITUDE", "NR_LONGITUDE"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["_k"] = d["NR_ZONA"].astype(str) + "-" + d["NR_LOCAL_VOTACAO"].astype(str)
    return d, p


def _no_anel(lon, lat, anel):
    """Ray casting: o ponto está dentro deste anel de coordenadas?"""
    dentro = False
    n = len(anel)
    j = n - 1
    for i in range(n):
        xi, yi = anel[i][0], anel[i][1]
        xj, yj = anel[j][0], anel[j][1]
        if (yi > lat) != (yj > lat):
            if lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                dentro = not dentro
        j = i
    return dentro


def _no_poligono(lon, lat, coords, tipo):
    """Polygon/MultiPolygon do GeoJSON, respeitando buracos (anéis internos)."""
    partes = [coords] if tipo == "Polygon" else coords
    for p in partes:
        if not p or not _no_anel(lon, lat, p[0]):
            continue
        if not any(_no_anel(lon, lat, buraco) for buraco in p[1:]):
            return True
    return False


def _caixa(coords, tipo):
    partes = [coords] if tipo == "Polygon" else coords
    xs, ys = [], []
    for p in partes:
        for x, y in p[0]:
            xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def atribuir_bairro_aos_locais(locais, geo, xy, raio_max_km=3.0):
    """bairro de cada local de votação, a partir da sua coordenada.

    Duas rotas, na ordem de preferência do §6:
      1. **Dentro do polígono** — onde o IBGE publica malha de bairros, o local cai
         literalmente dentro de um deles. É a atribuição exata.
      2. **Centroide mais próximo** — para o que sobra (município sem malha, ou local
         fora da mancha urbana mapeada), o bairro é o de centroide mais próximo,
         desde que dentro de `raio_max_km`. Além disso o local fica sem bairro em vez
         de ser forçado a um: um local a 20 km do bairro mais próximo não é dele.
    """
    caixas = []
    if geo is not None:
        for f in geo["features"]:
            g = f["geometry"]
            caixas.append((f["properties"]["bairro"], _caixa(g["coordinates"], g["type"]),
                           g["coordinates"], g["type"]))

    nomes_xy = {norm(b): b for b in xy}
    saida, metodo = {}, {}
    for _, r in locais.iterrows():
        lat, lon = r["NR_LATITUDE"], r["NR_LONGITUDE"]
        if pd.isna(lat) or pd.isna(lon):
            continue
        achou = None
        for nome, (x0, y0, x1, y1), coords, tipo in caixas:
            if x0 <= lon <= x1 and y0 <= lat <= y1 and _no_poligono(lon, lat, coords, tipo):
                achou, m = nome, "polígono"
                break
        if achou is None and xy:
            melhor, dmin = None, float("inf")
            for b, (blon, blat) in xy.items():
                if b == "Não classificado":
                    continue
                dx = (blon - lon) * math.cos(math.radians(lat)) * 111.32
                dy = (blat - lat) * 111.32
                d = math.hypot(dx, dy)
                if d < dmin:
                    melhor, dmin = b, d
            if melhor is not None and dmin <= raio_max_km:
                achou, m = melhor, "centroide"
        if achou is None:
            continue
        # A malha nomeia o bairro; o painel usa o nome da tabela. Junção por nome
        # normalizado, para as duas rotas caírem no mesmo universo de bairros.
        achou = nomes_xy.get(norm(achou), achou)
        saida[r["_k"]] = achou
        metodo[r["_k"]] = m
    return saida, metodo


def montar_votes24_locais(df, apelido, numero, mun_nome, geoloc=None, bairro_de=None):
    """Camada de 2024 com quebra por local de votação.

    Cada seção já foi contada uma única vez na agregação; aqui só se soma por local,
    de modo que o total do candidato reproduz o total oficial do município.

    A chave do local é o par (zona, número): o TSE numera os locais DENTRO de cada
    zona eleitoral, então o número sozinho colide entre zonas — em Belo Horizonte,
    que tem dezenas de zonas, isso fundiria locais de bairros distintos.

    `bairro_de` mapeia essa chave para o bairro; quando presente, a camada de 2024
    passa a existir também por bairro, na mesma unidade da camada de 2022."""
    df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
    df["QT_SECOES"] = pd.to_numeric(df["QT_SECOES"], errors="coerce").fillna(0).astype(int)
    df["_k"] = df["NR_ZONA"].astype(str) + "-" + df["NR_LOCAL_VOTACAO"].astype(str)
    nominal = df[(df["DS_CARGO"].map(norm) == "VEREADOR") &
                 (pd.to_numeric(df["SQ_CANDIDATO"], errors="coerce") > 0)].copy()
    if nominal.empty:
        return None

    tot_cand = (nominal.groupby(["NR_VOTAVEL", "NM_VOTAVEL"], as_index=False)["QT_VOTOS"]
                .sum().sort_values("QT_VOTOS", ascending=False).reset_index(drop=True))
    tot_nom = int(tot_cand["QT_VOTOS"].sum())

    if numero is None:
        raise SystemExit(f"{mun_nome}: informe --numero para localizar {apelido} em 2024")
    alvo = tot_cand[tot_cand["NR_VOTAVEL"].astype(str) == str(numero)]
    if alvo.empty:
        raise SystemExit(f"{mun_nome}: número {numero} não está entre os "
                         f"{len(tot_cand)} candidatos a vereador de 2024")
    pos = int(alvo.index[0]) + 1
    eu = alvo.iloc[0]

    def linha(r, i):
        return {"nr": str(r["NR_VOTAVEL"]), "nome": r["NM_VOTAVEL"],
                "votos": int(r["QT_VOTOS"]), "pos": i + 1,
                "pct": round(100 * r["QT_VOTOS"] / tot_nom, 2)}

    # ---- desempenho do candidato local a local ----
    meu = nominal[nominal["NR_VOTAVEL"].astype(str) == str(numero)]
    por_local_tot = nominal.groupby("_k")["QT_VOTOS"].sum()
    info = df.drop_duplicates("_k").set_index("_k")
    geoinfo = geoloc.drop_duplicates("_k").set_index("_k") if geoloc is not None else None
    por_local_cand = {k: g for k, g in nominal.groupby("_k")}

    locais = []
    for L, v in meu.groupby("_k")["QT_VOTOS"].sum().items():
        tot = int(por_local_tot.get(L, 0))
        no_local = (por_local_cand[L]
                    .groupby(["NR_VOTAVEL", "NM_VOTAVEL"], as_index=False)["QT_VOTOS"].sum()
                    .sort_values("QT_VOTOS", ascending=False).reset_index(drop=True))
        minha_pos = int(no_local[no_local["NR_VOTAVEL"].astype(str)
                                 == str(numero)].index[0]) + 1
        g = geoinfo.loc[L] if geoinfo is not None and L in geoinfo.index else None
        locais.append({
            "nr": str(info.loc[L, "NR_LOCAL_VOTACAO"]),
            "nome": str(info.loc[L, "NM_LOCAL_VOTACAO"]),
            "end": str(info.loc[L, "DS_LOCAL_VOTACAO_ENDERECO"]),
            "zona": str(info.loc[L, "NR_ZONA"]),
            "v": int(v), "tot": tot,
            "pct": round(100 * v / tot, 2) if tot else None,
            "pos": minha_pos, "n": len(no_local),
            "b": (bairro_de or {}).get(L),
            "lat": None if g is None or pd.isna(g["NR_LATITUDE"]) else round(float(g["NR_LATITUDE"]), 5),
            "lon": None if g is None or pd.isna(g["NR_LONGITUDE"]) else round(float(g["NR_LONGITUDE"]), 5),
            "elei": None if g is None else int(g["QT_ELEITORES"]),
            "lideres": [{"nome": x["NM_VOTAVEL"], "nr": str(x["NR_VOTAVEL"]),
                         "v": int(x["QT_VOTOS"])}
                        for _, x in no_local.head(3).iterrows()],
        })
    locais.sort(key=lambda x: -x["v"])

    n_loc = int(nominal["_k"].nunique())
    top8 = sum(x["v"] for x in locais[:8])
    pref = df[(df["DS_CARGO"].map(norm) == "PREFEITO") &
              (pd.to_numeric(df["SQ_CANDIDATO"], errors="coerce") > 0)]
    pref = (pref.groupby("NM_VOTAVEL", as_index=False)["QT_VOTOS"].sum()
            .sort_values("QT_VOTOS", ascending=False).head(3))

    return {
        "granularidade": "local de votação",
        "total_nominal": tot_nom, "n_cands": len(tot_cand),
        "n_locais": n_loc,
        "n_secoes": int(df.groupby("_k")["QT_SECOES"].max().sum()),
        "n_zonas": int(df["NR_ZONA"].nunique()),
        "candidato": {**linha(eu, pos - 1),
                      "locais": len(locais),
                      # seções em que o candidato teve ao menos um voto
                      "secoes": int(meu["QT_SECOES"].sum()),
                      "vence_em": sum(1 for x in locais if x["pos"] == 1),
                      "top8_pct": round(100 * top8 / int(eu["QT_VOTOS"]), 1)
                      if eu["QT_VOTOS"] else None},
        "mais_votados": [linha(r, i) for i, r in tot_cand.head(15).iterrows()],
        "locais": locais,
        "prefeito": [{"nome": r["NM_VOTAVEL"], "votos": int(r["QT_VOTOS"])}
                     for _, r in pref.iterrows()],
    }


def agregar_por_bairro(df, bairro_de, reg_por_bairro, numero):
    """Votos de 2024 por bairro, somando os locais atribuídos a cada um.

    Devolve (agregado do candidato, ranking dos mais votados em cada bairro). Cada
    local entra uma única vez; locais sem coordenada — e por isso sem bairro — ficam
    de fora do cruzamento e são contados no rodapé, em vez de rateados.
    """
    d = df.copy()
    d["QT_VOTOS"] = pd.to_numeric(d["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
    d["_k"] = d["NR_ZONA"].astype(str) + "-" + d["NR_LOCAL_VOTACAO"].astype(str)
    d["_b"] = d["_k"].map(bairro_de)
    d = d[d["_b"].notna()]
    nominal = d[(d["DS_CARGO"].map(norm) == "VEREADOR") &
                (pd.to_numeric(d["SQ_CANDIDATO"], errors="coerce") > 0)]
    if nominal.empty:
        return {}, {}

    agg, comp = {}, {}
    for b, sub in nominal.groupby("_b"):
        por_cand = (sub.groupby(["NR_VOTAVEL", "NM_VOTAVEL"], as_index=False)["QT_VOTOS"]
                    .sum().sort_values("QT_VOTOS", ascending=False).reset_index(drop=True))
        meu = por_cand[por_cand["NR_VOTAVEL"].astype(str) == str(numero)]
        pos = int(meu.index[0]) + 1 if len(meu) else None
        agg[b] = {
            "cand": int(meu["QT_VOTOS"].iloc[0]) if len(meu) else 0,
            "tot": int(por_cand["QT_VOTOS"].sum()),
            "locais": int(sub["_k"].nunique()),
            "reg": reg_por_bairro.get(b),
            "pos": pos, "n": len(por_cand),
        }
        comp[b] = {
            "pos": pos, "n": len(por_cand),
            "top": [{"nome": r["NM_VOTAVEL"], "nr": str(r["NR_VOTAVEL"]),
                     "v": int(r["QT_VOTOS"])} for _, r in por_cand.head(3).iterrows()],
        }
    return agg, comp


# ---------------------------------------------------- sobreposição

def spearman(a, b):
    """Correlação de postos, sem scipy. Empates recebem o posto médio."""
    n = len(a)
    if n < 3:
        return None
    def postos(v):
        ordem = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[ordem[j + 1]] == v[ordem[i]]:
                j += 1
            media = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[ordem[k]] = media
            i = j + 1
        return r
    ra, rb = postos(a), postos(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return round(num / den, 3) if den else None


def montar_sobreposicao(votes22, bairros, votes24, nominal_por_bairro, apelido):
    """Cruza as duas camadas no MESMO bairro e devolve os quatro quadrantes.

    A camada de 2022 vem de setor censitário agregado a bairro; a de 2024, de local
    de votação atribuído ao bairro pela coordenada. São duas malhas independentes
    somadas na mesma unidade — não há nenhuma estimativa no meio.

    O corte de cada eixo é a MEDIANA entre os bairros com dado nos dois anos: um
    corte relativo, que é o que a leitura pede ("forte para este município"), e não
    um limiar absoluto que dependeria do tamanho da cidade.
    """
    if votes22.get("suprimido") or not votes24 or not nominal_por_bairro:
        return None
    v22 = {r["Bairro"]: int(r["votos22"] or 0) for _, r in bairros.iterrows()}
    linhas = []
    for b, d in nominal_por_bairro.items():
        if b == "Não classificado" or b not in v22:
            continue
        linhas.append({"b": b, "v22": v22[b], "v24": d["cand"], "tot24": d["tot"],
                       "reg": d.get("reg"), "locais": d["locais"]})
    linhas = [x for x in linhas if x["v22"] > 0 or x["v24"] > 0]
    if len(linhas) < 4:
        return None

    def mediana(vs):
        v = sorted(vs); n = len(v)
        return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2
    c22 = mediana([x["v22"] for x in linhas])
    c24 = mediana([x["v24"] for x in linhas])

    quad = {"comum": [], "cand": [], "lohanna": [], "vazio": []}
    for x in linhas:
        alto22, alto24 = x["v22"] > c22, x["v24"] > c24
        x["q"] = ("comum" if alto22 and alto24 else "cand" if alto24 else
                  "lohanna" if alto22 else "vazio")
        quad[x["q"]].append(x)

    # Reciprocidade: assimetria entre as duas bases, medida em share do município.
    # Cada camada é normalizada pelo seu próprio total, senão a de maior volume
    # dominaria a diferença por puro tamanho.
    t22 = sum(x["v22"] for x in linhas) or 1
    t24 = sum(x["v24"] for x in linhas) or 1
    for x in linhas:
        x["s22"] = round(100 * x["v22"] / t22, 2)
        x["s24"] = round(100 * x["v24"] / t24, 2)
        x["dif"] = round(x["s24"] - x["s22"], 2)

    return {
        "corte22": c22, "corte24": c24,
        "n": len(linhas),
        "total22": t22, "total24": t24,
        "spearman": spearman([x["v22"] for x in linhas], [x["v24"] for x in linhas]),
        "pontos": [[x["b"], x["v22"], x["v24"], x["q"], x["reg"]] for x in linhas],
        "quadrantes": {k: sorted(v, key=lambda x: -(x["v22"] + x["v24"]))[:10]
                       for k, v in quad.items()},
        "n_quad": {k: len(v) for k, v in quad.items()},
        # território do candidato onde a Lohanna é fraca, e vice-versa
        "recip_cand": sorted([x for x in linhas if x["dif"] > 0],
                             key=lambda x: -x["dif"])[:10],
        "recip_loh": sorted([x for x in linhas if x["dif"] < 0],
                            key=lambda x: x["dif"])[:10],
    }


def regioes_oficiais(geo):
    """bairro -> regional, a partir do campo `regiao` da malha do IBGE."""
    if not geo:
        return {}
    return {f["properties"]["bairro"]: f["properties"].get("regiao")
            for f in geo["features"] if f["properties"].get("regiao")}


def carregar_locais22(mun_slug):
    """Votos da Lohanna em 2022 por local de votação (ver `agregar_2022.py`)."""
    for cand in (mun_slug, mun_slug.replace("del_rey", "del_rei"),
                 mun_slug.replace("del_rei", "del_rey")):
        p = f"dados/tse2022_locais/locais_{cand}.csv"
        if os.path.exists(p):
            d = pd.read_csv(p, sep=";", dtype=str)
            for c in ("QT_VOTOS_NOMINAIS", "QT_VOTOS_LOHANNA"):
                d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(int)
            d["_k"] = d["NR_ZONA"].astype(str) + "-" + d["NR_LOCAL_VOTACAO"].astype(str)
            return d, p
    return None, None



def carregar_locais24(mun_slug):
    """Agregados do TSE 2024 por local de votação, quando já colhidos."""
    for cand in (mun_slug, mun_slug.replace("del_rey", "del_rei"),
                 mun_slug.replace("del_rei", "del_rey")):
        p = f"dados/tse2024_locais/locais_{cand}.csv"
        if os.path.exists(p):
            return pd.read_csv(p, sep=";", dtype=str, encoding="utf-8"), p
    return None, None


def carregar_tse24(mun_nome):
    alvo = norm(mun_nome)
    for p in sorted(os.listdir("dados/tse2024")) if os.path.isdir("dados/tse2024") else []:
        if not p.endswith(".csv"):
            continue
        d = pd.read_csv(os.path.join("dados/tse2024", p))
        if norm(d["NM_MUNICIPIO"].iloc[0]) == alvo:
            return d, os.path.join("dados/tse2024", p)
    return None, None


# --------------------------------------------------- índice por setor

def indice_por_setor(df):
    """Percentil 0–100 de Valor_Ajustado, calculado DENTRO de cada pauta.

    Cada (setor, pauta) entra uma única vez: a tabela traz linhas repetidas por
    endereço/oportunidade, e mantê-las distorceria o percentil."""
    base = df.drop_duplicates(subset=["CD_setor", "Variável"]).copy()
    base["_idx"] = base.groupby("Variável")["Valor_Ajustado"].transform(pct_rank)
    return base


def montar_metricas(base):
    """Devolve (tabela setor x métrica, chaves, rótulos, mapa de eixos)."""
    piv = base.pivot_table(index="CD_setor", columns="_pauta", values="_idx", aggfunc="mean")

    pauta_eixo = base.drop_duplicates("_pauta").set_index("_pauta")["_eixo"].to_dict()
    pautas = sorted(piv.columns)

    out = pd.DataFrame(index=piv.index)
    labels, eixo_membros = {}, defaultdict(list)

    # métricas individuais: v0, v1, ...
    for i, p in enumerate(pautas):
        k = f"v{i}"
        out[k] = piv[p]
        labels[k] = p
        eixo_membros[pauta_eixo[p]].append(k)

    # agregados por eixo
    for ek, en in EIXOS:
        membros = eixo_membros.get(ek, [])
        if membros:
            out[ek] = out[membros].mean(axis=1)
            labels[ek] = f"{en} — {len(membros)} pauta" + ("s" if len(membros) > 1 else "")

    # agregados herdados do painel de referência
    cols_sup = [f"v{pautas.index(p)}" for p in SUP_PAUTAS if p in pautas]
    if len(cols_sup) >= 2:
        out["sup"] = out[cols_sup].mean(axis=1)
        labels["sup"] = f"Ensino superior — {len(cols_sup)} pautas combinadas"
    for k, p in ATALHOS.items():
        if p in pautas and k not in out.columns:
            out[k] = out[f"v{pautas.index(p)}"]
            labels[k] = p

    return out.round(1), labels, dict(eixo_membros), pautas


# ------------------------------------------------- regiões por cluster

def clusterizar(bairros_xy, n_alvo=6):
    """Agrupa bairros em regiões cardeais a partir do centroide da cidade.

    O §6 pede nomes neutros quando não há regionais oficiais. Usa-se o ângulo
    em relação ao centro, com um anel central para os bairros mais próximos."""
    if not bairros_xy:
        return {}
    lons = [p[0] for p in bairros_xy.values()]
    lats = [p[1] for p in bairros_xy.values()]
    c_lon, c_lat = sum(lons) / len(lons), sum(lats) / len(lats)
    raios = {}
    for b, (lon, lat) in bairros_xy.items():
        dx = (lon - c_lon) * math.cos(math.radians(c_lat))
        dy = lat - c_lat
        raios[b] = math.hypot(dx, dy)
    corte = sorted(raios.values())[max(0, len(raios) // 6)]  # ~17% mais centrais

    reg = {}
    for b, (lon, lat) in bairros_xy.items():
        if raios[b] <= corte:
            reg[b] = "Centro"
            continue
        dx = (lon - c_lon) * math.cos(math.radians(c_lat))
        dy = lat - c_lat
        ang = math.degrees(math.atan2(dy, dx))          # 0=leste, 90=norte
        if -45 <= ang < 45:      reg[b] = "Leste"
        elif 45 <= ang < 135:    reg[b] = "Norte"
        elif ang >= 135 or ang < -135: reg[b] = "Oeste"
        else:                    reg[b] = "Sul"
    return reg


# ------------------------------------------------------------- montagem

def construir(mun_nome, apelido, numero=None, min_setores=None, suprimir22=None, sem2024=False):
    mun_slug = slug(mun_nome)
    df, p_ader = carregar_aderencia(mun_slug)
    geo, p_geo = carregar_geo(mun_slug)
    tse, p_tse = carregar_tse24(mun_nome)

    base = indice_por_setor(df)
    met, labels, eixo_membros, pautas = montar_metricas(base)
    mk = list(met.columns)

    # ---- atributos por setor: bairro, coordenada, votos 2022 ----------
    setor_info = (df.drop_duplicates(subset=["CD_setor"])
                    .set_index("CD_setor")[["Bairro", "Bairro_Censo", "Latitude_Setor",
                                            "Longitude_Setor", "Votos_Candidato"]])
    tab = met.join(setor_info, how="left")

    # Bairro_Censo casa com a malha do IBGE; Bairro (bruto) é o recurso onde
    # não há malha. Setor sem nenhum dos dois vai para "Não classificado".
    usa_censo = geo is not None and tab["Bairro_Censo"].notna().any() \
        and (tab["Bairro_Censo"].map(norm) != "—").any()
    col_b = "Bairro_Censo" if usa_censo else "Bairro"
    tab["_bairro"] = tab[col_b].fillna("—").astype(str).str.strip()
    tab.loc[tab["_bairro"].map(norm).isin(["—", "", "NAN"]), "_bairro"] = "Não classificado"
    tab["_votos22"] = pd.to_numeric(tab["Votos_Candidato"], errors="coerce").fillna(0).astype(int)

    # ---- centroide de cada bairro e regiões ----------------------------
    xy = {}
    for b, sub in tab.groupby("_bairro"):
        la = pd.to_numeric(sub["Latitude_Setor"], errors="coerce").dropna()
        lo = pd.to_numeric(sub["Longitude_Setor"], errors="coerce").dropna()
        if len(la) and len(lo):
            xy[b] = (float(lo.mean()), float(la.mean()))
    # §6, ordem de preferência: regionais oficiais primeiro; clusters cardeais só
    # quando o IBGE não publica subdivisão para o município.
    reg_por_bairro, origem_reg = regioes_oficiais(geo), "oficial"
    if len(set(reg_por_bairro.values())) < 2:
        reg_por_bairro = clusterizar({k: v for k, v in xy.items() if k != "Não classificado"})
        origem_reg = "cluster"
    else:
        # A malha nomeia os bairros; a tabela usa Bairro_Censo. A junção é por nome normalizado.
        mapa = {norm(k): v for k, v in reg_por_bairro.items()}
        reg_por_bairro = {b: mapa.get(norm(b)) for b in xy}
        reg_por_bairro = {k: v for k, v in reg_por_bairro.items() if v}
        if len(reg_por_bairro) < 0.5 * len(xy):
            reg_por_bairro = clusterizar({k: v for k, v in xy.items() if k != "Não classificado"})
            origem_reg = "cluster"
    tab["_reg"] = tab["_bairro"].map(reg_por_bairro).fillna("Não classificado")

    # ---- agregação por bairro e por região -----------------------------
    def agrega(chave):
        g = tab.groupby(chave)
        out = g[mk].mean().round(1)
        out["votos22"] = g["_votos22"].sum()
        out["setores"] = g.size()
        return out.reset_index()

    bairros = agrega("_bairro").rename(columns={"_bairro": "Bairro"})
    bairros["regional"] = bairros["Bairro"].map(reg_por_bairro).fillna("Não classificado")
    # Centroide de cada bairro: é o que sustenta o mapa de pontos onde não há malha.
    bairros["lon"] = bairros["Bairro"].map(lambda b: round(xy[b][0], 5) if b in xy else None)
    bairros["lat"] = bairros["Bairro"].map(lambda b: round(xy[b][1], 5) if b in xy else None)
    regionais = agrega("_reg").rename(columns={"_reg": "regional"})

    # ---- camada 2022: votos reais do TSE, por local de votação ----------
    # A coluna Votos_Candidato da tabela de aderência NÃO é o voto do setor: é o
    # total do LOCAL DE VOTAÇÃO mais próximo, repetido em cada setor que o local
    # atende (verificado setor a setor). Somá-la inflaria o voto de 3× a 11×.
    # A camada vem, portanto, do próprio TSE — mesma unidade da camada de 2024.
    loc22, p_loc22 = carregar_locais22(mun_slug)
    geoloc22, p_geoloc22 = carregar_geo_locais(mun_nome, 2022)
    v22_locais, geo22 = [], None
    if loc22 is not None and geoloc22 is not None:
        b22, m22 = atribuir_bairro_aos_locais(geoloc22, geo, xy)
        gi = geoloc22.drop_duplicates("_k").set_index("_k")
        por_bairro22 = defaultdict(int)
        for _, r in loc22.iterrows():
            b = b22.get(r["_k"])
            if b:
                por_bairro22[b] += int(r["QT_VOTOS_LOHANNA"])
            g = gi.loc[r["_k"]] if r["_k"] in gi.index else None
            v22_locais.append({
                "nr": str(r["NR_LOCAL_VOTACAO"]), "zona": str(r["NR_ZONA"]),
                "nome": str(r["NM_LOCAL_VOTACAO"]),
                "end": str(r["DS_LOCAL_VOTACAO_ENDERECO"]),
                "v": int(r["QT_VOTOS_LOHANNA"]), "tot": int(r["QT_VOTOS_NOMINAIS"]),
                "pct": round(100 * r["QT_VOTOS_LOHANNA"] / r["QT_VOTOS_NOMINAIS"], 2)
                       if r["QT_VOTOS_NOMINAIS"] else None,
                "b": b,
                "lat": None if g is None or pd.isna(g["NR_LATITUDE"]) else round(float(g["NR_LATITUDE"]), 5),
                "lon": None if g is None or pd.isna(g["NR_LONGITUDE"]) else round(float(g["NR_LONGITUDE"]), 5),
            })
        v22_locais.sort(key=lambda x: -x["v"])
        geo22 = {"locais": int(len(geoloc22)),
                 "com_coord": int(geoloc22["NR_LATITUDE"].notna().sum()),
                 "com_bairro": len(b22),
                 "por_poligono": sum(1 for v in m22.values() if v == "polígono"),
                 "por_centroide": sum(1 for v in m22.values() if v == "centroide")}
        # O voto do bairro passa a ser a soma dos seus locais de votação; o índice
        # de aderência continua vindo do setor censitário, que é a unidade dele.
        bairros["votos22"] = bairros["Bairro"].map(por_bairro22).fillna(0).astype(int)
        regionais["votos22"] = regionais["regional"].map(
            bairros.groupby("regional")["votos22"].sum()).fillna(0).astype(int)
        tab["_votos22"] = 0
        total_tse22 = int(loc22["QT_VOTOS_LOHANNA"].sum())
    else:
        total_tse22 = None

    if suprimir22:
        # Município cujo Votos_Candidato está em escala incompatível com o setor
        # censitário. Suprimir é a aplicação literal da regra de não inventar dado:
        # o índice de aderência continua íntegro, só a contagem sai.
        tab["_votos22"] = 0
        bairros["votos22"] = 0
        regionais["votos22"] = 0

    total22 = total_tse22 if total_tse22 is not None else int(tab["_votos22"].sum())
    v22_reg = []
    for _, r in regionais.sort_values("votos22", ascending=False).iterrows():
        sub = (bairros[bairros["regional"] == r["regional"]]
               .sort_values("votos22", ascending=False))
        v22_reg.append({
            "regional": r["regional"], "votos": int(r["votos22"]), "setores": int(r["setores"]),
            "bairros": [{"b": x["Bairro"], "v": int(x["votos22"]), "s": int(x["setores"])}
                        for _, x in sub.iterrows() if x["votos22"] > 0],
        })
    top_b = bairros[bairros["Bairro"] != "Não classificado"] \
        .sort_values("votos22", ascending=False).iloc[0]
    votes22 = {
        "total": None if suprimir22 else total22,
        "suprimido": bool(suprimir22), "motivo": suprimir22,
        "granularidade": ("local de votação" if total_tse22 is not None
                          else "setor censitário"),
        "cargo": "Deputada Estadual" if total_tse22 is not None else None,
        "soma_bairros": int(bairros["votos22"].sum()) if total_tse22 is not None else None,
        "locais": v22_locais[:60],
        "n_locais": len(v22_locais),
        "n_locais_com_voto": sum(1 for x in v22_locais if x["v"] > 0),
        "geo": geo22,
        "regionais": [] if suprimir22 else v22_reg,
        "top_regional": None if suprimir22 else (v22_reg[0]["regional"] if v22_reg else None),
        "top_bairro": None if suprimir22 else {"nome": top_b["Bairro"],
            "regional": top_b["regional"], "votos": int(top_b["votos22"])},
        "circ": [] if suprimir22 else [[round(xy[b][1], 5), round(xy[b][0], 5), int(v), b,
                  reg_por_bairro.get(b, "Não classificado")]
                 for b, v in zip(bairros["Bairro"], bairros["votos22"])
                 if b in xy and v > 0],
    }
    if suprimir22:
        # Sem voto confiável, o campo sai do registro do bairro em vez de exibir zero,
        # que seria lido como "nenhum voto" em vez de "não medido".
        for col in (bairros, regionais):
            col["votos22"] = None

    # ---- camada 2024 -----------------------------------------------------
    votes24, over, comp_bairro, geo_stats = None, None, None, None
    loc24, p_loc24 = carregar_locais24(mun_slug)
    geoloc, p_geoloc = carregar_geo_locais(mun_nome)
    bairro_de, metodo = ({}, {})
    if geoloc is not None:
        bairro_de, metodo = atribuir_bairro_aos_locais(geoloc, geo, xy)
        geo_stats = {
            "locais": int(len(geoloc)),
            "com_coord": int(geoloc["NR_LATITUDE"].notna().sum()),
            "com_bairro": len(bairro_de),
            "por_poligono": sum(1 for v in metodo.values() if v == "polígono"),
            "por_centroide": sum(1 for v in metodo.values() if v == "centroide"),
            "fonte": os.path.basename(p_geoloc),
        }
    if loc24 is not None and not sem2024:
        votes24 = montar_votes24_locais(loc24, apelido, numero, mun_nome,
                                        geoloc, bairro_de)
        p_tse = p_loc24
        if votes24 and bairro_de:
            votes24["geo"] = geo_stats
            npb, comp_bairro = agregar_por_bairro(loc24, bairro_de, reg_por_bairro,
                                                  numero)
            votes24["bairros"] = [
                {"b": b, "v": d["cand"], "tot": d["tot"], "locais": d["locais"],
                 "reg": d.get("reg"),
                 "pct": round(100 * d["cand"] / d["tot"], 2) if d["tot"] else None}
                for b, d in sorted(npb.items(), key=lambda kv: -kv[1]["cand"])]
            over = montar_sobreposicao(votes22, bairros, votes24, npb, apelido)
    elif tse is not None and not sem2024:
        ver = tse[(tse["DS_CARGO"].map(norm) == "VEREADOR") & (tse["SQ_CANDIDATO"] > 0)].copy()
        ver = ver.sort_values("QT_VOTOS_TOTAL", ascending=False).reset_index(drop=True)
        tot_nom = int(ver["QT_VOTOS_TOTAL"].sum())
        # O apelido de urna raramente é o nome registrado ("Fabão" x "FABIO DIAS
        # QUEIROZ ZAVITOSKI"), então o número é a chave confiável.
        if numero:
            alvo = ver[ver["NR_VOTAVEL"].astype(str) == str(numero)]
        else:
            alvo = ver[ver["NM_VOTAVEL"].map(norm).str.contains(norm(apelido.split()[0]), na=False)]
        if not len(alvo):
            if sem2024:
                # Candidato que não disputou 2024: o painel é de camada única e a
                # seção correspondente é omitida, não preenchida.
                tse = None
            else:
                raise SystemExit(
                    f"não localizei o candidato (apelido={apelido!r}, numero={numero!r}) entre os "
                    f"{len(ver)} candidatos a vereador de {mun_nome}. Se ele não disputou 2024, "
                    f"use --sem-2024.")
        else:
            eu = alvo.iloc[0]
        def linha(r, i):
            pt = re.sub(r"\d+$", "", str(r["NR_VOTAVEL"]))[:2]
            return {"nr": str(r["NR_VOTAVEL"]), "nome": r["NM_VOTAVEL"],
                    "votos": int(r["QT_VOTOS_TOTAL"]),
                    "pct": round(100 * r["QT_VOTOS_TOTAL"] / tot_nom, 2),
                    "pos": i + 1, "locais": int(r["QT_LOCAIS_COM_VOTO"]),
                    "secoes": int(r["QT_SECOES_COM_VOTO"])}
        votes24 = {
            "granularidade": "municipal",
            "total_nominal": tot_nom, "n_cands": len(ver),
            "mais_votados": [linha(r, i) for i, r in ver.head(15).iterrows()],
            "candidato": linha(eu, int(alvo.index[0])),
            "prefeito": [{"nome": r["NM_VOTAVEL"], "votos": int(r["QT_VOTOS_TOTAL"])}
                         for _, r in tse[(tse["DS_CARGO"].map(norm) == "PREFEITO")
                                         & (tse["SQ_CANDIDATO"] > 0)]
                         .sort_values("QT_VOTOS_TOTAL", ascending=False).head(4).iterrows()],
            "n_locais": int(tse["QT_LOCAIS_COM_VOTO"].max()),
            "n_secoes": int(tse["QT_SECOES_COM_VOTO"].max()),
            "n_zonas": int(tse["QT_ZONAS_COM_VOTO"].max()),
        }

    # ---- filtro de robustez, calibrado ao município ----------------------
    # O corte de 5 setores do painel de BH pressupõe bairros grandes. Onde o IBGE
    # não delimita bairros, a unidade vem do campo de endereço e a mediana cai para
    # 1 ou 2 setores — o mesmo corte esvaziaria o ranking. Escolhe-se então o maior
    # corte que ainda preserva massa crítica de bairros.
    if min_setores is None:
        cand_b = bairros[bairros["Bairro"] != "Não classificado"]
        alvo_n = min(20, math.ceil(0.6 * len(cand_b)))
        min_setores = 2
        for m in (5, 3, 2):
            if (cand_b["setores"] >= m).sum() >= alvo_n:
                min_setores = m
                break

    # ---- tops por pauta (com filtro de robustez) -------------------------
    robusto = bairros[(bairros["setores"] >= min_setores) &
                      (bairros["Bairro"] != "Não classificado")]
    tops = {}
    for k in mk:
        s = robusto.nlargest(10, k)
        tops[k] = [{"b": r["Bairro"], "i": float(r[k]), "s": int(r["setores"]),
                    "reg": r["regional"]} for _, r in s.iterrows()]

    # ---- geojson com as métricas nas properties --------------------------
    gj = None
    if geo is not None:
        idx = bairros.set_index(bairros["Bairro"].map(norm))
        feats = []
        for i, f in enumerate(geo["features"]):
            nb = norm(f["properties"]["bairro"])
            props = {"bairro": f["properties"]["bairro"]}
            if nb in idx.index:
                r = idx.loc[nb]
                if isinstance(r, pd.DataFrame):
                    r = r.iloc[0]
                for k in mk:
                    props[k] = None if pd.isna(r[k]) else float(r[k])
                props["votos22"] = int(r["votos22"])
                props["setores"] = int(r["setores"])
                props["regional"] = r["regional"]
            else:
                for k in mk:
                    props[k] = None
                props["votos22"] = None
                props["setores"] = 0
                props["regional"] = None
            feats.append({"id": str(i), "type": "Feature", "properties": props,
                          "geometry": f["geometry"]})
        gj = {"type": "FeatureCollection", "features": feats}

    # ---- plano de mobilização -------------------------------------------
    def score(row, pesos):
        v = 0.0
        for k, w in pesos.items():
            x = row.get(k)
            if x is None or (isinstance(x, float) and math.isnan(x)):
                return None
            v += w * x
        return round(v, 1)

    vmax = 1 if suprimir22 else (max(1, int(robusto["votos22"].max())) if len(robusto) else 1)
    cons_p = {"sup": .40, "lgbt": .25}
    exp_p = {"rac": .45, "gen": .35}
    linhas = []
    for _, r in robusto.iterrows():
        d = r.to_dict()
        sc = score(d, cons_p)
        se = score(d, exp_p)
        vn = 0 if suprimir22 else 100 * (r["votos22"] or 0) / vmax
        linhas.append({
            "b": r["Bairro"], "reg": r["regional"],
            "lat": round(xy[r["Bairro"]][1], 5) if r["Bairro"] in xy else None,
            "lon": round(xy[r["Bairro"]][0], 5) if r["Bairro"] in xy else None,
            "sup": d.get("sup"), "lgbt": d.get("lgbt"), "gen": d.get("gen"),
            "rac": d.get("rac"),
            "votos22": None if suprimir22 else int(r["votos22"] or 0),
            "setores": int(r["setores"]),
            # Sem a camada de voto os pesos são renormalizados sobre as pautas, em vez
            # de tratar dado ausente como ausência de voto — que inverteria o sentido.
            "cons": None if sc is None else round(sc / .65 if suprimir22 else sc + .35 * vn, 1),
            "exp": None if se is None else round(se / .80 if suprimir22 else se + .20 * (100 - vn), 1),
        })
    mob = {
        "cons": sorted([x for x in linhas if x["cons"] is not None],
                       key=lambda x: -x["cons"])[:12],
        "exp": sorted([x for x in linhas if x["exp"] is not None],
                      key=lambda x: -x["exp"])[:12],
        "pesos": ({"cons": "62% ensino superior + 38% LGBT (pesos renormalizados: a camada de voto de 2022 está suprimida neste município)",
                   "exp": "56% antirracismo + 44% gênero (idem)"} if suprimir22 else
                  {"cons": "40% ensino superior + 25% LGBT + 35% votos 2022",
                   "exp": "45% antirracismo + 35% gênero + 20% ausência de voto"}),
    }

    # ---- quebra por eixo (gráficos de barras) ----------------------------
    quebras = {}
    for ek, en in EIXOS:
        membros = eixo_membros.get(ek, [])
        if len(membros) < 2:
            continue
        ordem = regionais.sort_values(ek, ascending=False)["regional"].tolist()
        quebras[ek] = {
            "titulo": en, "regionais": ordem,
            "vars": [labels[m] for m in membros],
            "values": [[float(regionais.loc[regionais["regional"] == rr, m].iloc[0])
                        for m in membros] for rr in ordem],
        }

    # ---- metadados e ressalvas -------------------------------------------
    dec = int(df["Total_Setores_Município"].dropna().iloc[0]) if \
        df["Total_Setores_Município"].notna().any() else None
    obs = int(df["CD_setor"].nunique())
    meta = {
        "gerado_em": pd.Timestamp.now().strftime("%d/%m/%Y"),
        "unidade": ("bairros do IBGE (Censo 2022)" if geo is not None
                    else "bairros declarados na base CNEFE, sem malha oficial"),
        "regioes_origem": origem_reg,
        "regioes_por_que": ("regionais oficiais publicadas pelo IBGE (distrito/subdistrito)"
                            if origem_reg == "oficial" else
                            "o IBGE não subdivide este município, então os bairros foram "
                            "agrupados em Centro, Norte, Sul, Leste e Oeste pela posição "
                            "relativa ao centroide da cidade"),
        "unidade_por_que": ("A malha de bairros do IBGE cobre este município, e a coluna "
                            "Bairro_Censo casa com ela." if geo is not None else
                            "O IBGE não delimita bairros neste município; a unidade vem do "
                            "campo Bairro da base de endereços, posicionado pelo centroide "
                            "dos seus setores."),
        "setores_declarados": dec, "setores_observados": obs,
        "cobertura": round(100 * obs / dec, 1) if dec else None,
        "min_setores": int(min_setores),
        "min_setores_por_que": (
            "corte padrão do painel de referência" if min_setores == 5 else
            f"corte reduzido para {min_setores}: neste município a unidade de bairro é "
            f"pequena (mediana de {int(bairros[bairros['Bairro']!='Não classificado']['setores'].median())} "
            f"setores por bairro) e o corte de 5 esvaziaria os rankings"),
        "fontes": {
            "2022": f"{os.path.basename(p_ader)} — aderência por setor censitário e votos "
                    f"da Lohanna França (2022), IBGE Censo 2022 + CNEFE",
            "2024": (f"{os.path.basename(p_tse)} — TSE, eleições municipais de 2024"
                     if p_tse else None),
            "geo": (f"{os.path.basename(p_geo)} — malha de bairros IBGE Censo 2022 "
                    f"(SIRGAS 2000)" if p_geo else None),
        },
    }

    return {
        "municipio": mun_nome, "uf": df["UF"].dropna().iloc[0],
        "apelido": apelido, "numero": numero,
        "mk": mk, "labels": labels,
        "eixos": [{"k": k, "nome": n, "membros": eixo_membros.get(k, [])}
                  for k, n in EIXOS if eixo_membros.get(k)],
        "pautas": pautas,
        "geojson": gj,
        "regionais": regionais.to_dict("records"),
        "bairros": bairros.to_dict("records"),
        "setores": [[round(float(r["Latitude_Setor"]), 5), round(float(r["Longitude_Setor"]), 5),
                     r["_bairro"], r["_reg"]]
                    # Os pontos por setor são lidos como cor de faixa, não como número:
                    # inteiro basta e reduz sensivelmente o tamanho do arquivo.
                    + [None if pd.isna(r[k]) else int(round(r[k])) for k in mk]
                    for _, r in tab.iterrows()
                    if pd.notna(r["Latitude_Setor"]) and pd.notna(r["Longitude_Setor"])],
        "tops": tops, "votes22": votes22, "votes24": votes24,
        "over": over, "comp_bairro": comp_bairro,
        "quebras": quebras, "mob": mob, "meta": meta,
    }


def limpar(o):
    """Troca NaN/inf por None em toda a estrutura.

    Um bairro pode não ter nenhum setor medido em alguma pauta; a média sai NaN e,
    serializada, viraria o literal NaN dentro do JS — que o navegador aceita e
    imprime na tela. Aqui isso vira None, que a interface já sabe exibir como '—'."""
    if isinstance(o, dict):
        return {k: limpar(v) for k, v in o.items()}
    if isinstance(o, list):
        return [limpar(v) for v in o]
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--municipio", required=True)
    ap.add_argument("--candidato", required=True)
    ap.add_argument("--numero", default=None,
                    help="número de urna do candidato em 2024 (chave confiável)")
    ap.add_argument("--min-setores", type=int, default=None,
                    help="corte de robustez; se omitido, é calibrado ao município")
    ap.add_argument("--sem-2024", action="store_true",
                    help="o candidato não disputou 2024; o painel fica de camada única")
    ap.add_argument("--suprimir-votos22", default=None, metavar="MOTIVO",
                    help="suprime a camada de votos de 2022 e registra o motivo no painel")
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()

    D = construir(a.municipio, a.candidato, a.numero, a.min_setores,
                  a.suprimir_votos22, a.sem_2024)
    dest = a.saida or f"dados/DATA_{slug(a.candidato)}_{slug(a.municipio)}.json"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    D = limpar(D)
    with open(dest, "w", encoding="utf-8") as f:
        # allow_nan=False faz a gravação falhar em vez de emitir NaN silenciosamente.
        json.dump(D, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    print(f"-> {dest} ({os.path.getsize(dest)/1024:.0f} KB)")
    print(f"   corte de robustez: >= {D['meta']['min_setores']} setores")
    print(f"   métricas: {len(D['mk'])} | bairros: {len(D['bairros'])} | "
          f"regiões: {len(D['regionais'])} | setores: {len(D['setores'])}")
    if D["votes22"]["suprimido"]:
        print(f"   Lohanna 2022: SUPRIMIDA — {D['votes22']['motivo'][:70]}...")
    else:
        print(f"   Lohanna 2022: {D['votes22']['total']:,} votos")
    if D["votes24"] and D["votes24"]["candidato"]:
        c = D["votes24"]["candidato"]
        print(f"   {a.candidato} 2024: {c['votos']:,} votos ({c['pos']}º de {D['votes24']['n_cands']})")


if __name__ == "__main__":
    main()
