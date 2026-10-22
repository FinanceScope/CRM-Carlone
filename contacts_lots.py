"""Prépare les lots de recherche de coordonnées (ext/contacts_in_hNN.json) dans l'ordre des priorités « œuvres d'art » :
cibles prioritaires par vague, puis priorité moyenne, puis le reste. Les entreprises déjà recherchées (contacts_ok) sont sautées.
À lancer après art_merge.py. Consigne des recherches : scratch/contacts_brief.txt ; résultats attendus dans ext/contacts_out_hNN.json."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = int(sys.argv[1]) if len(sys.argv) > 1 else 16

companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
PRIO = {'Haute': 0, 'Moyenne': 1, 'Basse': 2}
todo = [c for c in companies if not c.get('contacts_ok') and str(c.get('statut') or 'Active').lower().startswith('active')]
todo.sort(key=lambda c: (PRIO.get(c.get('priorite'), 3), c.get('vague') or 9, c['rang']))

def item(c):
    ic = c.get('interlocuteur_cible') or {}
    return {
        'rang': c['rang'], 'siren': c.get('siren'), 'nom': c['nom'],
        'enseigne': c.get('nom_court') or c.get('nom_commercial'), 'ville': c.get('ville'),
        'adresse': ', '.join(x for x in (c.get('adresse'), ' '.join(x for x in (c.get('code_postal'), c.get('ville')) if x)) if x) or None,
        'ca': (c.get('art') or {}).get('ca'), 'effectif': c.get('effectif'), 'activite': c.get('activite'),
        'deja': {
            'telephone': c.get('telephone'), 'email': c.get('email'), 'site_web': c.get('site_web'), 'linkedin': c.get('linkedin'),
            'dirigeants': [f"{d['nom']} ({d.get('fonction') or ''})".replace(' ()', '') for d in c.get('dirigeants') or []],
            'interlocuteur': (ic.get('nom') + (' — ' + ic['fonction'] if ic.get('fonction') else '')) if ic.get('nom') else None,
        },
        'opposition_prospection': bool(c.get('opposition_prospection')),
        'pappers_url': c.get('pappers_url') or ('https://www.pappers.fr/entreprise/' + re.sub(r'\D', '', str(c.get('siren') or ''))),
    }

# les lots déjà lancés (fichier de sortie présent) sont gardés ; les autres sont refaits, numérotés à la suite
EXT = ROOT + '/ext'
done = [int(m.group(1)) for f in os.listdir(EXT) for m in [re.fullmatch(r'contacts_out_h(\d+)\.json', f)] if m]
for f in os.listdir(EXT):
    m = re.fullmatch(r'contacts_in_h(\d+)\.json', f)
    if m and int(m.group(1)) not in done: os.remove(EXT + '/' + f)
first = max(done, default=0) + 1
lots = [todo[i:i + TAILLE] for i in range(0, len(todo), TAILLE)]
for k, lot in enumerate(lots, first):
    json.dump([item(c) for c in lot], open(f'{EXT}/contacts_in_h{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(todo), 'entreprises à rechercher en', len(lots), f'lots de {TAILLE} (h{first:02d} à h{first + len(lots) - 1:02d})')
for k, lot in list(enumerate(lots, first))[:8]:
    print(f'h{k:02d}', [(c['rang'], c.get('priorite'), c.get('vague')) for c in lot][:4], '…')
