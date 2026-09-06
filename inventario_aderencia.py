#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inventario_aderencia.py — inventário das tabelas de oportunidade (aderência a pautas).

Responde, por município e sem presumir nada:
  - quem é o candidato e de que ano são os votos;
  - qual a unidade real de uma linha e quanta duplicação existe;
  - o total de votos correto, contando cada setor UMA ÚNICA VEZ (§3.2.1);
  - quais eixos e pautas existem naquele município;
  - se os bairros casam com a malha do IBGE, e por qual coluna.
"""

import glob
import json
import os
import unicodedata

import pandas as pd


def norm(s):
    s = unicodedata.normalize("NFKD", str(s) if s is not None else "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper().replace("-", " ").strip()


def slug(s):
    return norm(s).lower().replace(" ", "_")


def carregar_ibge(mun):
    """Bairros da malha do IBGE para o município, se existir."""
    for cand in (slug(mun), slug(mun).replace("sao_joao_del_rei", "sao_joao_del_rei")):
        p = f"dados/geo/bairros_{cand}.geojson"
        if os.path.exists(p):
            fc = json.load(open(p, encoding="utf-8"))
            return {norm(f["properties"]["bairro"]) for f in fc["features"]}
    return None


def inventariar(path):
    df = pd.read_excel(path)
    mun = df["Município"].dropna().iloc[0]
    print("=" * 94)
    print(f"### {mun.upper()}   ({os.path.basename(path)}, {os.path.getsize(path)/1e6:.2f} MB)")
    print("=" * 94)

    anos = sorted(df["Ano"].dropna().unique())
    cands = sorted(df["Candidato"].dropna().unique())
    print(f"Candidato: {cands}")
    print(f"Ano......: {anos}")

    n_set = df["CD_setor"].nunique()
    print(f"\nLinhas: {len(df):,} | setores censitários: {n_set} | "
          f"pares (setor,variável): {df.groupby(['CD_setor','Variável']).ngroups:,}")
    dup = len(df) - df.groupby(["CD_setor", "Variável"]).ngroups
    print(f"Linhas excedentes por duplicação de (setor,variável): {dup:,}")

    # ---- §3.2.1: Votos_Candidato replicado ----
    g = df.groupby("CD_setor")["Votos_Candidato"].nunique()
    constante = (g > 1).sum() == 0
    ingenua = df["Votos_Candidato"].sum()
    correto = df.drop_duplicates(subset=["CD_setor"])["Votos_Candidato"].sum()
    print(f"\nVOTOS DE {cands[0].split()[0]} EM {anos[0]}")
    print(f"  Votos_Candidato constante dentro do setor: {'SIM' if constante else 'NÃO'}")
    print(f"  soma ingênua (toda linha) .......... {ingenua:>10,.0f}")
    print(f"  soma correta (1 setor = 1 vez) ..... {correto:>10,.0f}   <- usar este")
    if correto:
        print(f"  fator de inflação .................. {ingenua/correto:>10.1f}x")

    # ---- eixos e pautas ----
    var = df["Variável"].dropna()
    eixos = {}
    for v in var.unique():
        eixo = v.split(" - ")[0].strip()
        eixos.setdefault(eixo, []).append(v.split(" - ", 1)[1].strip())
    print(f"\nEIXOS TEMÁTICOS: {len(eixos)} | pautas: {var.nunique()}")
    for e in sorted(eixos):
        print(f"  {e} ({len(eixos[e])})")
        for p in sorted(eixos[e]):
            print(f"      · {p}")

    # ---- junção geográfica ----
    ibge = carregar_ibge(mun)
    bc = {norm(x) for x in df["Bairro_Censo"].dropna().unique()} - {"—", "", "NAN"}
    br = {norm(x) for x in df["Bairro"].dropna().unique()} - {"—", "", "NAN"}
    sem_bc = (df["Bairro_Censo"].map(norm).isin(["—", "", "NAN"])).sum()
    print(f"\nGEOGRAFIA")
    print(f"  Bairro (bruto): {len(br)} valores | Bairro_Censo: {len(bc)} valores")
    print(f"  linhas sem Bairro_Censo ('—'): {sem_bc:,} de {len(df):,} "
          f"({100*sem_bc/len(df):.1f}%)")
    if ibge is None:
        print(f"  malha do IBGE: AUSENTE para este município")
        tem_xy = df[["Latitude_Setor", "Longitude_Setor"]].notna().all(axis=1).sum()
        print(f"  fallback: {tem_xy:,} linhas têm Latitude_Setor/Longitude_Setor "
              f"-> mapa de pontos ou clusters")
    else:
        print(f"  malha do IBGE: {len(ibge)} bairros")
        print(f"  Bairro_Censo ∩ IBGE: {len(bc & ibge)}/{len(bc)}"
              f"   |   Bairro ∩ IBGE: {len(br & ibge)}/{len(br)}")
        falta = sorted(bc - ibge)
        if falta:
            print(f"  em Bairro_Censo mas não no IBGE: {falta}")
        orfaos = sorted(ibge - bc)
        if orfaos:
            print(f"  no IBGE mas sem dado: {orfaos}")

    # ---- setores por bairro (filtro de robustez do §3.2.3) ----
    por_b = df.drop_duplicates(subset=["CD_setor"]).groupby(
        df.drop_duplicates(subset=["CD_setor"])["Bairro_Censo"].map(norm)).size()
    por_b = por_b.drop(labels=[x for x in ["—", "", "NAN"] if x in por_b.index],
                       errors="ignore")
    if len(por_b):
        print(f"\n  setores por bairro (Bairro_Censo): mediana {por_b.median():.0f}, "
              f"máx {por_b.max()}, bairros com >=5 setores: {(por_b>=5).sum()} de {len(por_b)}")
    print()
    return dict(municipio=mun, ano=anos[0], candidato=cands[0], setores=n_set,
                votos=int(correto), inflacao=round(ingenua/correto, 1) if correto else None,
                pautas=var.nunique(), eixos=len(eixos), ibge=bool(ibge))


def main():
    resumo = [inventariar(p) for p in sorted(glob.glob("dados/aderencia/*.xlsx"))]
    print("=" * 94)
    print("RESUMO")
    print("=" * 94)
    print(f"{'MUNICÍPIO':22s} {'ANO':>5s} {'SETORES':>8s} {'VOTOS':>8s} {'INFL.':>7s} "
          f"{'PAUTAS':>7s} {'EIXOS':>6s} {'IBGE':>6s}")
    for r in resumo:
        print(f"{r['municipio'][:22]:22s} {r['ano']:>5d} {r['setores']:>8d} "
              f"{r['votos']:>8,d} {str(r['inflacao'])+'x':>7s} {r['pautas']:>7d} "
              f"{r['eixos']:>6d} {'sim' if r['ibge'] else 'NÃO':>6s}")
    json.dump(resumo, open("dados/aderencia/_resumo.json", "w"),
              ensure_ascii=False, indent=2, default=int)


if __name__ == "__main__":
    main()
