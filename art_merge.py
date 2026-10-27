"""Réoriente le CRM vers la vente d'œuvres d'art aux entreprises (article 238 bis AB du CGI).
À lancer après merge.py et ext_merge.py : ajoute à chaque fiche de site/companies.json le profil fiscal,
le plafond de déduction et le lieu d'exposition possible, puis recalcule priorités et vagues.

Règles (BOFiP BOI-BIC-CHG-70-10-20260415, à valider avec l'expert-comptable de chaque entreprise) :
- œuvres originales d'artistes vivants, inscrites à l'actif immobilisé, achetées avant le 31/12/2028 ;
- déduction du prix par cinquièmes (exercice d'achat + 4 suivants), dans la limite annuelle de 20 000 €
  ou 5 ‰ du CA HT si ce montant est plus élevé, minorée des dons de mécénat (article 238 bis) ;
- œuvre exposée gratuitement dans un lieu accessible au public ou aux salariés, sauf leurs bureaux ;
- réserve spéciale au passif du montant déduit."""
import glob, json, os, re
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = ROOT + '/site'

PLANCHER = 20000      # limite annuelle minimale
TAUX_CA = 0.005       # 5 ‰ du chiffre d'affaires HT
TAUX_IS = 0.25        # taux normal de l'IS (15 % sur les premiers 42 500 € de bénéfice des PME)

def emin(e):
    m = re.search(r'\d+', str(e or ''))
    return int(m.group()) if m else 0

def regime(forme):
    f = (forme or '').strip()
    if f.startswith('SARL'): return 'IS probable'          # IS par défaut, option IR possible (SARL de famille)
    if f.startswith(('SAS', 'SA ', 'SA\'', 'SELAS', 'SELARL', 'SCOP', 'Société européenne')) or f == 'SA': return 'IS'
    return 'À vérifier'                                      # EURL, SNC, entrepreneur individuel, forme inconnue

ESPACES = {
    'magasin': 'Surface de vente ouverte au public',
    'clientele': 'Espaces ouverts à la clientèle (accueil, salles)',
    'sante': "Hall et salles d'attente ouverts au public",
    'agence': "Espace d'accueil de la clientèle",
    'loisirs': 'Lieux ouverts au public',
    'groupe': 'Sites du groupe ouverts au public ou aux salariés (à valider)',
    'salaries': "Hall, salle de pause ou cantine, accessibles à tous les salariés",
    'a_identifier': 'Lieu à identifier (les bureaux ne comptent pas)',
}
PUBLIC = ('magasin', 'clientele', 'sante', 'agence', 'loisirs')

def espace(c):
    naf = str(c.get('code_naf') or '')
    n2, n4 = naf[:2], naf[:5]
    if c.get('secteur') == 'Holdings & finance' and n2 in ('64', '70'): return 'groupe'
    if n2 == '47' or n4 in ('45.11', '45.19', '45.32', '45.40'): return 'magasin'
    if n2 in ('55', '56'): return 'clientele'
    if n2 in ('86', '87', '75'): return 'sante'
    if n2 in ('64', '65', '66', '68', '69', '79', '96') or n4 in ('45.20', '77.11'): return 'agence'
    if n2 in ('90', '91', '93'): return 'loisirs'
    if emin(c.get('effectif')) >= 10: return 'salaries'
    return 'a_identifier'

def k_eur(n):
    return f"{round(n / 1000):,}".replace(',', ' ') + ' k€' if n < 1e6 else f"{n / 1e6:.1f}".replace('.', ',').replace(',0', '') + ' M€'

companies = json.load(open(SITE + '/companies.json', encoding='utf-8'))
# fiches consolidées des 100 entreprises du classement initial (top100_synthese.py, relues une par une)
SYN = {}
# puis fiches réécrites après la mise à jour des comptes (fiches_maj_lots.py), qui remplacent les premières
for f in sorted(glob.glob(ROOT + '/ext/top100_synth_out_*.json')) + sorted(glob.glob(ROOT + '/ext/fiches_maj_out_*.json')):
    for x in json.load(open(f, encoding='utf-8')):
        SYN[re.sub(r'\D', '', str(x.get('siren')))[-9:]] = x
# comptes plus récents cités dans les fiches du top 100 (comptes_lots.py, chaque relevé contre-vérifié) ;
# seuls les chiffres propres à la société comptent, pas ceux d'un groupe
CR = {}
for f in sorted(glob.glob(ROOT + '/ext/comptes_out_*.json')):
    for x in json.load(open(f, encoding='utf-8')):
        if x.get('trouve') and x.get('perimetre') == 'societe' and (x.get('ca') is not None or x.get('resultat') is not None):
            CR[re.sub(r'\D', '', str(x.get('siren')))[-9:]] = x
n_cr = 0
proche = lambda a, b: a is not None and b is not None and abs(a - b) <= max(1000, 0.01 * abs(b))
for c in companies:
    ca = c.get('ca_recent') if c.get('ca_recent') is not None else c.get('ca')
    res = c.get('res_recent') if c.get('res_recent') is not None else c.get('resultat')
    if c.get('ca_non_publie'): ca = res = None
    annee = c.get('annee_recent') or c.get('annee_ca') or None
    annee_res, source = annee, None
    c.pop('comptes_recherche', None)
    cr = CR.get(c.get('siren'))
    if cr and str(cr.get('annee') or '') > str(annee or ''):
        nca, nres = cr.get('ca'), cr.get('resultat')
        if nres is None and proche(nca, c.get('ca')): nca, nres = c.get('ca'), c.get('resultat')   # le classement donnait déjà cet exercice
        if proche(nca, ca): nca = ca          # chiffre arrondi d'un montant déjà connu : garder le montant exact
        if proche(nres, res): nres = res
        if nca is not None: ca = nca
        if nres is not None: res, annee_res = nres, cr['annee']
        annee, source, n_cr = cr['annee'], 'recherche', n_cr + 1
        c['comptes_recherche'] = {k: cr.get(k) for k in ('annee', 'cloture', 'ca', 'resultat', 'citation', 'remarque')}
    plafond = max(PLANCHER, round(TAUX_CA * ca)) if ca else PLANCHER
    reg = regime(c.get('forme_juridique'))
    esp = espace(c)
    benef = None if res is None else res > 0
    active = str(c.get('statut') or 'Active').lower().startswith('active')
    notes = []
    if not active: notes.append('Procédure en cours : pas de démarche pour l\'instant.')
    if benef is False: notes.append('Pas de bénéfice au dernier exercice publié : la déduction n\'allège pas l\'impôt cette année-là.')
    elif benef and res / (1 - TAUX_IS) < plafond:
        notes.append(f"Bénéfice modeste ({k_eur(res)}) : l'économie d'impôt est limitée par le bénéfice plus que par le plafond.")
    if ca is None: notes.append('Comptes non publiés : plafond minimal de 20 000 € par an, à affiner avec le CA réel.')
    if source: notes.append(f"Chiffres de l'exercice {annee} relevés par la recherche, à confirmer avec l'entreprise.")
    if source and annee_res != annee: notes.append(f"Résultat {annee} non connu : le résultat indiqué est celui de l'exercice précédent.")
    if reg == 'À vérifier': notes.append("Régime fiscal à vérifier (EURL, SNC ou forme inconnue : souvent à l'IR).")
    if esp == 'groupe': notes.append('Holding : à aborder avec la tête du groupe, l\'œuvre pouvant être exposée dans un site du groupe (à valider).')
    if c.get('opposition_prospection'): notes.append('Opposée à la prospection : pas de mailing, contact direct uniquement.')

    d = c.get('distance_cosne_km')
    near = c.get('site_cosne') or (d is not None and d <= 5)
    bassin = near or (d is not None and d <= 30)
    # cœur de cible : société à l'IS, bénéfice d'au moins 50 k€, lieu d'exposition évident ;
    # au-delà de 30 km, seulement les grands comptes (plafond au-dessus du plancher, soit plus de 4 M€ de CA)
    coeur = (active and esp != 'groupe' and reg != 'À vérifier' and benef and res >= 50000
             and (esp in PUBLIC or emin(c.get('effectif')) >= 10) and (bassin or plafond > PLANCHER))
    if coeur:
        prio = 'Haute'
    elif active and (benef or (benef is None and emin(c.get('effectif')) >= 20 and reg != 'À vérifier')):
        prio = 'Moyenne'
    else:
        prio = 'Basse'
    syn, exclue = SYN.get(c.get('siren')), False
    if syn and active:   # priorité revue fiche par fiche (rentabilité, lieu de décision, autonomie du site)
        pc = syn.get('priorite_conseillee')
        if pc == 'Exclure': prio, exclue = 'Basse', True
        elif pc in ('Haute', 'Moyenne', 'Basse') and not (pc != 'Basse' and benef is False): prio = pc   # en perte : Basse
    vague = (1 if near else 2 if bassin else 3) if prio == 'Haute' and active else None
    c['art'] = {
        'regime': reg, 'benefice': benef, 'resultat': res, 'ca': ca, 'annee': annee, 'annee_resultat': annee_res, 'source': source,
        'plafond': plafond, 'prix_max': 5 * plafond, 'economie_max': round(5 * plafond * TAUX_IS),
        'espace': esp, 'espace_txt': ESPACES[esp], 'public': esp in PUBLIC, 'notes': notes,
        'plafond_a_recalculer': esp == 'groupe',   # holding : CA souvent consolidé, la limite dépend de la société qui achète
    }
    c['priorite'], c['vague'] = prio, vague
    c['exclue'] = exclue
    c.pop('fiche', None); c.pop('priorite_raison', None)
    if syn:
        c['fiche'] = {k: syn.get(k) for k in ('activite', 'groupe', 'resume', 'angle_art', 'qui_appeler', 'vigilance', 'questions', 'priorite_conseillee', 'raison')}
        c['priorite_raison'] = syn.get('raison')
        if syn.get('nom_affiche'): c['nom_court'] = syn['nom_affiche'].strip()
    c['offres'] = []

# garde-fou : aucune mention des établissements des associés dans les textes générés
INTERDIT = re.compile(r"vieux relais|\ble m\b|\bdu m\b|\bau m\b|nos établissements|\bbar\b|\brestaurants?\b|chambres|bar-restaurant", re.I)
for c in companies:
    textes = [c['art']['espace_txt']] + c['art']['notes'] + [json.dumps(c.get('fiche') or {}, ensure_ascii=False), c.get('nom_court') or '']
    for t in textes:
        assert not INTERDIT.search(t), (c['rang'], t)

# contrôle : une fiche qui parle d'opposition à la prospection doit porter le drapeau (sinon la page proposerait le mail)
for c in companies:
    if c.get('fiche') and not c.get('opposition_prospection') and re.search(r'oppos[ée]+ (au marketing|à la prospection)', json.dumps(c['fiche'], ensure_ascii=False), re.I):
        print('ATTENTION opposition citée dans la fiche sans drapeau :', c['rang'], c['nom'])
json.dump(companies, open(SITE + '/companies.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

print('régime', Counter(c['art']['regime'] for c in companies))
print('espace', Counter(c['art']['espace'] for c in companies))
print('bénéfice', Counter(c['art']['benefice'] for c in companies))
print('plafond > 20 k€', sum(1 for c in companies if c['art']['plafond'] > PLANCHER))
print('comptes plus récents relevés par la recherche', n_cr)
print('fiches consolidées', sum(1 for c in companies if c.get('fiche')), '| exclues', sum(1 for c in companies if c.get('exclue')))
print('priorités', Counter(c['priorite'] for c in companies), '| vagues', Counter(c['vague'] for c in companies))
for v in (1, 2, 3):
    print(v, [(c['rang'], c.get('nom_court') or c.get('nom_commercial') or c['nom'], c.get('distance_cosne_km')) for c in companies if c['vague'] == v])
