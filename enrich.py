"""Enrichissement des fiches (après merge.py, ext_merge.py et art_merge.py) : croisement des standards, comptes liés,
fiabilité par champ et score de complétude.
- ext/tel_out_*.json (consigne scratch/verif_tel_brief.txt, lots préparés par verif_tel_lots.py) : un standard « à confirmer »
  retrouvé sur une deuxième source indépendante est confirmé (drapeau levé) ; un autre numéro publié par une source fiable est
  affiché à côté (« telephone_alternatif »), sans remplacer celui de la fiche ; un numéro attribué à un autre titulaire est signalé.
- ext/enr_out_*.json (consigne scratch/enrich_brief.txt, lots préparés par enrich_lots.py) : site, e-mail générique publié par
  l'entreprise elle-même, page LinkedIn et effectif affiché, actualités datées et sourcées, raison d'appeler maintenant.
- Comptes liés : même dirigeant personne au registre (nom et premier prénom), même société dirigeante, ou société dirigeante /
  dirigée de la liste. Un nom identique ne prouve pas l'identité : la page le dit.
- Fiabilité : niveau (haute / moyenne / basse), source et date pour le standard, le dirigeant, les chiffres, l'effectif, les
  interlocuteurs et l'opposition à la prospection ; score de complétude sur 100 pour cibler les fiches à enrichir.
Le fichier doit sortir d'art_merge.py (le script s'arrête sinon, pour ne jamais enrichir deux fois la même fiche).
Usage : python3 -I merge.py && python3 -I ext_merge.py && python3 -I art_merge.py && python3 -I enrich.py"""
import datetime, glob, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
EXT, SITE = ROOT + '/ext', ROOT + '/site'
companies = json.load(open(SITE + '/companies.json', encoding='utf-8'))
if any('fiab' in c for c in companies):
    sys.exit('companies.json est déjà enrichi : relancer merge.py, ext_merge.py et art_merge.py avant enrich.py.')
by_siren = {c['siren']: c for c in companies}
by_rang = {c['rang']: c for c in companies}
MOIS = datetime.date.today().strftime('%Y%m')
def tel_key(t): return re.sub(r'\D', '', str(t or ''))[-9:]
def clean_tel(t):
    d = re.sub(r'\D', '', str(t or ''))
    if d.startswith('33') and len(d) == 11: d = '0' + d[2:]
    return ' '.join(d[i:i + 2] for i in range(0, 10, 2)) if len(d) == 10 and d.startswith('0') else None
def ascii_low(s): return unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().lower()
FORMES = {'sas', 'sasu', 'sarl', 'eurl', 'sa', 'sci', 'snc', 'selarl', 'selas', 'sca', 'scea', 'earl', 'gaec', 'ste', 'societe'}
def cle(s):
    """Clé d'un nom : sans accents ni parenthèses, ponctuation retirée dans les mots (E.B.P. -> ebp, T.3.C -> t3c), sans forme sociale."""
    s = re.sub(r'\(.*?\)', ' ', ascii_low(s)).replace('-', ' ').replace("'", ' ')
    return [w for w in (re.sub(r'[^a-z0-9]', '', w) for w in s.split()) if w and w not in FORMES]
def urls(v, k):
    v = [v] if isinstance(v, str) else v if isinstance(v, list) else []
    return [u for u in v if isinstance(u, str) and re.match(r'https?://', u)][:k]
def dom(u): return re.sub(r'^www\.', '', (re.match(r'https?://([^/?#]+)', str(u or '')) or [None, ''])[1].lower())
n = Counter()

# ---- 1. standards : deuxième source ----
for f in sorted(glob.glob(EXT + '/tel_out_*.json')):
    try: data = json.load(open(f, encoding='utf-8'))
    except Exception as err: sys.exit(f'Fichier illisible : {f} ({err}). Attendre la fin du lot ou le corriger, puis relancer.')
    for e in data:
        if not isinstance(e, dict): n['entrées rejetées'] += 1; continue
        c = by_siren.get(str(e.get('siren')))
        if not c or not c.get('telephone') or tel_key(e.get('telephone')) != tel_key(c['telephone']): continue   # le numéro a changé depuis
        v, note = e.get('verdict'), str(e.get('note') or '').strip()
        date = (re.search(r'\((\d\d/\d\d/\d{4})\)', note) or [None, None])[1]
        src = urls(e.get('sources'), 3)
        alt = clean_tel(e.get('autre_numero'))
        if v == 'confirme' and src:
            c.pop('telephone_a_confirmer', None)
            c['telephone_verifie'] = {'sources': src, 'date': date}
            n['standards confirmés'] += 1
        elif v == 'conflit' and alt and urls(e.get('autre_source'), 1) and tel_key(alt) != tel_key(c['telephone']):
            c['telephone_alternatif'] = {'tel': alt, 'source': urls(e.get('autre_source'), 1)[0], 'date': date}
            n['autre numéro publié'] += 1
        elif v == 'autre_titulaire':
            c['telephone_doute'] = {'note': note, 'sources': src[:2], 'date': date}
            n['numéro attribué à un autre titulaire'] += 1
        else: n['non retrouvé'] += 1
        if note and note not in (c.get('note_contacts') or ''): c['note_contacts'] = ((c.get('note_contacts') or '') + ' ' + note).strip()

# ---- 2. comptes liés ----
MOT_SOCIETE = re.compile(r'\b(holding|groupe|group|family|financiere|participations?|developpement|investissements?|exploitation|gestion|conseil|'
                         r'distribution|services?|invest|capital|patrimoine|patrimoniale|fils|cie|compagnie|immobiliere|industries?|ets|etablissements|'
                         r'societe|sas|sasu|sarl|eurl|sci|scea|earl)\b', re.I)
def est_societe(x):
    nom, fct = str(x.get('nom') or ''), str(x.get('fonction') or '')
    if 'personne morale' in (nom + ' ' + fct).lower() or MOT_SOCIETE.search(ascii_low(nom)): return True
    if not re.search(r'[a-zà-ÿ]', nom):                       # tout en majuscules : sigle ou société, sauf « PRÉNOM NOM »
        t = cle(nom)
        return len(t) <= 1 or nom.strip().startswith(("L ", "L'", "LA ", "LE ", "LES "))
    return False
index_noms, compte_noms = {}, Counter()
for c in companies:
    for k in {' '.join(cle(c['nom'])), ' '.join(cle(c.get('nom_commercial')))} - {''}:
        compte_noms[k] += 1; index_noms[k] = c['rang']
index_noms = {k: r for k, r in index_noms.items() if compte_noms[k] == 1}   # clé ambiguë : pas de lien
personnes, societes = defaultdict(dict), defaultdict(dict)
dirigeante = defaultdict(set)
for c in companies:
    for x in c.get('dirigeants') or []:
        if not isinstance(x, dict) or not x.get('nom'): continue
        brut = re.sub(r'\s*\(.*?\)', '', str(x['nom'])).strip()
        t = cle(brut)
        if not t: continue
        if est_societe(x):
            k = ' '.join(t)
            societes[k][c['rang']] = brut
            r = index_noms.get(k)
            if r and r != c['rang']: dirigeante[c['rang']].add(r)
        elif len(t) >= 2 and max(len(w) for w in t) >= 3:
            personnes[(t[0], t[-1]) if t[0] <= t[-1] else (t[-1], t[0])][c['rang']] = (brut, frozenset(t))   # premier prénom et nom
def lier(a, b, lien, typ):
    lst = by_rang[a].setdefault('comptes_lies', [])
    if a != b and not any(x['rang'] == b for x in lst): lst.append({'rang': b, 'lien': lien, 'type': typ})
for a, bs in dirigeante.items():
    for b in bs:
        lier(a, b, 'société dirigeante de cette entreprise au registre', 'dirigeante')
        lier(b, a, 'société dirigée par cette entreprise au registre', 'dirigee')
for k, m in societes.items():
    if 2 <= len(m) <= 8:
        for a in m:
            for b in m: lier(a, b, f'même société dirigeante au registre : {m[a]}', 'societe')
for k, m in personnes.items():
    if 2 <= len(m) <= 6:
        for a in m:
            for b in m:
                if a != b: lier(a, b, f'même nom de dirigeant au registre : {m[a][0]}' + ('' if m[a][1] == m[b][1] else ' (prénoms différents)'), 'personne')
n['fiches avec comptes liés'] = sum(1 for c in companies if c.get('comptes_lies'))

# ---- 2 bis. site, e-mail générique, LinkedIn, actualités et raison d'appeler maintenant (ext/enr_out_*.json) ----
ASSOCIES = re.compile(r"vieux[\s-]*relais|\ble m\b|\bdu m\b|\bau m\b|nos établissements", re.I)       # établissements des associés : jamais
LIEUX = re.compile(r"\bexpos?\b|exposition|vernissage|\bbars?\b|restaurant", re.I)                    # lieu d'exposition : pas dans les faits
GENERIQUE = re.compile(r'(contact|accueil|info|infos|information|commercial|commerciale|ventes?|secretariat|direction|compta|comptabilite|'
                       r'administration|admin|rh|recrutement|magasin|boutique|service[._-]?clients?|sav|agence|reception|standard|devis|'
                       r'commandes?|bonjour|hello|office|courrier|mail|siege|bureau|atelier|cave|domaine|hotel|garage|direction[._-]?generale)'
                       r'([._-]?[a-z0-9]+)?$')
WEBMAIL = {'gmail.com', 'hotmail.com', 'hotmail.fr', 'outlook.com', 'outlook.fr', 'live.fr', 'yahoo.fr', 'yahoo.com', 'orange.fr', 'wanadoo.fr',
           'free.fr', 'laposte.net', 'sfr.fr', 'neuf.fr', 'aol.com', 'icloud.com', 'bbox.fr', 'nordnet.fr'}
PLATEFORMES = ('facebook.com', 'instagram.com', 'linkedin.com', 'intermarche.com', 'leclerc', 'magasins-u.com', 'bricomarche.com', 'all.accor.com',
               'carrefour.fr', 'pagesjaunes.fr', 'societe.com', 'pappers.fr', 'kompass.com', 'verif.com', 'manageo.fr', 'mappy.com', '118712.fr',
               'google.', 'tripadvisor', 'logishotels.com', 'groupevincent.fr')
def email_ok(em, src, c):
    if not re.fullmatch(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', em) or not src: return False
    local, edom = em.rsplit('@', 1)
    if not GENERIQUE.fullmatch(ascii_low(local)): return False                                     # adresse nominative : jamais
    noms = {w for p in (c.get('dirigeants') or []) + (c.get('contacts_admin') or []) + [c.get('contact_dirigeant') or {}, c.get('contact_finance') or {}]
            if isinstance(p, dict) for w in cle(p.get('nom')) if len(w) >= 4}
    if any(w in ascii_low(local) for w in noms): return False
    ds, site = dom(src), c.get('site_web') or ''
    if any(p in ds for p in PLATEFORMES):                                                          # page d'une plateforme : seulement la page propre
        return bool(site) and src.split('?')[0].rstrip('/').startswith(site.split('?')[0].rstrip('/'))
    marque = {w for w in cle(c['nom']) + cle(c.get('nom_commercial')) + cle(c.get('nom_court')) if len(w) >= 4}
    if edom in WEBMAIL: return ds == dom(site) and ds != ''                                         # messagerie : publiée sur le site propre
    return ds == edom or (ds == dom(site) and (edom == dom(site) or any(w in edom.replace('-', '') for w in marque)))   # pas l'adresse d'une agence web
for f in sorted(glob.glob(EXT + '/enr_out_*.json')):
    try: data = json.load(open(f, encoding='utf-8'))
    except Exception as err: sys.exit(f'Fichier illisible : {f} ({err}). Attendre la fin du lot ou le corriger, puis relancer.')
    for e in data:
        if not isinstance(e, dict): n['entrées rejetées'] += 1; continue
        c = by_siren.get(str(e.get('siren')))
        if not c: continue
        sw = urls(e.get('site_web'), 1)
        if sw and not c.get('site_web'): c['site_web'] = sw[0]; n['sites ajoutés'] += 1
        elif sw and dom(sw[0]) != dom(c['site_web']):
            c['site_corrige'] = {'ancien': c['site_web'], 'date': '28/10/2026'}; c['site_web'] = sw[0]; n['sites corrigés'] += 1
        li = urls(e.get('linkedin'), 1)
        if li and 'linkedin.com/company' in li[0] and not c.get('linkedin'): c['linkedin'] = li[0]; n['pages LinkedIn ajoutées'] += 1
        ef = e.get('effectif_linkedin')
        if isinstance(ef, str) and ef.strip() and c.get('linkedin') and (not li or li[0].rstrip('/') == c['linkedin'].rstrip('/')):
            c['effectif_linkedin'] = {'effectif': ef.strip()[:40], 'source': c['linkedin']}
        eg = e.get('email_generique') if isinstance(e.get('email_generique'), dict) else {}
        em, src = str(eg.get('email') or '').strip().lower(), (urls(eg.get('source'), 1) or [None])[0]
        if em and not c.get('email') and not c.get('opposition_prospection'):
            if email_ok(em, src, c): c['email'], c['email_source'] = em, src; n['e-mails génériques ajoutés'] += 1
            else: n['e-mails écartés (nominatif, tiers ou source non propre)'] += 1
        brut = [a for a in e.get('actualites') or [] if isinstance(a, dict)]
        rejet = any(ASSOCIES.search(str(a.get('fait'))) or LIEUX.search(str(a.get('fait'))) for a in brut)
        acts = []
        for a in brut:
            d, fait, s = str(a.get('date') or ''), a.get('fait'), urls(a.get('source'), 1)
            if not (isinstance(fait, str) and s and re.fullmatch(r'(0[1-9]|1[0-2])/20(2[4-9])', d) and d[3:] + d[:2] <= MOIS): continue
            if ASSOCIES.search(fait) or LIEUX.search(fait): continue
            acts.append({'date': d, 'fait': fait.strip(), 'source': s[0]})
        if acts:
            c['actualites'] = sorted(acts, key=lambda a: a['date'][3:] + a['date'][:2], reverse=True)[:3]; n['fiches avec actualités datées'] += 1
        dcl = e.get('declencheur')
        if isinstance(dcl, str) and dcl.strip() and acts and not rejet and not (ASSOCIES.search(dcl) or LIEUX.search(dcl)):
            c['declencheur'] = dcl.strip(); n["raisons d'appeler maintenant"] += 1
        note = str(e.get('note') or '').strip()
        if note and not ASSOCIES.search(note) and note not in (c.get('note_contacts') or ''): c['note_contacts'] = ((c.get('note_contacts') or '') + ' ' + note).strip()

# ---- 3. fiabilité par champ et complétude ----
def est_personne(p): return isinstance(p, dict) and p.get('nom') and 'personne morale' not in (str(p.get('nom')) + ' ' + str(p.get('fonction') or '')).lower()
def fiab(c):
    f, score = {}, 0
    if c.get('telephone'):
        if c.get('telephone_doute'): f['standard'] = ['basse', 'numéro aussi attribué à un autre titulaire', c['telephone_doute'].get('date')]; score += 5
        elif c.get('telephone_verifie'): f['standard'] = ['haute', 'deux sources indépendantes', c['telephone_verifie'].get('date')]; score += 30
        elif c.get('telephone_a_confirmer'): f['standard'] = ['basse', 'un seul annuaire ou source ancienne', None]; score += 15
        elif c.get('telephone_groupe'): f['standard'] = ['moyenne', "standard d'une société du groupe", None]; score += 20
        else: f['standard'] = ['haute', 'source officielle ou recherche vérifiée', None]; score += 30
    else: f['standard'] = ['aucune', 'aucun numéro publié trouvé', None]
    cd = c.get('contact_dirigeant') or {}
    if c.get('dirigeants'):
        f['dirigeant'] = ['moyenne', 'différent du registre, à confirmer', None] if cd.get('a_confirmer') else ['haute', 'registre (RNE / Pappers)', None]; score += 15
    elif cd.get('nom'):
        f['dirigeant'] = ['moyenne', 'source : ' + (dom(cd.get('source')) or 'non précisée'), None]; score += 10
    a = c.get('art') or {}
    yr = str(a.get('annee') or '')
    if yr.isdigit() and int(yr) >= 2024: f['chiffres'] = ['haute', f"comptes {yr}" + (' (recherche)' if a.get('source') == 'recherche' else ' publiés'), None]; score += 15
    elif yr.isdigit(): f['chiffres'] = ['moyenne', f'comptes {yr}, plus récents non publiés', None]; score += 8
    else: f['chiffres'] = ['basse', 'comptes non publiés ou confidentiels : plafond estimé', None]
    ea = str(c.get('eff_annee') or '')
    el = (c.get('effectif_linkedin') or {}).get('effectif')
    f['effectif'] = ['haute' if ea.isdigit() and int(ea) >= 2024 else 'moyenne', (f'tranche INSEE {ea}' if ea else 'tranche du registre, année non précisée')
                     + (f' ; LinkedIn : {el}' if el else ''), None]
    adm = c.get('contacts_admin') or []
    cf = c.get('contact_finance') or {}
    cf_ok = est_personne(cf) and cf.get('type') in ('DAF/RAF', 'comptable')
    if any(p.get('fiabilite') == 'confirme' for p in adm) or cf_ok and not cf.get('a_confirmer'):
        fin = any(p.get('role') == 'finance' and p.get('fiabilite') == 'confirme' for p in adm) or cf_ok and not cf.get('a_confirmer')
        f['interlocuteurs'] = ['haute', 'responsable finance confirmé' if fin else 'interlocuteur confirmé (hors finance)', None]; score += 20
    elif adm or cf_ok: f['interlocuteurs'] = ['moyenne', 'nommé(s) par une seule source ou source ancienne, à confirmer', None]; score += 10
    elif c.get('note_admin'): f['interlocuteurs'] = ['aucune', 'recherché, aucun nom publié : demander au standard', None]
    else: f['interlocuteurs'] = ['aucune', 'pas encore recherché', None]
    if c.get('site_web'): score += 10
    op = c.get('opposition_prospection')
    f['opposition'] = ['haute', 'vérifiée lors de la recherche : ' + ('opposée, pas de mailing' if op else 'non opposée'), None] if op in (True, False) \
        else ['basse', 'non vérifiée : contrôler la fiche Pappers avant tout e-mail', None]
    if op in (True, False): score += 10
    return f, max(0, min(100, score))
for c in companies:
    c['fiab'], c['completude'] = fiab(c)
act = [c for c in companies if str(c.get('statut') or 'Active').lower().startswith('active') and not c.get('exclue') and not c.get('cessation')]
n['complétude moyenne (actives)'] = round(sum(c['completude'] for c in act) / len(act))
n['standards encore à confirmer'] = sum(1 for c in act if c.get('telephone_a_confirmer'))
json.dump(companies, open(SITE + '/companies.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('enrichissement :', dict(n))
