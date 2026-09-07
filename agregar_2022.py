#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agregar_2022.py — votos da Lohanna França em 2022 por LOCAL DE VOTAÇÃO.

POR QUE ISTO EXISTE
-------------------
A coluna `Votos_Candidato` da tabela de aderência NÃO é o voto do setor censitário:
é o total do LOCAL DE VOTAÇÃO mais próximo, repetido em cada setor que aquele local
atende. Somá-la sobre os setores multiplica o voto pelo número de setores por local —
uma inflação de 3× a 11×, conforme o município. (Verificado: em Uberlândia 96,8% dos
setores têm exatamente o valor do local mais próximo; em Divinópolis, 91,4%.)

Este script vai à fonte: `votacao_secao_2022_MG`, cargo de Deputado Estadual, que é o
cargo que a Lohanna disputou em 2022. Cada seção entra uma única vez e é somada ao seu
local de votação — a mesma unidade da camada de 2024, o que torna as duas comparáveis.

Entrada : dados/tse2022_secao/votos_2022_<MUNICIPIO>.csv
Saída   : dados/tse2022_locais/locais_<municipio>.csv
"""
import glob, os, re, sys, unicodedata
import pandas as pd

ENT, SAI = "dados/tse2022_secao", "dados/tse2022_locais"
CANDIDATA = "LOHANNA"
CARGO = "DEPUTADO ESTADUAL"

def norm(s):
    s = unicodedata.normalize("NFKD", str(s) if s is not None else "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper().replace("-", " ")).strip()

def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", norm(s).lower()).strip("_")

def main():
    os.makedirs(SAI, exist_ok=True)
    arquivos = sorted(glob.glob(f"{ENT}/*.csv"))
    if not arquivos:
        sys.exit(f"nada em {ENT}")

    print(f"{'MUNICÍPIO':24s}{'LOCAIS':>8s}{'C/ VOTO':>9s}{'SEÇÕES':>8s}"
          f"{'NOMINAL EST.':>14s}{'LOHANNA':>10s}{'POSIÇÃO':>10s}")
    print("-" * 83)
    for p in arquivos:
        mun = slug(os.path.basename(p)[len("votos_2022_"):-len(".csv")])
        por_local, por_cand, secoes = {}, {}, {}
        nm_completo = None
        for ch in pd.read_csv(p, sep=";", dtype=str, chunksize=300_000, low_memory=False):
            ch = ch[ch["DS_CARGO"].map(norm) == CARGO]
            if ch.empty:
                continue
            ch = ch.copy()
            ch["QT_VOTOS"] = pd.to_numeric(ch["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
            ch["_k"] = ch["NR_ZONA"].astype(str) + "-" + ch["NR_LOCAL_VOTACAO"].astype(str)
            nominal = ch[pd.to_numeric(ch["SQ_CANDIDATO"], errors="coerce") > 0]
            for k, v in nominal.groupby("_k")["QT_VOTOS"].sum().items():
                por_local[k] = por_local.get(k, 0) + int(v)
            for k, v in nominal.groupby(["NR_VOTAVEL", "NM_VOTAVEL"])["QT_VOTOS"].sum().items():
                por_cand[k] = por_cand.get(k, 0) + int(v)
            eu = nominal[nominal["NM_VOTAVEL"].map(norm).str.contains(CANDIDATA, na=False)]
            if len(eu):
                nm_completo = eu["NM_VOTAVEL"].iloc[0]
                for k, v in eu.groupby("_k")["QT_VOTOS"].sum().items():
                    secoes[k] = secoes.get(k, 0) + int(v)

        if not por_local:
            print(f"{mun[:24]:24s}{'—':>8s}   sem cargo de deputado estadual no arquivo")
            continue

        info = {}
        for ch in pd.read_csv(p, sep=";", dtype=str, chunksize=300_000, low_memory=False):
            ch = ch[ch["DS_CARGO"].map(norm) == CARGO]
            if ch.empty:
                continue
            ch = ch.copy()
            ch["_k"] = ch["NR_ZONA"].astype(str) + "-" + ch["NR_LOCAL_VOTACAO"].astype(str)
            for _, r in ch.drop_duplicates("_k").iterrows():
                info.setdefault(r["_k"], (r["NR_ZONA"], r["NR_LOCAL_VOTACAO"],
                                          r["NM_LOCAL_VOTACAO"], r["DS_LOCAL_VOTACAO_ENDERECO"]))

        linhas = [{"NR_ZONA": info[k][0], "NR_LOCAL_VOTACAO": info[k][1],
                   "NM_LOCAL_VOTACAO": info[k][2], "DS_LOCAL_VOTACAO_ENDERECO": info[k][3],
                   "QT_VOTOS_NOMINAIS": por_local[k], "QT_VOTOS_LOHANNA": secoes.get(k, 0)}
                  for k in sorted(por_local)]
        pd.DataFrame(linhas).to_csv(os.path.join(SAI, f"locais_{mun}.csv"),
                                    index=False, sep=";", encoding="utf-8")

        ordem = sorted(por_cand.values(), reverse=True)
        meu = sum(secoes.values())
        pos = ordem.index(meu) + 1 if meu in ordem else None
        print(f"{mun[:24]:24s}{len(linhas):>8d}{sum(1 for x in linhas if x['QT_VOTOS_LOHANNA']):>9d}"
              f"{'':>8s}{sum(por_local.values()):>14,}{meu:>10,}"
              f"{(str(pos)+'º de '+str(len(por_cand))) if pos else '—':>10s}")

    print(f"\n-> {SAI}/ ({sum(os.path.getsize(os.path.join(SAI,f)) for f in os.listdir(SAI))/1e6:.2f} MB)"
          f"\n   candidata: {nm_completo}")

if __name__ == "__main__":
    main()
