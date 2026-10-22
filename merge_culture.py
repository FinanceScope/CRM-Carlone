import json, os, re

BASE = '/home/claude/crm/culture'
FAM = {
    'Artiste': 'Artistes', "Collectif d'artistes": 'Artistes', "Artisan d'art": 'Artistes',
    "Galerie & lieu d'expo": 'Lieux & institutions', 'Institution culturelle': 'Lieux & institutions', "Atelier & école d'art": 'Lieux & institutions',
    'Événement artistique': 'Réseaux & événements', 'Réseau & financeur': 'Réseaux & événements',
}

def load(name):
    p = os.path.join(BASE, name)
    if not os.path.exists(p):
        print('absent :', name); return None
    return json.load(open(p, encoding='utf-8'))

def clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v

prospects, seen = [], set()
for fname, default_fam in (('assos.json', 'Associations'), ('art.json', None), ('art2.json', None)):
    data = load(fname) or []
    for o in data:
        typ = clean(o.get('type')) or ''
        fam = default_fam or FAM.get(typ, 'Réseaux & événements')
        nom = clean(o.get('nom'))
        if not nom: continue
        k = re.sub(r'\W+', '', nom.lower())
        if k in seen:
            print('doublon ignoré :', nom); continue
        seen.add(k)
        d = o.get('distance_cosne_km')
        try: d = int(round(float(d))) if d is not None else None
        except Exception: d = None
        ville = clean(o.get('ville')) or ''
        if 'non précisée' in ville: d = None   # distance = lieu d'expo, pas l'atelier
        if len(ville) > 30 and ' (' in ville: ville = ville.split(' (')[0]
        ct = {kk: clean(vv) for kk, vv in (o.get('contact') or {}).items()}
        rp = o.get('responsable')
        if not (isinstance(rp, dict) and clean(rp.get('nom'))): rp = None
        prio = o.get('priorite') if o.get('priorite') in ('Haute', 'Moyenne', 'Basse') else None
        prospects.append({
            'id': 'c-' + str(o.get('id') or len(prospects)),
            'nom': nom, 'famille': fam, 'type': typ or None,
            'discipline': clean(o.get('discipline')), 'ville': ville or None, 'code_postal': clean(o.get('code_postal')),
            'distance_cosne_km': d, 'description': clean(o.get('description')),
            'evenements_existants': clean(o.get('evenements_existants')), 'idee_evenement': clean(o.get('idee_evenement')),
            'contact': ct, 'responsable': rp, 'priorite': prio, 'sources': [s for s in (o.get('sources') or []) if isinstance(s, str)],
        })

# doublon : le club photo de Cosne apparaît dans les deux recherches (a03 et b10) -> fusion dans a03
byid = {p['id']: p for p in prospects}
if 'c-a03' in byid and 'c-b10' in byid:
    a, b = byid['c-a03'], byid['c-b10']
    for k, v in b['contact'].items():
        if v and not a['contact'].get(k): a['contact'][k] = v
    for k in ('evenements_existants', 'idee_evenement', 'description'):
        if not a.get(k) and b.get(k): a[k] = b[k]
    a['sources'] = list(dict.fromkeys(a['sources'] + b['sources']))
    prospects.remove(b)
    print('fusion : c-b10 -> c-a03')

# contacts complétés pour les associations (2e passe)
byid = {p['id']: p for p in prospects}
for u in (load('assos_contacts.json') or []):
    p = byid.get('c-' + str(u.get('id')))
    if not p: continue
    for k, v in (u.get('contact') or {}).items():
        v = clean(v)
        if v and not p['contact'].get(k): p['contact'][k] = v
    rp = u.get('responsable')
    if isinstance(rp, dict) and clean(rp.get('nom')) and not p.get('responsable'): p['responsable'] = rp
    ar = clean(u.get('activite_recente'))
    if ar: p['activite_recente'] = ar
    if u.get('statut') == 'probablement inactive':
        p['a_confirmer'] = True
        if p.get('priorite') == 'Haute': p['priorite'] = 'Moyenne'
    p['sources'] = list(dict.fromkeys(p['sources'] + [x for x in (u.get('sources') or []) if isinstance(x, str)]))

# associations sans trace d'activité depuis leur subvention municipale de 2023 (2e passe)
for pid in ('c-a02', 'c-a08', 'c-a22', 'c-a23', 'c-a24'):
    p = byid.get(pid)
    if p:
        p['a_confirmer'] = True
        if p.get('priorite') == 'Haute': p['priorite'] = 'Moyenne'

playbook = load('playbook.json')
out = {'prospects': prospects, 'playbook': playbook}
json.dump(out, open('/home/claude/crm/site/culture.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

from collections import Counter
print('prospects', len(prospects), Counter(p['famille'] for p in prospects), Counter(p['priorite'] for p in prospects))
print('avec tel', sum(1 for p in prospects if p['contact'].get('telephone')), '| email', sum(1 for p in prospects if p['contact'].get('email')),
      '| site', sum(1 for p in prospects if p['contact'].get('site')), '| fb/ig', sum(1 for p in prospects if p['contact'].get('facebook') or p['contact'].get('instagram')))
if playbook:
    print('playbook', {k: len(v) if isinstance(v, list) else type(v).__name__ for k, v in playbook.items()})
