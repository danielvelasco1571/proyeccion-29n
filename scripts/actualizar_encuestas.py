"""Añade a encuestas_nuevas.json las encuestas de las generales del 29-N publicadas después del corte.
Fuentes: Objetivo 176 (ciento76.es) y Wikipedia; Electomanía se intenta primero pero suele bloquear accesos automáticos.
Uso: python scripts/actualizar_encuestas.py  (sin dependencias salvo beautifulsoup4)"""
import json, re, sys, unicodedata, urllib.request, datetime, os
from bs4 import BeautifulSoup
CORTE = '2026-10-15'          # solo se buscan encuestas con fin de campo posterior a esta fecha
BASE = os.path.join(os.path.dirname(__file__), 'base_incluidas.json')   # encuestas que ya trae index.html
OUT = os.path.join(os.path.dirname(__file__), '..', 'encuestas_nuevas.json')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'}
CASAS = ['ElectoPanel','Sigma Dos','40dB','SocioMétrica','Target Point','NC Report','Hamalgama Métrica','DYM','InvyMark','Simple Lógica',
         'Celeste-Tel','GAD3','GESOP','Ateneo del Dato','Ipsos','Data10','More in Common','Sondaxe','Cluster17','IMOP','Winston','Opina 360','ODEC','The Objective','CIS','KeyData']
PARTIDOS = ['PP','PSOE','VOX','FA','COMPROMIS','PODEMOS','SALF','ERC','JUNTS','BILDU','PNV','BNG','CC','UPN','AA']

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')

def slug(t):
    t = unicodedata.normalize('NFD', t.lower()); t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')

def casa_norm(nombre):
    n = re.sub(r'\[.*?\]', '', nombre).split('/')[0].strip()
    if n.startswith('EM-Analytics') or n.lower().startswith('electopanel'): return 'ElectoPanel'
    for c in CASAS:
        if slug(c) == slug(n) or slug(n).startswith(slug(c)): return c
    return n

def estado_de(casa, firma=''):
    if 'CIS' in casa or 'CIS' in firma: return 'CIS'
    if casa == 'KeyData': return 'agregador'
    if casa in ('PSOE', 'PP', 'VOX', 'Sumar', 'Podemos'): return 'partidista'
    return 'modelo'

def de_ciento76():
    s = get('https://www.ciento76.es/encuestas')
    trozos = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', s, re.S)
    txt = ''.join(json.loads('"' + t + '"') for t in trozos)
    i = txt.find('{"encuestas":[')
    obj, _ = json.JSONDecoder().raw_decode(txt[i:])
    out = []
    for e in obj['encuestas']:
        casa = casa_norm(e['encuestadora'])
        r = {'fecha': e['fin'], 'casa': casa, 'medio': '', 'n': e.get('n'), 'url': e.get('url'), 'fuente': 'ciento76',
             'estado': estado_de(casa)}
        if r['estado'] == 'modelo' and not e.get('incluida', True) and 'repite' in (e.get('motivo') or '').lower():
            r['estado'] = 'repite'
        for k, src in [('PP','pp'),('PSOE','psoe'),('VOX','vox'),('FA','sumar'),('PODEMOS','podemos'),('SALF','salf')]:
            if e.get(src) is not None: r[k] = float(e[src])
        out.append(r)
    return out

def de_wikipedia():
    s = get('https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Spanish_general_election')
    soup = BeautifulSoup(s, 'html.parser')
    t = soup.find('table', class_='wikitable')
    MAP = {'PP':'PP','PSOE':'PSOE','Vox':'VOX','FA':'FA','Sumar':'FA','FV':'COMPROMIS','ERC':'ERC','Junts':'JUNTS','EH Bildu':'BILDU','PNV':'PNV',
           'BNG':'BNG','CCa':'CC','UPN':'UPN','Adelante Andalucía (2021)':'AA','Podemos':'PODEMOS','Se Acabó La Fiesta':'SALF'}
    trs = t.find_all('tr'); hdr = []
    for th in trs[0].find_all(['th', 'td']):
        a = th.find('a'); nm = (a.get('title') if a and a.get('title') else th.get_text(' ', strip=True))
        hdr += [nm] * int(th.get('colspan', 1))
    meses = {m: i + 1 for i, m in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}
    out = []
    for tr in trs[1:]:
        celdas, spans = [], []
        for td in tr.find_all(['td', 'th']):
            cs = int(td.get('colspan', 1)); celdas += [td.get_text(' ', strip=True)] * cs; spans += [cs] * cs
        if len(celdas) != len(hdr): continue
        r = dict(zip(hdr, celdas)); sp = dict(zip(hdr, spans))
        firma = re.sub(r'\[.*?\]', '', r.get('Polling firm/Commissioner', ''))
        if 'election' in firma.lower(): continue
        toks = re.findall(r'(\d{1,2})\s*([A-Z][a-z]{2})?', r.get('Fieldwork date', ''))
        d = m = None
        for a, b in toks:
            d = int(a); m = meses.get(b, m) if b else m
        if not d or not m: continue
        anio = 2026 if m >= 7 else 2027
        casa = casa_norm(firma)
        x = {'fecha': f'{anio}-{m:02d}-{d:02d}', 'casa': casa, 'medio': firma.split('/')[1].strip() if '/' in firma else '',
             'fuente': 'wikipedia', 'estado': estado_de(casa, firma)}
        nn = re.sub(r'\D', '', r.get('Sample size', '')); x['n'] = int(nn) if nn else None
        for k, v in MAP.items():
            if k in r:
                mm = re.match(r'\s*([\d.]+)', r[k])
                if mm:
                    if v == 'COMPROMIS' and sp.get(k, 1) > 1: continue   # celda compartida FA+FV: se queda en FA
                    x[v] = float(mm.group(1))
        out.append(x)
    return out

def fusiona(a, b):
    """a (Wikipedia) manda en los porcentajes (separa FA y Compromís); b (ciento76) completa y aporta la marca de oleada repetida.
    En ciento76, «sumar» es FA con Compromís: si solo existe esa fuente, se guarda como FA sin Compromís."""
    res = {}
    for r in a + b:
        clave = None
        for k in list(res):
            c, f = k
            if c == r['casa'] and abs((datetime.date.fromisoformat(f) - datetime.date.fromisoformat(r['fecha'])).days) <= 1:
                clave = k; break
        if clave is None:
            res[(r['casa'], r['fecha'])] = dict(r)
        else:
            base = res[clave]
            for k, v in r.items():
                if k == 'estado':
                    if v != 'modelo': base['estado'] = v
                elif base.get(k) in (None, '') and v not in (None, ''):
                    base[k] = v
            base['fuente'] = base['fuente'] + '+' + r['fuente'] if r['fuente'] not in base['fuente'] else base['fuente']
    return list(res.values())

def main():
    previas = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else []
    ids = {p['id'] for p in previas}
    incluidas = [tuple(x) for x in json.load(open(BASE, encoding='utf-8'))] + [(p['casa'], p['fecha']) for p in previas]
    def ya_esta(casa, fecha):
        f = datetime.date.fromisoformat(fecha)
        return any(c == casa and abs((datetime.date.fromisoformat(d) - f).days) <= 1 for c, d in incluidas)
    fuentes, errores = [], []
    try:
        get('https://electomania.es/category/encuestas/encuestas-generales/'); errores.append('electomania: accesible pero sin lector de tablas (se usan sus datos vía Objetivo 176 y Wikipedia)')
    except Exception as e:
        errores.append(f'electomania: {e.__class__.__name__}')
    c76, wk = [], []
    try: c76 = de_ciento76(); fuentes.append(f'ciento76 ({len(c76)})')
    except Exception as e: errores.append(f'ciento76: {e}')
    try: wk = de_wikipedia(); fuentes.append(f'wikipedia ({len(wk)})')
    except Exception as e: errores.append(f'wikipedia: {e}')
    nuevas = []
    for r in fusiona(wk, c76):
        if r['fecha'] <= CORTE: continue
        r['id'] = r['fecha'] + '-' + slug(r['casa'])
        if r['id'] in ids or ya_esta(r['casa'], r['fecha']): continue
        if r.get('PP') is None or r.get('PSOE') is None: continue
        r = {k: v for k, v in r.items() if v not in (None, '')}
        nuevas.append(r); ids.add(r['id'])
    if nuevas:
        todas = sorted(previas + nuevas, key=lambda p: p['fecha'], reverse=True)
        json.dump(todas, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('Fuentes:', ', '.join(fuentes) or 'ninguna'); print('Avisos:', '; '.join(errores) or 'ninguno')
    print(f'Encuestas nuevas: {len(nuevas)}', *[f"  {p['fecha']} {p['casa']} ({p['estado']})" for p in nuevas], sep='\n')

if __name__ == '__main__':
    main()
