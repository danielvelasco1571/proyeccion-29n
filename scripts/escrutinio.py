"""Escrutinio del 29-N -> escrutinio.json (lo lee la sección «Noche electoral» de la web).

Uso:
  python scripts/escrutinio.py                 # usa la fuente de scripts/escrutinio_config.json si está activa
  python scripts/escrutinio.py --csv f.csv     # CSV provincial: prov;escrutado;PP;PSOE;...;BLANCO (cabecera con siglas)
  python scripts/escrutinio.py --estado definitivo --csv f.csv

Formato de escrutinio.json:
  {"estado":"sin_datos|provisional|definitivo","actualizado":ISO,"fuente":str,"escrutado":%,"participacion":%,
   "orden":[siglas],"prov":{"28":{"e":%,"v":[votos en el orden de "orden"]}},
   "escanos":[escaños nacionales en el orden de "orden"] (opcional),
   "historial":[{"t":ISO,"e":%,"prov":{"28":[e, votos...]}}]}
"""
import json, re, sys, os, csv, io, argparse, datetime, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'escrutinio.json'); CFG = os.path.join(ROOT, 'scripts', 'escrutinio_config.json')
ORDEN = ['PP','PSOE','VOX','FA','PODEMOS','COMPROMIS','SALF','ERC','JUNTS','BILDU','PNV','BNG','CC','AA','OTROS','BLANCO']
REGLAS = [  # (regex sobre el nombre o siglas de la candidatura, clave del modelo)
 (r'^(UPN.?PP|PP|PARTIDO POPULAR|PP.?PAR|PP.?UPN)\b|PARTIDO POPULAR', 'PP'),
 (r'PSOE|PSC|PSDEG|PSE.?EE|PARTIDO SOCIALISTA|SOCIALISTES', 'PSOE'),
 (r'^VOX\b', 'VOX'), (r'PODEMOS|PODEM\b', 'PODEMOS'), (r'COMPROM', 'COMPROMIS'),
 (r'FRENTE AMPLIO|SUMAR|FRONT AMPLI|MOVIMIENTO SUMAR|IU\b|IZQUIERDA UNIDA|COMUNS', 'FA'),
 (r'SE ACAB|SALF|ALVISE', 'SALF'), (r'^ERC|ESQUERRA REPUBLICANA', 'ERC'), (r'JUNTS|JxCAT', 'JUNTS'),
 (r'BILDU', 'BILDU'), (r'PNV|EAJ', 'PNV'), (r'^BNG|BLOQUE NACIONALISTA GALEGO', 'BNG'),
 (r'COALICI[OÓ]N CANARIA|^CC\b', 'CC'), (r'ADELANTE ANDALUC', 'AA'), (r'BLANCO|BLANCOS', 'BLANCO')]
def clave(nombre):
    n = nombre.upper().strip()
    for rx, k in REGLAS:
        if re.search(rx, n): return k
    return 'OTROS'
PROVN = {}  # nombre de provincia -> código INE (para fuentes que den nombres)
for c, n in json.load(open(os.path.join(ROOT, 'scripts', 'provincias.json'), encoding='utf8')).items():
    PROVN[re.sub(r'[^a-z]', '', n.lower())] = c
def cod_prov(x):
    x = str(x).strip()
    if re.fullmatch(r'\d{1,2}', x): return x.zfill(2)
    import unicodedata
    k = re.sub(r'[^a-z]', '', unicodedata.normalize('NFD', x.lower()).encode('ascii', 'ignore').decode())
    for n, c in PROVN.items():
        if k == n or k in n or n in k: return c
    return None
def guardar(prov, estado='provisional', fuente='', participacion=None, escanos=None):
    """prov: {cod: {'e': % escrutado, 'votos': {nombre_candidatura: votos}}}"""
    old = json.load(open(OUT, encoding='utf8')) if os.path.exists(OUT) else {}
    P = {}
    for c, o in prov.items():
        v = [0] * len(ORDEN)
        for nom, n in o['votos'].items(): v[ORDEN.index(clave(nom))] += int(n or 0)
        if sum(v): P[c] = {'e': round(float(o.get('e') or 0), 2), 'v': v}
    if not P: print('sin datos'); return False
    W = json.load(open(os.path.join(ROOT, 'scripts', 'provincias_votos23.json')))
    tot = sum(W.values()); esc = sum(P[c]['e'] * W.get(c, 0) for c in P) / tot if tot else 0
    hist = [h for h in old.get('historial', []) if h.get('e', 0) < esc - 0.05]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
    hist.append({'t': now, 'e': round(esc, 2), 'prov': {c: [o['e']] + o['v'] for c, o in P.items()}})
    if old.get('prov') == P and old.get('estado') == estado: print('sin cambios'); return False
    out = {'version': 1, 'estado': estado, 'actualizado': now, 'fuente': fuente, 'escrutado': round(esc, 2),
           'participacion': participacion, 'orden': ORDEN, 'prov': P, 'historial': hist[-40:]}
    if escanos: out['escanos'] = [sum(n for nom, n in escanos.items() if clave(nom) == k) for k in ORDEN]
    json.dump(out, open(OUT, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print(f'escrutinio.json: {len(P)} provincias, {esc:.1f} % escrutado ({estado})'); return True
def leer_csv(texto):
    rd = csv.reader(io.StringIO(texto), delimiter=';' if texto.count(';') > texto.count(',') else ',')
    head = next(rd); prov = {}
    for r in rd:
        if not r or not r[0].strip(): continue
        c = cod_prov(r[0])
        if not c: continue
        prov[c] = {'e': float(r[1].replace(',', '.') or 0), 'votos': {h: int(float(x.replace('.', '').replace(',', '.') or 0)) for h, x in zip(head[2:], r[2:]) if x.strip()}}
    return prov
def fuente_config():
    """Fuente configurable para la noche electoral (la rellena quien conozca el formato publicado por Interior)."""
    if not os.path.exists(CFG): return None
    cfg = json.load(open(CFG, encoding='utf8'))
    if not cfg.get('activo'): return None
    hoy = datetime.date.today().isoformat()
    if not (cfg.get('desde', '2026-11-29') <= hoy <= cfg.get('hasta', '2026-12-31')): return None
    raw = urllib.request.urlopen(urllib.request.Request(cfg['url'], headers={'User-Agent': 'proyeccion-29n'}), timeout=30).read().decode('utf8', 'replace')
    if cfg.get('formato') == 'csv': return leer_csv(raw), cfg
    if cfg.get('formato') == 'parser':  # módulo Python en scripts/ con una función parse(texto) -> prov
        import importlib; sys.path.insert(0, os.path.dirname(CFG))
        return importlib.import_module(cfg['modulo']).parse(raw), cfg
    return None
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--csv'); ap.add_argument('--estado', default='provisional'); ap.add_argument('--fuente', default=''); ap.add_argument('--participacion', type=float)
    a = ap.parse_args()
    if a.csv: guardar(leer_csv(open(a.csv, encoding='utf8').read()), a.estado, a.fuente or 'Ministerio del Interior', a.participacion)
    else:
        r = fuente_config()
        if r: guardar(r[0], r[1].get('estado', 'provisional'), r[1].get('fuente', 'Ministerio del Interior'))
        else: print('fuente inactiva')
