"""Genera le infografiche MAKA 2000x2000 da specs.json.
Uso: python render.py specs.json cartella_output [--local-img file]"""
import json, sys, os, html, asyncio, urllib.request, base64, hashlib
from playwright.async_api import async_playwright

CSS = """
*{box-sizing:border-box}html,body{margin:0;background:#fff}
#ig{width:1000px;height:1000px;position:relative;font-family:'Inter','Segoe UI',Arial,sans-serif;color:#13263a;overflow:hidden;background:#fff}
.hd{position:absolute;left:0;top:0;width:1000px;height:150px;background:#13263a;color:#fff}
.brand{position:absolute;left:40px;top:26px;font-size:22px;letter-spacing:6px;font-weight:700;color:#f08a34}
.t1{position:absolute;left:40px;top:56px;right:40px;font-size:40px;font-weight:800;letter-spacing:.3px;white-space:nowrap;overflow:hidden}
.t2{position:absolute;left:40px;top:106px;right:40px;font-size:22px;opacity:.85;white-space:nowrap;overflow:hidden}
.prod{position:absolute;left:250px;top:190px;width:500px;height:500px;object-fit:contain}
.card{position:absolute;width:210px;height:150px;border:2px solid #dfe5ec;border-radius:16px;background:#f6f8fb;padding:18px}
.lab{font-size:15px;font-weight:700;letter-spacing:1.5px;color:#6b7c8f;text-transform:uppercase}
.val{font-size:27px;font-weight:800;margin-top:10px;line-height:1.1}
.sub{font-size:15px;margin-top:6px;color:#4a5b6e}
.hl{border-color:#f08a34;background:#fff7f0}
.ft{position:absolute;left:0;bottom:0;width:1000px;height:180px;background:#f2f4f7;border-top:4px solid #f08a34}
.chip{position:absolute;top:34px;height:112px;width:290px;border-radius:14px;background:#fff;border:2px solid #dfe5ec;padding:18px 20px}
.chip .val{font-size:23px}
"""
LEFT = [(30, 190), (30, 380), (30, 570)]
RIGHT = [(760, 190), (760, 380), (760, 570)]
CHIPS = [40, 355, 670]

def e(s): return html.escape(str(s or ''))

def fit(val, base=27, width=174):
    # riduce il corpo se il testo e' lungo
    longest = max((len(x) for x in str(val).split('<br>')), default=1)
    size = base
    while size > 17 and longest * size * 0.58 > width: size -= 1
    return size

def card(x, y, c, hl=False):
    v = e(c.get('valore')).replace('\n', '<br>')
    lines = v.count('<br>') + 1
    fs = fit(c.get('valore', '').replace('\n', '<br>'))
    if lines >= 3: fs = min(fs, 21)
    sub = f"<div class='sub'>{e(c.get('sotto'))}</div>" if c.get('sotto') else ''
    return (f"<div class='card{' hl' if hl else ''}' style='left:{x}px;top:{y}px'><div class='lab'>{e(c.get('etichetta'))}</div>"
            f"<div class='val' style='font-size:{fs}px'>{v}</div>{sub}</div>")

def page(s, img_src):
    h = [f"<div id='ig'><div class='hd'><div class='brand'>MAKA</div><div class='t1'>{e(s['titolo'])}</div><div class='t2'>{e(s.get('sottotitolo'))}</div></div>",
         f"<img class='prod' src='{img_src}'>"]
    for (x, y), c in zip(LEFT, s.get('sinistra', [])):
        h.append(card(x, y, c, hl=c.get('etichetta', '').lower() == 'spessore'))
    for (x, y), c in zip(RIGHT, s.get('destra', [])):
        h.append(card(x, y, c))
    h.append("<div class='ft'>")
    for x, c in zip(CHIPS, s.get('fondo', [])):
        fs = fit(c.get('valore', ''), 23, 246)
        h.append(f"<div class='chip' style='left:{x}px'><div class='lab'>{e(c.get('etichetta'))}</div><div class='val' style='font-size:{fs}px'>{e(c.get('valore'))}</div></div>")
    h.append("</div></div>")
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap' rel='stylesheet'>"
            f"<style>{CSS}</style></head><body>{''.join(h)}</body></html>")

def fetch(url, cache):
    os.makedirs(cache, exist_ok=True)
    p = os.path.join(cache, hashlib.md5(url.encode()).hexdigest() + '.jpg')
    if not os.path.exists(p):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        open(p, 'wb').write(urllib.request.urlopen(req, timeout=60).read())
    return 'data:image/jpeg;base64,' + base64.b64encode(open(p, 'rb').read()).decode()

async def main():
    specs = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    local = sys.argv[sys.argv.index('--local-img') + 1] if '--local-img' in sys.argv else None
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1000, 'height': 1000}, device_scale_factor=1.6)
        done = 0
        for s in specs:
            dest = os.path.join(out, s['file'])
            if os.path.exists(dest) and '--force' not in sys.argv: continue
            try:
                src = ('data:image/jpeg;base64,' + base64.b64encode(open(local, 'rb').read()).decode()) if local else fetch(s['immagine'], '/tmp/imgcache')
                await pg.set_content(page(s, src), wait_until='networkidle')
                await pg.evaluate("document.fonts.ready")
                await pg.screenshot(path=dest, type='jpeg', quality=85, clip={'x': 0, 'y': 0, 'width': 1000, 'height': 1000})
                done += 1
            except Exception as ex:
                print('ERRORE', s.get('sku'), ex)
        await b.close()
    print('fatte', done)

asyncio.run(main())
