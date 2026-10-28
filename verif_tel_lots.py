"""Enrichissement : deuxième source pour les standards « à confirmer » (un seul annuaire ou source ancienne).
Prépare ext/tel_in_vNN.json (lots de 12 : priorité haute, moyenne puis basse ; vague ; effectif décroissant) pour la consigne
scratch/verif_tel_brief.txt ; résultats ext/tel_out_vNN.json, lus par ext_merge.py (confirmé : drapeau levé ; autre numéro publié : affiché à côté).
Usage : python3 verif_tel_lots.py [préfixe, par défaut v]"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PREFIXE = sys.argv[1] if len(sys.argv) > 1 else 'v'
TAILLE = 12
ORDRE = {'Haute': 0, 'Moyenne': 1, 'Basse': 2}
def emin(e):
    m = re.search(r'(\d+)', str(e or ''))
    return int(m.group(1)) if m else 0
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
cibles = sorted([c for c in companies if c.get('telephone') and c.get('telephone_a_confirmer') and not c.get('exclue') and not c.get('cessation')
                 and str(c.get('statut') or 'Active').lower().startswith('active')],
                key=lambda c: (ORDRE.get(c.get('priorite'), 3), c.get('vague') or 9, -emin(c.get('effectif')), c['rang']))
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'nom_court', 'ville', 'adresse', 'code_postal', 'activite', 'telephone', 'telephone_groupe', 'site_web', 'groupe', 'opposition_prospection')
def rec(c):
    r = {k: c.get(k) for k in GARDER if c.get(k) not in (None, '', [], {})}
    r['sources'] = [s for s in c.get('sources') or [] if 'api.gouv' not in s][:6]
    if c.get('note_contacts'): r['note_contacts'] = c['note_contacts'][-900:]
    return r
for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    json.dump([rec(c) for c in cibles[i:i + TAILLE]], open(f'{ROOT}/ext/tel_in_{PREFIXE}{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'standards à confirmer en', -(-len(cibles) // TAILLE), 'lots', f'tel_in_{PREFIXE}01…')
