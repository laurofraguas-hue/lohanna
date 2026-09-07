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


def regioes_oficiais(geo):
    """bairro -> regional, a partir do campo `regiao` da malha do IBGE."""
    if not geo:
        return {}
    return {f["properties"]["bairro"]: f["properties"].get("regiao")
            for f in geo["features"] if f["properties"].get("regiao")}


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

    # ---- camada 2022 -----------------------------------------------------
    if suprimir22:
        # Município cujo Votos_Candidato está em escala incompatível com o setor
        # censitário. Suprimir é a aplicação literal da regra de não inventar dado:
        # o índice de aderência continua íntegro, só a contagem sai.
        tab["_votos22"] = 0
        bairros["votos22"] = 0
        regionais["votos22"] = 0

    total22 = int(tab["_votos22"].sum())
    v22_reg = []
    for _, r in regionais.sort_values("votos22", ascending=False).iterrows():
        sub = (bairros[bairros["regional"] == r["regional"]]
               .sort_values("votos22", ascending=False))
        v22_reg.append({
            "regional": r["regional"], "votos": int(r["votos22"]), "setores": int(r["setores"]),
            "bairros": [{"b": x["Bairro"], "v": int(x["votos22"]), "s": int(x["setores"])}
                        for _, x in sub.iterrows() if x["votos22"] > 0],
        })
    top_b = bairros.sort_values("votos22", ascending=False).iloc[0]
    votes22 = {
        "total": None if suprimir22 else total22,
        "suprimido": bool(suprimir22), "motivo": suprimir22,
        "granularidade": "setor censitário",
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
    votes24 = None
    if tse is not None and not sem2024:
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
