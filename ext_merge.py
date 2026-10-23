"""Ajoute au CRM les entreprises 101 à 500 de la Nièvre.
Sources : classements Pappers par commune (relevés le 22/10/2026), passe complémentaire sous 500 k€,
registre officiel (API Recherche d'entreprises, à défaut fiche Pappers) pour le siège exact, les dirigeants, l'état."""
import json, glob, os, re, math, unicodedata
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
EXT = ROOT + '/ext'
SITE = ROOT + '/site'

def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s.lower())

# ---- centroïdes et noms officiels des communes ----
g = json.load(open(EXT + '/communes58.geojson', encoding='utf-8'))
cent, canon = {}, {}
for f in g['features']:
    geom = f['geometry']
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    W = X = Y = 0.0
    for poly in polys:
        ring = poly[0]
        a = cx = cy = 0.0
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            cr = x1 * y2 - x2 * y1
            a += cr; cx += (x1 + x2) * cr; cy += (y1 + y2) * cr
        a *= 0.5
        if a == 0: continue
        cx /= (6 * a); cy /= (6 * a)
        W += abs(a); X += abs(a) * cx; Y += abs(a) * cy
    k = norm(f['properties']['nom'])
    cent[k] = (Y / W, X / W)
    canon[k] = f['properties']['nom']

def hav(p, q):
    R = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (p[0], p[1], q[0], q[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

COSNE = cent[norm('Cosne-Cours-sur-Loire')]
ALIAS = {norm('Château-Chinon Ville'): ['chateauchinonville'], norm('Château-Chinon Campagne'): ['chateauchinoncampagne'],
         norm("Vaux d'Amognes"): ['vauxdamognes', 'ourouer'], norm('Balleray'): ['vauxdamognes', 'ourouer']}

def ckey(commune):
    k = norm(commune)
    if k in cent: return k
    for art in ('la', 'le', 'les', 'l'):
        if k.startswith(art) and k[len(art):] in cent: return k[len(art):]
    for alt in ALIAS.get(k, []):
        if alt in cent: return alt
    cands = [c for c in cent if c.startswith(k[:10])] if len(k) >= 10 else []
    return cands[0] if len(cands) == 1 else None

def nice_commune(s):
    s = (s or '').strip()
    if not s: return None
    k = ckey(s)
    if k and k == norm(s): return canon[k]
    if k:   # le fichier des contours omet l'article : « Charité-sur-Loire » pour « La Charité-sur-Loire »
        for art, txt in (('la', 'La '), ('le', 'Le '), ('les', 'Les '), ('l', "L'")):
            if norm(s) == art + k: return txt + canon[k]
    if s.isupper():
        small = {'sur', 'sous', 'les', 'lès', 'les', 'en', 'de', 'des', 'du', 'la', 'le', 'aux', 'au', 'et', 'd', 'l'}
        parts = re.split(r'([-\s\'])', s.lower())
        out = []
        for i, p in enumerate(parts):
            out.append(p if (i > 0 and p in small) else p[:1].upper() + p[1:])
        return ''.join(out)
    return s

def road_from(point):
    return int(round(hav(COSNE, point) * 1.15))  # facteur route / vol d'oiseau mesuré sur Donzy, Pouilly, Nevers, Clamecy

def eff_txt(s):
    s = (s or '').strip()
    m = re.match(r'Entre ([\d\s  ]+) et ([\d\s  ]+) salariés', s)
    if m:
        a = re.sub(r'\D', '', m.group(1)); b = re.sub(r'\D', '', m.group(2))
        return f'{a}-{b} salariés'
    if re.match(r'Au moins 1 salari', s): return '1+ salarié'
    m = re.match(r'(\d[\d\s  ]*) salariés? et plus', s)
    if m: return re.sub(r'\D', '', m.group(1)) + '+ salariés'
    return s or None

TRANCHES = {'00': '0 salarié', '01': '1-2 salariés', '02': '3-5 salariés', '03': '6-9 salariés', '11': '10-19 salariés', '12': '20-49 salariés',
            '21': '50-99 salariés', '22': '100-199 salariés', '31': '200-249 salariés', '32': '250-499 salariés', '41': '500-999 salariés',
            '42': '1000-1999 salariés', '51': '2000-4999 salariés', '52': '5000-9999 salariés', '53': '10000+ salariés'}

def emin(e):
    m = re.search(r'\d+', str(e or ''))
    return int(m.group()) if m else 0

def forme(code):
    c = str(code or '').strip()
    if not c: return None
    if not c.isdigit(): return c  # libellé déjà lisible (fiche Pappers)
    table = {'5498': 'EURL', '5499': 'SARL', '5485': 'SELARL', '5458': 'SCOP (SARL)', '5710': 'SAS', '5720': 'SASU', '5785': 'SELAS', '5202': 'SNC',
             '5515': "SA d'économie mixte", '5558': 'SCOP (SA)', '5599': 'SA', '5800': 'Société européenne', '6540': 'SCI', '6533': 'GAEC',
             '6598': 'EARL', '6597': 'SCEA', '6599': 'Société civile', '6589': 'Société civile de moyens', '6316': 'CUMA', '6317': 'Coopérative agricole',
             '6318': 'Union de coopératives agricoles', '9220': 'Association déclarée', '9221': "Association d'insertion",
             '9230': "Association reconnue d'utilité publique", '5370': 'Société de participations financières', '5385': "Société d'exercice libéral"}
    if c in table: return table[c]
    if c.startswith('1'): return 'Entrepreneur individuel'
    if c.startswith('54'): return 'SARL'
    if c.startswith('55') or c.startswith('56'): return 'SA'
    if c.startswith('57'): return 'SAS'
    if c.startswith('63'): return 'Coopérative'
    if c.startswith('65'): return 'Société civile'
    if c.startswith('92'): return 'Association'
    if c.startswith('7'): return 'Personne morale de droit public'
    return None

def secteur(act):
    a = (act or '').lower()
    # libellés NAF complets : « Commerce de détail, à l'exception des automobiles… » ne doit pas tomber dans Automobile
    if a.strip() in ('restauration', 'hébergement'): return 'Hôtellerie & restauration'
    if a.startswith(('activités administratives', 'activités comptables', 'autres activités spécialisées', 'activités des agences de voyage')): return 'Services aux entreprises'
    if a.startswith('collecte et traitement des eaux'): return 'Énergie & environnement'
    if a.startswith(('commerce de détail', 'commerce de gros')): return 'Commerce & distribution'
    if a.startswith(("commerce et réparation d'automobiles", 'industrie automobile')): return 'Automobile'
    if a.startswith(('fabrication', 'industrie', 'métallurgie', 'travail du bois', 'imprimerie', 'réparation et installation', 'autres industries manufacturières', 'cokéfaction')):
        if 'meubles' in a and a.startswith('fabrication de meubles') or a.startswith('travail du bois'): return 'Bois & forêt'
        if 'papier' in a or 'imprimerie' in a: return 'Imprimerie & papier'
        if 'pharmaceutique' in a: return 'Santé'
        return 'Industrie'
    rules = [
        ('automobile', 'Automobile'), ('motocycles', 'Automobile'),
        ('sièges sociaux', 'Holdings & finance'), ('financiers', 'Holdings & finance'), ('assurance', 'Holdings & finance'),
        ('commerce de détail', 'Commerce & distribution'), ('commerce de gros', 'Commerce & distribution'),
        ('transport', 'Transport & logistique'), ('entreposage', 'Transport & logistique'), ('location', 'Transport & logistique'), ('postales', 'Transport & logistique'),
        ('bois', 'Bois & forêt'), ('sylviculture', 'Bois & forêt'), ('meubles', 'Bois & forêt'),
        ('santé', 'Santé'), ('pharma', 'Santé'), ('médico-social', 'Santé'), ('action sociale', 'Santé'), ('vétérinaires', 'Santé'),
        ('sportives', 'Sport, loisirs & médias'), ('jeux', 'Sport, loisirs & médias'), ('édition', 'Sport, loisirs & médias'), ('créatives', 'Sport, loisirs & médias'), ('hébergement', 'Sport, loisirs & médias'), ('restauration', 'Sport, loisirs & médias'), ('culturelles', 'Sport, loisirs & médias'),
        ('imprimerie', 'Imprimerie & papier'), ('papier', 'Imprimerie & papier'),
        ('déchets', 'Énergie & environnement'), ('électricité', 'Énergie & environnement'), ('raffinage', 'Énergie & environnement'), ('captage', 'Énergie & environnement'), ('dépollution', 'Énergie & environnement'),
        ('construction', 'BTP & matériaux'), ('génie civil', 'BTP & matériaux'), ('minéraux', 'BTP & matériaux'), ('extractives', 'BTP & matériaux'), ('immobilières', 'BTP & matériaux'), ('architecture', 'BTP & matériaux'),
        ('culture et production', 'Agriculture'), ('pêche', 'Agriculture'),
        ('alimentaires', 'Industrie'), ('boissons', 'Industrie'),
        ('conseil', 'Services aux entreprises'), ('juridiques', 'Services aux entreprises'), ('informatique', 'Services aux entreprises'), ('publicité', 'Services aux entreprises'), ('emploi', 'Services aux entreprises'), ('enquêtes', 'Services aux entreprises'), ('services administratifs', 'Services aux entreprises'), ('bâtiments et aménagement paysager', 'Services aux entreprises'), ('ingénierie', 'Services aux entreprises'), ('enseignement', 'Services aux entreprises'), ('télécommunications', 'Services aux entreprises'), ("réparation d'ordinateurs", 'Services aux entreprises'), ('autres services personnels', 'Services aux entreprises'),
    ]
    for k, v in rules:
        if k in a: return v
    return 'Industrie'

NAF_DIV = {
    '01': 'Culture et production animale, chasse et services annexes', '02': 'Sylviculture et exploitation forestière', '03': 'Pêche et aquaculture',
    '08': 'Autres industries extractives', '09': 'Services de soutien aux industries extractives', '10': 'Industries alimentaires', '11': 'Fabrication de boissons',
    '13': 'Fabrication de textiles', '14': "Industrie de l'habillement", '15': 'Industrie du cuir et de la chaussure',
    '16': "Travail du bois et fabrication d'articles en bois et en liège, à l'exception des meubles ; fabrication d'articles en vannerie et sparterie",
    '17': 'Industrie du papier et du carton', '18': "Imprimerie et reproduction d'enregistrements", '19': 'Cokéfaction et raffinage', '20': 'Industrie chimique',
    '21': 'Industrie pharmaceutique', '22': 'Fabrication de produits en caoutchouc et en plastique', '23': "Fabrication d'autres produits minéraux non métalliques",
    '24': 'Métallurgie', '25': "Fabrication de produits métalliques, à l'exception des machines et des équipements",
    '26': 'Fabrication de produits informatiques, électroniques et optiques', '27': "Fabrication d'équipements électriques",
    '28': 'Fabrication de machines et équipements n.c.a.', '29': 'Industrie automobile', '30': "Fabrication d'autres matériels de transport",
    '31': 'Fabrication de meubles', '32': 'Autres industries manufacturières', '33': "Réparation et installation de machines et d'équipements",
    '35': "Production et distribution d'électricité, de gaz, de vapeur et d'air conditionné", '36': "Captage, traitement et distribution d'eau",
    '37': 'Collecte et traitement des eaux usées', '38': 'Collecte, traitement et élimination des déchets ; récupération',
    '39': 'Dépollution et autres services de gestion des déchets', '41': 'Construction de bâtiments', '42': 'Génie civil', '43': 'Travaux de construction spécialisés',
    '45': "Commerce et réparation d'automobiles et de motocycles", '46': "Commerce de gros, à l'exception des automobiles et des motocycles",
    '47': "Commerce de détail, à l'exception des automobiles et des motocycles", '49': 'Transports terrestres et transport par conduites',
    '50': 'Transports par eau', '51': 'Transports aériens', '52': 'Entreposage et services auxiliaires des transports', '53': 'Activités de poste et de courrier',
    '55': 'Hébergement', '56': 'Restauration', '58': 'Édition',
    '59': 'Production de films cinématographiques, de vidéo et de programmes de télévision ; enregistrement sonore et édition musicale',
    '60': 'Programmation et diffusion', '61': 'Télécommunications', '62': 'Programmation, conseil et autres activités informatiques', '63': "Services d'information",
    '64': 'Activités des services financiers, hors assurance et caisses de retraite', '65': 'Assurance',
    '66': "Activités auxiliaires de services financiers et d'assurance", '68': 'Activités immobilières', '69': 'Activités juridiques et comptables',
    '70': 'Activités des sièges sociaux ; conseil de gestion',
    '71': "Activités d'architecture et d'ingénierie ; activités de contrôle et analyses techniques", '72': 'Recherche-développement scientifique',
    '73': 'Publicité et études de marché', '74': 'Autres activités spécialisées, scientifiques et techniques', '75': 'Activités vétérinaires',
    '77': 'Activités de location et location-bail', '78': "Activités liées à l'emploi",
    '79': 'Activités des agences de voyage, voyagistes, services de réservation et activités connexes', '80': 'Enquêtes et sécurité',
    '81': 'Services relatifs aux bâtiments et aménagement paysager', '82': 'Activités administratives et autres activités de soutien aux entreprises',
    '84': 'Administration publique et défense ; sécurité sociale obligatoire', '85': 'Enseignement', '86': 'Activités pour la santé humaine',
    '87': 'Hébergement médico-social et social', '88': 'Action sociale sans hébergement', '90': 'Activités créatives, artistiques et de spectacle',
    '91': 'Bibliothèques, archives, musées et autres activités culturelles', '92': "Organisation de jeux de hasard et d'argent",
    '93': 'Activités sportives, récréatives et de loisirs', '94': 'Activités des organisations associatives',
    '95': "Réparation d'ordinateurs et de biens personnels et domestiques", '96': 'Autres services personnels',
}

# procédures signalées par les collectes (pages de classement) quand le nom n'en porte pas la mention
BADGES = {norm(k): v for k, v in {
    'WATTERLOT VIANDES': 'Liquidation judiciaire (10/03/2025)', 'LES 200 BORNES': 'Liquidation judiciaire (20/03/2023)',
    'LEAJULES': 'Liquidation judiciaire', 'JSP PAYSAGE': 'Redressement judiciaire', 'BATI PRO 58': 'Redressement judiciaire',
}.items()}
PROC = re.compile(r'^(.*?)\s*\(((?:Liquidation judiciaire|Redressement judiciaire|Procédure de sauvegarde|Sauvegarde|Radiée|Plan de)[^()]*(?:\([^()]*\))?[^()]*)\)\s*$', re.I)

BRANDS = {'INTERMARCHE': 'Intermarché', 'BRICOMARCHE': 'Bricomarché', 'CARREFOUR CONTACT': 'Carrefour Contact', 'CARREFOUR CITY': 'Carrefour City',
          "MC DONALD'S": "McDonald's", 'BURGER KING': 'Burger King', 'IBIS NEVERS': 'Ibis Nevers', 'NOZ': 'Noz', 'OPTIC 2000': 'Optic 2000',
          'INTERSPORT': 'Intersport', 'ROC-ECLERC': 'Roc-Eclerc', 'OPTICIEN KRYS': 'Krys', "DOMINO'S PIZZA": "Domino's Pizza",
          'COCCIMARKET': 'Coccimarket', 'PROXIMARCHE': 'Proximarché', 'CENTRAKOR': 'Centrakor', 'MERCURE NEVERS PONT DE LOIRE': 'Mercure Nevers Pont de Loire',
          'ADEQUAT INTERIM': 'Adéquat Intérim', 'UTILE': 'Utile', 'ROADY': 'Roady', 'INTER CAVES': 'Inter Caves', 'TC TRANSPORTS': 'TC Transports',
          'LES RIVES DE LA NIEVRE': 'Les Rives de la Nièvre', 'PHARMACIE DE LA FONDERIE': 'Pharmacie de la Fonderie',
          'RESIDENCE MARION DE GIVRY': 'Résidence Marion de Givry', 'MAISON DE LA CULTURE NEVERS AGGLOMERATION': 'Maison de la Culture Nevers Agglomération',
          'VIABELA ET VIABELA VOYAGES': 'Viabela Voyages', 'OMNIMAT': 'Omnimat', 'TECHNITOIT': 'Technitoit', 'TPA': 'TPA', 'EG CURT': 'EG Curt',
          'DOMAINE DE LISPAUL': 'Domaine de Lispaul', 'LE RELAIS DES LACS': 'Le Relais des Lacs', 'LES BOUCHERIES DU BOEUF TRICOLORE': 'Les Boucheries du Bœuf Tricolore',
          'MEUBLES LAURENT': 'Meubles Laurent', 'C3L': 'C3L', 'ASTREA': 'Astrea', 'SOPADEC': 'Sopadec', 'NOHAIN': 'Nohain', 'UNAE': 'Unae',
          'DAVID LANGE': 'David Lange', 'ACTION NETTOYAGE': 'Action Nettoyage', 'OPTIQUE POULAIN': 'Optique Poulain', 'LE GRAND SALOIR': 'Le Grand Saloir',
          'FERMETURES ET CUISINES DU MORVAN': 'Fermetures et Cuisines du Morvan', 'GROUPE-LE CARRE': 'Groupe Le Carré', 'CABINET MERCIER LECROT': 'Cabinet Mercier Lecrot'}
LEGAL = re.compile(r'\b(SARL|SAS|SASU|EURL|SA|SNC|SCI|ETS|ETABLISSEMENTS|STE|SOCIETE|SOC|LE|LA|LES)\b', re.I)
def clean_enseigne(nc, nom):
    if not nc: return None
    nc = re.sub(r'(\s+-\s+\S{1,2})+\s*$', '', nc.strip())          # enseigne tronquée au registre : « … - I »
    a, b = norm(LEGAL.sub(' ', nc)), norm(LEGAL.sub(' ', nom))
    if not a or a in b or b in a: return None                            # simple variante du nom légal
    if nc.upper() in ('ELECTRICITE GENERALE', 'CARROSSEIRE MECANIQUE JLB'): return None   # générique ou coquille du registre
    return BRANDS.get(nc.upper(), nc)
def clean_adresse(a):
    a = re.sub(r'\s+', ' ', (a or '').strip())
    if not a: return None
    m = re.match(r'^(\d+)\s*(-|/|ET)\s*(\d+),?\s+\1\s+(.*)$', a, re.I)       # « 28-30 28 BOULEVARD … » -> « 28-30 BOULEVARD … »
    if m: a = f"{m.group(1)}{' et ' if m.group(2).upper() == 'ET' else m.group(2)}{m.group(3)} {m.group(4)}"
    t = a.split()
    if len(t) % 2 == 0 and t[:len(t) // 2] == t[len(t) // 2:]: a = ' '.join(t[:len(t) // 2])
    return a

def sid(x):
    s = re.sub(r'\D', '', str(x or ''))
    return s[-9:] if len(s) >= 9 else ''

# ---- lecture : pages de classement (>= 500 k€) + passe complémentaire (200-500 k€, comptes non publiés >= 10 salariés) ----
cand = {}
def add(r, commune, regle, badge=None):
    k = sid(r.get('siren'))
    if not k:
        m = re.search(r'(\d{9})/?$', r.get('url') or '')
        k = m.group(1) if m else ''
    nom = (r.get('nom') or '').strip()
    m = PROC.match(nom)
    if m: nom, badge = m.group(1).strip(), badge or m.group(2).strip()
    if len(k) != 9 or not isinstance(r.get('ca'), int): return   # nom vide : complété plus bas par le registre
    badge = badge or BADGES.get(norm(nom))
    prev = cand.get(k)
    item = {'siren': k, 'nom': nom, 'url': r.get('url'), 'activite': r.get('activite'), 'ca': r['ca'], 'resultat': r.get('resultat'),
            'effectif': eff_txt(r.get('effectif')), 'commune_page': commune, 'regle': regle, 'badge': badge or (prev or {}).get('badge')}
    if not prev or (item['regle'] == 'ca' and (prev['regle'] != 'ca' or item['ca'] > prev['ca'])): cand[k] = item
    elif badge and not prev.get('badge'): prev['badge'] = badge

for f in sorted(glob.glob(EXT + '/out_*.json')):
    for com in json.load(open(f, encoding='utf-8')):
        for r in com.get('rows') or []: add(r, com.get('commune'), 'ca')
slug2com = {l.split('|')[0].strip(): l.split('|')[1].strip() for l in open(EXT + '/slugs.txt', encoding='utf-8') if '|' in l}
n_supp = Counter()
for f in sorted(glob.glob(EXT + '/supp_[A-Z].json')):
    for com in json.load(open(f, encoding='utf-8')):
        for r in com.get('rows') or []:
            rg = r.get('regle') or ('b' if not r.get('ca') else 'a')
            if rg == 'b' and emin(eff_txt(r.get('effectif'))) < 10: continue
            if rg == 'a' and not (isinstance(r.get('ca'), int) and r['ca'] > 0): continue
            n_supp[rg] += 1
            add(r, slug2com.get(com.get('slug'), com.get('slug')), 'ca' if rg == 'a' else 'effectif', r.get('statut_badge'))

# ---- registre officiel ----
reg = {}
for f in sorted(glob.glob(EXT + '/reg_out_*.json')):
    for e in json.load(open(f, encoding='utf-8')):
        k = sid(e.get('siren'))
        if k: reg[k] = e

# noms absents des pages Pappers (lien sans texte) : nom du registre, sans l'enseigne entre parenthèses
for k, c in list(cand.items()):
    if not c['nom']:
        nc = re.sub(r'\s*\([^()]*\)\s*$', '', (reg.get(k) or {}).get('nom_complet') or '').strip()
        if nc: c['nom'] = nc
        else: del cand[k]

PUBLIC = re.compile(r"^(COMMUNE|MAIRIE|CCAS|CIAS|SIVOM|SIVU|SYNDICAT INTERCOMMUNAL|COMMUNAUTE (DE COMMUNES|D'AGGLOMERATION)|DEPARTEMENT|CENTRE COMMUNAL)\b", re.I)
def public(c):
    nj = str((reg.get(c['siren']) or {}).get('nature_juridique') or '')
    return bool(PUBLIC.match(c['nom'])) or nj.startswith('7') or c['siren'][:1] in ('1', '2')   # SIREN 1xx/2xx = personne publique
def asso(c):
    nj = str((reg.get(c['siren']) or {}).get('nature_juridique') or '')
    return nj.startswith('92') or bool(re.search(r'^(ASSOCIATION|ESPACE SOCIOCULTUREL|COMITE|FOYER)\b|MISSION LOCALE|CENTRE SOCIAL', c['nom'], re.I))

existing = json.load(open(SITE + '/companies.json', encoding='utf-8'))
base = [c for c in existing if c['rang'] <= 100]
assert len(base) == 100, len(base)
known = {sid(c.get('siren')) for c in base}

LIQ = set()   # liquidateur amiable relevé au registre (fichiers de l'API) : dissolution en cours
for f in sorted(glob.glob(EXT + '/gap_*.json')):
    for e in json.load(open(f, encoding='utf-8')):
        if any('liquidateur' in str((x or {}).get('fonction') or '').lower() for x in (e.get('dirigeants') or [])): LIQ.add(sid(e.get('siren')))

def gone(c):
    """Entreprise fermée, radiée ou en liquidation : écartée de la liste."""
    e = reg.get(c['siren']) or {}
    st = str(e.get('etat_administratif') or '').strip().lower()
    txt = ' '.join(str(x or '') for x in (c.get('badge'), e.get('procedure'))).lower()
    liq = any('liquidateur' in str((x or {}).get('fonction') or '').lower() for x in (e.get('dirigeants') or []))
    return (st in ('c', 'cessée', 'cessee', 'fermée', 'fermee', 'radiée', 'radiee') or 'radi' in txt or 'liquidation' in txt
            or 'dissolution' in txt or "cessation d'activit" in txt or liq or c['siren'] in LIQ)

# ---- trou du 58000 : Pappers n'affiche que les 100 premières de Nevers (> ~620 k€) ; complément par l'API officielle ----
n_gap = 0
for f in sorted(glob.glob(EXT + '/gap_*.json')):
    for e in json.load(open(f, encoding='utf-8')):
        k = sid(e.get('siren'))
        if len(k) != 9 or k in cand or k in reg: continue
        if not str(e.get('siege_code_postal') or '').startswith('58'): continue
        if str(e.get('etat_administratif') or 'A').upper() != 'A': continue
        if any('liquidateur' in str((x or {}).get('fonction') or '').lower() for x in (e.get('dirigeants') or [])): continue   # liquidation amiable
        if not isinstance(e.get('ca'), int) or e['ca'] < 200000 or str(e.get('annee') or '0') < '2022': continue
        tr = str(e.get('tranche_effectif') or '').strip()
        cand[k] = {'siren': k, 'nom': (e.get('nom_complet') or '').strip(), 'url': 'https://www.pappers.fr/entreprise/' + k,
                   'activite': None, 'ca': e['ca'], 'resultat': e.get('resultat_net'),
                   'effectif': TRANCHES.get(tr.zfill(2)) if tr.isdigit() else None, 'commune_page': e.get('siege_commune'),
                   'regle': 'ca', 'badge': None, 'annee': str(e.get('annee')), 'via_api': True}
        reg[k] = {'siren': k, 'enseignes': e.get('enseignes') or [], 'adresse': e.get('adresse'), 'code_postal': e.get('siege_code_postal'),
                  'commune': e.get('siege_commune'), 'latitude': e.get('latitude'), 'longitude': e.get('longitude'), 'naf': e.get('naf'),
                  'nature_juridique': e.get('nature_juridique'), 'date_creation': e.get('date_creation'), 'tranche_effectif': tr,
                  'etat_administratif': 'A', 'procedure': None, 'dirigeants': e.get('dirigeants') or [], 'source': 'api'}
        n_gap += 1

pool = [c for k, c in cand.items() if k not in known]
dropped = [c for c in pool if gone(c)]
pool = [c for c in pool if not gone(c)]
non_ent = [c['nom'] for c in pool if public(c) or (c['regle'] == 'effectif' and asso(c))]
pool = [c for c in pool if not (public(c) or (c['regle'] == 'effectif' and asso(c)))]
# 1) toutes les entreprises à plus de 500 k€ de CA publié ; 2) les plus gros employeurs aux comptes confidentiels (10 salariés et plus) ;
# 3) au besoin, les CA publiés entre 200 et 500 k€
def km_guess(c):
    e = reg.get(c['siren']) or {}
    k = ckey(e.get('commune') or '') or ckey(c.get('commune_page') or '')
    return hav(COSNE, cent[k]) if k else 999
# ---- derniers comptes publiés : registre national (API), à défaut fiche Pappers ; CA et résultat du même exercice ----
FIN = {}
for f in sorted(glob.glob(EXT + '/fin_out_*.json')):
    for e in json.load(open(f, encoding='utf-8')):
        k = sid(e.get('siren'))
        if k: FIN[k] = e
for f in sorted(glob.glob(EXT + '/fin2_out_*.json')):          # compléments : API relancée, fiche Pappers pour les CA non publiés au registre
    for e in json.load(open(f, encoding='utf-8')):
        k = sid(e.get('siren'))
        if not k: continue
        cur = FIN.setdefault(k, {'siren': k, 'api': None, 'pappers': None})
        if e.get('api') and (e['api'].get('etat_administratif') or e['api'].get('finances')): cur['api'] = e['api']
        if e.get('pappers'): cur['pappers'] = e['pappers']
for f in sorted(glob.glob(EXT + '/gap_*.json')):
    for e in json.load(open(f, encoding='utf-8')):
        k = sid(e.get('siren'))
        if k and k not in FIN:
            FIN[k] = {'siren': k, 'api': {'etat_administratif': e.get('etat_administratif'), 'tranche_effectif': e.get('tranche_effectif'),
                                         'annee_tranche_effectif': e.get('annee_tranche_effectif'), 'finances': e.get('finances')}, 'pappers': None}
FIN_MODE = bool(glob.glob(EXT + '/fin_out_*.json'))

def num_txt(t):
    """« 3,03 M€ » -> 3030000 ; « 459,9 k€ » -> 459900"""
    if t is None: return None
    t = str(t).replace('\u202f', ' ').replace('\xa0', ' ').replace('\u2212', '-').replace('\u2013', '-').strip()
    m = re.match(r'^(-?)\s*([\d ]+(?:[.,]\d+)?)\s*(M|k|K)?', t)
    if not m or not m.group(2).strip(): return None
    v = float(m.group(2).replace(' ', '').replace(',', '.')) * {'M': 1e6, 'k': 1e3, 'K': 1e3}.get(m.group(3), 1)
    return int(round(-v if m.group(1) else v))

def fin_info(k):
    e = FIN.get(k)
    if not e: return None
    api = e.get('api') or {}
    pap = e.get('pappers') or {}
    best = None
    fins = api.get('finances') or {}
    if isinstance(fins, dict):
        for y, v in fins.items():
            if isinstance(v, dict) and isinstance(v.get('ca'), (int, float)) and v['ca'] > 0 and re.fullmatch(r'\d{4}', str(y)):
                if not best or str(y) > best[0]: best = (str(y), int(v['ca']), v.get('resultat_net'), 'api')
    pbest = None
    for x in (pap.get('exercices') or []):
        y = str(x.get('annee') or '')
        ca = x['ca'] if isinstance(x.get('ca'), int) else num_txt(x.get('ca_txt'))
        res = x['resultat'] if isinstance(x.get('resultat'), int) else num_txt(x.get('resultat_txt'))
        if re.fullmatch(r'\d{4}', y) and ca and ca > 0 and (not pbest or y > pbest[0]): pbest = (y, int(ca), res, 'pappers')
    if pbest and (not best or (pbest[0] > best[0] and abs(pbest[1] - best[1]) > 0.005 * best[1])): best = pbest
    out = {'annee': None, 'ca': None, 'res': None, 'src': None}
    if best: out.update(annee=best[0], ca=best[1], res=best[2], src=best[3])
    out['recent'] = bool(best and best[0] >= '2023')
    tr = str(api.get('tranche_effectif') or '').strip()
    an = str(api.get('annee_tranche_effectif') or '').strip()
    out['eff'] = TRANCHES.get(tr.zfill(2)) if tr.isdigit() else None
    out['eff_annee'] = an or None
    if out['eff'] and an and an < '2021': out['eff'] = None
    if not out['eff']:
        out['eff'] = eff_txt(pap.get('effectif')) if pap.get('effectif') else None
        out['eff_annee'] = None
    st = str(api.get('etat_administratif') or 'A').strip().upper()
    ptxt = str(pap.get('procedure') or '').strip()
    pl = ptxt.lower()
    out['gone'] = st == 'C' or bool(pap.get('radiee_ou_dissoute'))
    out['proc'] = out['proc_note'] = None
    if ptxt:
        plans = re.findall(r'plan de (redressement|sauvegarde)[^.;]*?(?:adopté|arrêté|publié|homologué)[^.;]*?(\d{2}/\d{2}/(20\d\d))', ptxt, re.I)
        if plans:   # plan de continuation : récent (depuis 2023) = signalé ; plus ancien = simple note
            typ, date, yr = plans[0]
            label = f"Plan de {typ.lower()} adopté le {date}"
            if int(yr) >= 2023: out['proc'] = label
            else: out['proc_note'] = label
        elif 'liquidation' in pl and not re.search(r'clôtur|close', pl):
            out['gone'] = True
        elif re.search(r'redressement|sauvegarde', pl) and re.search(r'en cours|observation|ouvert', pl) \
                and not re.search(r"pas de procédure|aucune procédure|clôtur|terminée|a pris fin|close", pl):
            typ = 'Redressement judiciaire' if 'redressement' in pl else 'Procédure de sauvegarde'
            m = re.search(r'(?:depuis le|ouverte? le)\s*(\d{2}/\d{2}/\d{4})', ptxt)
            out['proc'] = typ + ' en cours' + (f' (depuis le {m.group(1)})' if m else '')
    return out

def eur_txt(n):
    if n is None: return None
    return (f"{n/1e6:.1f}".replace('.', ',').replace(',0', '') + ' M€') if abs(n) >= 1e6 else f"{round(n/1e3):,}".replace(',', ' ') + ' k€'

if FIN_MODE:
    FI = {c['siren']: fin_info(c['siren']) for c in pool}
    sans_fin = [c['nom'] for c in pool if not FI[c['siren']] and not (c['regle'] == 'ca' and c['ca'] < 250000)]
    dropped += [c for c in pool if FI[c['siren']] and FI[c['siren']]['gone']]
    pool = [c for c in pool if FI[c['siren']] and not FI[c['siren']]['gone']]
    for c in pool:
        fi = FI[c['siren']]; c['fi'] = fi
        c['regle_pappers'] = c['regle']
        if fi['recent']: c['regle'], c['ca'], c['resultat'] = 'ca', fi['ca'], fi['res']
        else: c['regle'], c['ca'], c['resultat'] = 'effectif', 0, None
        if fi['eff']: c['effectif'] = fi['eff']
        c['badge'] = fi['proc']
    pool = [c for c in pool if c['regle'] == 'ca' or (emin(c['effectif']) >= 10 and not asso(c))]

# top 100 : on garde les chiffres du classement photographié, et on signale un exercice plus récent très différent au registre
n_top_maj = 0
for c in base:
    fi = fin_info(sid(c.get('siren'))) if FIN_MODE else None
    if not fi or not fi['ca'] or not fi['annee'] or fi['annee'] < '2024': continue
    if c.get('ca_recent') is not None and not c.get('annee_recent'): continue      # déjà contre-vérifiée sur Pappers
    if abs(fi['ca'] - c['ca']) > 0.1 * c['ca']:
        c['ca_recent'], c['res_recent'], c['annee_recent'] = fi['ca'], fi['res'], fi['annee']; n_top_maj += 1

grp_a = sorted([c for c in pool if c['regle'] == 'ca' and c['ca'] >= 500000], key=lambda c: -c['ca'])
grp_b = sorted([c for c in pool if c['regle'] == 'effectif'], key=lambda c: (-emin(c['effectif']), km_guess(c), c['nom']))
grp_c = sorted([c for c in pool if c['regle'] == 'ca' and 0 < c['ca'] < 500000], key=lambda c: -c['ca'])
chosen = grp_a[:400]
n_eff = min(len(grp_b), 400 - len(chosen))
chosen += grp_b[:n_eff]
chosen += grp_c[:400 - len(chosen)]
# ordre d'affichage : CA publiés (A puis C) d'abord, comptes confidentiels ensuite
chosen = sorted([c for c in chosen if c['regle'] == 'ca'], key=lambda c: -c['ca']) + [c for c in chosen if c['regle'] == 'effectif']
by_ca = grp_a + grp_c

# changements de dénomination récents relevés au registre (le classement Pappers affiche encore l'ancien nom)
RENAMES = {'530610187': 'CF2C (ex-ACORDIA)', '888980596': 'PHARMACIE DES EDUENS (ex-Pharmacie Maillot-Debrousse)'}
for r in chosen:
    if r['siren'] in RENAMES: r['nom'] = RENAMES[r['siren']]

ext, hors58 = [], []
for i, r in enumerate(chosen):
    e = reg.get(r['siren']) or {}
    cp = str(e.get('code_postal') or '').strip() or None
    commune = nice_commune(e.get('commune')) or nice_commune(r['commune_page'])
    if cp and not cp.startswith('58'): hors58.append((r['nom'], cp, commune))
    pt = None
    try:
        if e.get('latitude') not in (None, '') and e.get('longitude') not in (None, ''):
            pt = (float(e['latitude']), float(e['longitude']))
            if not (46.0 < pt[0] < 48.5 and 2.0 < pt[1] < 5.0): pt = None   # géocodage aberrant
    except Exception: pt = None
    if pt is None:
        k = ckey(commune or '') or ckey(r['commune_page'] or '')
        pt = cent.get(k) if k else None
    d = None if pt is None else road_from(pt)
    if norm(commune) == norm('Cosne-Cours-sur-Loire'): d = 2 if d is None else max(1, min(d, 5))
    tr = str(e.get('tranche_effectif') or '').strip()
    eff = r['effectif'] or (TRANCHES.get(tr.zfill(2)) if tr.isdigit() else (tr or None))
    e_min = emin(eff)
    naf = str(e.get('naf') or '').strip()
    act = r.get('activite') or NAF_DIV.get(naf[:2])
    sect = secteur(act)
    badge = r.get('badge') or (str(e['procedure']).strip() if e.get('procedure') else None)
    horeca = (act or '').strip().lower() in ('restauration', 'hébergement') or naf[:2] in ('55', '56')
    near = d is not None and d <= 5
    if (near and e_min >= 10) or (d is not None and d <= 30 and e_min >= 50): prio = 'Haute'
    elif (d is not None and d <= 30 and e_min >= 6) or (d is not None and d <= 70 and e_min >= 100) or near: prio = 'Moyenne'
    else: prio = 'Basse'
    if sect == 'Holdings & finance' and prio == 'Haute': prio = 'Moyenne'
    if badge or horeca: prio = 'Basse'
    dd = 999 if d is None else d
    offres = []
    if e_min >= 10 and not badge and not horeca:
        if dd <= 30 and e_min >= 50: offres.append('carte')
        if dd <= 25: offres.append('dej')
        if dd <= 25 and e_min >= 20: offres.append('afterwork')
        if dd <= 70 and e_min >= 50: offres.append('events')
    if not badge and not horeca and dd <= 30 and naf[:2] in ('01', '10', '11') or (not badge and dd <= 30 and (act or '').startswith(('Culture et production', 'Industries alimentaires', 'Fabrication de boissons'))):
        offres.insert(0, 'local')   # producteurs et fournisseurs du territoire
    vague = None
    if not badge and not horeca and prio in ('Haute', 'Moyenne') and e_min >= 10 and sect != 'Holdings & finance':
        vague = 1 if dd <= 5 else (2 if dd <= 30 else 3)
    ens = [x.strip() for x in (e.get('enseignes') or []) if isinstance(x, str) and x.strip()]
    nom_com = next((x for x in ens if norm(x) != norm(r['nom'])), None)
    if not nom_com:   # le registre ajoute parfois l'enseigne entre parenthèses : « CLEMENCIEL (BRICOMARCHE) »
        mb = re.search(r'\(([^()]{3,60})\)\s*$', e.get('nom_complet') or '')
        if mb and norm(mb.group(1)) not in (norm(r['nom']), 'voirobservations') and not norm(r['nom']).startswith(norm(mb.group(1))):
            nom_com = mb.group(1).strip()
    if nom_com and nom_com.isupper() and len(nom_com) > 3: nom_com = nom_com  # tel qu'au registre
    nom_com = clean_enseigne(nom_com, r['nom'])
    adr = clean_adresse(e.get('adresse'))
    if adr and cp and cp in adr: adr = adr[:adr.find(cp)].strip(' ,') or adr      # le registre colle parfois « 58640 VARENNES-VAUZELLES » à la rue
    dirs = [x for x in (e.get('dirigeants') or []) if isinstance(x, dict) and (x.get('nom') or '').strip()
            and not re.search(r'commissaire aux comptes|liquidateur', str(x.get('fonction') or ''), re.I)][:4]
    for x in dirs:
        if str(x.get('fonction') or '').strip() == 'Président de SAS': x['fonction'] = 'Président'
    src = [r.get('url')]
    if e.get('source') == 'api': src.append('https://annuaire-entreprises.data.gouv.fr/entreprise/' + r['siren'])
    ext.append({
        'rang': 101 + i, 'nom': r['nom'], 'nom_commercial': nom_com, 'activite': act, 'secteur': sect,
        'ca': r['ca'] if r['regle'] == 'ca' else None, 'resultat': r.get('resultat') if r['regle'] == 'ca' else None,
        'ca_non_publie': r['regle'] == 'effectif', 'effectif': eff,
        'ville': commune, 'code_postal': cp, 'adresse': adr,
        'distance_cosne_km': d, 'siren': r['siren'], 'pappers_url': r.get('url'),
        'code_naf': e.get('naf'), 'forme_juridique': forme(e.get('nature_juridique')), 'date_creation': None,   # date du registre parfois celle de l'établissement : non affichée
        'dirigeants': [{'nom': x['nom'].strip(), 'fonction': (x.get('fonction') or '').strip() or None} for x in dirs],
        'priorite': prio, 'vague': vague, 'offres': offres, 'site_cosne': near,
        'sources': [s for s in src if s], 'ext': True, 'registre': bool(e), 'verifie': False,
        'statut': badge or 'Active',
    })
    fi = r.get('fi')
    if fi:
        x = ext[-1]
        x['eff_annee'] = fi['eff_annee']
        if fi['recent']:
            x['annee_ca'] = fi['annee']
            x['fig_src'] = f"Derniers comptes publiés : exercice {fi['annee']} ({'registre national' if fi['src'] == 'api' else 'fiche Pappers'})"
        else:
            x['fig_src'] = 'Comptes non publiés'
            if fi['annee']: x['note_comptes'] = f"Derniers chiffres publiés : exercice {fi['annee']} (CA {eur_txt(fi['ca'])}), rien depuis."
        if fi['proc_note']: x['note_classement'] = 'Procédure collective passée : ' + fi['proc_note']
        x['sources'] = list(dict.fromkeys(['https://annuaire-entreprises.data.gouv.fr/entreprise/' + r['siren']] + x['sources']))
    elif r.get('via_api'):
        ext[-1]['fig_src'] = f"Comptes publiés {r.get('annee')} (registre national, API Recherche d'entreprises)"
        ext[-1]['sources'] = ['https://annuaire-entreprises.data.gouv.fr/entreprise/' + r['siren'], r.get('url')]

min_top = min(c['ca'] for c in base)
for c in ext:
    if c['ca'] and c['ca'] > min_top:
        c['note_classement'] = ("Absente du classement Pappers du 02/09/2026 : avec ce chiffre d'affaires, "
                                "elle se placerait aujourd'hui dans le top 100.")

# coordonnées signalées comme incertaines par l'enrichissement (mobile non attribué, annuaire marchand) : non affichées
DOUTEUX = {'501271068': ('telephone',), '353323843': ('telephone',)}

def short_alias(nc):
    nc = re.split(r'\s*;\s*', str(nc).strip())[0]
    m = re.match(r'^(.*?)\s*\((.*)\)\s*$', nc)
    if m:
        base, par = m.group(1).strip(), m.group(2).strip()
        nc = par if norm(par).startswith(norm(base)) else base
    return nc.replace('Cosne-Cours-sur-Loire', 'Cosne').replace('La Charité-sur-Loire', 'La Charité').strip()

# ---- enrichissement des cibles proches (recherches complémentaires) ----
ALLOWED = ('nom_commercial', 'dirigeants', 'groupe', 'description', 'actualite', 'site_web', 'telephone', 'email', 'linkedin',
           'interlocuteur_cible', 'angle_partenariat', 'statut', 'site_local', 'opposition_prospection')
INTERDIT = re.compile(r"vieux relais|\ble m\b|\bdu m\b|\bau m\b|nos établissements|\bbar\b|\brestaurants?\b|chambres|bar-restaurant", re.I)
by_siren = {c['siren']: c for c in ext}
n_enr = 0
for f in sorted(glob.glob(EXT + '/enrich_*.json')):
    for e in json.load(open(f, encoding='utf-8')):
        c = by_siren.get(sid(e.get('siren')))
        if not c: continue
        for k in ALLOWED:
            v = e.get(k)
            if v in (None, '', []): continue
            if k == 'nom_commercial': v = short_alias(v)
            c[k] = v
        if INTERDIT.search(c.get('angle_partenariat') or ''): c['angle_partenariat'] = None
        for k2 in ('angle_partenariat', 'description', 'actualite'):
            if isinstance(c.get(k2), str): c[k2] = re.sub(r' :(?=\S)', ' : ', c[k2])
        if c.get('linkedin') and '/company/' not in c['linkedin']: c['linkedin'] = None      # profil personnel, pas une page entreprise
        for k in DOUTEUX.get(c['siren'], ()): c[k] = None
        c['sources'] = list(dict.fromkeys((c.get('sources') or []) + [x for x in (e.get('sources') or []) if isinstance(x, str)]))
        c['enrichie'] = True; n_enr += 1
        if e.get('site_cosne') is True and not c['site_cosne']:
            c['site_cosne'] = True
            if c['vague'] in (2, 3): c['vague'] = 1
        if not str(c.get('statut') or 'Active').lower().startswith('active'):
            c['vague'] = None; c['offres'] = []; c['priorite'] = 'Basse'

# corrections relevées par le second contrôle indépendant (registre en retard sur les BODACC)
ANCIENS_DIRIGEANTS = {'309230084': ('Fabrice CHARLES',), '351271127': ('Thierry MOSSON',), '*': ('AP2',)}
PROC_MANUELLES = {'818200396': 'Plan de redressement adopté le 01/12/2025'}
for c in ext:
    out_names = set(ANCIENS_DIRIGEANTS.get(c['siren'], ())) | set(ANCIENS_DIRIGEANTS['*'] if 'AP NEVERS' in c['nom'] else ())
    if out_names: c['dirigeants'] = [d for d in c['dirigeants'] if d['nom'] not in out_names]
    if c['siren'] in PROC_MANUELLES:
        c['statut'] = PROC_MANUELLES[c['siren']]; c['vague'] = None; c['offres'] = []; c['priorite'] = 'Basse'

# cas particuliers relevés pendant l'enrichissement
SENSIBLES = {'387932437': "Activité suspendue en décembre 2025, l'abattoir a rouvert depuis : sujet à aborder avec tact."}
for c in ext:
    if c['siren'] in SENSIBLES:
        c['note_classement'] = SENSIBLES[c['siren']]

for c in ext:
    for k in ('angle_partenariat', 'description', 'actualite', 'interlocuteur_cible'):
        assert not INTERDIT.search(str(c.get(k) or '')), (c['rang'], k, c.get(k))

json.dump([{'siren': c['siren'], 'nom': c['nom'], 'url': c.get('url'), 'ca': c['ca'], 'regle': c['regle'], 'badge': c.get('badge'), 'via_api': bool(c.get('via_api'))}
           for c in pool], open(EXT + '/pool.json', 'w', encoding='utf-8'), ensure_ascii=False)
chosen_ids = {c['siren'] for c in chosen}
json.dump([{'siren': c['siren'], 'nom': c['nom'], 'url': c.get('url'), 'ca': c['ca']} for c in grp_c if c['siren'] not in chosen_ids][:20],
          open(EXT + '/margin.json', 'w', encoding='utf-8'), ensure_ascii=False)
# ---- coordonnées et décideur financier (recherche de contacts, top 100 compris) ----
CONTACTS = {}
for f in sorted(glob.glob(EXT + '/contacts_out_*.json')):
    try: data = json.load(open(f, encoding='utf-8'))
    except Exception: continue   # fichier en cours d'écriture par un agent
    for e in data:
        k = sid(e.get('siren'))
        if re.match(r'\s*(non traité|pending)', str(e.get('note') or ''), re.I): continue   # lot interrompu : entreprise pas encore recherchée
        if not k: continue
        old = CONTACTS.get(k)
        if old:   # une passe plus récente complète la précédente sans effacer ce qu'elle avait trouvé
            e = dict(old, **{kk: vv for kk, vv in e.items() if vv not in (None, '', [], {}) and not (kk == 'standard' and not (vv or {}).get('tel'))})
            if old.get('note') and e.get('note') != old.get('note') and old['note'] not in (e.get('note') or ''):
                e['note'] = old['note'] + ' ' + (e.get('note') or '')
        CONTACTS[k] = e
def clean_tel(t):
    if not t: return None
    d = re.sub(r'\D', '', str(t))
    if d.startswith('33') and len(d) == 11: d = '0' + d[2:]
    if len(d) == 10 and d.startswith('0'): return ' '.join(d[i:i + 2] for i in range(0, 10, 2))
    return str(t).strip()
n_ct = Counter()
for c in base + ext:
    if c.get('telephone'): c['telephone'] = clean_tel(c['telephone'])   # « +33 7 … » -> « 07 … », comparable aux résultats des recherches
for c in base + ext:
    e = CONTACTS.get(sid(c.get('siren')))
    if not e: continue
    c['contacts_ok'] = True
    if e.get('note'): c['note_contacts'] = str(e['note']).strip()
    if e.get('decision'): c['decision'] = str(e['decision']).strip()      # où se prend la décision d'achat (recherche approfondie du top 100)
    std = e.get('standard') or {}
    if std.get('tel') and not c.get('telephone'): c['telephone'] = clean_tel(std['tel']); n_ct['tel ajouté'] += 1
    elif std.get('tel') and std.get('fiabilite') == 'officielle' and c.get('telephone') != clean_tel(std['tel']):
        c['telephone'] = clean_tel(std['tel']); n_ct['tel remplacé par un numéro officiel'] += 1   # source officielle plutôt qu'un annuaire
    if std.get('tel') and c.get('telephone') == clean_tel(std['tel']) and std.get('fiabilite') == 'officielle':
        c.pop('telephone_a_confirmer', None)
    if std.get('tel') and c.get('telephone') == clean_tel(std['tel']) and std.get('fiabilite') in ('annuaire', 'ancienne'):
        c['telephone_a_confirmer'] = True                    # annuaire seul ou source ancienne (levé si la vérification confirme)
    eg = e.get('email_generique') or {}
    if eg.get('email') and not c.get('email'): c['email'] = eg['email'].strip(); n_ct['email ajouté'] += 1
    if e.get('site_web') and not c.get('site_web'): c['site_web'] = e['site_web']
    df = e.get('decideur_financier') or None
    if isinstance(df, dict) and df.get('nom'):
        cf = {k: df.get(k) for k in ('nom', 'fonction', 'type', 'tel_direct', 'email', 'linkedin', 'source')}
        cf['tel_direct'] = clean_tel(cf.get('tel_direct'))
        if c.get('opposition_prospection'): cf['tel_direct'] = cf['email'] = None
        c['contact_finance'] = cf; n_ct['décideur'] += 1
        if cf.get('type') in ('DAF/RAF', 'comptable'): n_ct['dont finance'] += 1
        if cf.get('tel_direct') or cf.get('email'): n_ct['dont coordonnées directes'] += 1
    dp = e.get('dirigeant_principal')
    if isinstance(dp, dict) and dp.get('nom'):
        cd = {k: dp.get(k) for k in ('nom', 'fonction', 'tel_direct', 'email', 'linkedin', 'source')}
        cd['tel_direct'] = clean_tel(cd.get('tel_direct'))
        if c.get('opposition_prospection'): cd['tel_direct'] = cd['email'] = None
        c['contact_dirigeant'] = cd; n_ct['dirigeant'] += 1
    ad = e.get('adresse')
    if isinstance(ad, dict) and ad.get('adresse') and not c.get('adresse'):
        c['adresse'] = ad['adresse'].strip(); n_ct['adresse ajoutée'] += 1
        m = re.search(r'\b(58\d{3})\b', c['adresse'])
        if m and not c.get('code_postal'): c['code_postal'] = m.group(1)
    ac = [x for x in (e.get('autres_contacts') or []) if isinstance(x, dict) and x.get('nom')][:2]
    if ac and not c.get('opposition_prospection'): c['autres_contacts'] = ac
    # format_email_observe non repris : afficher un format inviterait à deviner des adresses
print('contacts :', len(CONTACTS), dict(n_ct), '| avec téléphone :', sum(1 for c in base + ext if c.get('telephone')), '/ 500')

# vérification indépendante (contacts_verif_*.json) : valeur contredite corrigée ou retirée, valeur non confirmée signalée
VERIF = {}
for f in sorted(glob.glob(EXT + '/contacts_verif_*.json')):
    try: data = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    for v in data:
        k = sid(v.get('siren'))
        if k: VERIF[k] = dict(VERIF.get(k) or {}, **{kk: vv for kk, vv in v.items() if vv not in (None, '', [])})   # vérifications successives cumulées
def verdict(x): return x.get('verdict') if isinstance(x, dict) else None
n_vf = Counter()
for c in base + ext:
    k = sid(c.get('siren')); v = VERIF.get(k); e = CONTACTS.get(k)
    if not v or not e: continue
    for champ, cle, val in (('telephone', 'standard', clean_tel((e.get('standard') or {}).get('tel'))),
                            ('email', 'email_generique', ((e.get('email_generique') or {}).get('email') or '').strip() or None)):
        x = v.get(cle)
        if not val or c.get(champ) != val: continue          # valeur déjà connue avant la recherche : non concernée
        if verdict(x) == 'contredit':
            c[champ] = (clean_tel(x['corrige']) if champ == 'telephone' else x['corrige'].strip()) if x.get('corrige') else None
            n_vf[champ + (' corrigé' if x.get('corrige') else ' retiré')] += 1
        elif verdict(x) == 'non_confirme' and not (champ == 'telephone' and (e.get('standard') or {}).get('fiabilite') == 'officielle'):
            c[champ + '_a_confirmer'] = True; n_vf[champ + ' à confirmer'] += 1
        elif verdict(x) == 'confirme':
            c.pop(champ + '_a_confirmer', None)
    cf, x = c.get('contact_finance'), v.get('decideur_financier')
    if cf and verdict(x) == 'contredit':
        if x.get('corrige'):
            nom, _, fct = str(x['corrige']).partition(' — ')
            cf.update(nom=nom.strip(), fonction=fct.strip() or None, tel_direct=None, email=None, linkedin=None, source=x.get('source'))
            n_vf['décideur corrigé'] += 1
        else:
            del c['contact_finance']; n_vf['décideur retiré'] += 1
    elif cf and verdict(x) == 'non_confirme' and cf.get('type') != 'dirigeant':   # un dirigeant du registre n'a pas à être retrouvé sur le web
        cf['a_confirmer'] = True; n_vf['décideur à confirmer'] += 1
    cd, x = c.get('contact_dirigeant'), v.get('dirigeant_principal')
    if cd and verdict(x) == 'contredit':
        if x.get('corrige'):
            nom, _, fct = str(x['corrige']).partition(' — ')
            cd.update(nom=nom.strip(), fonction=fct.strip() or None, tel_direct=None, email=None, linkedin=None, source=x.get('source'))
            n_vf['dirigeant corrigé'] += 1
        else:
            del c['contact_dirigeant']; n_vf['dirigeant retiré'] += 1
    elif cd and verdict(x) == 'non_confirme':      # signalé seulement s'il diffère du registre et n'a pas de source indépendante
        au_registre = ' '.join(norm(d.get('nom')) for d in c.get('dirigeants') or [])
        if not any(len(t) > 3 and norm(t) in au_registre for t in re.split(r'[\s-]+', cd.get('nom') or '')):
            cd['a_confirmer'] = True; n_vf['dirigeant à confirmer'] += 1
    ad0 = e.get('adresse')
    adr, x = ((ad0.get('adresse') if isinstance(ad0, dict) else ad0) or '').strip(), v.get('adresse')
    if adr and c.get('adresse') == adr and verdict(x) == 'contredit':
        c['adresse'] = x['corrige'].strip() if x.get('corrige') else None; n_vf['adresse ' + ('corrigée' if x.get('corrige') else 'retirée')] += 1
    if c.get('autres_contacts'):
        faux = {y.get('nom') for y in (v.get('autres_contacts') or []) if verdict(y) == 'contredit'}
        c['autres_contacts'] = [y for y in c['autres_contacts'] if y.get('nom') not in faux]
        if not c['autres_contacts']: del c['autres_contacts']
print('vérifications :', len(VERIF), dict(n_vf))

# relecture du 22/10/2026 : coordonnées sans source publiée, profils LinkedIn personnels, libellés
RETIRER = {'823687033': ('email',),       # adresse hotmail nominative, introuvable sur une page publique
           '397727397': ('telephone', 'autres_contacts')}   # LOOK Fixations (Rossignol) : numéro et contact des passes précédentes = LOOK Cycle
# le mobile d'Aizen (331967943), d'abord retiré faute de source, figure dans la présentation 2024 de l'entreprise (lot h23)
AUDITEURS = re.compile(r'(KPMG|DELOITTE|MAZARS|ERNST|PRICEWATERHOUSE|GRANT THORNTON|BDO)\b', re.I)
for c in base + ext:
    for k in RETIRER.get(sid(c.get('siren')), ()): c[k] = None
    c.pop('format_email', None)
    c['sources'] = [s for s in (c.get('sources') or []) if 'linkedin.com/in/' not in s]
    if c.get('effectif') == 'NN': c['effectif'] = 'Non employeuse'
    c['dirigeants'] = [x for x in (c.get('dirigeants') or []) if not AUDITEURS.match(x.get('nom') or '')]
    for k in ('description', 'angle_partenariat'):
        if isinstance(c.get(k), str):
            c[k] = re.sub(r" ; des profils LinkedIn de salariés[^.]*", '', c[k])
            c[k] = c[k].replace("travaux d'aménagement des établissements", "travaux d'aménagement")

json.dump(ext, open(EXT + '/ext_companies.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(base + ext, open(SITE + '/companies.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

print('candidats', len(cand), '| hors top 100 actifs', len(pool), '| écartées (liquidation/fermées)', len(dropped), [c['nom'] for c in dropped][:12])
print('complément lu', dict(n_supp), '| retenues', len(ext), '| par CA', len(ext) - n_eff, '| comptes non publiés', n_eff,
      '| avec registre', sum(c['registre'] for c in ext), '| enrichies', n_enr)
if ext:
    last_ca = [c for c in ext if c['ca']]
    print('rang 101 :', ext[0]['ca'], ext[0]['nom'], '| dernier CA :', last_ca[-1]['rang'], last_ca[-1]['ca'], last_ca[-1]['nom'])
    print('groupes : CA >= 500 k€', len(grp_a), '| comptes confidentiels >= 10 sal.', len(grp_b), '| CA 200-500 k€', len(grp_c), '| ajoutées via API 58000', n_gap)
    print('premiers non retenus :', [(c['nom'], c['ca'], c['effectif']) for c in (grp_b[n_eff:n_eff + 3] + [x for x in grp_c if x not in chosen][:3])])
print('écartées car organismes publics ou associations sans comptes :', non_ent)
if FIN_MODE: print('top 100 avec exercice récent signalé :', n_top_maj, '| candidates sans comptes vérifiés :', len(sans_fin), sans_fin[:10])
print('sans distance', [(c['nom'], c['ville']) for c in ext if c['distance_cosne_km'] is None][:10])
print('siège hors Nièvre au registre', hors58[:10])
print('priorités', Counter(c['priorite'] for c in ext), '| vagues', Counter(c['vague'] for c in ext))
print('procédures en cours', [(c['nom'], c['statut']) for c in ext if c['statut'] != 'Active'])
print('à Cosne et autour (<=5 km)', [(c['rang'], c['nom'], c['effectif']) for c in ext if c['site_cosne']])
