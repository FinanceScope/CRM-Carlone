# CRM-Carlone — CRM Entreprises Nièvre

CRM partagé pour démarcher les entreprises de la Nièvre (projet Le Vieux Relais / le M, Cosne-Cours-sur-Loire).
Contexte, consignes et liste des tâches : [`PASSATION.md`](PASSATION.md).

## Contenu

- `site/` : la page (`index.html`) et ses données (`companies.json`, `culture.json`), publiées ensemble comme artifact claude.ai.
- `merge.py` : top 100 (classement Pappers du 02/09/2026) → `site/companies.json`.
- `ext_merge.py` : rangs 101–500, comptes, enrichissements et contacts (`ext/contacts_out_*.json`) ; à relancer après `merge.py`.
- `art_merge.py` : profil pour la vente d'œuvres d'art (article 238 bis AB du CGI) : régime fiscal, plafond de déduction, lieu d'exposition, priorités et vagues ; à relancer après `ext_merge.py`.
- `merge_culture.py` : artistes, associations, lieux → `site/culture.json`.
- Préparation des recherches sur le top 100 (lots lus par les agents, consignes dans `scratch/`) : `top100_lots.py` (coordonnées), `top100_synthese.py` (fiches d'appel consolidées), `comptes_lots.py` (comptes 2025 cités dans les fiches, contrôle `scratch/check_comptes.py`), `fiches_maj_lots.py` (fiches à réécrire quand les chiffres changent). `art_merge.py` applique `ext/top100_synth_out_*`, `ext/comptes_out_*` et `ext/fiches_maj_out_*`.
- `ext/`, `culture/`, `research/`, `base.tsv` : données brutes.
- `scratch/` : consignes des recherches (briefs) réutilisables.

## Régénérer les données

```sh
python3 -I merge.py && python3 -I ext_merge.py && python3 -I art_merge.py
python3 -I merge_culture.py
```

Les scripts lisent et écrivent dans le dossier où ils se trouvent.
