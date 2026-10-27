"""Rangs 101 à 500 en priorité basse sans téléphone (étape 3) : prépare ext/bas_in_sNN.json (lots de 10, par rang)
pour la recherche du standard (même consigne que l'étape 2, scratch/moyennes_brief.txt ; résultats ext/contacts_out_sNN.json,
lus après les passes h et p). Entreprises en procédure collective écartées. Deux passages (6 lots, puis le reste) à cause du quota de recherches web."""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = int(sys.argv[1]) if len(sys.argv) > 1 else 10
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
cibles = sorted([c for c in companies if c['rang'] > 100 and c.get('priorite') == 'Basse' and not c.get('telephone') and not c.get('vague')
                 and str(c.get('statut') or 'Active').lower().startswith('active')], key=lambda c: c['rang'])
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'ville', 'adresse', 'code_postal', 'activite', 'code_naf', 'effectif', 'groupe', 'site_web', 'email',
          'dirigeants', 'contact_dirigeant', 'note_contacts', 'opposition_prospection')
for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    json.dump([{kk: c.get(kk) for kk in GARDER if c.get(kk) not in (None, '', [], {})} for c in cibles[i:i + TAILLE]],
              open(f'{ROOT}/ext/bas_in_s{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'entreprises en', -(-len(cibles) // TAILLE), 'lots')
