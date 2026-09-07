#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo_locais.py — extrai a geocodificação dos locais de votação (2022 ou 2024)
(lat/lon, bairro, endereço, eleitorado) para os 10 municípios do projeto.

Fonte: eleitorado_local_votacao_2024.csv (TSE), que traz NR_LATITUDE/NR_LONGITUDE
por seção. Aqui a seção é colapsada para o local: uma linha por
(município, zona, local), com o eleitorado somado sobre as seções distintas.

    python3 geo_locais.py --ano 2024
    python3 geo_locais.py --ano 2022

Saída: dados/geo/locais_<ano>.csv
"""
import argparse, csv, os, re, sys, unicodedata

ENTRADA = "dados/bruto/eleitorado_local_votacao_{ano}.csv"
SAIDA = "dados/geo/locais_{ano}.csv"

MUNICIPIOS = [
    "BELO HORIZONTE", "BETIM", "UBERLANDIA", "DIVINOPOLIS", "SAO JOAO DEL REI",
    "PARA DE MINAS", "LAGOA SANTA", "MARIANA", "CONSELHEIRO LAFAIETE", "CURVELO",
]

def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.upper().replace("-", " ")).strip()

ALVO = {norm(m) for m in MUNICIPIOS}

def num(v):
    """O TSE marca coordenada ausente com -1 (e às vezes 0)."""
    try:
        x = float(str(v).replace(",", "."))
    except ValueError:
        return None
    return None if x == -1 or x == 0 else x

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano", default="2024", choices=["2022", "2024"])
    ano = ap.parse_args().ano
    entrada, saida = ENTRADA.format(ano=ano), SAIDA.format(ano=ano)
    os.makedirs("dados/geo", exist_ok=True)
    locais = {}
    secoes_vistas = set()
    lidas = 0
    with open(entrada, encoding="latin1", newline="") as fh:
        r = csv.DictReader(fh, delimiter=";", quotechar='"')
        for row in r:
            lidas += 1
            if row.get("SG_UF") != "MG":
                continue
            mun = norm(row["NM_MUNICIPIO"])
            if mun not in ALVO:
                continue
            if row.get("NR_TURNO") not in (None, "", "1"):
                continue
            chave = (mun, row["NR_ZONA"], row["NR_LOCAL_VOTACAO"])
            lat, lon = num(row["NR_LATITUDE"]), num(row["NR_LONGITUDE"])
            d = locais.get(chave)
            if d is None:
                d = locais[chave] = {
                    "NM_MUNICIPIO": row["NM_MUNICIPIO"],
                    "NR_ZONA": row["NR_ZONA"],
                    "NR_LOCAL_VOTACAO": row["NR_LOCAL_VOTACAO"],
                    "NM_LOCAL_VOTACAO": row["NM_LOCAL_VOTACAO"],
                    "DS_ENDERECO": row["DS_ENDERECO"],
                    "NM_BAIRRO": row["NM_BAIRRO"],
                    "DS_TIPO_LOCAL": row.get("DS_TIPO_LOCAL", ""),
                    "NR_LATITUDE": lat,
                    "NR_LONGITUDE": lon,
                    "QT_ELEITORES": 0,
                    "QT_SECOES": 0,
                }
            # coordenada pode faltar em algumas seções do mesmo local
            if d["NR_LATITUDE"] is None and lat is not None:
                d["NR_LATITUDE"], d["NR_LONGITUDE"] = lat, lon
            # cada seção conta uma única vez (o arquivo repete a seção por eleição)
            sk = chave + (row["NR_SECAO"],)
            if sk not in secoes_vistas:
                secoes_vistas.add(sk)
                d["QT_SECOES"] += 1
                try:
                    d["QT_ELEITORES"] += int(row["QT_ELEITOR_SECAO"] or 0)
                except ValueError:
                    pass

    campos = list(next(iter(locais.values())).keys())
    with open(saida, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for k in sorted(locais):
            w.writerow(locais[k])

    print(f"{ano} · {lidas:,} linhas lidas · {len(locais):,} locais nos 10 municípios\n")
    print(f"{'MUNICÍPIO':24s}{'LOCAIS':>8s}{'C/ COORD':>10s}{'SEÇÕES':>8s}{'ELEITORES':>12s}")
    print("-" * 62)
    por_mun = {}
    for d in locais.values():
        m = por_mun.setdefault(norm(d["NM_MUNICIPIO"]), [0, 0, 0, 0])
        m[0] += 1
        m[1] += 1 if d["NR_LATITUDE"] is not None else 0
        m[2] += d["QT_SECOES"]
        m[3] += d["QT_ELEITORES"]
    for m in sorted(por_mun):
        n, c, s, e = por_mun[m]
        print(f"{m:24s}{n:>8,}{c:>10,}{s:>8,}{e:>12,}")

if __name__ == "__main__":
    main()
