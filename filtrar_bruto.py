#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filtrar_bruto.py — recorta os CSVs brutos do TSE (MG inteiro, ~1-2 GB cada) para
os 10 municípios do projeto, lendo em fluxo direto de dentro do .zip.

Não descompacta o arquivo inteiro: lê linha a linha, decodifica latin-1 e grava
apenas as linhas cujo NM_MUNICIPIO normalizado está na lista. Assim o pico de
disco é o do próprio .zip.

    python3 filtrar_bruto.py --ano 2024
    python3 filtrar_bruto.py --ano 2022

Saída: dados/tse<ano>_secao/votos_<ano>_<MUNICIPIO>.csv (separador ';', UTF-8)
"""
import argparse, os, re, sys, unicodedata, zipfile

MUNICIPIOS = [
    "BELO HORIZONTE", "BETIM", "UBERLANDIA", "DIVINOPOLIS", "SAO JOAO DEL REI",
    "PARA DE MINAS", "LAGOA SANTA", "MARIANA", "CONSELHEIRO LAFAIETE", "CURVELO",
]

def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper().replace("-", " ")).strip()

ALVO = {norm(m) for m in MUNICIPIOS}

def nome_arquivo(mun):
    return re.sub(r"[^A-Z0-9]+", "_", norm(mun)).strip("_")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano", required=True, choices=["2022", "2024"])
    ap.add_argument("--zip", default=None)
    a = ap.parse_args()

    zp = a.zip or f"dados/bruto/votacao_secao_{a.ano}_MG.zip"
    membro = f"votacao_secao_{a.ano}_MG.csv"
    saida = f"dados/tse{a.ano}_secao"
    os.makedirs(saida, exist_ok=True)

    z = zipfile.ZipFile(zp)
    with z.open(membro) as fh:
        cab = fh.readline().decode("latin1").rstrip("\r\n")
        cols = [c.strip('"') for c in cab.split(";")]
        i_mun = cols.index("NM_MUNICIPIO")

        handles, contagem = {}, {}
        lidas = 0
        for linha in fh:
            lidas += 1
            txt = linha.decode("latin1")
            # NM_MUNICIPIO nunca contém ';' nos dados do TSE (campos entre aspas,
            # mas o município é um nome simples) — split direto é seguro e rápido.
            campos = txt.split(";")
            if len(campos) <= i_mun:
                continue
            mun = norm(campos[i_mun].strip('"'))
            if mun not in ALVO:
                continue
            h = handles.get(mun)
            if h is None:
                p = os.path.join(saida, f"votos_{a.ano}_{nome_arquivo(mun)}.csv")
                h = handles[mun] = open(p, "w", encoding="utf-8", newline="")
                h.write(cab + "\n")
                contagem[mun] = 0
            h.write(txt.rstrip("\r\n") + "\n")
            contagem[mun] += 1
            if lidas % 2_000_000 == 0:
                print(f"  ... {lidas:,} linhas lidas", file=sys.stderr, flush=True)

    for h in handles.values():
        h.close()

    print(f"\n{a.ano} — {lidas:,} linhas lidas de MG\n")
    print(f"{'MUNICÍPIO':24s}{'LINHAS':>12s}{'ARQUIVO':>12s}")
    print("-" * 48)
    for mun in sorted(contagem):
        p = os.path.join(saida, f"votos_{a.ano}_{nome_arquivo(mun)}.csv")
        print(f"{mun:24s}{contagem[mun]:>12,}{os.path.getsize(p)/1e6:>10.1f} MB")
    faltando = ALVO - set(contagem)
    if faltando:
        print("\nSEM NENHUMA LINHA:", ", ".join(sorted(faltando)))

if __name__ == "__main__":
    main()
