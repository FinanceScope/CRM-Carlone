"""Usage : python3 api_etat.py (depuis la racine du dépôt ; résultats dans ext/api_etat/). Interroge l'API Recherche d'entreprises pour chaque SIREN de site/companies.json, lentement (1 requête toutes les 5 s),
en sauvegardant au fur et à mesure (reprise possible) ; en cas de coupure, attend de plus en plus longtemps."""
import json,time,urllib.request,urllib.error,os
OUT='ext/api_etat/recherche_entreprises_20261105.json'
c=json.load(open('site/companies.json',encoding='utf-8'))
res=json.load(open(OUT,encoding='utf-8')) if os.path.exists(OUT) else {'date':'2026-11-05','source':'https://recherche-entreprises.api.gouv.fr/search','fiches':{}}
F=res['fiches']
def save(): json.dump(res,open(OUT+'.tmp','w',encoding='utf-8'),ensure_ascii=False); os.replace(OUT+'.tmp',OUT)
attente=60
for o in c:
    s=o['siren']
    if s in F and F[s].get('ok'): continue
    while True:
        try:
            req=urllib.request.Request(f"https://recherche-entreprises.api.gouv.fr/search?q={s}&per_page=5",headers={'User-Agent':'CRM-Nievre/1.0'})
            d=json.load(urllib.request.urlopen(req,timeout=30)); attente=60; break
        except urllib.error.HTTPError as e:
            w=int(e.headers.get('Retry-After') or 5)+1 if e.code==429 else 10
            print('http',e.code,'attente',w,flush=True); time.sleep(w)
        except Exception as e:
            print('coupure',type(e).__name__,'attente',attente,flush=True); time.sleep(attente); attente=min(attente*2,900)
    r=next((x for x in d.get('results',[]) if x.get('siren')==s),None)
    F[s]={'ok':True,'trouve':r is not None,'data':r}; save()
    print('fait',len(F),flush=True)
    time.sleep(5)
print('termine',len(F),sum(1 for v in F.values() if v.get('trouve')))
