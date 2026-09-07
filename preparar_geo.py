#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preparar_geo.py — extrai a malha de bairros do IBGE (Censo 2022) para os
municípios do projeto e gera GeoJSON simplificado, pronto para embutir no painel.

Entrada:  shapefile MG_bairros_CD2022 (IBGE, Censo 2022, SIRGAS 2000 / EPSG:4674)
Saída:    dados/geo/bairros_<municipio>.geojson

A simplificação usa Douglas-Peucker (shapely) com tolerância em graus e mantém a
topologia de cada polígono. O objetivo é caber no orçamento de ~2 MB por painel
somando geometria + dados, com os polígonos ainda reconhecíveis no mapa.

Sobre a projeção: o IBGE entrega em SIRGAS 2000 (EPSG:4674). SIRGAS 2000 e WGS 84
(EPSG:4326) diferem por menos de 1 m no Brasil — irrelevante na escala de um mapa
de bairros — então as coordenadas vão para o GeoJSON como lon/lat sem reprojeção,
e o rodapé do painel registra isso, como faz o painel de referência.
"""

import argparse
import json
import os
import unicodedata

import shapefile
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

MUNICIPIOS = [
    "BELO HORIZONTE", "BETIM", "UBERLANDIA", "DIVINOPOLIS", "SAO JOAO DEL REI",
    "PARA DE MINAS", "LAGOA SANTA", "MARIANA", "CONSELHEIRO LAFAIETE", "CURVELO",
]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper().replace("-", " ").strip()


def slug(s):
    return norm(s).lower().replace(" ", "_")


def conta_vertices(coords):
    """Conta pares [x, y] em qualquer profundidade de aninhamento."""
    if isinstance(coords[0], (int, float)):
        return 1
    return sum(conta_vertices(c) for c in coords)


def uniao_robusta(geoms):
    """União tolerante a polígonos inválidos, que são comuns em malhas oficiais.

    Tenta em três níveis: direto; depois saneando cada peça com buffer(0); e por
    fim com make_valid. Devolve None se nem assim fechar, para o chamador seguir
    sem contorno em vez de abortar o município inteiro."""
    from shapely.validation import make_valid
    for preparo in (lambda g: g,
                    lambda g: g.buffer(0),
                    lambda g: make_valid(g)):
        try:
            partes = [preparo(g) for g in geoms]
            partes = [g for g in partes if not g.is_empty]
            return unary_union(partes)
        except Exception:
            continue
    return None


def arredondar(geom, casas=5):
    """~1 m de precisão. Corta o tamanho do JSON quase pela metade sem efeito visível."""
    def r(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], casas), round(c[1], casas)]
        return [r(x) for x in c]
    g = mapping(geom)
    g["coordinates"] = r(g["coordinates"])

    # Arredondar pode encostar vértices vizinhos e invalidar o polígono.
    # Se isso acontecer, saneia o resultado já arredondado em vez de devolver
    # geometria quebrada para o painel.
    try:
        gg = shape(g)
        if not gg.is_valid:
            gg = gg.buffer(0)
            if gg.is_valid and not gg.is_empty:
                g = mapping(gg)
    except Exception:
        pass
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shp", default="dados/geo/MG_bairros_CD2022",
                    help="caminho do shapefile, sem extensão")
    ap.add_argument("--saida", default="dados/geo")
    ap.add_argument("--tolerancia", type=float, default=0.00015,
                    help="tolerância Douglas-Peucker em graus (~17 m). 0 desliga")
    a = ap.parse_args()

    os.makedirs(a.saida, exist_ok=True)
    r = shapefile.Reader(a.shp)
    flds = [f[0] for f in r.fields if f[0] != "DeletionFlag"]
    i_mun, i_bai = flds.index("NM_MUN"), flds.index("NM_BAIRRO")
    i_dist = flds.index("NM_DIST")
    i_sub = flds.index("NM_SUBDIST")

    alvo = {norm(m) for m in MUNICIPIOS}
    por_mun = {}
    for sr in r.iterShapeRecords():
        m = norm(sr.record[i_mun])
        if m in alvo:
            por_mun.setdefault(m, []).append(sr)

    print(f"{'MUNICÍPIO':24s} {'BAIRROS':>8s} {'VÉRT.ORIG':>11s} {'VÉRT.SIMPL':>11s} "
          f"{'GEOJSON':>10s}")
    print("-" * 72)

    ausentes = []
    for m in MUNICIPIOS:
        m = norm(m)
        srs = por_mun.get(m)
        if not srs:
            ausentes.append(m)
            print(f"{m:24s} {'—':>8s} {'—':>11s} {'—':>11s} {'AUSENTE':>10s}")
            continue

        feats, geoms, vo, vs = [], [], 0, 0
        for i, sr in enumerate(srs):
            g = shape(sr.shape.__geo_interface__)
            vo += len(sr.shape.points)
            if not g.is_valid:
                g = g.buffer(0)
            if a.tolerancia > 0:
                g2 = g.simplify(a.tolerancia, preserve_topology=True)
                if not g2.is_empty and g2.is_valid:
                    g = g2
            vs += conta_vertices(mapping(g)["coordinates"])
            geoms.append(g)
            feats.append({
                "id": str(i),
                "type": "Feature",
                "properties": {
                    "bairro": sr.record[i_bai],
                    "distrito": sr.record[i_dist],
                    # Regional oficial quando o IBGE a publica. Em BH, subdistrito dá
                    # as 7 regionais internas e distrito dá Barreiro e Venda Nova —
                    # juntas, as 9 do painel de referência.
                    "regiao": (sr.record[i_sub].strip() or sr.record[i_dist].strip()),
                },
                "geometry": arredondar(g),
            })

        fc = {"type": "FeatureCollection", "features": feats}
        dest = os.path.join(a.saida, f"bairros_{slug(m)}.geojson")
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(fc, f, ensure_ascii=False, separators=(",", ":"))
        kb = os.path.getsize(dest) / 1024
        print(f"{m:24s} {len(feats):>8d} {vo:>11,d} {vs:>11,d} {kb:>9.0f}K")

        # Contorno do município: união dos bairros, útil como moldura do mapa.
        # A união roda sobre as geometrias ANTES do arredondamento — arredondar
        # coordenadas pode encostar vértices e produzir topologia inválida.
        env = uniao_robusta(geoms)
        if env is None:
            print(f"{'':24s} (contorno não gerado: topologia irrecuperável)")
            continue
        env = env.simplify(a.tolerancia * 2, preserve_topology=True)
        with open(os.path.join(a.saida, f"contorno_{slug(m)}.geojson"), "w",
                  encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": {"municipio": m},
                 "geometry": arredondar(env)}]}, f, ensure_ascii=False,
                separators=(",", ":"))

    if ausentes:
        print(f"\nSEM MALHA DE BAIRROS ({len(ausentes)}): {', '.join(ausentes)}")
        print("A camada de bairros do IBGE cobre só municípios selecionados.")
        print("Para estes, a unidade geográfica cai para o nível seguinte do §6:")
        print("  zonas eleitorais, ou locais de votação agrupados por proximidade")
        print("  (lat/lon vêm de eleitorado_local_votacao_*.csv).")


if __name__ == "__main__":
    main()
