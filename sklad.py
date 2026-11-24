"""Stáhne feed (adresa v tajné proměnné FEED_URL) a vytvoří malý soubor se skladem velikostí.
Výstup: public/sklad.json  ->  {"t": čas, "s": {"2743": "7,5|8|9|9,5", "2989": "*", ...}}
("*" = produkt bez variant skladem, "" = není skladem)
Produkt, u kterého neznáme velikost některé varianty, se vynechá (stránka si ji pak ověří sama)."""
import json, os, re, sys, time, urllib.request, urllib.parse, datetime, socket

FEED = os.environ.get('FEED_URL', '')
PORADI = ['6','6,5','7','7,5','8','8,5','9','9,5','10','10,5','11','11,5','12','13','XS','S','M','L','XL','XXL','90','95','100','105','110','115']

_puvodni_gai = socket.getaddrinfo
def jen_ipv4(zapnout):
    """GitHub runnery občas nemají IPv6 – pak se připojujeme jen přes IPv4."""
    if zapnout:
        socket.getaddrinfo = lambda host, port, family=0, *a, **k: _puvodni_gai(host, port, socket.AF_INET, *a, **k)
    else:
        socket.getaddrinfo = _puvodni_gai

def diagnostika():
    try:
        host = urllib.parse.urlparse(FEED).hostname
        adr = sorted({x[4][0] for x in _puvodni_gai(host, 443)})
        print('Adresy serveru:', ', '.join(adr), flush=True)
    except Exception as e:
        print('DNS se nepovedlo:', e, flush=True)

def nacti_feed():
    if len(sys.argv) > 1:
        return open(sys.argv[1], encoding='utf-8').read()
    if not FEED: sys.exit('Chybí tajná proměnná FEED_URL.')
    posledni = None
    diagnostika()
    for pokus in range(1, 4):
        jen_ipv4(pokus >= 2)                       # 3 pokusy; 1. normálně, další jen přes IPv4
        try:
            req = urllib.request.Request(FEED, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read().decode('utf-8')
            if '</SHOP>' not in data:              # feed se zrovna generuje / nestáhl se celý
                raise ValueError('neúplný feed (%d B)' % len(data))
            return data
        except Exception as e:
            posledni = e
            print('Pokus %d se nepovedl: %s' % (pokus, e), flush=True)
            if pokus < 3: time.sleep(30)
    raise RuntimeError('Feed se nepodařilo stáhnout: %s' % posledni)

def hotovo(ok):
    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        open(out, 'a').write('ok=%s\n' % ('true' if ok else 'false'))

def main():
    velikosti = json.load(open('varianty.json', encoding='utf-8'))   # "2743-1335": "7,5"
    try:
        xml = nacti_feed()
    except Exception as e:
        print('VAROVÁNÍ:', e, '– na webu zůstává poslední úspěšná verze.')
        hotovo(False); return
    produkty, sklad, nezname = set(), {}, set()
    hlavni = {}   # produkty bez variant: ITEM_ID bez pomlčky -> je skladem?
    for it in re.finditer(r'<SHOPITEM>(.*?)</SHOPITEM>', xml, re.S):
        blok = it.group(1)
        iid = re.search(r'<ITEM_ID>(.*?)</ITEM_ID>', blok)
        if not iid: continue
        iid = iid.group(1).strip()
        grp = re.search(r'<ITEMGROUP_ID>(.*?)</ITEMGROUP_ID>', blok)
        dd = re.search(r'<DELIVERY_DATE>(.*?)</DELIVERY_DATE>', blok)
        try: dostupne = int(dd.group(1)) >= 0 if dd else True
        except ValueError: dostupne = True
        if '-' not in iid:
            hlavni[iid] = dostupne   # hlavní položka – použije se jen u produktů bez variant
            continue
        pid = iid.split('-')[0]
        produkty.add(pid)
        if not dostupne: continue
        v = velikosti.get(iid)
        if v is None: nezname.add(pid); continue
        sklad.setdefault(pid, set()).add(v)
    if len(produkty) < 500:
        print('VAROVÁNÍ: feed vypadá podezřele malý (%d produktů) – soubor nepřepisuji.' % len(produkty))
        hotovo(False); return
    # produkty s variantami, které ve feedu vůbec nejsou = nic skladem
    for k in velikosti:
        pid = k.split('-')[0]
        if pid not in produkty and pid not in nezname:
            produkty.add(pid)
    out = {}
    for pid in produkty:
        if pid in nezname: continue
        out[pid] = '|'.join(sorted(sklad.get(pid, ()), key=lambda x: PORADI.index(x) if x in PORADI else 99))
    # produkty bez variant (velikost se píše do poznámky): "*" = skladem, "" = není skladem
    s_variantami = produkty | {k.split('-')[0] for k in velikosti}
    for pid, ok in hlavni.items():
        if pid not in s_variantami:
            out[pid] = '*' if ok else ''
    os.makedirs('public', exist_ok=True)
    data = {'t': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), 's': out}
    json.dump(data, open('public/sklad.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    open('public/index.html', 'w', encoding='utf-8').write('<meta charset="utf-8">ok %s (%d)' % (data['t'], len(out)))
    print('produktů:', len(out), 'vynecháno (neznámá velikost):', len(nezname))
    hotovo(True)

main()
