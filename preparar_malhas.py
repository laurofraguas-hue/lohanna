#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preparar_malhas.py — constrói a malha de bairros dos dez municípios do projeto
dissolvendo os SETORES CENSITÁRIOS do IBGE (Censo 2022).

Por que não usar direto `MG_bairros_CD2022`: o IBGE só delimita bairros em
municípios selecionados. Dos dez do projeto, só quatro estão lá (Belo Horizonte,
Betim, Uberlândia e São João del-Rei) — e mesmo nesses a malha de bairros deixa
setores de fora (o rural, sobretudo). Os outros seis ficavam sem mapa nenhum.

A malha de SETORES, ao contrário, cobre o território inteiro dos 5.570 municípios.
Como cada setor traz o campo `NM_BAIRRO` (preenchido onde o IBGE nomeia bairros) e
a tabela de aderência traz o campo `Bairro` do CNEFE para todo setor pesquisado,
dá para rotular cada setor e dissolver os polígonos por rótulo. O resultado é uma
malha de bairros para os dez municípios, sem buraco: todo setor entra em algum
polígono.

Regra de rótulo, nesta ordem:
  1. `NM_BAIRRO` do IBGE, quando preenchido — é o nome oficial;
  2. `Bairro` da tabela de aderência (CNEFE), quando o IBGE não nomeia;
  3. setor URBANO que sobrou herda o bairro do vizinho com quem divide a maior
     fronteira, em rodadas (ver `preencher_por_vizinho`);
  4. o resto recebe a unidade oficial que o contém: "Zona rural — <distrito>" ou
     "<distrito> — sem bairro declarado".

Onde os nomes do IBGE e do CNEFE coexistem eles coincidem 100% (verificado setor
a setor nos quatro municípios com malha do IBGE), então a regra 1 só consolida.
A coluna `fonte_nome` do CSV registra qual das quatro regras nomeou cada setor,
e o painel declara no rodapé quantos vieram de cada uma.

Saídas, em `dados/geo/`:
  bairros_<slug>.geojson    polígonos dissolvidos, com `bairro`/`distrito`/`regiao`
  contorno_<slug>.geojson   união de tudo — o limite do município
  setores_<slug>.csv        CD_SETOR -> bairro, situação, distrito

O CSV é o que amarra geometria e dado: `gerar_painel.py` lê esse mapa em vez de
reinventar o rótulo a partir da planilha, e assim o nome do polígono e o nome do
bairro na tabela são, por construção, o mesmo.

Uso:
    python3 preparar_malhas.py                    # todos os dez
    python3 preparar_malhas.py --municipio mariana
"""

import argparse
import csv
import json
import os
import unicodedata
from collections import Counter, defaultdict

import openpyxl
import shapefile
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

MUNICIPIOS = [
    "BELO HORIZONTE", "BETIM", "UBERLANDIA", "DIVINOPOLIS", "SAO JOAO DEL REI",
    "PARA DE MINAS", "LAGOA SANTA", "MARIANA", "CONSELHEIRO LAFAIETE", "CURVELO",
]

SEM_BAIRRO = "Não classificado"


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper().replace("-", " ").strip()


def slug(s):
    return norm(s).lower().replace(" ", "_")


def valido(nome):
    """A planilha usa '—' e vazio para 'sem bairro'; ambos não são nome."""
    n = norm(nome)
    return bool(n) and n not in {"—", "-", "NAN", "NONE", "SEM BAIRRO"}


MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "d'", "à", "a", "o"}


def titulo(nome):
    """CNEFE escreve tudo em caixa alta; o IBGE, em caixa de título.

    Sem isto o mesmo mapa mistura 'Santa Mônica' e 'CHACARAS ARCO IRIS'. A
    conversão preserva siglas de até duas letras (I, II, IV) e as preposições em
    minúscula, como o IBGE faz."""
    if not nome:
        return nome
    if nome != nome.upper():          # já vem em caixa de título (IBGE)
        return nome
    palavras = nome.lower().split()
    out = []
    for i, p in enumerate(palavras):
        if i and p in MINUSCULAS:
            out.append(p)
        elif set(p) <= set("ivx") and len(p) <= 4:   # numeral romano
            out.append(p.upper())
        else:
            out.append(p[:1].upper() + p[1:])
    return " ".join(out)


# ------------------------------------------------------ tabela de aderência

def bairro_cnefe(mun_slug):
    """CD_setor -> nome de bairro do CNEFE, lido da tabela de aderência.

    Lê em modo read_only e para na primeira ocorrência de cada setor: a planilha
    repete o setor uma vez por endereço/oportunidade e chega a centenas de
    milhares de linhas."""
    for cand in (mun_slug, mun_slug.replace("del_rei", "del_rey"),
                 mun_slug.replace("del_rey", "del_rei")):
        p = f"dados/aderencia/tabela_oportunidade_{cand}.xlsx"
        if os.path.exists(p):
            break
    else:
        return {}
    wb = openpyxl.load_workbook(p, read_only=True)
    ws = wb.active
    linhas = ws.iter_rows(values_only=True)
    hdr = list(next(linhas))
    i_cs, i_b = hdr.index("CD_setor"), hdr.index("Bairro")
    out = {}
    for row in linhas:
        cs = str(row[i_cs]).strip()
        if cs and cs not in out and valido(row[i_b]):
            out[cs] = titulo(str(row[i_b]).strip())
    wb.close()
    return out


# --------------------------------------------------------------- geometria

def sanear(g):
    if g.is_valid:
        return g
    g2 = g.buffer(0)
    if g2.is_valid and not g2.is_empty:
        return g2
    return make_valid(g)


def dissolver(geoms):
    """União tolerante a polígonos inválidos, comuns em malhas oficiais."""
    partes = [sanear(g) for g in geoms]
    partes = [g for g in partes if not g.is_empty]
    if not partes:
        return None
    try:
        return unary_union(partes)
    except Exception:
        try:
            return unary_union([g.buffer(0) for g in partes])
        except Exception:
            return None


def conta_vertices(coords):
    if isinstance(coords[0], (int, float)):
        return 1
    return sum(conta_vertices(c) for c in coords)


def arredondar(geom, casas=5):
    """~1 m de precisão; corta o JSON quase pela metade sem efeito visível."""
    def r(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], casas), round(c[1], casas)]
        return [r(x) for x in c]
    g = mapping(geom)
    g["coordinates"] = r(g["coordinates"])
    try:
        gg = shape(g)
        if not gg.is_valid:
            gg = gg.buffer(0)
            if gg.is_valid and not gg.is_empty:
                g = mapping(gg)
    except Exception:
        pass
    return g


# ------------------------------------------------- preenchimento por vizinhança

def preencher_por_vizinho(nomes, geoms, situacao, distrito, rodadas=12):
    """Dá nome aos setores urbanos que ficaram sem, pelo bairro vizinho.

    Por que é preciso: o `Bairro` do CNEFE só existe para os setores que entraram
    na tabela de aderência, e ela não cobre o município inteiro — em Divinópolis
    faltam 103 setores URBANOS, em Lagoa Santa 78, em Conselheiro Lafaiete 67.
    Deixá-los sem nome abre um vazio no meio da cidade e joga os votos das urnas
    que caem ali num balde chamado "Não classificado": em Mariana eram 104 dos 620
    votos do candidato.

    O que a função faz é propagação de rótulo sobre uma partição contígua: o setor
    sem nome adota o bairro do vizinho com quem divide a maior fronteira, em
    rodadas, até parar de mudar. Não inventa número nenhum — só estende ao setor
    vazio o nome do bairro que o cerca, que é como o próprio IBGE descreve o
    tecido urbano. E só vale para setor URBANO: no rural o vizinho pode estar a
    quilômetros e o nome certo é o do distrito, não o do bairro mais próximo.

    Devolve quantos setores foram nomeados assim, para o painel poder declarar."""
    pend = [i for i, n in enumerate(nomes)
            if n is None and norm(situacao[i]) == "URBANA"]
    if not pend:
        return 0

    from shapely.strtree import STRtree
    arvore = STRtree(geoms)
    preenchidos = 0
    for _ in range(rodadas):
        # Candidatos desta rodada: quem já tem nome no início dela. Congelar a
        # referência evita que um rótulo recém-propagado sirva de base no mesmo
        # passo, o que faria o resultado depender da ordem da lista.
        base = [i for i, n in enumerate(nomes) if n is not None]
        if not base:
            return preenchidos
        com_nome = set(base)
        novos = {}
        for i in pend:
            if nomes[i] is not None:
                continue
            g = geoms[i]
            melhor, maior = None, 0.0
            for j in arvore.query(g):
                j = int(j)
                if j == i or j not in com_nome:
                    continue
                try:
                    inter = g.intersection(geoms[j])
                except Exception:
                    continue
                if inter.is_empty:
                    continue
                comp = inter.length if inter.geom_type != "Point" else 0.0
                if comp > maior:
                    melhor, maior = nomes[j], comp
            if melhor is not None:
                novos[i] = melhor
        if not novos:
            break
        for i, nome in novos.items():
            nomes[i] = nome
        preenchidos += len(novos)
        pend = [i for i in pend if nomes[i] is None]
        if not pend:
            break
    return preenchidos


def nome_residual(situacao, dist):
    """Rótulo do que sobrou: sempre uma unidade oficial do IBGE, nunca um palpite."""
    d = (dist or "").strip()
    if norm(situacao) == "RURAL":
        return f"Zona rural — {d}" if d else "Zona rural"
    return f"{d} — sem bairro declarado" if d else SEM_BAIRRO


# ------------------------------------------------------------------ montagem

def montar(mun, srs, cnefe, tol, saida):
    """Dissolve os setores de um município por bairro e grava os três arquivos."""
    grupos = defaultdict(list)          # bairro -> [geometria]
    atributos = {}                      # bairro -> (distrito, regiao)
    urbano = defaultdict(int)           # bairro -> nº de setores urbanos

    # 1ª passada: nome direto (IBGE, depois CNEFE) e geometria saneada.
    cds, geoms, nomes, fontes, sits, dists, subs = [], [], [], [], [], [], []
    for sr, cd, nm_b, dist, sub, sit in srs:
        g = sanear(shape(sr.shape.__geo_interface__))
        if g.is_empty:
            continue
        if valido(nm_b):
            nome, fonte = titulo(nm_b.strip()), "IBGE"
        elif cd in cnefe:
            nome, fonte = cnefe[cd], "CNEFE"
        else:
            nome, fonte = None, None
        cds.append(cd); geoms.append(g); nomes.append(nome); fontes.append(fonte)
        sits.append(sit); dists.append(dist.strip()); subs.append(sub.strip())

    # 2ª passada: o urbano sem nome herda o bairro do vizinho de maior fronteira.
    antes = [n for n in nomes]
    preencher_por_vizinho(nomes, geoms, sits, dists)
    for i, n in enumerate(nomes):
        if fontes[i] is None and n is not None:
            fontes[i] = "vizinho"

    # 3ª passada: o que sobrou recebe o nome da unidade oficial que o contém.
    for i, n in enumerate(nomes):
        if n is None:
            nomes[i] = nome_residual(sits[i], dists[i])
            fontes[i] = "distrito"

    linhas_csv = []
    for i, cd in enumerate(cds):
        nome = nomes[i]
        grupos[nome].append(geoms[i])
        atributos.setdefault(nome, (dists[i], subs[i] or dists[i]))
        if norm(sits[i]) == "URBANA":
            urbano[nome] += 1
        linhas_csv.append({"CD_SETOR": cd, "bairro": nome, "situacao": sits[i],
                           "distrito": dists[i], "fonte_nome": fontes[i]})

    feats, todos, vs = [], [], 0
    # Ordem estável: bairros nomeados em ordem alfabética, "Não classificado" por
    # último — assim ele fica no fim do SVG e não cobre os polígonos com dado.
    ordem = sorted([b for b in grupos if b != SEM_BAIRRO]) + \
            ([SEM_BAIRRO] if SEM_BAIRRO in grupos else [])
    for i, b in enumerate(ordem):
        g = dissolver(grupos[b])
        if g is None or g.is_empty:
            continue
        if tol > 0:
            g2 = g.simplify(tol, preserve_topology=True)
            if not g2.is_empty and g2.is_valid:
                g = g2
        todos.append(g)
        vs += conta_vertices(mapping(g)["coordinates"])
        dist, reg = atributos[b]
        feats.append({
            "id": str(i), "type": "Feature",
            "properties": {
                "bairro": b, "distrito": dist, "regiao": reg,
                "setores": len(grupos[b]),
                # Um bairro sem nenhum setor urbano é área rural: o painel usa
                # isso para não deixar o rural dominar o enquadramento do mapa.
                "urbano": urbano.get(b, 0),
            },
            "geometry": arredondar(g),
        })

    sl = slug(mun)
    dest = os.path.join(saida, f"bairros_{sl}.geojson")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f,
                  ensure_ascii=False, separators=(",", ":"))

    env = dissolver(todos)
    if env is not None and not env.is_empty:
        env = env.simplify(max(tol, 1e-5) * 2, preserve_topology=True)
        with open(os.path.join(saida, f"contorno_{sl}.geojson"), "w",
                  encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": [
                {"type": "Feature", "properties": {"municipio": norm(mun)},
                 "geometry": arredondar(env)}]}, f, ensure_ascii=False,
                separators=(",", ":"))

    with open(os.path.join(saida, f"setores_{sl}.csv"), "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=["CD_SETOR", "bairro", "situacao",
                                          "distrito", "fonte_nome"])
        w.writeheader()
        w.writerows(sorted(linhas_csv, key=lambda x: x["CD_SETOR"]))

    kb = os.path.getsize(dest) / 1024
    conta = Counter(x["fonte_nome"] for x in linhas_csv)
    print(f"{norm(mun):22s} {len(feats):5d} bairros  {len(linhas_csv):6d} setores "
          f"(IBGE {conta['IBGE']:5d} · CNEFE {conta['CNEFE']:5d} · "
          f"vizinho {conta['vizinho']:4d} · distrito {conta['distrito']:4d})  "
          f"{vs:8,d} vért.  {kb:7.0f}K")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shp", default="dados/geo/MG_setores_CD2022",
                    help="shapefile de setores censitários, sem extensão")
    ap.add_argument("--saida", default="dados/geo")
    ap.add_argument("--tolerancia", type=float, default=0.00012,
                    help="tolerância Douglas-Peucker em graus (~13 m); 0 desliga")
    ap.add_argument("--municipio", action="append",
                    help="restringe a um município (pode repetir)")
    a = ap.parse_args()

    os.makedirs(a.saida, exist_ok=True)
    alvos = [m for m in MUNICIPIOS
             if not a.municipio or slug(m) in {slug(x) for x in a.municipio}]
    if not alvos:
        raise SystemExit("nenhum município corresponde ao filtro")

    r = shapefile.Reader(a.shp)
    flds = [f[0] for f in r.fields if f[0] != "DeletionFlag"]
    i = {k: flds.index(k) for k in
         ("CD_SETOR", "NM_MUN", "NM_BAIRRO", "NM_DIST", "NM_SUBDIST", "SITUACAO")}

    chave = {norm(m): m for m in alvos}
    por_mun = defaultdict(list)
    for sr in r.iterShapeRecords():
        m = norm(sr.record[i["NM_MUN"]])
        if m in chave:
            por_mun[m].append((sr, sr.record[i["CD_SETOR"]],
                               sr.record[i["NM_BAIRRO"]], sr.record[i["NM_DIST"]],
                               sr.record[i["NM_SUBDIST"]], sr.record[i["SITUACAO"]]))

    print(f"{'MUNICÍPIO':22s} {'BAIRROS':>7s}  {'SETORES E ORIGEM DO NOME':^46s} "
          f"{'VÉRTICES':>13s} {'ARQUIVO':>8s}")
    print("-" * 104)
    for m in alvos:
        srs = por_mun.get(norm(m))
        if not srs:
            print(f"{norm(m):22s} AUSENTE do shapefile de setores")
            continue
        montar(m, srs, bairro_cnefe(slug(m)), a.tolerancia, a.saida)


if __name__ == "__main__":
    main()
