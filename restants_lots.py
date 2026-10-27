"""Entreprises actives encore sans téléphone après les étapes 1 à 3 (toutes priorités, hors campagne exclues) :
prépare ext/rest_in_zrNN.json (lots de 10, par priorité puis rang) pour une passe approfondie
(consigne scratch/restants_brief.txt ; résultats ext/contacts_out_zrNN.json, lus après toutes les passes précédentes).
Deux passages de 5 lots à cause du quota de recherches web.
Usage : python3 restants_lots.py [préfixe, par défaut zr] (quatrième passe : zs, consigne scratch/quatrieme_brief.txt)."""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = 10
PREFIXE = sys.argv[1] if len(sys.argv) > 1 else 'zr'
ORDRE = {'Haute': 0, 'Moyenne': 1, 'Basse': 2}
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
cibles = sorted([c for c in companies if not c.get('telephone') and not c.get('exclue') and not c.get('cessation')
                 and str(c.get('statut') or 'Active').lower().startswith('active')], key=lambda c: (ORDRE.get(c.get('priorite'), 3), c['rang']))
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'ville', 'adresse', 'code_postal', 'activite', 'code_naf', 'effectif', 'groupe', 'site_web', 'email',
          'dirigeants', 'contact_dirigeant', 'note_contacts', 'opposition_prospection')
for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    json.dump([{kk: c.get(kk) for kk in GARDER if c.get(kk) not in (None, '', [], {})} for c in cibles[i:i + TAILLE]],
              open(f'{ROOT}/ext/rest_in_{PREFIXE}{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'entreprises en', -(-len(cibles) // TAILLE), 'lots', f'rest_in_{PREFIXE}01…')
