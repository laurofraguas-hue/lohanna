#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preparar_dados.py — reduz os dados brutos do TSE ao recorte dos 10 municípios
dos candidatos aliados, para que os arquivos caibam no limite de anexo.

POR QUE ISTO EXISTE
-------------------
O ambiente onde o painel é gerado não alcança o Google Drive (egress bloqueado)
e o conector do Drive tem teto de 10 MB por arquivo. Os arquivos brutos somam
~679 MB. Este script roda NA SUA MÁQUINA, filtra e agrega, e produz CSVs de
poucos MB que podem ser anexados direto na conversa.

USO
---
    python3 preparar_dados.py --entrada /caminho/da/pasta/com/os/zips
    # saída em ./dados_filtrados/

Requisitos: python3 + pandas.  (pip install pandas openpyxl)

O QUE ELE FAZ
-------------
1. Filtra tudo para os 10 municípios da planilha de candidatos.
2. Agrega os votos de SEÇÃO para LOCAL DE VOTAÇÃO (soma QT_VOTOS agrupando por
   município + zona + local + candidato). Isso corta o tamanho em ~1 ordem de
   grandeza e é a granularidade que o painel usa de fato — sem dupla contagem,
   cada seção entra uma única vez.
3. Mantém 2024 (Vereador + Prefeito) e 2022 (Deputado Estadual + Federal) em
   arquivos SEPARADOS. As duas camadas nunca se misturam.
4. Extrai a geocodificação dos locais de votação (bairro, lat, lon, eleitorado).
5. Filtra a tabela de aderência a pautas pelos mesmos municípios.
6. Imprime o inventário de cada arquivo (colunas, nº de linhas, tamanho).
"""

import argparse
import io
import os
import sys
import unicodedata
import zipfile

import pandas as pd

# --------------------------------------------------------------------------
# Os 10 municípios da planilha "Mapeamento candidatos 2026.xlsx"
# --------------------------------------------------------------------------
MUNICIPIOS = [
    "BELO HORIZONTE",       # Professor Gabriel Mendes, Sara Vitral
    "BETIM",                # Professor Gabriel Mendes
    "UBERLANDIA",           # Fabão
    "DIVINOPOLIS",          # Kell Silva
    "SAO JOAO DEL REI",     # Sinara Campos
    "PARA DE MINAS",        # Irene Melo Franco
    "LAGOA SANTA",          # Marcelo Monteiro
    "MARIANA",              # Pedro Sousa
    "CONSELHEIRO LAFAIETE", # Damires Rinarlly
    "CURVELO",              # Douglas Verissimo
]

CARGOS_2024 = ["VEREADOR", "PREFEITO"]
CARGOS_2022 = ["DEPUTADO ESTADUAL", "DEPUTADO FEDERAL"]

SEP = ";"
ENCODINGS = ["latin-1", "utf-8-sig", "utf-8"]


def norm(s):
    """Maiúsculas, sem acento, sem hífen — para casar nomes de município."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper().replace("-", " ").replace("'", "").strip()


ALVO = {norm(m) for m in MUNICIPIOS}


def achar_col(cols, *candidatas):
    """Localiza uma coluna pelo nome, tolerando variações. Nada é presumido:
    se não achar, devolve None e o chamador decide."""
    mapa = {norm(c).replace(" ", "_"): c for c in cols}
    for cand in candidatas:
        k = norm(cand).replace(" ", "_")
        if k in mapa:
            return mapa[k]
    return None


def abrir_membros(caminho):
    """Devolve [(nome, bytes_ou_path)] dos CSVs, seja zip ou csv solto."""
    if caminho.lower().endswith(".zip"):
        with zipfile.ZipFile(caminho) as z:
            nomes = [n for n in z.namelist() if n.lower().endswith((".csv", ".txt"))]
            if not nomes:
                print(f"  !! nenhum CSV dentro de {os.path.basename(caminho)}: "
                      f"{z.namelist()[:10]}")
            for n in nomes:
                yield n, z.read(n)
    else:
        yield os.path.basename(caminho), None


def ler_chunks(caminho, membro, dados, chunksize=400_000):
    """Lê o CSV em pedaços, tentando as codificações usuais do TSE."""
    ultimo_erro = None
    for enc in ENCODINGS:
        try:
            fonte = io.BytesIO(dados) if dados is not None else caminho
            it = pd.read_csv(fonte, sep=SEP, encoding=enc, dtype=str,
                             chunksize=chunksize, low_memory=False,
                             on_bad_lines="warn")
            primeiro = True
            for ch in it:
                if primeiro:
                    print(f"  codificação={enc} · colunas={list(ch.columns)}")
                    primeiro = False
                yield ch
            return
        except UnicodeDecodeError as e:
            ultimo_erro = e
            continue
    raise RuntimeError(f"não consegui decodificar {membro}: {ultimo_erro}")


def processar_votacao(caminho, cargos, rotulo, saida):
    """Filtra por município + cargo e agrega seção -> local de votação."""
    print(f"\n=== {rotulo}: {os.path.basename(caminho)}")
    if not os.path.exists(caminho):
        print("  !! arquivo não encontrado — pulando")
        return None

    partes, total_lidas, total_mantidas = [], 0, 0
    cargos_vistos = set()

    for membro, dados in abrir_membros(caminho):
        print(f"  membro: {membro}")
        for ch in ler_chunks(caminho, membro, dados):
            total_lidas += len(ch)
            c_mun = achar_col(ch.columns, "NM_MUNICIPIO")
            c_cargo = achar_col(ch.columns, "DS_CARGO")
            c_votos = achar_col(ch.columns, "QT_VOTOS")
            if not (c_mun and c_cargo and c_votos):
                print(f"  !! colunas essenciais ausentes; achei: {list(ch.columns)}")
                return None

            cargos_vistos.update(ch[c_cargo].dropna().unique())

            m = ch[c_mun].map(norm).isin(ALVO)
            m &= ch[c_cargo].map(norm).isin({norm(c) for c in cargos})
            ch = ch[m]
            if ch.empty:
                continue

            ch[c_votos] = pd.to_numeric(ch[c_votos], errors="coerce").fillna(0).astype(int)

            # Agrega seção -> local de votação. Cada seção entra uma única vez.
            chaves = [c for c in [
                achar_col(ch.columns, "SG_UF"),
                achar_col(ch.columns, "CD_MUNICIPIO"),
                c_mun,
                achar_col(ch.columns, "NR_ZONA"),
                achar_col(ch.columns, "NR_LOCAL_VOTACAO"),
                c_cargo,
                achar_col(ch.columns, "NR_VOTAVEL"),
                achar_col(ch.columns, "NM_VOTAVEL"),
                achar_col(ch.columns, "SG_PARTIDO"),
                achar_col(ch.columns, "NR_PARTIDO"),
            ] if c]

            n_secoes = achar_col(ch.columns, "NR_SECAO")
            agg = {c_votos: "sum"}
            if n_secoes:
                ch["_secoes"] = ch[n_secoes]
                agg["_secoes"] = "nunique"

            g = ch.groupby(chaves, dropna=False, as_index=False).agg(agg)
            partes.append(g)
            total_mantidas += len(g)

    if not partes:
        print(f"  !! nada casou. Cargos encontrados no arquivo: "
              f"{sorted(cargos_vistos)[:20]}")
        return None

    df = pd.concat(partes, ignore_index=True)
    # Reagrega: um mesmo local pode ter caído em chunks diferentes.
    chaves = [c for c in df.columns if c not in ("QT_VOTOS", "_secoes")]
    agg = {"QT_VOTOS": "sum"}
    if "_secoes" in df.columns:
        agg["_secoes"] = "sum"
    df = df.groupby(chaves, dropna=False, as_index=False).agg(agg)
    if "_secoes" in df.columns:
        df = df.rename(columns={"_secoes": "QT_SECOES"})

    df.to_csv(saida, index=False, sep=SEP, encoding="utf-8")
    mb = os.path.getsize(saida) / 1e6
    print(f"  lidas {total_lidas:,} linhas -> {len(df):,} linhas agregadas")
    print(f"  -> {saida} ({mb:.1f} MB)")
    for mun, sub in df.groupby(achar_col(df.columns, "NM_MUNICIPIO")):
        print(f"     {mun:24s} {sub['QT_VOTOS'].sum():>10,} votos")
    return df


def processar_locais(caminho, rotulo, saida):
    """Extrai bairro + lat/lon + eleitorado de cada local de votação."""
    print(f"\n=== {rotulo}: {os.path.basename(caminho)}")
    if not os.path.exists(caminho):
        print("  !! arquivo não encontrado — pulando")
        return None

    partes = []
    for membro, dados in abrir_membros(caminho):
        print(f"  membro: {membro}")
        for ch in ler_chunks(caminho, membro, dados):
            c_mun = achar_col(ch.columns, "NM_MUNICIPIO")
            if not c_mun:
                print(f"  !! sem NM_MUNICIPIO; colunas: {list(ch.columns)}")
                return None
            ch = ch[ch[c_mun].map(norm).isin(ALVO)]
            if not ch.empty:
                partes.append(ch)

    if not partes:
        print("  !! nada casou")
        return None

    df = pd.concat(partes, ignore_index=True).drop_duplicates()
    df.to_csv(saida, index=False, sep=SEP, encoding="utf-8")
    mb = os.path.getsize(saida) / 1e6
    print(f"  -> {saida} ({len(df):,} linhas, {mb:.1f} MB)")

    c_bairro = achar_col(df.columns, "NM_BAIRRO")
    c_lat = achar_col(df.columns, "NR_LATITUDE")
    print(f"  bairro={c_bairro or 'AUSENTE'} · latitude={c_lat or 'AUSENTE'}")
    if not c_lat:
        print("  !! ATENÇÃO: sem coordenadas, não há como montar os mapas.")
    return df


def processar_aderencia(caminho, saida):
    """Filtra a tabela de aderência a pautas pelos mesmos municípios."""
    print(f"\n=== ADERÊNCIA A PAUTAS: {os.path.basename(caminho)}")
    if not os.path.exists(caminho):
        print("  !! arquivo não encontrado — pulando")
        return None

    xl = pd.ExcelFile(caminho)
    print(f"  abas: {xl.sheet_names}")
    escritos = []
    for aba in xl.sheet_names:
        df = xl.parse(aba, dtype=str)
        print(f"  -- aba '{aba}': {df.shape[0]:,} linhas x {df.shape[1]} colunas")
        print(f"     colunas: {list(df.columns)}")

        c_mun = achar_col(df.columns, "NM_MUNICIPIO", "MUNICIPIO", "municipio",
                          "cidade", "NM_MUN")
        if not c_mun:
            print("     !! sem coluna de município reconhecível — aba salva inteira "
                  "se couber, senão precisa de recorte manual")
            if len(df) <= 200_000:
                dest = f"{saida}_{norm(aba).replace(' ', '_')}.csv"
                df.to_csv(dest, index=False, sep=SEP, encoding="utf-8")
                escritos.append(dest)
            continue

        sub = df[df[c_mun].map(norm).isin(ALVO)]
        print(f"     filtrado por '{c_mun}': {len(sub):,} linhas")
        if sub.empty:
            print(f"     amostra de municípios no arquivo: "
                  f"{df[c_mun].dropna().unique()[:10].tolist()}")
            continue
        dest = f"{saida}_{norm(aba).replace(' ', '_')}.csv"
        sub.to_csv(dest, index=False, sep=SEP, encoding="utf-8")
        print(f"     -> {dest} ({os.path.getsize(dest)/1e6:.1f} MB)")
        escritos.append(dest)
    return escritos


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", required=True,
                    help="pasta com os zips/xlsx baixados do Drive")
    ap.add_argument("--saida", default="dados_filtrados",
                    help="pasta de saída (padrão: ./dados_filtrados)")
    a = ap.parse_args()

    os.makedirs(a.saida, exist_ok=True)
    E = lambda n: os.path.join(a.entrada, n)
    S = lambda n: os.path.join(a.saida, n)

    print("Municípios do recorte:", ", ".join(MUNICIPIOS))

    processar_votacao(E("votacao_secao_2024_MG.zip"), CARGOS_2024,
                      "VOTAÇÃO 2024 (vereador + prefeito)", S("votos_2024_locais.csv"))
    processar_votacao(E("votacao_secao_2022_MG.zip"), CARGOS_2022,
                      "VOTAÇÃO 2022 (dep. estadual + federal)", S("votos_2022_locais.csv"))
    processar_locais(E("eleitorado_local_votacao_2024.zip"),
                     "LOCAIS DE VOTAÇÃO 2024", S("locais_2024.csv"))
    processar_locais(E("eleitorado_local_votacao_2022.zip"),
                     "LOCAIS DE VOTAÇÃO 2022", S("locais_2022.csv"))
    processar_aderencia(E("tabela_oportunidades_lohanna_franca_mg_2022.xlsx"),
                        S("aderencia"))

    print("\n" + "=" * 70)
    print("RESULTADO — anexe estes arquivos na conversa:")
    total = 0
    for f in sorted(os.listdir(a.saida)):
        p = os.path.join(a.saida, f)
        mb = os.path.getsize(p) / 1e6
        total += mb
        marca = "  <-- ainda grande, ver nota abaixo" if mb > 25 else ""
        print(f"  {f:42s} {mb:8.1f} MB{marca}")
    print(f"  {'TOTAL':42s} {total:8.1f} MB")
    print("\nSe algum arquivo passar de ~25 MB, rode de novo com menos municípios")
    print("(edite a lista MUNICIPIOS no topo) — dá para fazer em duas levas.")


if __name__ == "__main__":
    sys.exit(main())
