"""Recherche approfondie sur les 100 entreprises du classement initial : prépare ext/contacts_in_tNN.json
(fiche actuelle complète), dans l'ordre des vagues puis des priorités. Consigne : scratch/top100_brief.txt ;
résultats ext/contacts_out_tNN.json, chargés après les autres passes par ext_merge.py (ils complètent sans effacer)."""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = int(sys.argv[1]) if len(sys.argv) > 1 else 6
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
PRIO = {'Haute': 0, 'Moyenne': 1, 'Basse': 2}
top = [c for c in companies if c['rang'] <= 100 and str(c.get('statut') or 'Active').lower().startswith('active')]
top.sort(key=lambda c: (c.get('vague') or 9, PRIO.get(c.get('priorite'), 3), c['rang']))

def item(c):
    return {'rang': c['rang'], 'siren': c['siren'], 'nom': c['nom'], 'enseigne': c.get('nom_court') or c.get('nom_commercial'),
            'ville': c.get('ville'), 'adresse': c.get('adresse'), 'activite': c.get('activite'), 'effectif': c.get('effectif'),
            'ca': c.get('ca'), 'groupe': c.get('groupe'),
            'dirigeants_registre': [d['nom'] + (' (' + d['fonction'] + ')' if d.get('fonction') else '') for d in c.get('dirigeants') or []],
            'deja': {'telephone': c.get('telephone'), 'telephone_fiabilite': 'à confirmer' if c.get('telephone_a_confirmer') else None,
                     'email': c.get('email'), 'site_web': c.get('site_web'), 'contact_dirigeant': c.get('contact_dirigeant'),
                     'contact_finance': c.get('contact_finance'), 'note': c.get('note_contacts')},
            'opposition_prospection': bool(c.get('opposition_prospection'))}

for k, i in enumerate(range(0, len(top), TAILLE), 1):
    json.dump([item(c) for c in top[i:i + TAILLE]], open(f'{ROOT}/ext/contacts_in_t{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(top), 'entreprises en', -(-len(top) // TAILLE), 'lots de', TAILLE)
