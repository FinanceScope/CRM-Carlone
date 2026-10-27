"""Après la recherche des décideurs financiers (ext/contacts_out_w*.json, contre-vérifiés) : prépare ext/fiches_daf_in.json,
les fiches d'appel à mettre à jour quand un DAF, un responsable comptable ou un DAF de groupe a été trouvé
(consigne scratch/fiches_daf_brief.txt ; résultat ext/fiches_maj_out_m05.json, appliqué par art_merge.py)."""
import glob, json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
sid = lambda v: re.sub(r'\D', '', str(v))[-9:]
SYN = {}
for f in sorted(glob.glob(ROOT + '/ext/top100_synth_out_*.json')) + sorted(glob.glob(ROOT + '/ext/fiches_maj_out_*.json')):
    if f.endswith('_m05.json'): continue
    for x in json.load(open(f, encoding='utf-8')): SYN[sid(x.get('siren'))] = x
companies = {c.get('siren'): c for c in json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))}
lot = []
for f in sorted(glob.glob(ROOT + '/ext/contacts_out_w*.json')):
    for x in json.load(open(f, encoding='utf-8')):
        k = sid(x.get('siren'))
        if x.get('statut_daf') in ('trouve', 'groupe') and x.get('decideur_financier') and k in SYN:
            c = companies.get(k) or {}
            lot.append({'rang': c.get('rang'), 'siren': k, 'nom': c.get('nom'), 'fiche': {kk: v for kk, v in SYN[k].items() if kk not in ('siren', 'modifs')},
                        'decideur_financier': x['decideur_financier'], 'autres_contacts': x.get('autres_contacts') or [], 'note': x.get('note'),
                        'contact_dirigeant': c.get('contact_dirigeant'), 'opposition_prospection': c.get('opposition_prospection')})
json.dump(sorted(lot, key=lambda x: x['rang'] or 999), open(ROOT + '/ext/fiches_daf_in.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(lot), 'fiches à mettre à jour :', [x['rang'] for x in lot])
