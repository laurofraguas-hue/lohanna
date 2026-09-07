import sys, json, asyncio
from playwright.async_api import async_playwright

async def main(path):
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width":1400,"height":1000})
        erros, req = [], []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: erros.append("console."+m.type+": "+m.text) if m.type=="error" else None)
        pg.on("request", lambda r: req.append(r.url) if not r.url.startswith("file:") else None)
        await pg.goto("file://"+path, wait_until="networkidle")
        await pg.wait_for_timeout(2500)

        print("### ERROS DE JAVASCRIPT:", len(erros))
        for e in erros[:10]: print("   !!", e[:220])
        print("### REQUISIÇÕES EXTERNAS:", len(req))
        for r in req[:5]: print("   !!", r[:150])

        async def n(sel): return await pg.locator(sel).count()
        print("\n### ELEMENTOS RENDERIZADOS")
        for nome, sel in [("cards",".cards .card"),("insights","#insights .insight"),
                          ("polígonos do mapa","#map svg path"),
                          ("polígonos da seção unificada","#mapCam svg path"),
                          ("círculos 2022","#mapCam svg circle[data-l*='Lohanna']"),
                          ("círculos 2024","#mapCam svg circle:not([data-l*='Lohanna'])"),
                          ("botões de camada",".camctl .tgb"),
                          ("linhas por bairro (2 camadas)",".crow2"),
                          ("acordeão unificado",".vreg"),("linhas da tabela","#tb tbody tr"),
                          ("colunas Top10","#tops .topcol"),("frentes de mobilização",".front"),
                          ("bairros-alvo",".front .trow"),("gráficos (canvas)","canvas"),
                          ("mapa mobilização","#mapM svg path"),("competitiva",".crow"),
                          ("scatter da sobreposição",".scatter circle"),
                          ("mapa dos quadrantes","#mapQ svg path, #mapQ svg circle"),
                          ("listas de quadrante",".qcol .qrow"),
                          ("reciprocidade","#recip .trow"),
                          ("competitiva por bairro",".cbtab tbody tr")]:
            c = await n(sel); print(f"   {nome:26s} {c:5d}{'   <-- VAZIO' if c==0 else ''}")

        print("\n### TEXTO VISÍVEL — amostras")
        for sel in ["#cards",".insight:first-child","#cam .big","#foot"]:
            t = (await pg.locator(sel).first.inner_text())[:300].replace("\n"," | ")
            print(f"   {sel}: {t}")

        body = await pg.locator("body").inner_text()
        print("\n### LITERAIS PROIBIDOS NO TEXTO RENDERIZADO")
        for t in ["NaN","undefined","null","Infinity","[object"]:
            c = body.count(t); print(f"   {t:10s} {c}{'   <-- PROBLEMA' if c else ''}")

        print("\n### TROCA DE MÉTRICA (mapa+ranking+legenda juntos)")
        t0 = await pg.locator("#mapTitle").inner_text()
        f0 = await pg.locator("#map svg path").first.get_attribute("fill")
        opts = await pg.locator("#selMetric option").all()
        alvo = await opts[-1].get_attribute("value")
        await pg.select_option("#selMetric", alvo)
        await pg.wait_for_timeout(900)
        t1 = await pg.locator("#mapTitle").inner_text()
        f1 = await pg.locator("#map svg path").first.get_attribute("fill")
        r1 = await pg.locator("#rkTitle").inner_text()
        print(f"   título antes : {t0}\n   título depois: {t1}\n   ranking      : {r1}")
        print(f"   cor do 1º polígono: {f0} -> {f1}   {'(mudou)' if f0!=f1 else '(igual — pode ser coincidência de faixa)'}")

        print("\n### BOTÕES DE CÍRCULOS (liga/desliga por camada)")
        for bid, rot in [("#tg22","Lohanna 2022"), ("#tg24","candidato 2024")]:
            if not await pg.locator(bid).count():
                print(f"   {rot:18s} ausente (camada não existe neste município)"); continue
            sel = "#mapCam svg circle[data-l*='Lohanna']" if bid=="#tg22" \
                  else "#mapCam svg circle:not([data-l*='Lohanna'])"
            antes = await pg.locator(sel).count()
            await pg.click(bid); await pg.wait_for_timeout(500)
            desl = await pg.locator(sel).count()
            await pg.click(bid); await pg.wait_for_timeout(500)
            volta = await pg.locator(sel).count()
            ok = antes > 0 and desl == 0 and volta == antes
            print(f"   {rot:18s} {antes} -> {desl} -> {volta}   {'OK' if ok else '<-- FALHOU'}")

        print("\n### ENQUADRAMENTO (município inteiro x mancha urbana)")
        vb0 = await pg.locator("#map svg").first.get_attribute("viewBox")
        d0 = await pg.locator("#map svg path").first.get_attribute("d")
        await pg.select_option("#selEnq","urb"); await pg.wait_for_timeout(800)
        d1 = await pg.locator("#map svg path").first.get_attribute("d")
        n1 = await pg.locator("#map svg path").count()
        await pg.select_option("#selEnq","mun"); await pg.wait_for_timeout(800)
        n0 = await pg.locator("#map svg path").count()
        print(f"   polígonos desenhados: município={n0} urbano={n1} "
              f"{'OK (nenhum some)' if n0==n1 else '<-- POLÍGONO SUMIU'}")
        print(f"   projeção mudou: {'sim' if d0!=d1 else 'NÃO — o recorte não teve efeito'}")

        print("\n### RESPONSIVO 900px / 380px")
        for w in (900, 380):
            await pg.set_viewport_size({"width":w,"height":900})
            await pg.wait_for_timeout(600)
            sw = await pg.evaluate("document.documentElement.scrollWidth")
            print(f"   {w}px -> scrollWidth={sw} {'OK' if sw<=w+2 else '<-- ESTOURA NA HORIZONTAL'}")

        await pg.set_viewport_size({"width":1400,"height":1000})
        await pg.wait_for_timeout(400)
        await pg.screenshot(path="/tmp/painel_topo.png")
        await pg.screenshot(path="/tmp/painel_full.png", full_page=True)
        await b.close()

asyncio.run(main(sys.argv[1]))
