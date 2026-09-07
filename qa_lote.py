import sys, glob, asyncio, json, os
from playwright.async_api import async_playwright

async def testa(pg, path):
    erros, req = [], []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.on("console", lambda m: erros.append(m.type+": "+m.text) if m.type=="error" else None)
    pg.on("request", lambda r: req.append(r.url) if not r.url.startswith("file:") else None)
    await pg.goto("file://"+path, wait_until="networkidle")
    await pg.wait_for_timeout(2200)
    n = lambda sel: pg.locator(sel).count()
    body = await pg.locator("body").inner_text()
    proibidos = {t: body.count(t) for t in ("NaN","undefined","Infinity","[object")}
    # troca de métrica atualiza mapa+ranking?
    t0 = await pg.locator("#mapTitle").inner_text()
    opts = await pg.locator("#selMetric option").all()
    await pg.select_option("#selMetric", await opts[-1].get_attribute("value"))
    await pg.wait_for_timeout(700)
    t1 = await pg.locator("#mapTitle").inner_text()
    r1 = await pg.locator("#rkTitle").inner_text()
    # responsivo
    resp = {}
    for w in (900, 380):
        await pg.set_viewport_size({"width":w,"height":900}); await pg.wait_for_timeout(450)
        resp[w] = await pg.evaluate("document.documentElement.scrollWidth")
    await pg.set_viewport_size({"width":1400,"height":1000})
    return {
        "erros": erros, "req": req, "proibidos": proibidos,
        "cards": await n(".cards .card"), "insights": await n("#insights .insight, #insights .warn"),
        "mapa": await n("#map svg path") + await n("#map svg circle"),
        "acordeao": await n(".vreg"), "tabela": await n("#tb tbody tr"),
        "tops": await n("#tops .topcol"), "alvos": await n(".front .trow"),
        "canvas": await n("canvas"), "mapaMob": await n("#mapM svg path")+await n("#mapM svg circle"),
        "over": await n(".scatter circle"),
        "mapaQ": await n("#mapQ svg path")+await n("#mapQ svg circle"),
        "recip": await n("#recip .trow"), "cbair": await n(".cbtab tbody tr"),
        "trocou": t0 != t1 and t1.split('—')[-1].strip() == r1.split('—')[-1].strip(),
        "resp": resp, "rodape": len(await pg.locator("#foot").inner_text()),
    }

async def main():
    ok = True
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args=["--no-sandbox"])
        print(f"{'PAINEL':44s}{'ERR':>4s}{'NET':>4s}{'PROIB':>6s}{'CARD':>5s}{'INS':>4s}{'MAPA':>6s}{'ACORD':>6s}{'TAB':>5s}{'TOP':>4s}{'ALVO':>5s}{'CNV':>4s}{'MOB':>5s}{'OVER':>6s}{'MAPQ':>6s}{'RECP':>6s}{'CBAI':>6s}{'SEL':>5s}{'RESP':>6s}")
        print("-"*154)
        for p in sorted(glob.glob("/home/user/lohanna/paineis/*.html")):
            pg = await b.new_page(viewport={"width":1400,"height":1000})
            r = await testa(pg, p); await pg.close()
            prob = sum(r["proibidos"].values())
            resp_ok = all(r["resp"][w] <= w+2 for w in r["resp"])
            falhou = (r["erros"] or r["req"] or prob or not r["trocou"] or not resp_ok
                      or r["cards"]==0 or r["mapa"]==0 or r["tabela"]==0 or r["tops"]==0
                      or r["canvas"]==0 or r["rodape"]<200)
            ok = ok and not falhou
            nome = os.path.basename(p).replace("Painel_","").replace(".html","")
            print(f"{nome[:44]:44s}{len(r['erros']):>4d}{len(r['req']):>4d}{prob:>6d}"
                  f"{r['cards']:>5d}{r['insights']:>4d}{r['mapa']:>6d}{r['acordeao']:>6d}"
                  f"{r['tabela']:>5d}{r['tops']:>4d}{r['alvos']:>5d}{r['canvas']:>4d}"
                  f"{r['mapaMob']:>5d}{r['over']:>6d}{r['mapaQ']:>6d}{r['recip']:>6d}{r['cbair']:>6d}"
                  f"{'ok' if r['trocou'] else 'FALHA':>5s}{'ok' if resp_ok else 'FALHA':>6s}"
                  + ("   <-- REVISAR" if falhou else ""))
            if r["erros"]: print("        erro:", r["erros"][0][:150])
            if r["req"]:   print("        rede:", r["req"][0][:120])
            if prob:       print("        literais:", {k:v for k,v in r["proibidos"].items() if v})
        await b.close()
    print("\nRESULTADO:", "TODOS PASSARAM" if ok else "há painéis a revisar")

asyncio.run(main())
