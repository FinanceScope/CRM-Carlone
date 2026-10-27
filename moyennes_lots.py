"""Rangs 101 à 500 en priorité moyenne sans téléphone : prépare ext/moy_in_pNN.json (lots de 10, par rang)
pour la recherche du standard (consigne scratch/moyennes_brief.txt ; résultats ext/contacts_out_pNN.json).
Trois passages de 6 lots, à lancer un par un à cause du quota de recherches web."""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = int(sys.argv[1]) if len(sys.argv) > 1 else 10
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
cibles = sorted([c for c in companies if c['rang'] > 100 and c.get('priorite') == 'Moyenne' and not c.get('telephone') and not c.get('vague')
                 and str(c.get('statut') or 'Active').lower().startswith('active')], key=lambda c: c['rang'])
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'ville', 'adresse', 'code_postal', 'activite', 'code_naf', 'effectif', 'groupe', 'site_web', 'email',
          'dirigeants', 'contact_dirigeant', 'note_contacts', 'opposition_prospection')
for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    json.dump([{kk: c.get(kk) for kk in GARDER if c.get(kk) not in (None, '', [], {})} for c in cibles[i:i + TAILLE]],
              open(f'{ROOT}/ext/moy_in_p{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'entreprises en', -(-len(cibles) // TAILLE), 'lots')
