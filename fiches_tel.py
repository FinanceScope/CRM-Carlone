"""Fiches d'appel qui disent encore « aucun numéro » alors qu'un standard a été trouvé depuis : prépare ext/fiches_tel_in.json
(consigne scratch/fiches_tel_brief.txt ; résultat ext/fiches_maj_out_<lot>.json, appliqué par art_merge.py).
Usage : python3 -I fiches_tel.py m07  →  ext/fiches_tel_in_m07.json (sans argument : m06, premier lot)."""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sid = lambda v: re.sub(r'\D', '', str(v))[-9:]
LOT = sys.argv[1] if len(sys.argv) > 1 else 'm06'
SANS = re.compile(r"aucun (numéro|standard)|numéro (est |reste )?à (trouver|obtenir)|sans (aucun )?numéro|pas de numéro|aucun téléphone|standard introuvable|numéro inconnu", re.I)
SYN = {}
for f in sorted(glob.glob(ROOT + '/ext/top100_synth_out_*.json')) + sorted(glob.glob(ROOT + '/ext/fiches_maj_out_*.json')):
    if f.endswith(f'_{LOT}.json'): continue
    for x in json.load(open(f, encoding='utf-8')): SYN[sid(x.get('siren'))] = x
lot = []
for c in sorted(json.load(open(ROOT + '/site/companies.json', encoding='utf-8')), key=lambda c: c['rang']):
    s = SYN.get(c.get('siren'))
    if not s or not c.get('telephone'): continue
    txt = ' '.join([s.get('qui_appeler') or ''] + list(s.get('vigilance') or []) + [s.get('raison') or ''])
    if not SANS.search(txt) or c['telephone'] in (s.get('qui_appeler') or ''): continue
    note = c.get('note_contacts') or ''
    i = max(note.rfind('Deuxième cercle'), note.rfind('Confirmation du standard'), note.rfind('4e passe'))
    lot.append({'rang': c['rang'], 'siren': c['siren'], 'nom': c['nom'], 'fiche': {k: v for k, v in s.items() if k not in ('siren', 'modifs')},
                'telephone': c['telephone'], 'telephone_a_confirmer': bool(c.get('telephone_a_confirmer')), 'telephone_groupe': bool(c.get('telephone_groupe')),
                'email': c.get('email'), 'site_web': c.get('site_web'), 'recherche': note[i:] if i >= 0 else note[-800:],
                'opposition_prospection': c.get('opposition_prospection')})
json.dump(lot, open(ROOT + ('/ext/fiches_tel_in.json' if LOT == 'm06' else f'/ext/fiches_tel_in_{LOT}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(lot), 'fiches à mettre à jour :', [x['rang'] for x in lot])
