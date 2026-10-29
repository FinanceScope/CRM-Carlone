"""Version autonome du CRM (sans claude.ai) : prépare autonome/public, le dossier publié sur Firebase Hosting.
Il ne contient que l'écran de connexion (index.html, crm-firebase.js) et le SDK Firebase ; le CRM, les données et l'étude
Hermes360 sont chargés dans Firestore depuis l'écran de connexion (site/index.html, site/companies.json, site/culture.json, docs/hermes.html)
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
# l'étude Hermes360 n'est plus publiée : elle est chargée dans Firestore avec le CRM (lisible après connexion seulement)
if os.path.exists(PUB + '/etude-hermes.html'): os.remove(PUB + '/etude-hermes.html')
print('autonome/public prêt :', sorted(os.listdir(PUB)))
