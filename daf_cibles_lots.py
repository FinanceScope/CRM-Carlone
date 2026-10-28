"""DAF des 37 cibles prioritaires (priorité haute, en vague, top 100) : prépare ext/admin_in_fNN.json (lots de 5, vague puis effectif décroissant)
pour une passe ciblée sur le décideur financier (consigne scratch/daf2_brief.txt ; résultats ext/admin_out_fNN.json, même format que les autres
passes « décideurs », fusionnés par ext_merge.py). Sont exclues les cibles qui ont déjà un responsable finance confirmé.
Usage : python3 daf_cibles_lots.py [préfixe, par défaut f] [grands]
« grands » : à la place des 37 cibles, les entreprises d'au moins 100 salariés hors cibles qui n'ont encore aucun responsable finance."""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PREFIXE = sys.argv[1] if len(sys.argv) > 1 else 'f'
TAILLE = 5
def emin(e):
    m = re.search(r'(\d+)', str(e or ''))
    return int(m.group(1)) if m else 0
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
GRANDS = len(sys.argv) > 2 and sys.argv[2] == 'grands'
est_cible = lambda c: c.get('priorite') == 'Haute' and c.get('vague') and c['rang'] <= 100
if GRANDS:
    cibles = [c for c in companies if not est_cible(c) and emin(c.get('effectif')) >= 100 and not c.get('exclue')
              and str(c.get('statut') or 'Active').lower().startswith('active') and not any(p.get('role') == 'finance' for p in c.get('contacts_admin') or [])]
else:
    cibles = [c for c in companies if est_cible(c) and not c.get('exclue')]
garder = [c for c in cibles if not any(p.get('role') == 'finance' and p.get('fiabilite') == 'confirme' for p in c.get('contacts_admin') or [])]
garder.sort(key=lambda c: (c.get('vague') or 9, -emin(c.get('effectif')), c['rang']))
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'nom_court', 'ville', 'adresse', 'activite', 'effectif', 'groupe', 'site_web', 'linkedin',
          'dirigeants', 'contact_dirigeant', 'contact_finance', 'autres_contacts', 'contacts_admin', 'decision', 'note_contacts', 'note_admin', 'opposition_prospection')
def rec(c):
    r = {k: c.get(k) for k in GARDER if c.get(k) not in (None, '', [], {})}
    if (c.get('fiche') or {}).get('qui_appeler'): r['qui_appeler'] = c['fiche']['qui_appeler']
    return r
for k, i in enumerate(range(0, len(garder), TAILLE), 1):
    json.dump([rec(c) for c in garder[i:i + TAILLE]], open(f'{ROOT}/ext/admin_in_{PREFIXE}{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'cibles ;', len(cibles) - len(garder), 'avec un responsable finance confirmé ;', len(garder), 'à chercher en', -(-len(garder) // TAILLE), 'lots', f'admin_in_{PREFIXE}01…')
