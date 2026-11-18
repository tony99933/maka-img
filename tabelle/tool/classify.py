# Classifica le foto Amazon: infografica con fascia blu scura in alto (per variante) o no.
import json, sys, io, urllib.request, concurrent.futures as cf
from PIL import Image
ids = json.load(open('tabelle/ids.json'))
def one(i):
    url = 'https://m.media-amazon.com/images/I/%s._SL200_.jpg' % i
    for t in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert('RGB')
            w, h = im.size
            top = im.crop((0, 0, w, max(2, int(h * 0.07)))).resize((20, 4))
            px = list(top.getdata())
            r = sum(p[0] for p in px) / len(px); g = sum(p[1] for p in px) / len(px); b = sum(p[2] for p in px) / len(px)
            # parte bassa del centro per riconoscere il fondo
            return i, [round(r), round(g), round(b), w, h]
        except Exception as e:
            err = str(e)
    return i, ['ERR', err]
out = {}
with cf.ThreadPoolExecutor(32) as ex:
    for i, v in ex.map(one, ids):
        out[i] = v
json.dump(out, open('tabelle/colori.json', 'w'))
print(len(out), sum(1 for v in out.values() if v[0] == 'ERR'))
