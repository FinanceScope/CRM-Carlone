"""Comptes les plus récents des 100 entreprises du classement initial : prépare ext/comptes_in_cNN.json
(chiffres de référence et tous les textes de la fiche où la recherche a pu relever un exercice plus récent)
pour l'extraction (consigne scratch/comptes_brief.txt). Les relevés ext/comptes_out_cNN.json sont appliqués par art_merge.py."""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = int(sys.argv[1]) if len(sys.argv) > 1 else 20
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
SYN = {}
for f in sorted(glob.glob(ROOT + '/ext/top100_synth_out_*.json')):
    for x in json.load(open(f, encoding='utf-8')):
        SYN[re.sub(r'\D', '', str(x.get('siren')))[-9:]] = x
top = sorted([c for c in companies if c['rang'] <= 100 and str(c.get('statut') or 'Active').lower().startswith('active')], key=lambda c: c['rang'])
GARDER = ('rang', 'siren', 'nom', 'nom_court', 'forme_juridique', 'ca', 'resultat', 'ca_recent', 'res_recent', 'annee_recent', 'actualite',
          'description', 'note_classement', 'corrections', 'note_contacts', 'decision')
for k, i in enumerate(range(0, len(top), TAILLE), 1):
    lot = []
    for c in top[i:i + TAILLE]:
        x = {kk: c.get(kk) for kk in GARDER if c.get(kk) not in (None, '', [], {})}
        s = SYN.get(c.get('siren'))
        if s: x['fiche_redigee'] = {kk: s.get(kk) for kk in ('resume', 'angle_art', 'vigilance', 'raison')}
        x['sources'] = c.get('sources') or []
        lot.append(x)
    json.dump(lot, open(f'{ROOT}/ext/comptes_in_c{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(top), 'fiches en', -(-len(top) // TAILLE), 'lots')
