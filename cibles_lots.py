"""Cibles prioritaires des rangs 101 à 500 (vagues 1 à 3) : prépare ext/contacts_in_qNN.json pour une recherche approfondie
comme celle du top 100 (consigne scratch/cibles_brief.txt). Résultats ext/contacts_out_qNN.json, fusionnés par ext_merge.py."""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = int(sys.argv[1]) if len(sys.argv) > 1 else 7
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
cibles = sorted([c for c in companies if c['rang'] > 100 and c.get('vague')], key=lambda c: (c['vague'], c['rang']))

def item(c):
    return {'rang': c['rang'], 'siren': c['siren'], 'nom': c['nom'], 'enseigne': c.get('nom_court') or c.get('nom_commercial'),
            'ville': c.get('ville'), 'adresse': c.get('adresse'), 'activite': c.get('activite'), 'code_naf': c.get('code_naf'),
            'effectif': c.get('effectif'), 'ca': c.get('ca'), 'resultat': c.get('resultat'), 'groupe': c.get('groupe'),
            'description': c.get('description'),
            'dirigeants_registre': [d['nom'] + (' (' + d['fonction'] + ')' if d.get('fonction') else '') for d in c.get('dirigeants') or []],
            'deja': {'telephone': c.get('telephone'), 'telephone_fiabilite': 'à confirmer' if c.get('telephone_a_confirmer') else None,
                     'email': c.get('email'), 'site_web': c.get('site_web'), 'contact_dirigeant': c.get('contact_dirigeant'),
                     'contact_finance': c.get('contact_finance'), 'note': c.get('note_contacts')},
            'opposition_prospection': bool(c.get('opposition_prospection'))}

for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    json.dump([item(c) for c in cibles[i:i + TAILLE]], open(f'{ROOT}/ext/contacts_in_q{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'cibles en', -(-len(cibles) // TAILLE), 'lots :', [c['rang'] for c in cibles])
