"""Cibles prioritaires dont le standard ne vient que d'annuaires : prépare ext/confirm_in_f01.json pour une recherche
du numéro sur une page officielle (consigne scratch/confirm_brief.txt ; résultat ext/contacts_out_y01.json)."""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
cibles = sorted([c for c in companies if c['rang'] <= 100 and c.get('vague') and c.get('telephone_a_confirmer')], key=lambda c: c['rang'])
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'nom_court', 'ville', 'adresse', 'code_postal', 'telephone', 'site_web', 'email', 'groupe', 'note_contacts')
json.dump([{k: c.get(k) for k in GARDER if c.get(k) not in (None, '', [], {})} for c in cibles],
          open(ROOT + '/ext/confirm_in_f01.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'numéros à confirmer :', [c['rang'] for c in cibles])
