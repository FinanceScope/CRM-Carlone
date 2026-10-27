"""Deuxième cercle du top 100 (priorité moyenne, sans téléphone ; ou « Basse » : troisième cercle) : prépare ext/cercle2_in_eNN.json
(ou ext/cercle3_in_gNN.json) pour la recherche
du standard du site ou du siège qui décide (consigne scratch/cercle2_brief.txt). Résultats : ext/contacts_out_x01.json…"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = 9
PRIO = sys.argv[1] if len(sys.argv) > 1 else 'Moyenne'          # « Basse » : entreprises en perte, à rappeler plus tard
PREFIXE = {'Moyenne': 'cercle2_in_e', 'Basse': 'cercle3_in_g'}[PRIO]
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
cibles = sorted([c for c in companies if c['rang'] <= 100 and c.get('priorite') == PRIO and not c.get('telephone') and not c.get('exclue')
                 and str(c.get('statut') or 'Active').lower().startswith('active')], key=lambda c: c['rang'])
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'nom_court', 'ville', 'adresse', 'code_postal', 'effectif', 'groupe', 'site_web', 'email',
          'decision', 'dirigeants', 'contact_dirigeant', 'note_contacts', 'opposition_prospection')
for k, i in enumerate(range(0, len(cibles), TAILLE), 1):
    lot = []
    for c in cibles[i:i + TAILLE]:
        x = {kk: c.get(kk) for kk in GARDER if c.get(kk) not in (None, '', [], {})}
        fi = c.get('fiche') or {}
        x['fiche'] = {kk: fi.get(kk) for kk in ('nom_affiche', 'activite', 'groupe', 'qui_appeler', 'vigilance')}
        lot.append(x)
    json.dump(lot, open(f'{ROOT}/ext/{PREFIXE}{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(cibles), 'entreprises en', -(-len(cibles) // TAILLE), 'lots :', [c['rang'] for c in cibles])
