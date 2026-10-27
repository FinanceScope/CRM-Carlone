"""Responsables finance, RH et administration : prépare ext/admin_in_<préfixe>NN.json (lots de 10, effectif décroissant)
pour la recherche des décideurs (consigne scratch/admin_brief.txt ; résultats ext/admin_out_<préfixe>NN.json).
Usage : python3 admin_lots.py <Haute|Moyenne|Basse> <préfixe> [effectif minimal] [sans]
Entreprises actives, hors campagne exclues ; « sans » : seulement celles qui n'ont encore aucun interlocuteur finance, RH ou administratif. Lancer les lots par passages de 6 au plus à cause du quota de recherches web."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PRIO, PREFIXE = sys.argv[1], sys.argv[2]
EFF_MIN = int(sys.argv[3]) if len(sys.argv) > 3 else 0
SANS = len(sys.argv) > 4 and sys.argv[4] == 'sans'
TAILLE = 10
def emin(e):
    m = re.search(r'(\d+)', str(e or ''))
    return int(m.group(1)) if m else 0
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
cibles = sorted([c for c in companies if c.get('priorite') == PRIO and not c.get('exclue') and emin(c.get('effectif')) >= EFF_MIN
                 and str(c.get('statut') or 'Active').lower().startswith('active') and not (SANS and c.get('contacts_admin'))],
                key=lambda c: (-emin(c.get('effectif')), c['rang']))
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'nom_court', 'ville', 'adresse', 'activite', 'effectif', 'groupe', 'site_web', 'linkedin',
          'dirigeants', 'contact_dirigeant', 'contact_finance', 'autres_contacts', 'decision', 'note_contacts', 'note_admin', 'opposition_prospection')
def rec(c):
    r = {k: c.get(k) for k in GARDER if c.get(k) not in (None, '', [], {})}
    if (c.get('fiche') or {}).get('qui_appeler'): r['qui_appeler'] = c['fiche']['qui_appeler']
    return r
for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    json.dump([rec(c) for c in cibles[i:i + TAILLE]], open(f'{ROOT}/ext/admin_in_{PREFIXE}{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'entreprises en', -(-len(cibles) // TAILLE), 'lots', f'admin_in_{PREFIXE}01…')
