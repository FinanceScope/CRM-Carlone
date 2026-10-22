"""Seconde passe sur les cibles prioritaires restées sans téléphone : prépare ext/contacts_in_rNN.json
(fiche actuelle + entrée de la première recherche). Les résultats ext/contacts_out_rNN.json reprennent l'entrée
de la première passe en la complétant ; chargés après les lots hNN, ils la remplacent."""
import glob, json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
EXT = ROOT + '/ext'
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
premiere = {}
for f in sorted(glob.glob(EXT + '/contacts_out_h*.json')):
    for e in json.load(open(f, encoding='utf-8')):
        premiere[re.sub(r'\D', '', str(e.get('siren')))[-9:]] = e

cibles = [c for c in companies if c.get('priorite') == 'Haute' and not c.get('telephone')]
cibles.sort(key=lambda c: (c.get('vague') or 9, c['rang']))
TAILLE = 16
for old in glob.glob(EXT + '/contacts_in_r*.json'):
    if not os.path.exists(old.replace('_in_', '_out_')): os.remove(old)
for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    lot = [{'rang': c['rang'], 'siren': c['siren'], 'nom': c['nom'], 'enseigne': c.get('nom_court') or c.get('nom_commercial'),
            'ville': c.get('ville'), 'adresse': ', '.join(x for x in (c.get('adresse'), ' '.join(x for x in (c.get('code_postal'), c.get('ville')) if x)) if x),
            'activite': c.get('activite'), 'effectif': c.get('effectif'), 'groupe': c.get('groupe'),
            'dirigeants': [d['nom'] + (' (' + d['fonction'] + ')' if d.get('fonction') else '') for d in c.get('dirigeants') or []],
            'opposition_prospection': bool(c.get('opposition_prospection')),
            'premiere_passe': premiere.get(c['siren'])} for c in cibles[i:i + TAILLE]]
    json.dump(lot, open(f'{EXT}/contacts_in_r{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'r{k:02d}', len(lot), [(x['rang'], x['enseigne'] or x['nom']) for x in lot][:5], '…')
