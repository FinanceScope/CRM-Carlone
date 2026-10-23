"""Après la mise à jour des comptes (comptes_out_*), prépare ext/fiches_maj_in_mNN.json : les fiches consolidées
dont le plafond, le résultat ou la rentabilité ont changé, pour réécriture (consigne scratch/fiches_maj_brief.txt).
Usage : python3 -I fiches_maj_lots.py <companies.json d'avant la mise à jour>"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = 8
sid = lambda v: re.sub(r'\D', '', str(v))[-9:]
avant = {c.get('siren'): c for c in json.load(open(sys.argv[1], encoding='utf-8'))}
apres = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
SYN = {}
for f in sorted(glob.glob(ROOT + '/ext/top100_synth_out_*.json')):
    for x in json.load(open(f, encoding='utf-8')):
        SYN[sid(x.get('siren'))] = x
K = ('plafond', 'resultat', 'benefice', 'annee')
lot = []
for c in sorted(apres, key=lambda c: c['rang']):
    s, a0, a1 = SYN.get(c.get('siren')), (avant.get(c.get('siren')) or {}).get('art') or {}, c.get('art') or {}
    if not s or not c.get('comptes_recherche'): continue
    if round(a0.get('plafond') or 0, -3) == round(a1.get('plafond') or 0, -3) and a0.get('resultat') == a1.get('resultat') and a0.get('benefice') == a1.get('benefice'): continue
    lot.append({'rang': c['rang'], 'siren': c['siren'], 'nom': c['nom'], 'fiche': {k: v for k, v in s.items() if k != 'siren'},
                'avant': {k: a0.get(k) for k in K},
                'apres': {k: a1.get(k) for k in K + ('annee_resultat', 'prix_max', 'regime', 'espace_txt')},
                'comptes_recherche': c['comptes_recherche'], 'priorite_calculee': c.get('priorite')})
for f in glob.glob(ROOT + '/ext/fiches_maj_in_*.json'): os.remove(f)
for k, i in enumerate(range(0, len(lot), TAILLE), 1):
    json.dump(lot[i:i + TAILLE], open(f'{ROOT}/ext/fiches_maj_in_m{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(lot), 'fiches à réécrire en', -(-len(lot) // TAILLE), 'lots :', [x['rang'] for x in lot])
