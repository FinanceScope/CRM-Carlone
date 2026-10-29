"""Version autonome du CRM (sans claude.ai) : prépare autonome/public, le dossier publié sur Firebase Hosting.
Il ne contient que l'écran de connexion (index.html, crm-firebase.js), le SDK Firebase et l'étude Hermes360 ; le CRM et les
données sont chargés dans Firestore depuis l'écran de connexion (fichiers site/index.html, site/companies.json, site/culture.json)
et ne sont lisibles qu'après connexion d'un associé autorisé. public/config.js (configuration du projet Firebase) n'est jamais
écrasé. Usage : python3 build_autonome.py, puis voir autonome/LISEZMOI.md."""
import os, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC, PUB = ROOT + '/autonome/source', ROOT + '/autonome/public'
os.makedirs(PUB + '/vendor', exist_ok=True)
for f in ('index.html', 'crm-firebase.js'):
    shutil.copyfile(f'{SRC}/{f}', f'{PUB}/{f}')
for f in os.listdir(SRC + '/vendor'):
    shutil.copyfile(f'{SRC}/vendor/{f}', f'{PUB}/vendor/{f}')
if not os.path.exists(PUB + '/config.js'):
    shutil.copyfile(SRC + '/config.exemple.js', PUB + '/config.js')
# l'étude Hermes360 est un fragment (publiée sur claude.ai dans un squelette) : on l'enveloppe dans une page complète
etude = open(ROOT + '/docs/hermes.html', encoding='utf-8').read()
open(PUB + '/etude-hermes.html', 'w', encoding='utf-8').write(
    '<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    '<style>:root{color-scheme:light}body{margin:0;font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>'
    '</head><body>' + etude + '</body></html>')
print('autonome/public prêt :', sorted(os.listdir(PUB)))
