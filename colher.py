#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""colher.py — decodifica os downloads do conector do Drive que o harness gravou em disco.

O conector devolve resultados grandes como arquivo em vez de despejá-los no contexto.
Cada arquivo é um JSON {content: base64, title: ...}; aqui ele vira o CSV original,
nomeado pelo título real, em dados/tse2024_secao/.
"""
import base64, glob, json, os, sys

ORIG = "/root/.claude/projects/-home-user-lohanna/0dfa31eb-97c4-57d4-8256-3df0b073670e/tool-results"
DEST = "dados/tse2024_secao"
os.makedirs(DEST, exist_ok=True)

novos = 0
for p in sorted(glob.glob(f"{ORIG}/mcp-Google_Drive-download_file_content-*.txt")):
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print(f"  ignorado (não é JSON): {os.path.basename(p)} — {e}")
        continue
    titulo = d.get("title")
    if not titulo or not titulo.endswith(".csv"):
        continue
    dest = os.path.join(DEST, titulo)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        continue
    raw = base64.b64decode(d["content"])
    open(dest, "wb").write(raw)
    print(f"  {titulo:46s} {len(raw)/1e6:6.2f} MB")
    novos += 1
    os.remove(p)          # libera espaço: o base64 ocupa 4/3 do arquivo final

print(f"\n{novos} novo(s). Total em {DEST}:")
tot = 0
for f in sorted(os.listdir(DEST)):
    tot += os.path.getsize(os.path.join(DEST, f))
print(f"  {len(os.listdir(DEST))} arquivos, {tot/1e6:.1f} MB")
