import json, glob, re, sys

base = {}
for line in open('/home/claude/crm/base.tsv', encoding='utf-8'):
    r, nom, act, ca, res, eff = line.rstrip('\n').split('\t')
    base[int(r)] = dict(rang=int(r), nom=nom, activite=act, ca=int(ca), resultat=int(res),
                        effectif=(eff + ' salariés') if eff[0].isdigit() and eff not in ('0',) else ('0 salarié' if eff == '0' else eff))

def secteur(act):
    a = act.lower()
    rules = [
        ('automobile', 'Automobile'), ('motocycles', 'Automobile'),
        ('sièges sociaux', 'Holdings & finance'), ('financiers', 'Holdings & finance'),
        ('commerce de détail', 'Commerce & distribution'), ('commerce de gros', 'Commerce & distribution'),
        ('transport', 'Transport & logistique'), ('entreposage', 'Transport & logistique'), ('location', 'Transport & logistique'),
        ('bois', 'Bois & forêt'), ('sylviculture', 'Bois & forêt'), ('meubles', 'Bois & forêt'),
        ('santé', 'Santé'), ('pharma', 'Santé'),
        ('sportives', 'Sport, loisirs & médias'), ('jeux', 'Sport, loisirs & médias'), ('édition', 'Sport, loisirs & médias'),
        ('imprimerie', 'Imprimerie & papier'), ('papier', 'Imprimerie & papier'),
        ('déchets', 'Énergie & environnement'), ('électricité', 'Énergie & environnement'), ('raffinage', 'Énergie & environnement'),
        ('construction', 'BTP & matériaux'), ('génie civil', 'BTP & matériaux'), ('minéraux', 'BTP & matériaux'), ('extractives', 'BTP & matériaux'),
        ('culture', 'Agriculture'),
    ]
    for k, v in rules:
        if k in a:
            return v
    return 'Industrie'

research = {}
for f in sorted(glob.glob('/home/claude/crm/research/batch_*.json')):
    for o in json.load(open(f, encoding='utf-8')):
        research[int(o['rang'])] = o

verif = {}
for f in sorted(glob.glob('/home/claude/crm/research/verif_out_*.json')):
    for o in json.load(open(f, encoding='utf-8')):
        verif[int(o['rang'])] = o
out, missing = [], []
for r in sorted(base):
    b = base[r]
    o = research.get(r)
    if not o:
        missing.append(r); o = {}
    c = dict(o)
    v = verif.get(r)
    c['verifie'] = bool(v)
    if v:
        for k, val in v.items():
            if k in ('rang', 'sources_verif'): continue
            if val is None and k not in ('site_local', 'interlocuteur_cible'): continue
            c[k] = val
        c['sources'] = list(dict.fromkeys((c.get('sources') or []) + (v.get('sources_verif') or [])))
    # chiffres du classement = référence
    vca = (v or {}).get('ca'); vres = (v or {}).get('resultat')
    c['ca_recent'] = vca if isinstance(vca, (int, float)) and vca != b['ca'] else None
    c['res_recent'] = vres if isinstance(vres, (int, float)) and vres != b['resultat'] else None
    c.update(rang=r, nom=b['nom'], activite=b['activite'], ca=b['ca'], resultat=b['resultat'])
    if not c.get('effectif'):
        c['effectif'] = b['effectif']
    c['secteur'] = secteur(b['activite'])
    for k in ('siren',):
        if c.get(k): c[k] = re.sub(r'\s', '', str(c[k]))
    d = c.get('distance_cosne_km')
    try: c['distance_cosne_km'] = int(round(float(d))) if d is not None else None
    except Exception: c['distance_cosne_km'] = None
    if c.get('priorite') not in ('Haute', 'Moyenne', 'Basse'): c['priorite'] = None
    c['dirigeants'] = [x for x in (c.get('dirigeants') or []) if isinstance(x, dict) and x.get('nom')]
    out.append(c)

json.dump(out, open('/home/claude/crm/site/companies.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('total', len(out), 'missing research', missing)
for k in ('siren', 'site_web', 'telephone', 'email', 'linkedin', 'adresse'):
    print(k, sum(1 for c in out if c.get(k)))
print('dirigeants', sum(1 for c in out if c['dirigeants']))
from collections import Counter
print(Counter(c['priorite'] for c in out))

# ---- Plan d'attaque : vagues et offres (règles) ----
def emin(e):
    m = re.search(r'\d+', str(e or ''))
    return int(m.group()) if m else 0
FOURNISSEURS = {59, 39}
VISIBILITE = {88, 64, 84}
LOCAL_COSNE = {90, 19, 66, 94, 59, 88}  # site à Cosne vérifié : Styl'Habitat, SUMA VW Cosne, labo Evorial, agence Distance
MEDIAS = {88}
OPPOSITION = {100, 66}
NOMS_COURTS = {19: "SUMA Volkswagen (Nevers et Cosne)", 60: "GEFICCA", 49: "Pasori (centre de rééducation)", 10: "E.Leclerc Nevers",
  39: "Saget La Perrière", 59: "CHR Boissons / Cave du Val d'Or", 75: "Garage GRV (Citroën et Peugeot Cosne)", 3: "Groupe Vincent (holding)",
  38: "Renault Cosne (groupe Simonneau)", 15: "Renault Nevers (groupe Simonneau)", 88: "Le Journal du Centre", 94: "Distance location auto (groupe Vincent)"}
for c in out:
    d = c.get('distance_cosne_km'); d = 999 if d is None else d
    if c['rang'] in LOCAL_COSNE: d = min(d, 3)
    e = emin(c.get('effectif'))
    active = not c.get('statut') or str(c['statut']).lower().startswith('active')
    offres = []
    if c['rang'] in FOURNISSEURS or c['rang'] in VISIBILITE: offres.append('local')
    if active and e >= 10:
        if d <= 30 and e >= 50: offres.append('carte')
        if d <= 25: offres.append('dej')
        if d <= 25 and e >= 20: offres.append('afterwork')
        if d <= 70 and e >= 50: offres.append('events')
    c['offres'] = offres
    vague = None
    if False: pass
    elif active and c['priorite'] in ('Haute', 'Moyenne') and e >= 10 and c['secteur'] != 'Holdings & finance':
        vague = 1 if d <= 5 else (2 if d <= 30 else 3)
    c['vague'] = vague
    c['opposition_prospection'] = c['rang'] in OPPOSITION
    c['site_cosne'] = (c.get('distance_cosne_km') is not None and c['distance_cosne_km'] <= 5 and c['rang'] != 59) or c['rang'] in LOCAL_COSNE or c['rang'] in (59, 88)
    if c['rang'] in NOMS_COURTS: c['nom_court'] = NOMS_COURTS[c['rang']]
# formulations non vérifiées sur les établissements (on ne sait pas encore lequel est le bar)
TEXT_FIXES = [(49, "à quelques minutes à pied", "à Cosne même"), (97, "à quelques minutes du bar", "à Cosne même"), (100, "à deux pas du centre-ville", "à Cosne même")]
byr = {c['rang']: c for c in out}
for r, a, b2 in TEXT_FIXES:
    t = byr[r].get('angle_partenariat') or ''
    assert a in t, (r, a)
    byr[r]['angle_partenariat'] = t.replace(a, b2)
ANGLE_OVERRIDES = {
  2: "Siège de Garchizy (100-199 salariés) à ≈48 km : repas d'affaires ponctuels pour des visiteurs venant de Paris par l'A77 (qui passe à Cosne) ; décisions largement prises au niveau du groupe, potentiel limité.",
  12: "Faible : groupe basé à ~95 km ; éventuellement prestataire déchets/recyclage plutôt que client.",
  20: "Repas d'équipe pour ~150 salariés ; éventuellement fournisseur local de mobilier et de sièges plutôt que client.",
  39: "Maison de vins de Pouilly-sur-Loire (Pouilly-Fumé, Sancerre) : partenariat local, achats en circuit court et soirées dégustation co-organisées.",
  45: "Potentiel faible ; éventuellement prestataire de collecte et de recyclage des déchets plutôt que client.",
  59: "Grossiste en boissons avec un dépôt à Cosne : partenaire local pour l'approvisionnement, le prêt de matériel et le soutien aux soirées et événements.",
  64: "Entrer dans le club partenaires (sponsoring, visibilité au stade) et organiser des soirées autour des matchs pour fédérer les supporters du nord Nièvre.",
  75: "Partenaire local idéal : repas d'affaires et afterworks pour l'équipe, soirées clients et lancements de modèles, offres croisées pour leurs clients.",
  83: "Repas d'affaires et déjeuners de chantier pour les équipes qui interviennent sur le secteur de Cosne ; potentiel partenaire technique (électricité) plutôt que client.",
  88: "Visibilité locale : l'agence de Cosne (31 rue Saint-Agnan) peut relayer les actions de partenariat ; achat d'espace ou partenariat publicitaire via la régie du groupe, Centre France Publicité (78 avenue Colbert, Nevers – 03 86 59 89 70 – contact.regie@centrefrance.com, selon l'annuaire Cylex).",
  91: "Repas d'affaires et afterworks d'équipe à 25 km ; vitrine possible pour leur savoir-faire bois (parquet, mobilier) dans le cadre d'un partenariat local.",
}
for r, t in ANGLE_OVERRIDES.items():
    byr[r]['angle_partenariat'] = t
# garde-fou : aucune mention des établissements dans les angles
INTERDIT = re.compile(r"vieux relais|\ble m\b|\bdu m\b|\bau m\b|nos établissements|\bbar\b|\brestaurants?\b|chambres|bar-restaurant", re.I)
for c in out:
    assert not INTERDIT.search(c.get('angle_partenariat') or ''), (c['rang'], c.get('angle_partenariat'))
json.dump(out, open('/home/claude/crm/site/companies.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(Counter(c['vague'] for c in out))
for v in (1, 2, 3):
    print(v, [(c['rang'], c.get('nom_commercial') or c['nom'], c.get('distance_cosne_km')) for c in out if c['vague'] == v])
