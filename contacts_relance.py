"""Passes de relance sur les cibles restées sans téléphone : prépare ext/contacts_in_<préfixe>NN.json
(fiche actuelle + toutes les passes précédentes). Les résultats ext/contacts_out_<préfixe>NN.json reprennent
l'entrée précédente en la complétant ; ext_merge.py les fusionne sans effacer ce qui était déjà trouvé.
  python3 -I contacts_relance.py            -> lots rNN : cibles prioritaires des 500 (seconde passe)
  python3 -I contacts_relance.py top100     -> lots uNN : cibles en vague du top 100 (troisième passe)"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
EXT = ROOT + '/ext'
TOP100 = len(sys.argv) > 1 and sys.argv[1] == 'top100'
PREFIXE = 'u' if TOP100 else 'r'
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
precedent = {}
for f in sorted(glob.glob(EXT + '/contacts_out_*.json')):
    for e in json.load(open(f, encoding='utf-8')):
        k = re.sub(r'\D', '', str(e.get('siren')))[-9:]
        if k in precedent:   # même fusion que ext_merge.py : une passe plus récente complète la précédente
            e = dict(precedent[k], **{kk: vv for kk, vv in e.items() if vv not in (None, '', [], {}) and not (kk == 'standard' and not (vv or {}).get('tel'))})
        precedent[k] = e

if TOP100:
    cibles = [c for c in companies if c['rang'] <= 100 and c.get('vague') and not c.get('telephone')]
else:
    cibles = [c for c in companies if c.get('priorite') == 'Haute' and not c.get('telephone')]
cibles.sort(key=lambda c: (c.get('vague') or 9, c['rang']))
TAILLE = 10 if TOP100 else 16
for old in glob.glob(f'{EXT}/contacts_in_{PREFIXE}*.json'):
    if not os.path.exists(old.replace('_in_', '_out_')): os.remove(old)
for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    lot = [{'rang': c['rang'], 'siren': c['siren'], 'nom': c['nom'], 'enseigne': c.get('nom_court') or c.get('nom_commercial'),
            'ville': c.get('ville'), 'adresse': ', '.join(x for x in (c.get('adresse'), ' '.join(x for x in (c.get('code_postal'), c.get('ville')) if x)) if x),
            'activite': c.get('activite'), 'effectif': c.get('effectif'), 'groupe': c.get('groupe'), 'site_web': c.get('site_web'),
            'dirigeants': [d['nom'] + (' (' + d['fonction'] + ')' if d.get('fonction') else '') for d in c.get('dirigeants') or []],
            'opposition_prospection': bool(c.get('opposition_prospection')),
            'lieu_decision': c.get('decision'),
            'premiere_passe': precedent.get(c['siren'])} for c in cibles[i:i + TAILLE]]
    json.dump(lot, open(f'{EXT}/contacts_in_{PREFIXE}{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{PREFIXE}{k:02d}', len(lot), [(x['rang'], x['enseigne'] or x['nom']) for x in lot])
