#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agregar_2024.py — consolida os CSVs do TSE 2024 por seção em agregados por local
de votação, um arquivo por município.

Regra do §3.2.1: cada seção entra uma única vez. A agregação soma QT_VOTOS por
(município, zona, local, cargo, candidato) e conta as seções distintas, de modo que
o total por candidato reproduz exatamente o total oficial do município.

Entrada : dados/tse2024_secao/votos_2024_<MUNICIPIO>[_parteNdeM].csv
Saída   : dados/tse2024_locais/locais_<municipio>.csv
"""
import glob, os, re, sys, unicodedata
from collections import defaultdict
import pandas as pd

ENT = "dados/tse2024_secao"
SAI = "dados/tse2024_locais"

def norm(s):
    s = unicodedata.normalize("NFKD", str(s) if s is not None else "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper().replace("-", " ").strip()

def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", norm(s).lower()).strip("_")

CHAVE = ["NM_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO",
         "DS_LOCAL_VOTACAO_ENDERECO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL",
         "SQ_CANDIDATO"]

def familia(nome):
    """votos_2024_BELO_HORIZONTE_parte3de19.csv -> belo_horizonte"""
    b = os.path.basename(nome)[len("votos_2024_"):-len(".csv")]
    return slug(re.sub(r"_parte\d+de\d+$", "", b))

def main():
    os.makedirs(SAI, exist_ok=True)
    grupos = defaultdict(list)
    for p in sorted(glob.glob(f"{ENT}/*.csv")):
        grupos[familia(p)].append(p)

    if not grupos:
        sys.exit(f"nada em {ENT}")

    print(f"{'MUNICÍPIO':24s}{'PARTES':>7s}{'LINHAS':>10s}{'LOCAIS':>8s}{'SEÇÕES':>8s}"
          f"{'CANDS':>7s}{'VOTOS VEREADOR':>16s}")
    print("-" * 80)
    for mun, partes in sorted(grupos.items()):
        pedacos, linhas = [], 0
        for p in partes:
            for ch in pd.read_csv(p, sep=";", dtype=str, encoding="utf-8",
                                  chunksize=300_000, low_memory=False):
                linhas += len(ch)
                ch["QT_VOTOS"] = pd.to_numeric(ch["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
                ch["_sec"] = ch["NR_ZONA"].astype(str) + "-" + ch["NR_SECAO"].astype(str)
                g = ch.groupby(CHAVE, dropna=False).agg(
                    QT_VOTOS=("QT_VOTOS", "sum"), QT_SECOES=("_sec", "nunique")).reset_index()
                pedacos.append(g)

        df = pd.concat(pedacos, ignore_index=True)
        # Reagrega: um mesmo local aparece em partes e blocos diferentes.
        df = df.groupby(CHAVE, dropna=False).agg(
            QT_VOTOS=("QT_VOTOS", "sum"), QT_SECOES=("QT_SECOES", "sum")).reset_index()

        dest = os.path.join(SAI, f"locais_{mun}.csv")
        df.to_csv(dest, index=False, sep=";", encoding="utf-8")

        ver = df[df["DS_CARGO"].map(norm) == "VEREADOR"]
        nom = ver[pd.to_numeric(ver["SQ_CANDIDATO"], errors="coerce") > 0]
        print(f"{mun[:24]:24s}{len(partes):>7d}{linhas:>10,}{df['NR_LOCAL_VOTACAO'].nunique():>8d}"
              f"{int(ver['QT_SECOES'].max()):>8d}{nom['NR_VOTAVEL'].nunique():>7d}"
              f"{nom['QT_VOTOS'].sum():>16,}")

    print(f"\n-> {SAI}/ ({sum(os.path.getsize(os.path.join(SAI,f)) for f in os.listdir(SAI))/1e6:.1f} MB)")

if __name__ == "__main__":
    main()
