"""Passe Serper (recherche Google par API) : pour chaque entreprise des lots ext/admin_in_<préfixe>NN.json, lance 4 requêtes Google
(LinkedIn finance, web finance/administratif, LinkedIn RH/administratif, site de l'entreprise) et garde les résultats bruts
(titre, lien, extrait, date) dans ext/serper/brut_<préfixe>NN.json, que lisent ensuite les agents de recherche (consigne scratch/serper_brief.txt).
La clé Serper n'est jamais dans le code : le proxy de la session l'ajoute aux requêtes vers google.serper.dev.
Usage : python3 serper_brut.py [préfixe, par défaut s]"""
import json, glob, os, re, sys, time, urllib.request, urllib.error
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PREFIXE = sys.argv[1] if len(sys.argv) > 1 else 's'
FIN = '(DAF OR "directeur financier" OR "directrice financière" OR "administratif et financier" OR "responsable financier" OR "contrôleur de gestion" OR "chef comptable" OR comptable)'
ADM = '("responsable administratif" OR "responsable administrative" OR "administratif et financier" OR "responsable comptable" OR "chef comptable" OR "directeur financier" OR DAF OR RAF OR comptable)'
RH = '(DRH OR "ressources humaines" OR "responsable RH" OR "assistante de direction" OR "responsable administrative" OR "office manager")'

def serper(q):
    for essai in range(4):
        try:
            req = urllib.request.Request('https://google.serper.dev/search', method='POST',
                                         data=json.dumps({'q': q, 'gl': 'fr', 'hl': 'fr', 'num': 10}).encode(),
                                         headers={'Content-Type': 'application/json', 'X-API-KEY': 'proxy-injected'})
            d = json.load(urllib.request.urlopen(req, timeout=40))
            return [{k: r.get(k) for k in ('title', 'link', 'snippet', 'date') if r.get(k)} for r in d.get('organic', [])]
        except urllib.error.HTTPError as e:
            if e.code in (401, 403): sys.exit(f'Clé Serper refusée ({e.code}) : vérifier la clé enregistrée pour google.serper.dev.')
            time.sleep(5 * (essai + 1))
        except Exception:
            time.sleep(5 * (essai + 1))
    return None

def nom_court(c):
    n = c.get('nom_court') or c.get('nom_commercial') or c.get('nom') or ''
    n = re.sub(r'\b(SAS|SASU|SARL|EURL|SA|SNC|SCOP|SCIC|SC|GIE)\b\.?', '', n, flags=re.I)
    return re.sub(r'\s+', ' ', n).strip(' -,')

def domaine(u):
    try: h = urlparse(u if '//' in u else '//' + u).hostname or ''
    except Exception: return ''
    return h[4:] if h.startswith('www.') else h

n_req = 0
for f in sorted(glob.glob(f'{ROOT}/ext/admin_in_{PREFIXE}[0-9][0-9].json')):
    out = f.replace('/admin_in_', '/serper/brut_')
    if os.path.exists(out): continue
    lot = []
    for c in json.load(open(f, encoding='utf-8')):
        nom, ville = nom_court(c), (c.get('ville') or '').split('(')[0].strip()
        reqs = [f'site:linkedin.com/in "{nom}" {FIN}', f'"{nom}" {ville} {ADM}', f'site:linkedin.com/in "{nom}" {RH}']
        d = domaine(c.get('site_web') or '')
        if d and not re.search(r'facebook|linkedin|pagesjaunes|societe\.com|pappers|kompass', d):
            reqs.append(f'site:{d} (comptable OR comptabilité OR financier OR administratif OR "ressources humaines" OR équipe OR organigramme)')
        else:
            reqs.append(f'"{nom}" {ville} (organigramme OR "notre équipe" OR "rattaché" OR "service comptable" OR "service administratif")')
        res = []
        for q in reqs:
            r = serper(q); n_req += 1
            res.append({'requete': q, 'resultats': r})
            time.sleep(0.3)
        lot.append({'siren': c['siren'], 'nom': c.get('nom'), 'nom_recherche': nom, 'ville': ville, 'recherches': res})
    json.dump(lot, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(os.path.basename(out), len(lot), 'entreprises', flush=True)
print(n_req, 'requêtes Serper')
