"""Décideurs financiers des cibles prioritaires du top 100 (vagues 1 à 3) : prépare ext/daf_in_dNN.json
pour la recherche (consigne scratch/daf_brief.txt). Les résultats ext/contacts_out_wNN.json sont fusionnés par ext_merge.py."""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = int(sys.argv[1]) if len(sys.argv) > 1 else 10
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
cibles = sorted([c for c in companies if c['rang'] <= 100 and c.get('vague')], key=lambda c: c['rang'])
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'nom_court', 'ville', 'adresse', 'effectif', 'forme_juridique', 'groupe', 'site_web',
          'decision', 'dirigeants', 'contact_dirigeant', 'contact_finance', 'autres_contacts', 'note_contacts', 'opposition_prospection')
for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    lot = []
    for c in cibles[i:i + TAILLE]:
        x = {kk: c.get(kk) for kk in GARDER if c.get(kk) not in (None, '', [], {})}
        fi = c.get('fiche') or {}
        x['fiche'] = {kk: fi.get(kk) for kk in ('nom_affiche', 'activite', 'groupe', 'qui_appeler', 'vigilance')}
        lot.append(x)
    json.dump(lot, open(f'{ROOT}/ext/daf_in_d{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'cibles en', -(-len(cibles) // TAILLE), 'lots')
