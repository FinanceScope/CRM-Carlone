"""Fiches consolidées des 100 entreprises du classement initial : prépare ext/top100_synth_in_sNN.json
(fiche complète, notes de recherche et de vérification) pour la rédaction (consigne scratch/top100_synthese_brief.txt).
Les fiches rédigées ext/top100_synth_out_sNN.json sont appliquées par art_merge.py."""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TAILLE = int(sys.argv[1]) if len(sys.argv) > 1 else 10
companies = json.load(open(ROOT + '/site/companies.json', encoding='utf-8'))
top = [c for c in companies if c['rang'] <= 100 and str(c.get('statut') or 'Active').lower().startswith('active')]
top.sort(key=lambda c: c['rang'])
GARDER = ('rang', 'siren', 'nom', 'nom_commercial', 'nom_court', 'activite', 'secteur', 'description', 'actualite', 'groupe', 'ca', 'resultat',
          'ca_recent', 'res_recent', 'annee_recent', 'effectif', 'forme_juridique', 'ville', 'adresse', 'code_postal', 'distance_cosne_km',
          'site_cosne', 'site_local', 'priorite', 'vague', 'art', 'telephone', 'telephone_a_confirmer', 'telephone_groupe', 'email', 'site_web',
          'dirigeants', 'contact_dirigeant', 'contact_finance', 'autres_contacts', 'decision', 'note_contacts', 'note_classement', 'corrections',
          'opposition_prospection', 'angle_partenariat', 'interlocuteur_cible')
for k, i in enumerate(range(0, len(top), TAILLE), 1):
    lot = [{kk: c.get(kk) for kk in GARDER if c.get(kk) not in (None, '', [], {})} | {'sources': (c.get('sources') or [])[:6]} for c in top[i:i + TAILLE]]
    json.dump(lot, open(f'{ROOT}/ext/top100_synth_in_s{k:02d}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(top), 'fiches en', -(-len(top) // TAILLE), 'lots')
