"""Lit une page web et en affiche le texte visible (et les liens utiles), pour les recherches de décideurs.
Usage : python3 -I scratch/page.py <url> [nombre max de caractères, défaut 6000]
Identifiant normal (pas de déguisement en navigateur) ; un site qui refuse (403, 429, captcha) est laissé de côté."""
import sys, re, html, urllib.request, urllib.error
from urllib.parse import urljoin

url = sys.argv[1]
maxc = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
try:
    r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'CRM-Nievre/1.0 (recherche de contacts professionnels publiés)'}), timeout=25)
    brut = r.read(3_000_000)
    enc = r.headers.get_content_charset() or 'utf-8'
    page = brut.decode(enc, 'replace')
except urllib.error.HTTPError as e:
    sys.exit(f'REFUS {e.code} : site laissé de côté')
except Exception as e:
    sys.exit(f'ÉCHEC {type(e).__name__} : {e}')
titre = re.search(r'<title[^>]*>(.*?)</title>', page, re.S | re.I)
liens = []
for href, txt in re.findall(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', page, re.S | re.I):
    t = html.unescape(re.sub(r'<[^>]+>', ' ', txt)).strip()
    if re.search(r'équipe|equipe|team|qui sommes|about|propos|contact|mentions|légal|legal|recrut|emploi|carri|organigramme|direction|société|societe|groupe', t + ' ' + href, re.I):
        liens.append((t[:60], urljoin(url, href)))
corps = re.sub(r'(?is)<(script|style|noscript|svg)\b.*?</\1>', ' ', page)
corps = re.sub(r'(?i)<br\s*/?>|</(p|div|li|h\d|tr|td|section)>', '\n', corps)
texte = html.unescape(re.sub(r'<[^>]+>', ' ', corps))
texte = '\n'.join(l for l in (re.sub(r'[ \t\xa0]+', ' ', x).strip() for x in texte.split('\n')) if l)
print('TITRE :', html.unescape(titre.group(1).strip()) if titre else '-', '| URL finale :', r.geturl())
print(texte[:maxc])
if liens:
    print('\nLIENS UTILES :')
    for t, h in list(dict.fromkeys(liens))[:25]: print(' -', t, '→', h)
