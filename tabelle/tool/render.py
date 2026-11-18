# Genera le tabelle misure MAKA (1600x1600 jpg) dalle specifiche in tabelle/specs/*.json
import asyncio, base64, glob, html, io, json, os, urllib.request
from PIL import Image, ImageChops
from playwright.async_api import async_playwright

OUT = 'tabelle/img'
os.makedirs(OUT, exist_ok=True)
os.makedirs('/tmp/imgc', exist_ok=True)

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1000px;height:1000px;font-family:Inter,Arial,sans-serif;background:#fff;color:#111;position:relative;overflow:hidden}
.head{background:#000;color:#fff;height:150px;display:flex;align-items:center;padding:0 36px;gap:26px}
.logo{font-weight:900;font-size:44px;letter-spacing:6px;border:3px solid #fff;padding:6px 14px;flex:none}
.t1{font-size:34px;font-weight:800;line-height:1.1}
.t2{font-size:19px;color:#f0a24a;font-weight:700;margin-top:7px;letter-spacing:.4px}
.body{position:absolute;top:172px;left:32px;right:32px;bottom:108px;display:flex;gap:24px}
.left{width:250px;flex:none;display:flex;flex-direction:column;gap:9px;overflow:hidden}
.left .ph{width:250px;height:210px;border:1px solid #e5e5e5;border-radius:14px;display:flex;align-items:center;justify-content:center;background:#fff;flex:none}
.left .ph img{max-width:226px;max-height:192px}
.box{background:#f4f5f7;border-radius:11px;padding:8px 13px;flex:none}
.box .k{font-size:12px;color:#777;text-transform:uppercase;letter-spacing:1px;font-weight:700}
.box .v{font-size:var(--bv,18px);font-weight:800;margin-top:2px;line-height:1.2}
.right{flex:1;min-width:0;display:flex;flex-direction:column}
.extra{margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:9px}
table{border-collapse:separate;border-spacing:0;width:100%}
th{background:#1d1d1f;color:#fff;font-size:var(--th,20px);padding:10px 6px;font-weight:800;line-height:1.1;vertical-align:middle}
th:first-child{border-radius:10px 0 0 0;text-align:left;padding-left:16px}th:last-child{border-radius:0 10px 0 0}
th .s{display:block;font-size:12px;font-weight:600;color:#c9c9c9;margin-top:3px}
td{font-size:var(--td,21px);height:var(--rh,40px);padding:0 6px;text-align:center;border-bottom:1px solid #e6e6e6;font-weight:600;line-height:1.1;vertical-align:middle}
td:first-child{font-weight:800;text-align:left;padding-left:16px;white-space:nowrap}
td.tx{font-size:calc(var(--td,21px) * .8)}
tr:nth-child(even) td{background:#f7f7f8}
.ok{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;background:#1f9d55;color:#fff;font-size:18px;font-weight:900}
.no{color:#bbb;font-size:22px}
.foot{position:absolute;left:0;right:0;bottom:0;height:88px;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;padding:0 30px;text-align:center}
.foot span{color:#f0a24a}
"""

FIT = """() => {
 const L=document.querySelector('.left'), R=document.querySelector('.right'), T=document.querySelector('table');
 const set=(k,v)=>document.body.style.setProperty(k,v);
 let td=21, th=20;
 while((T.scrollWidth>R.clientWidth || T.offsetHeight>R.clientHeight) && td>11){td-=1; th=Math.max(12,th-1); set('--td',td+'px'); set('--th',th+'px');
   const rh=parseFloat(getComputedStyle(document.body).getPropertyValue('--rh')); if(T.offsetHeight>R.clientHeight) set('--rh',Math.max(22,rh-2)+'px');}
 let bv=18; set('--bv',bv+'px');
 while(L.scrollHeight>L.clientHeight && bv>15){bv-=1; set('--bv',bv+'px');}
 if(L.scrollHeight>L.clientHeight){
   const X=document.createElement('div'); X.className='extra'; R.appendChild(X);
   const free=()=>R.clientHeight-T.offsetHeight-X.offsetHeight-14;
   while(L.scrollHeight>L.clientHeight){ const bs=L.querySelectorAll('.box'); if(!bs.length) break; const b=bs[bs.length-1]; X.prepend(b); if(free()<0){L.appendChild(b); break;} }
 }
 while(L.scrollHeight>L.clientHeight && bv>12){bv-=1; set('--bv',bv+'px');}
 if(L.scrollHeight>L.clientHeight){document.querySelector('.ph').style.height='140px';}
 return [L.scrollHeight<=L.clientHeight, T.scrollWidth<=R.clientWidth, T.offsetHeight<=R.clientHeight];
}"""

def e(s):
    return html.escape(str(s or ''))

def photo(i):
    if not i:
        return ''
    p = '/tmp/imgc/%s.png' % i.replace('+', '_')
    if not os.path.exists(p):
        url = 'https://m.media-amazon.com/images/I/%s._SL800_.jpg' % i
        for t in range(3):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=60).read())).convert('RGB')
                bg = Image.new('RGB', im.size, (255, 255, 255))
                d = ImageChops.difference(im, bg).convert('L').point(lambda x: 255 if x > 18 else 0)
                b = d.getbbox()
                if b:
                    m = 16
                    im = im.crop((max(0, b[0] - m), max(0, b[1] - m), min(im.width, b[2] + m), min(im.height, b[3] + m)))
                im.save(p)
                break
            except Exception as ex:
                print('foto', i, ex)
        if not os.path.exists(p):
            return ''
    return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode()

def page(t):
    n = len(t['rows'])
    rh = max(26, min(56, int(640 / max(1, n)) - 1))
    ths = ''.join('<th>%s%s</th>' % (e(c['h']), ('<span class="s">%s</span>' % e(c['s'])) if c.get('s') else '') for c in t['cols'])
    trs = ''
    for r in t['rows']:
        cells = '<td>%s</td>' % e(r[0])
        for x in r[1:]:
            if x is True:
                cells += '<td><span class="ok">✓</span></td>'
            elif x is False or x is None or x == '':
                cells += '<td><span class="no">—</span></td>' if x is False else '<td></td>'
            else:
                cells += '<td class="tx">%s</td>' % e(x)
        trs += '<tr>%s</tr>' % cells
    boxes = ''.join('<div class="box"><div class="k">%s</div><div class="v">%s</div></div>' % (e(k), e(v)) for k, v in t['boxes'])
    src = photo(t.get('img'))
    img = '<div class="ph"><img src="%s"></div>' % src if src else ''
    return ("<html><head><meta charset='utf-8'><link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap' rel='stylesheet'>"
            "<style>%s</style></head><body style='--rh:%dpx'>"
            "<div class='head'><div class='logo'>MAKA</div><div><div class='t1'>%s</div><div class='t2'>%s</div></div></div>"
            "<div class='body'><div class='left'>%s%s</div><div class='right'><table><tr>%s</tr>%s</table></div></div>"
            "<div class='foot'><div>%s</div></div></body></html>") % (CSS, rh, e(t['title']), e(t['sub']), img, boxes, ths, trs, t['foot'])

async def main():
    todo = []
    for f in sorted(glob.glob('tabelle/specs/*.json')):
        for t in json.load(open(f)):
            if not os.path.exists(os.path.join(OUT, t['file'])):
                todo.append(t)
    print('da fare', len(todo))
    rep = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={'width': 1000, 'height': 1000}, device_scale_factor=1.6)
        for t in todo:
            await pg.set_content(page(t), wait_until='networkidle')
            ok = await pg.evaluate(FIT)
            await pg.screenshot(path=os.path.join(OUT, t['file']), type='jpeg', quality=88)
            if not all(ok):
                rep.append([t['file'], ok])
        await b.close()
    json.dump(rep, open('tabelle/problemi.json', 'w'))
    print('problemi', len(rep))

asyncio.run(main())
