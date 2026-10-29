# CRM Entreprises Nièvre : version autonome (sans Claude)

Cette version du CRM tourne sur **Firebase**, le service d'hébergement et de base de données de Google, sous votre propre compte. Une fois installée, elle ne dépend plus de Claude ni de claude.ai : chaque associé ouvre une adresse web (par exemple `https://crm-nievre.web.app`), se connecte avec son compte Google, et retrouve le CRM et le suivi partagé en temps réel.

Le CRM est **le même** que sur claude.ai : mêmes vues, mêmes fiches, même panneau Hermes360. Seuls changent l'hébergement, la connexion et l'endroit où le suivi est enregistré.

## Ce qui est protégé

- L'adresse publique ne montre qu'un écran de connexion. Le CRM, les 500 fiches, le suivi des appels et les prospects culture sont dans la base Firestore et ne sont lisibles **qu'après connexion d'un associé autorisé**.
- Un associé est autorisé quand son adresse e-mail figure dans les règles de la base (`firestore.rules`) **et** qu'elle est vérifiée (toujours le cas avec un compte Google).
- Testé le 29/10/2026 avec les émulateurs officiels de Firebase : lecture refusée sans connexion, compte non autorisé refusé, adresse non vérifiée refusée, deux associés synchronisés en direct.

## Installation (une fois, environ 30 minutes)

Il faut un compte Google (celui qui « possède » le CRM), un ordinateur avec Python 3 et [Node.js](https://nodejs.org) installés, et une copie du dépôt du CRM.

### 1. Créer le projet Firebase

1. Aller sur la [console Firebase](https://console.firebase.google.com) et « Créer un projet », par exemple `crm-nievre`. Google Analytics n'est pas nécessaire.
2. Dans le projet, cliquer sur l'icône Web (`</>`) pour « Ajouter une application Web ». Lui donner un nom (CRM). Ne pas cocher Firebase Hosting à cette étape.
3. Firebase affiche un bloc `firebaseConfig`. Ouvrir le fichier `autonome/public/config.js` du dépôt et y recopier les valeurs `apiKey`, `authDomain`, `projectId` et `appId` à la place des `A_REMPLACER`. Ces valeurs ne sont pas secrètes.

### 2. Activer la connexion

1. Menu **Authentication** > « Commencer ».
2. Onglet « Mode de connexion » : activer **Google**. Facultatif : activer aussi « Adresse e-mail/Mot de passe » pour un associé sans compte Google (son compte se crée ensuite dans l'onglet « Utilisateurs » ; il recevra un e-mail de vérification à sa première connexion).

### 3. Créer la base et ses règles

1. Menu **Firestore Database** > « Créer une base de données », en **mode production**, emplacement **europe-west9 (Paris)**.
2. Onglet « Règles » : remplacer tout le contenu par celui du fichier `autonome/firestore.rules`, en mettant **les adresses e-mail des associés** (en minuscules) à la place des deux adresses d'exemple. Cliquer sur « Publier ».

### 4. Mettre le CRM en ligne

Dans un terminal, à la racine du dépôt :

```
python3 build_autonome.py
npm install -g firebase-tools
firebase login
cd autonome
firebase use --add        (choisir le projet créé à l'étape 1)
firebase deploy --only hosting,firestore:rules
```

La dernière commande affiche l'adresse du CRM : `https://<votre-projet>.web.app`.

### 5. Première connexion et chargement du CRM

1. Ouvrir cette adresse et se connecter avec Google (une adresse autorisée à l'étape 3).
2. L'écran « Première installation » s'affiche : choisir ensemble les trois fichiers du dossier `site` du dépôt, **index.html**, **companies.json** et **culture.json**, puis « Charger dans le CRM ».
3. Le CRM s'ouvre. Les autres associés n'ont plus qu'à ouvrir l'adresse et se connecter.

## Au quotidien

- **Ajouter un associé** : ajouter son adresse dans les règles (console Firebase > Firestore > Règles) et publier.
- **Mettre à jour le CRM** (nouvelle version ou nouvelles données dans le dépôt) : bouton « Mettre à jour » en haut à droite du CRM, puis les trois mêmes fichiers. Le suivi des appels n'est pas touché.
- **Se déconnecter** : bouton « Déconnexion » en haut à droite.
- **Sauvegarder** : « Exporter (CSV) » dans Entreprises et dans la feuille d'appels ; les données restent aussi dans votre projet Firebase.
- **Hermes360** : dans le panneau Hermes360, l'adresse du CRM est celle du site Firebase ; c'est elle qu'on donne à Hermes360 pour ouvrir les fiches au décroché.

## Coûts

L'offre gratuite de Firebase (Spark) suffit pour 2 à 4 associés : la grille connue au moment de l'écriture prévoit 50 000 lectures et 20 000 écritures par jour dans la base, 1 Go de stockage, 10 Go d'hébergement et 360 Mo de transfert par jour. Une ouverture du CRM lit une douzaine de documents de données plus une fiche de suivi par entreprise déjà travaillée. À vérifier sur la [page des tarifs Firebase](https://firebase.google.com/pricing) avant de choisir une offre payante.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `build_autonome.py` | Prépare `autonome/public` (écran de connexion, SDK Firebase, étude Hermes360) ; ne touche jamais `config.js` |
| `autonome/source/` | Sources de l'écran de connexion et du raccord Firebase (`crm-firebase.js`), SDK Firebase 10.14.1 copié tel quel |
| `autonome/public/` | Dossier mis en ligne par `firebase deploy` |
| `autonome/firestore.rules` | Qui peut lire et écrire (liste des adresses des associés) |
| `autonome/firebase.json` | Réglages d'hébergement et des émulateurs de test |
| `site/index.html`, `site/companies.json`, `site/culture.json` | Le CRM et ses données, chargés depuis l'écran « Mettre à jour » |
