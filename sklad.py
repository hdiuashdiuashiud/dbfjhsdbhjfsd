"""Stáhne feed pro Zboží.cz z e-shopu a vytvoří malý soubor se skladem velikostí.
Výstup: public/sklad.json  ->  {"t": čas, "s": {"2743": "7,5|8|9|9,5", ...}}
Produkt, u kterého neznáme velikost některé varianty, se vynechá (stránka si ji pak ověří sama)."""
import json, os, re, sys, urllib.request, datetime

FEED = os.environ.get('FEED_URL', 'https://www.kvalitnirukavice.cz/fotky9964/xml/zbozi_cz_new.xml')
PORADI = ['6','6,5','7','7,5','8','8,5','9','9,5','10','10,5','11','11,5','12','13','XS','S','M','L','XL','XXL','90','95','100','105','110','115']

def nacti_feed():
    if len(sys.argv) > 1:
        return open(sys.argv[1], encoding='utf-8').read()
    req = urllib.request.Request(FEED, headers={'User-Agent': 'napa-sklad/1.0'})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read().decode('utf-8')

def main():
    velikosti = json.load(open('varianty.json', encoding='utf-8'))   # "2743-1335": "7,5"
    xml = nacti_feed()
    produkty, sklad, nezname = set(), {}, set()
    for it in re.finditer(r'<SHOPITEM>(.*?)</SHOPITEM>', xml, re.S):
        blok = it.group(1)
        iid = re.search(r'<ITEM_ID>(.*?)</ITEM_ID>', blok)
        if not iid: continue
        iid = iid.group(1).strip()
        grp = re.search(r'<ITEMGROUP_ID>(.*?)</ITEMGROUP_ID>', blok)
        if '-' not in iid:
            if grp: produkty.add(grp.group(1).strip())
            continue
        pid = iid.split('-')[0]
        produkty.add(pid)
        dd = re.search(r'<DELIVERY_DATE>(.*?)</DELIVERY_DATE>', blok)
        try: dostupne = int(dd.group(1)) >= 0 if dd else True
        except ValueError: dostupne = True
        if not dostupne: continue
        v = velikosti.get(iid)
        if v is None: nezname.add(pid); continue
        sklad.setdefault(pid, set()).add(v)
    if len(produkty) < 500:
        sys.exit('Feed vypadá podezřele malý (%d produktů) – soubor nepřepisuji.' % len(produkty))
    out = {}
    for pid in produkty:
        if pid in nezname: continue
        out[pid] = '|'.join(sorted(sklad.get(pid, ()), key=lambda x: PORADI.index(x) if x in PORADI else 99))
    os.makedirs('public', exist_ok=True)
    data = {'t': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 's': out}
    json.dump(data, open('public/sklad.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    open('public/index.html', 'w', encoding='utf-8').write('<meta charset="utf-8">Sklad velikostí NAPA Dobříš – aktualizováno %s UTC, %d produktů.' % (data['t'], len(out)))
    print('produktů:', len(out), 'vynecháno (neznámá velikost):', len(nezname))

main()
