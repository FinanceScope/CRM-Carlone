"""Contrôle d'un relevé de comptes : python3 -I scratch/check_comptes.py ext/comptes_out_cNN.json ext/comptes_in_cNN.json"""
import json, sys

def textes(v):
    if isinstance(v, str): yield v
    elif isinstance(v, dict):
        for x in v.values(): yield from textes(x)
    elif isinstance(v, list):
        for x in v: yield from textes(x)

out, inp = (json.load(open(p, encoding='utf-8')) for p in sys.argv[1:3])
assert [str(x['siren']) for x in out] == [str(x['siren']) for x in inp], 'ordre ou SIREN différents'
for x, r in zip(out, inp):
    if not x.get('trouve'): continue
    if not x.get('citation') or not any(x['citation'] in t for t in textes(r)): print(x['siren'], 'citation absente du dossier')
    if x.get('ca') is None and x.get('resultat') is None: print(x['siren'], 'aucun chiffre relevé')
    for k in ('ca', 'resultat'):
        if x.get(k) is not None and not isinstance(x[k], int): print(x['siren'], k, 'doit être un entier')
    if not str(x.get('annee') or '').isdigit(): print(x['siren'], 'année manquante')
print(len(out), 'fiches,', sum(1 for x in out if x.get('trouve')), 'relevés')
