"""Met en page la note docs/hermes-vocalcom.md en docs/hermes.html (même identité visuelle que le CRM).
Nécessite le module Python « markdown » (pip install markdown==3.7)."""
import html, os, re, sys
import markdown

ROOT = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(ROOT, 'hermes-vocalcom.md'), encoding='utf-8').read()

# en-tête : titre et chapeau en italique, remplacés par le bandeau de la page
src = re.sub(r'\A# .*\n+', '', src)
chapeau = re.match(r'\*(.+?)\*\n', src, re.S)
src = src[chapeau.end():] if chapeau else src

body = markdown.markdown(src, extensions=['tables', 'sane_lists'])

# renvois aux sources : [12] -> petite pastille cliquable
body = re.sub(r'<a href="([^"]+)">\[(\d+)\]</a>', r'<a class="ref" href="\1" target="_blank" rel="noopener" title="Source \2">\2</a>', body)
# autres liens : nouvel onglet
body = re.sub(r'<a href="(https?://[^"]+)">', r'<a href="\1" target="_blank" rel="noopener">', body)
# mentions « (non confirmé …) » : étiquette
body = re.sub(r'<em>\((non confirmé|non recoupé|source commerciale, non recoupée|discours commercial, non recoupé|source éditeur[^)]*|date non confirmée|prix non confirmé|non confirmé[^)]*)\)</em>',
              lambda m: f'<span class="nc">{m.group(1)}</span>', body)
# tableaux défilants sur téléphone
body = body.replace('<table>', '<div class="tbl"><table>').replace('</table>', '</table></div>')

# découpage en sections (h2) avec ancres et sommaire
parts = re.split(r'(?=<h2>)', body)
intro, sections, toc = parts[0], [], []
for i, p in enumerate(parts[1:], 1):
    m = re.match(r'<h2>(.*?)</h2>', p)
    titre = re.sub(r'<[^>]+>', '', m.group(1))
    court = re.sub(r'^\d+\.\s*', '', titre)
    ident = 's%d' % i
    toc.append(f'<li><a href="#{ident}">{html.escape(court)}</a></li>')
    cls = 'sec brief' if i == 1 else ('sec sources' if court.startswith('Sources') else 'sec')
    p = re.sub(r'^<h2>(.*?)</h2>', lambda mm: f'<h2><span class="num">{i}</span>{html.escape(court)}</h2>', p)
    sections.append(f'<section class="{cls}" id="{ident}">{p}</section>')

PAGE = """<title>Hermès, utile pour notre prospection ?</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600..800&family=Figtree:wght@400;500;600;700&display=swap">
<style>
/* Mise en page : bandeau du CRM (même palette et mêmes polices), verdict en tête,
   sommaire collant à gauche sur grand écran, texte de lecture à droite, sources en petit. */
:root{
  --bg:#F7F1EA; --wash:#EFE3D4; --surface:#FFFCF8; --sunk:#F1E9DE; --line:#E5D9C9; --line-2:#EEE5D9;
  --ink:#2B211A; --muted:#6C5D50; --faint:#9E8D7D;
  --accent:#7B2D3A; --accent-ink:#FFF8F2; --accent-soft:#F3E0E1;
  --v2:#5E7A34; --v2-soft:#E7EDD8; --warm:#9A6408; --warm-soft:#F6EACD;
  --shadow:0 1px 2px rgba(70,45,20,.06),0 8px 24px rgba(70,45,20,.07);
  --font-display:"Bricolage Grotesque","Trebuchet MS",system-ui,sans-serif;
  --font-body:"Figtree",system-ui,-apple-system,"Segoe UI",sans-serif;
  --r:18px; --r-sm:11px;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#1B1612; --wash:#261D17; --surface:#241D18; --sunk:#2D251F; --line:#3A3029; --line-2:#312821;
  --ink:#F2E9DE; --muted:#C3B4A4; --faint:#8F8072;
  --accent:#E6A3AE; --accent-ink:#2A1015; --accent-soft:#46262D;
  --v2:#AAC37B; --v2-soft:#2D3620; --warm:#E8B85A; --warm-soft:#3F3117;
  --shadow:0 1px 2px rgba(0,0,0,.35),0 10px 26px rgba(0,0,0,.3);
  color-scheme:dark;
}}
:root[data-theme="dark"]{
  --bg:#1B1612; --wash:#261D17; --surface:#241D18; --sunk:#2D251F; --line:#3A3029; --line-2:#312821;
  --ink:#F2E9DE; --muted:#C3B4A4; --faint:#8F8072;
  --accent:#E6A3AE; --accent-ink:#2A1015; --accent-soft:#46262D;
  --v2:#AAC37B; --v2-soft:#2D3620; --warm:#E8B85A; --warm-soft:#3F3117;
  --shadow:0 1px 2px rgba(0,0,0,.35),0 10px 26px rgba(0,0,0,.3);
  color-scheme:dark;
}
*{box-sizing:border-box}
html{background:var(--bg)}
body{background:var(--bg);color:var(--ink);font-family:var(--font-body);font-size:15.5px;line-height:1.6;margin:0}
a{color:var(--accent);text-underline-offset:2px;overflow-wrap:anywhere}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.gutter{max-width:1180px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.band{background:linear-gradient(to bottom,var(--wash),var(--bg) 90%);border-bottom:1px solid var(--line)}
.band .gutter{padding-block:34px 30px;display:flex;flex-direction:column;gap:14px}
.eyebrow{font-size:13.5px;font-weight:600;color:var(--v2)}
h1{font-family:var(--font-display);font-weight:800;font-size:clamp(32px,4.6vw,50px);line-height:1.04;letter-spacing:-.025em;margin:0;text-wrap:balance;max-width:20ch}
.lead{margin:0;color:var(--muted);max-width:68ch}
.verdicts{display:flex;flex-wrap:wrap;gap:8px;margin-top:4px}
.chip{display:inline-flex;align-items:center;gap:8px;font-size:13.5px;font-weight:600;padding:7px 14px;border-radius:999px;background:var(--surface);border:1px solid var(--line);box-shadow:var(--shadow)}
.chip b{color:var(--accent)}
.layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:40px;padding-block:30px 72px;align-items:start}
@media (max-width:900px){.layout{grid-template-columns:minmax(0,1fr);gap:18px}}
nav.toc{position:sticky;top:calc(env(safe-area-inset-top,0px) + 18px)}
nav.toc b{display:block;font-size:12.5px;color:var(--muted);font-weight:700;margin-bottom:8px;letter-spacing:.02em}
nav.toc ol{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:2px;counter-reset:t}
nav.toc li{counter-increment:t}
nav.toc a{display:flex;gap:10px;padding:6px 10px;border-radius:var(--r-sm);color:var(--ink);text-decoration:none;font-size:14px;line-height:1.35}
nav.toc a::before{content:counter(t);color:var(--faint);font-variant-numeric:tabular-nums;min-width:1.2em}
nav.toc a:hover{background:var(--sunk);color:var(--accent)}
@media (max-width:900px){nav.toc{position:static;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:14px}}
main{min-width:0;display:flex;flex-direction:column;gap:30px}
.sec{min-width:0;scroll-margin-top:16px}
.sec h2{font-family:var(--font-display);font-weight:800;font-size:clamp(24px,2.6vw,30px);line-height:1.12;letter-spacing:-.02em;margin:0 0 12px;display:flex;align-items:baseline;gap:12px;text-wrap:balance}
.sec h2 .num{font-size:15px;font-weight:700;color:var(--accent-ink);background:var(--accent);border-radius:999px;min-width:28px;height:28px;display:inline-grid;place-items:center;flex:none;transform:translateY(-3px)}
.sec h3{font-family:var(--font-display);font-weight:700;font-size:19px;letter-spacing:-.01em;margin:22px 0 8px}
.sec p,.sec li{max-width:70ch}
.sec p{margin:0 0 12px}
.sec ul,.sec ol{margin:0 0 14px;padding-left:22px;display:flex;flex-direction:column;gap:6px}
.sec strong{font-weight:700}
.brief{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);padding:22px 24px}
.brief ul{gap:10px}
.ref{display:inline-block;font-size:11px;font-weight:700;line-height:1;padding:3px 5px;margin-left:2px;border-radius:6px;background:var(--sunk);color:var(--muted);text-decoration:none;vertical-align:2px;font-variant-numeric:tabular-nums}
.ref:hover{background:var(--accent-soft);color:var(--accent)}
.nc{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:999px;background:var(--warm-soft);color:var(--warm);font-style:normal;white-space:nowrap}
.tbl{overflow-x:auto;margin:6px 0 16px;border:1px solid var(--line);border-radius:var(--r-sm);background:var(--surface)}
table{border-collapse:collapse;width:100%;min-width:640px;font-size:14px}
th,td{text-align:left;vertical-align:top;padding:10px 12px;border-bottom:1px solid var(--line-2)}
th{background:var(--sunk);font-size:13px;color:var(--muted);font-weight:700}
tr:last-child td{border-bottom:0}
td code,p code,li code{font-size:13px;background:var(--sunk);padding:1px 6px;border-radius:6px;overflow-wrap:anywhere}
.sources ol{font-size:13px;color:var(--muted);gap:4px}
.sources li{max-width:none}
.foot{font-size:13px;color:var(--muted);border-top:1px solid var(--line);padding-top:14px}
</style>

<header class="band"><div class="gutter">
  <span class="eyebrow">Note du 22/10/2026 pour les associés · CRM Entreprises Nièvre</span>
  <h1>Hermès, utile pour notre prospection ?</h1>
  <p class="lead">__CHAPEAU__</p>
  <div class="verdicts">
    <span class="chip"><b>Hermès :</b> non, surdimensionné pour 2 à 4 appelants</span>
    <span class="chip"><b>Prix :</b> sur devis, 55 à 190 $ par poste estimés</span>
    <span class="chip"><b>D'abord :</b> notre CRM et nos téléphones</span>
  </div>
</div></header>

<div class="gutter layout">
  <nav class="toc" aria-label="Sommaire"><b>Sommaire</b><ol>__TOC__</ol></nav>
  <main>
    <div class="sec intro">__INTRO__</div>
    __SECTIONS__
    <p class="foot">Note établie à partir de résultats de recherche web contre-vérifiés, sans contact avec l'éditeur. Tout montant, toute règle et tout format d'import sont à confirmer avant engagement.</p>
  </main>
</div>
"""
chap = markdown.markdown(chapeau.group(1)).removeprefix('<p>').removesuffix('</p>') if chapeau else ''
chap = re.sub(r'^Note du [^.]+\.\s*', '', chap)   # déjà dans le surtitre
out = (PAGE.replace('__CHAPEAU__', chap).replace('__TOC__', ''.join(toc))
           .replace('__INTRO__', intro).replace('__SECTIONS__', '\n'.join(sections)))
INTERDIT = re.compile(r"vieux relais|\ble m\b", re.I)
assert not INTERDIT.search(out), 'mention interdite'
open(os.path.join(ROOT, 'hermes.html'), 'w', encoding='utf-8').write(out)
print('docs/hermes.html', len(out), 'octets,', len(sections), 'sections,', body.count('class="ref"'), 'renvois,', body.count('class="nc"'), 'mentions non confirmé')
