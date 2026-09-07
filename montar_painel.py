#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""montar_painel.py — junta template + CSS + Chart.js + DATA num único HTML offline."""
import argparse, json, os, re, unicodedata

def slug(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True)
ap.add_argument("--cargo", default="Deputado Estadual")
ap.add_argument("--saida", default=None)
a = ap.parse_args()

D = json.load(open(a.data, encoding="utf-8"))
tpl = open("template_painel.html", encoding="utf-8").read()
css = open("lib/painel.css", encoding="utf-8").read()
chart = open("lib/chartjs.min.js", encoding="utf-8").read()
js = open("painel.js", encoding="utf-8").read()

mun, ape = D["municipio"].title(), D["apelido"]
c24 = (D.get("votes24") or {}).get("candidato")
sub = f"Aderência a {len(D['pautas'])} pautas em {len(D['eixos'])} eixos, por bairro e setor censitário"
if D["votes22"].get("suprimido"):
    sub += " · Camada de votos da Lohanna 2022 SUPRIMIDA neste município (ver rodapé)"
else:
    sub += (f" · Lohanna França · 2022: {D['votes22']['total']:,} votos sem dupla contagem"
            .replace(",", "."))
if c24:
    sub += f" · {ape} · vereador 2024: {c24['votos']:,}".replace(",", ".") + f" votos ({c24['pos']}º)"
sub += f" · Unidade: {D['meta']['unidade']}"

out = (tpl
   .replace("__TITULO__", f"Painel Estratégico – {ape} | {mun}")
   .replace("__H1__", "Painel Estratégico Unificado – Dados e Mobilização de Rua")
   .replace("__TAG__", f"{ape} · {mun} · {a.cargo} 2026")
   .replace("__SUB__", sub)
   .replace("__MINSET__", str(D["meta"]["min_setores"]))
   .replace("__APELIDO__", ape)
   .replace("<!--CHARTJS-->", "<script>" + chart + "</script>")
   .replace("__CSS_BASE__", css)
   .replace("__DATA__", json.dumps(D, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
   .replace("__JS__", js))

dest = a.saida or f"paineis/Painel_{slug(ape).title()}_{slug(mun).title()}.html"
os.makedirs(os.path.dirname(dest), exist_ok=True)
open(dest, "w", encoding="utf-8").write(out)
print(f"-> {dest} ({os.path.getsize(dest)/1e6:.2f} MB)")
