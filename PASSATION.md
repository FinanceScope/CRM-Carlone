# Passation — CRM Entreprises Nièvre (projet Vieux Relais / le M)

## Mise à jour du 22/10/2026 (nouveau compte, dépôt FinanceScope/CRM-Carlone)
- **Page CRM republiée** depuis le nouveau compte (privée) : https://claude.ai/artifact/CrKrSAuH9mUAaey2wN8uSV — capacités `db` (collection « suivi », vide au départ), `user` (noms des associés dans l'historique), `downloads` (export CSV). Le suivi saisi sur l'ancienne page n'a pas été repris.
- **Réorientation vers la vente d'œuvres d'art faite** (`art_merge.py`, à lancer après `ext_merge.py`) : régime fiscal probable, bénéfice, plafond de déduction par entreprise (20 000 € ou 5 ‰ du CA, plancher confirmé par le BOFiP), lieu d'exposition, nouvelles priorités et vagues (96 cibles prioritaires : 16 à Cosne, 18 dans le bassin, 62 grands comptes). Page : dispositif en cinq conditions, calcul de la déduction, discours, objections, cadre légal sourcé, mail neutre par fiche.
- **Contacts (terminé le 22/10/2026)** : les 489 entreprises en activité sont recherchées (les 11 en procédure collective sont écartées). Lots `ext/contacts_in_h01` à `h30` (ordre des priorités art, `contacts_lots.py`), seconde passe sur les cibles prioritaires sans téléphone (`contacts_relance.py`, lots `r01` à `r03`), vérification indépendante des lots prioritaires h01 à h06 (`contacts_verif_*.json`, aucune valeur fausse trouvée). Résultat : 185 téléphones (63 des 96 cibles prioritaires), 38 e-mails génériques, 127 sites, 418 dirigeants nommés, 2 responsables financiers seulement (la recherche web n'en trouve presque jamais dans ces PME). Un numéro d'annuaire seul ou ancien est marqué « à confirmer à l'appel » ; les notes de recherche sont dans chaque fiche. `ext_merge.py` fusionne les passes successives sans effacer les précédentes.
- **Recentrage sur les 100 entreprises du classement initial (23/10/2026, demande de Mathys)** : la page affiche par défaut les 100 (sélecteur « 100 entreprises / Les 500 »). Recherche approfondie des 97 actives (`top100_lots.py`, consigne `scratch/top100_brief.txt`, lots `ext/contacts_in_t01` à `t17`, 6 recherches par entreprise) puis contre-vérification adverse des 51 nouveautés sensibles (`ext/contacts_verif_t1` à `t3`, aucune contredite). Résultat sur les 97 : 61 standards (37 sans réserve), 25 e-mails génériques, 68 sites, 93 dirigeants (10 différents du registre, « à confirmer »), 6 directeurs financiers de groupe (Aperam, Elsan, Chopard, Centre France, Babeau Seguin, TFF), aucun DAF propre à une société, lieu de décision renseigné pour les 97. Correction : le rang 35 est l'usine de fixations de ski LOOK (groupe Rossignol), pas LOOK Cycle. Ensuite : troisième passe sur les 19 cibles en vague sans standard (`contacts_relance.py top100`, lots `u01`, `u02` : IGOL Centre et le standard du groupe Rave pour ASM) et contre-vérification des 76 « autres contacts » (`contacts_verif_x1` à `x3` : 7 confirmés, 1 retiré, le reste « à confirmer »). Bilan : 63 standards sur 97 (39 sans réserve), vague 1 : 8/9, vague 2 : 7/8, vague 3 : 36/51. Les 17 cibles restantes sans numéro (filtre « Sans téléphone ») sont à relever à la main (Pages Jaunes, 118 712, site de l'entreprise).
- **Quota** : la session est limitée à 200 recherches web par tour, partagées entre tous les agents ; travailler par paquets de moins de 150 recherches, un par tour.
- **Étude Hermès (Vocalcom)** : `docs/hermes-vocalcom.md`, publiée en page (https://claude.ai/artifact/7CxFvbouc5d9Y4Xcxq4wMk). Conclusion : surdimensionné ; commencer avec le CRM et les téléphones, puis éventuellement Ringover ou Aircall. Les règles de prospection 2026 (téléphone, e-mail, rétractation de 14 jours des entreprises de 5 salariés au plus) sont reprises dans l'onglet Plan d'attaque.
- **Réseau** : l'environnement cloud bloque l'accès direct aux sites (bofip, legifrance, pappers, API recherche-entreprises) ; seule la recherche web fonctionne. Élargir l'accès réseau dans les réglages de l'environnement pour les recherches qui demandent d'ouvrir des pages.
- **Point à faire valider** : exposer des œuvres achetées par une entreprise dans un lieu tiers ouvert au public (piste du Vieux Relais) n'est pas explicitement prévu par le BOFiP (qui cite les locaux de l'entreprise, les événements et le dépôt dans un musée) : à valider par un expert-comptable ou un avocat fiscaliste.

Document de reprise, rédigé le 22/10/2026, pour continuer le projet depuis un autre compte Claude.
À joindre dans la nouvelle conversation avec l'archive `crm-nievre-projet.zip`.

## 1. Contexte
- Un associé rachète deux établissements à Cosne-Cours-sur-Loire : **Le Vieux Relais** (hôtel-restaurant) et **le M** (bar).
- Mission : démarcher les entreprises de la Nièvre à partir du classement Pappers, avec un CRM partagé entre associés.
- **Principe du CRM (pas encore intégré dans la page)** : proposer aux entreprises d'acheter des œuvres d'art, avec la défiscalisation comme argument.
  - Dispositif : article 238 bis AB du CGI, prorogé jusqu'au 31/12/2028 par l'article 89 de la loi de finances pour 2026 (actualité BOFiP du 15/04/2026).
  - Conditions : entreprises surtout à l'IS ; œuvres originales d'artistes vivants inscrites à l'actif ; exposées dans un lieu accessible au public ou aux salariés (pas les bureaux) ; déduction sur 5 ans par cinquièmes ; plafond annuel lié à 5 ‰ du CA, minoré du mécénat (plancher de 20 000 € à vérifier) ; réserve spéciale au passif. À valider avec l'expert-comptable de chaque entreprise.
- **Ensuite** : le CRM servira de base d'appels dans le logiciel « Hermès Pro ». Logiciel pas formellement identifié (peut-être Vocalcom Hermes360) : récupérer son modèle d'import (colonnes attendues) et adapter l'export CSV.

## 2. Consignes à respecter
- **Ne jamais parler du Vieux Relais ni du M aux entreprises**, ni du lieu d'exposition des œuvres, pour l'instant. Les textes côté entreprises (angles, mails, scripts) sont neutres ; un garde-fou dans `ext_merge.py` / `merge.py` (regex INTERDIT) bloque ces mentions.
- Exception : le Vieux Relais peut être nommé dans les messages aux **artistes et associations** (onglet Culture). Le M n'est jamais nommé.
- 13 entreprises se sont opposées à la prospection sur Pappers (drapeau dans leur fiche) : pas de mailing, contact direct uniquement.
- Coordonnées : uniquement des coordonnées professionnelles publiées ; ne jamais deviner une adresse e-mail.

## 3. Ce qui existe
- **Page CRM** (artifact claude.ai de l'ancien compte, privé, version 9) : https://claude.ai/artifact/4UxtzQPwRBXPKNNYuDqFTG
  - Onglets : Plan d'attaque (vagues, pistes, discours au téléphone), Les 500 entreprises (liste, filtres, fiche détaillée, suivi), Culture & événements (97 artistes, associations, lieux et réseaux).
  - Suivi partagé (statut, responsable, relances, notes, historique) enregistré dans l'artifact. **Il ne suit pas le changement de compte** : exporter le CSV depuis la page si des notes ont été saisies.
  - Capacités de la page : `db` (collection « suivi »), `user`, `downloads` — à redéclarer en republiant depuis le nouveau compte.
- **Fichiers** (archive, dossier `site/`) : `index.html` (la page), `companies.json` (500 fiches), `culture.json`.

## 4. Les 500 entreprises — méthode
- Rangs 1–100 : classement Pappers du 02/09/2026 (photo fournie) ; 43 cibles contre-vérifiées ; un encadré signale 24 entreprises dont le registre donne un exercice récent très différent.
- Rangs 101–432 : classés par CA du dernier exercice publié (2023 ou plus récent), CA et résultat du même exercice, d'après le registre national (API recherche-entreprises.api.gouv.fr) ou la fiche Pappers. Candidates repérées sur les classements Pappers par commune (relevés le 22/10/2026) et au registre (tranche 300 k€–1 M€). Seuil d'entrée ≈ 278 k€.
- Rangs 433–500 : entreprises sans comptes publiés employant au moins 10 salariés (tranche INSEE), classées par effectif.
- Écartées : fermées, en liquidation ou dissolution, organismes publics, associations sans comptes. Procédures en cours ou plans de redressement récents : signalés et hors vagues.
- Deux contrôles indépendants sur 20 fiches tirées au hasard : le 2e confirme les chiffres ; limites connues : statut des procédures vérifié surtout pour les cibles, dirigeants du registre parfois en retard (avertissement dans les fiches).

## 5. Plan d'attaque actuel
- Vague 1 (site à Cosne, ≤ 5 km) : 25 entreprises ; vague 2 (5–30 km) : 22 ; vague 3 (grands comptes jusqu'à Nevers) : 22.
- Les priorités et les « pistes » reposent encore sur l'ancienne logique (repas d'affaires, moments d'équipe, avantages salariés, événements). Hôtels et restaurants sont hors vagues dans cette logique.
- L'abattoir de Cosne a rouvert : remis en vague 1 (note dans la fiche).

## 6. À faire
1. **Coordonnées** (demande en cours) : trouver pour chaque entreprise le standard, un e-mail générique et le décideur financier (DAF/RAF, sinon le dirigeant) avec ses coordonnées pro publiées. Aujourd'hui 54 fiches sur 500 ont un téléphone. Recherche lancée en 17 lots puis interrompue par la limite d'usage : résultats partiels dans `ext/contacts_out_a1.json`, `contacts_out_b2.json`, `contacts_out_b4.json` (59 entreprises). Consigne détaillée : `scratch/contacts_brief.txt` ; lots préparés : `ext/contacts_in_*.json` (a = cibles des vagues, b = priorité 2, c = reste). Relancer par petits lots pour ménager la limite d'usage. `ext_merge.py` intègre déjà les fichiers `contacts_out_*.json` (bloc « Décideur financier », filtre « Avec téléphone », colonnes CSV).
2. **Réorienter le CRM vers la vente d'œuvres d'art** : nouveau pitch, scripts et mails ; plafond de déduction calculé par entreprise ; prioriser les entreprises bénéficiaires à l'IS et celles qui ont des espaces recevant du public ou des salariés (commerces, concessions, hôtels, restaurants…).
3. **Export pour Hermès Pro** une fois le modèle d'import récupéré.
4. Volet culture : contacter artistes et associations (messages prêts dans l'onglet Culture).

## 7. Contenu de l'archive
- `site/` : la page et ses données (à republier ensemble).
- `merge.py` (top 100 → `site/companies.json`), puis `ext_merge.py` (rangs 101–500, comptes, enrichissements, contacts ; à relancer après `merge.py`), `merge_culture.py` (→ `site/culture.json`).
- `ext/` : données brutes (classements par commune, registre, derniers comptes, compléments, enrichissements, contrôles qualité, contacts).
- `culture/`, `research/`, `base.tsv` : sources du volet culture et du top 100.
- `scratch/` : consignes des recherches (briefs) réutilisables.
