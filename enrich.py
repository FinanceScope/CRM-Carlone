"""Enrichissement des fiches (après merge.py, ext_merge.py et art_merge.py) : croisement des standards, comptes liés,
fiabilité par champ et score de complétude.
- ext/tel_out_*.json (consigne scratch/verif_tel_brief.txt, lots préparés par verif_tel_lots.py) : un standard « à confirmer »
  retrouvé sur une deuxième source indépendante est confirmé (drapeau levé) ; un autre numéro publié par une source fiable est
  affiché à côté (« telephone_alternatif »), sans remplacer celui de la fiche ; un numéro attribué à un autre titulaire est signalé.
- Comptes liés : même dirigeant (personne) au registre, ou société dirigeante d'une autre société de la liste. Un nom seul ne
  suffit pas pour affirmer l'identité : la page dit « même nom de dirigeant au registre ».
- Fiabilité : niveau (haute / moyenne / basse), source et date pour le standard, le dirigeant, les chiffres, l'effectif, les
  interlocuteurs et l'opposition à la prospection ; score de complétude sur 100 pour cibler les fiches à enrichir.
Usage : python3 -I merge.py && python3 -I ext_merge.py && python3 -I art_merge.py && python3 -I enrich.py"""
import glob, json, os, re, sys, unicodedata
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
EXT, SITE = ROOT + '/ext', ROOT + '/site'
companies = json.load(open(SITE + '/companies.json', encoding='utf-8'))
by_siren = {c['siren']: c for c in companies}
def tel_key(t): return re.sub(r'\D', '', str(t or ''))[-9:]
def clean_tel(t):
    d = re.sub(r'\D', '', str(t or ''))
    if d.startswith('33') and len(d) == 11: d = '0' + d[2:]
    return ' '.join(d[i:i + 2] for i in range(0, 10, 2)) if len(d) == 10 and d.startswith('0') else None
def norm_tokens(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return [w for w in re.sub(r'\(.*?\)', ' ', s).replace('-', ' ').split() if w.isalpha()]
n = Counter()

# ---- 1. standards : deuxième source ----
for c in companies:
    for k in ('telephone_verifie', 'telephone_alternatif', 'telephone_doute'): c.pop(k, None)
for f in sorted(glob.glob(EXT + '/tel_out_*.json')):
    try: data = json.load(open(f, encoding='utf-8'))
    except Exception as err: sys.exit(f'Fichier illisible : {f} ({err}). Attendre la fin du lot ou le corriger, puis relancer.')
    for e in data:
        c = by_siren.get(str(e.get('siren')))
        if not c or not c.get('telephone') or tel_key(e.get('telephone')) != tel_key(c['telephone']): continue   # le numéro a changé depuis
        v, note = e.get('verdict'), str(e.get('note') or '').strip()
        date = (re.search(r'\((\d\d/\d\d/\d{4})\)', note) or [None, None])[1]
        if v == 'confirme' and e.get('sources'):
            c.pop('telephone_a_confirmer', None)
            c['telephone_verifie'] = {'sources': e['sources'][:3], 'date': date}
            n['standards confirmés'] += 1
        elif v == 'conflit' and clean_tel(e.get('autre_numero')) and e.get('autre_source') and tel_key(e['autre_numero']) != tel_key(c['telephone']):
            c['telephone_alternatif'] = {'tel': clean_tel(e['autre_numero']), 'source': e['autre_source'], 'date': date}
            n['autre numéro publié'] += 1
        elif v == 'autre_titulaire':
            c['telephone_doute'] = {'note': note, 'sources': (e.get('sources') or [])[:2], 'date': date}
            n['numéro attribué à un autre titulaire'] += 1
        else: n['non retrouvé'] += 1
        if note and note not in (c.get('note_contacts') or ''): c['note_contacts'] = ((c.get('note_contacts') or '') + ' ' + note).strip()

# ---- 2. comptes liés ----
PM = re.compile(r'\b(sas|sasu|sarl|eurl|sa|sci|holding|groupe|family|financiere|participations|personne morale)\b', re.I)
personnes, morales = defaultdict(set), {}
noms = {' '.join(norm_tokens(c['nom'])): c['rang'] for c in companies}
for c in companies:
    for x in c.get('dirigeants') or []:
        if not isinstance(x, dict) or not x.get('nom'): continue
        brut = str(x['nom'])
        t = norm_tokens(brut)
        if 'personne morale' in brut.lower() or PM.search(brut) or brut.isupper() and len(t) <= 3 and ' '.join(t) in noms:
            k = ' '.join(t).replace(' personne morale', '')
            if k in noms and noms[k] != c['rang']: morales.setdefault(c['rang'], set()).add(noms[k])
            continue
        if len(t) >= 2 and max(len(w) for w in t) >= 4: personnes[' '.join(sorted(t))].add(c['rang'])
by_rang = {c['rang']: c for c in companies}
for c in companies: c.pop('comptes_lies', None)
def lier(a, b, lien):
    ca = by_rang[a]
    lst = ca.setdefault('comptes_lies', [])
    if not any(x['rang'] == b for x in lst): lst.append({'rang': b, 'lien': lien})
for k, rangs in personnes.items():
    if len(rangs) < 2 or len(rangs) > 6: continue
    nom = next(x['nom'] for x in by_rang[min(rangs)].get('dirigeants') or [] if isinstance(x, dict) and ' '.join(sorted(norm_tokens(x.get('nom')))) == k)
    for a in rangs:
        for b in rangs:
            if a != b: lier(a, b, f'même nom de dirigeant au registre : {re.sub(r" *\(.*?\)", "", nom)}')
for a, bs in morales.items():
    for b in bs:
        lier(a, b, 'société dirigeante de cette entreprise au registre')
        lier(b, a, 'société dirigée par cette entreprise au registre')
n['fiches avec comptes liés'] = sum(1 for c in companies if c.get('comptes_lies'))

# ---- 2 bis. site, e-mail générique, LinkedIn, actualités et raison d'appeler maintenant (ext/enr_out_*.json) ----
INTERDIT = re.compile(r"vieux relais|\ble m\b|\bdu m\b|\bau m\b|restaurant|\bbar\b|exposition|nos établissements", re.I)
def dom(u): return re.sub(r'^www\.', '', (re.match(r'https?://([^/]+)', str(u or '')) or [None, ''])[1].lower())
for c in companies:
    for k in ('actualites', 'declencheur', 'effectif_linkedin', 'email_source'): c.pop(k, None)
for f in sorted(glob.glob(EXT + '/enr_out_*.json')):
    try: data = json.load(open(f, encoding='utf-8'))
    except Exception as err: sys.exit(f'Fichier illisible : {f} ({err}). Attendre la fin du lot ou le corriger, puis relancer.')
    for e in data:
        c = by_siren.get(str(e.get('siren')))
        if not c: continue
        if e.get('site_web') and not c.get('site_web') and re.match(r'https?://', e['site_web']): c['site_web'] = e['site_web']; n['sites ajoutés'] += 1
        if e.get('linkedin') and not c.get('linkedin') and 'linkedin.com/company' in e['linkedin']: c['linkedin'] = e['linkedin']; n['pages LinkedIn ajoutées'] += 1
        if e.get('effectif_linkedin'): c['effectif_linkedin'] = str(e['effectif_linkedin'])[:40]
        eg = e.get('email_generique') or {}
        em, src = str(eg.get('email') or '').strip().lower(), eg.get('source')
        # e-mail générique publié par l'entreprise : source sur son propre domaine ou domaine de l'adresse identique au site
        if em and src and not c.get('email') and not c.get('opposition_prospection') and not re.match(r'[a-z]+[.-][a-z]+@', em) \
                and (dom(src) == em.split('@')[1] or dom(src) == dom(c.get('site_web')) or em.split('@')[1] == dom(c.get('site_web'))):
            c['email'], c['email_source'] = em, src; n['e-mails génériques ajoutés'] += 1
        acts = [a for a in e.get('actualites') or [] if isinstance(a, dict) and a.get('fait') and a.get('source') and re.fullmatch(r'\d\d/20(2[4-9])', str(a.get('date') or '')) and not INTERDIT.search(a['fait'])]
        if acts: c['actualites'] = sorted(acts, key=lambda a: a['date'][3:] + a['date'][:2], reverse=True)[:3]; n['fiches avec actualités datées'] += 1
        dcl = str(e.get('declencheur') or '').strip()
        if dcl and acts and not INTERDIT.search(dcl): c['declencheur'] = dcl; n['raisons d\'appeler maintenant'] += 1
        note = str(e.get('note') or '').strip()
        if note and note not in (c.get('note_contacts') or ''): c['note_contacts'] = ((c.get('note_contacts') or '') + ' ' + note).strip()

# ---- 3. fiabilité par champ et complétude ----
def fiab(c):
    f, score = {}, 0
    if c.get('telephone'):
        if c.get('telephone_verifie'): f['standard'] = ['haute', 'deux sources indépendantes', c['telephone_verifie'].get('date')]; score += 30
        elif c.get('telephone_a_confirmer'): f['standard'] = ['basse', 'un seul annuaire ou source ancienne', None]; score += 15
        elif c.get('telephone_groupe'): f['standard'] = ['moyenne', "standard d'une société du groupe", None]; score += 20
        else: f['standard'] = ['haute', "source officielle ou recherche vérifiée", None]; score += 30
        if c.get('telephone_doute'): f['standard'] = ['basse', 'numéro aussi attribué à un autre titulaire', c['telephone_doute'].get('date')]; score -= 10
    else: f['standard'] = ['aucune', 'aucun numéro publié trouvé', None]
    cd = c.get('contact_dirigeant') or {}
    if c.get('dirigeants') or cd.get('nom'):
        f['dirigeant'] = ['moyenne', 'différent du registre, à confirmer', None] if cd.get('a_confirmer') else ['haute', 'registre (RNE / Pappers)', None]
        score += 15
    a = c.get('art') or {}
    yr = a.get('annee')
    if yr and int(yr) >= 2024: f['chiffres'] = ['haute', f"comptes {yr}" + (' (recherche)' if a.get('source') == 'recherche' else ' publiés'), None]; score += 15
    elif yr: f['chiffres'] = ['moyenne', f'comptes {yr}, plus récents non publiés', None]; score += 8
    else: f['chiffres'] = ['basse', 'comptes non publiés ou confidentiels : plafond estimé', None]
    ea = c.get('eff_annee')
    f['effectif'] = ['haute' if ea and int(ea) >= 2024 else 'moyenne', (f'tranche INSEE {ea}' if ea else 'tranche du registre, année non précisée')
                     + (f" ; LinkedIn : {c['effectif_linkedin']}" if c.get('effectif_linkedin') else ''), None]
    adm = c.get('contacts_admin') or []
    if any(p.get('role') == 'finance' and p.get('fiabilite') == 'confirme' for p in adm): f['interlocuteurs'] = ['haute', 'responsable finance confirmé', None]; score += 20
    elif adm: f['interlocuteurs'] = ['moyenne', 'nommé(s) par une seule source', None]; score += 10
    elif c.get('note_admin'): f['interlocuteurs'] = ['aucune', 'recherché, aucun nom publié : demander au standard', None]
    else: f['interlocuteurs'] = ['aucune', 'pas encore recherché', None]
    if c.get('site_web'): score += 10
    op = c.get('opposition_prospection')
    f['opposition'] = ['haute', 'vérifiée sur Pappers : ' + ('opposée, pas de mailing' if op else 'non opposée'), None] if op in (True, False) else ['basse', 'non vérifiée : contrôler Pappers avant tout e-mail', None]
    if op in (True, False): score += 10
    return f, max(0, min(100, score))
for c in companies:
    c['fiab'], c['completude'] = fiab(c)
act = [c for c in companies if str(c.get('statut') or 'Active').lower().startswith('active') and not c.get('exclue') and not c.get('cessation')]
n['complétude moyenne (actives)'] = round(sum(c['completude'] for c in act) / len(act))
n['standards encore à confirmer'] = sum(1 for c in act if c.get('telephone_a_confirmer'))
json.dump(companies, open(SITE + '/companies.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('enrichissement :', dict(n))
