"""Enrichissement firmographique et signaux d'appel : prépare ext/enr_in_NN.json (lots de 8 : priorité haute puis moyenne, vague,
effectif décroissant) pour la consigne scratch/enrich_brief.txt ; résultats ext/enr_out_NN.json, lus par enrich.py
(site, e-mail générique publié par l'entreprise, page LinkedIn et effectif affiché, actualités datées et sourcées, « pourquoi appeler maintenant »).
Usage : python3 enrich_lots.py [préfixe, par défaut r] [taille, par défaut 8]"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PREFIXE = sys.argv[1] if len(sys.argv) > 1 else 'r'
TAILLE = int(sys.argv[2]) if len(sys.argv) > 2 else 8
ORDRE = {'Haute': 0, 'Moyenne': 1, 'Basse': 2}
def emin(e):
    m = re.search(r'(\d+)', str(e or ''))
    return int(m.group(1)) if m else 0
deja = set()
for f in glob.glob(ROOT + '/ext/enr_out_*.json'):
    try: deja |= {str(x.get('siren')) for x in json.load(open(f, encoding='utf-8'))}
    except Exception: pass
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
cibles = sorted([c for c in companies if not c.get('exclue') and not c.get('cessation') and str(c.get('statut') or 'Active').lower().startswith('active')
                 and c.get('priorite') in ('Haute', 'Moyenne') and c['siren'] not in deja],
                key=lambda c: (ORDRE.get(c.get('priorite'), 3), c.get('vague') or 9, -emin(c.get('effectif')), c['rang']))
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'nom_court', 'ville', 'adresse', 'activite', 'effectif', 'groupe', 'site_web', 'email', 'linkedin',
          'description', 'actualite', 'opposition_prospection')
for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    json.dump([{kk: c.get(kk) for kk in GARDER if c.get(kk) not in (None, '', [], {})} for c in cibles[i:i + TAILLE]],
              open(f'{ROOT}/ext/enr_in_{PREFIXE}{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'entreprises en', -(-len(cibles) // TAILLE), 'lots', f'enr_in_{PREFIXE}01…')
