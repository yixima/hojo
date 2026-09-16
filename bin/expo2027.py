# -*- coding: utf-8 -*-
"""2027年国際園芸博覧会協会（GREEN×EXPO 2027）の契約情報を巡回する。
   協会そのものが年間を通じて委託・プロポーザルを出す一次発注者。
   各県の出展業務とは別枠で、規模も大きい。"""
import re, html, subprocess, csv, urllib.parse
from concurrent.futures import ThreadPoolExecutor

BASE = 'https://expo2027yokohama.or.jp'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
ENTRIES = [f'{BASE}/contract/', f'{BASE}/contract/services/', f'{BASE}/contract/goods/',
           f'{BASE}/contract/construction/', f'{BASE}/contract/other/']
CASE = re.compile(r'委託|業務|プロポーザル|企画競争|企画提案|入札|公募|請負|調達|選定')

def fetch(u, t=25):
    for _ in range(2):
        try:
            b = subprocess.run(['curl','-sSL','-A',UA,'--max-time',str(t),'--compressed',u],
                               capture_output=True, timeout=t+8).stdout.decode('utf-8','replace')
            if len(b) > 400: return b
        except Exception: pass
    return ''

def anchors(base, s):
    out=[]
    for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', s, re.S|re.I):
        t=html.unescape(re.sub(r'<[^>]+>','',m.group(2))); t=re.sub(r'\s+',' ',t).strip()
        if 6 <= len(t) <= 240: out.append((t, urllib.parse.urljoin(base, m.group(1))))
    return out

seen, rows, level2 = set(), [], []
for u in ENTRIES:
    s = fetch(u)
    if not s: continue
    for t, link in anchors(u, s):
        if CASE.search(t) and '/contract/' in link:
            k = t[:70]
            if k in seen: continue
            seen.add(k); rows.append((t, link))
        elif '/contract/' in link and link not in level2:
            level2.append(link)

# 一覧が分割されている（ページャ・年度別）ため、下位ページも辿る
def deeper(u):
    s = fetch(u, 20); out=[]
    if not s: return out
    for t, link in anchors(u, s):
        if CASE.search(t) and '/contract/' in link: out.append((t, link))
    return out

with ThreadPoolExecutor(max_workers=10) as ex:
    for got in ex.map(deeper, level2[:40]):
        for t, link in got:
            k = t[:70]
            if k in seen: continue
            seen.add(k); rows.append((t, link))

with open('data/expo2027_20260828.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['案件名','URL']); w.writerows(rows)
print(f'2027年国際園芸博覧会協会 契約情報 {len(rows)}件\n')
for t, link in rows: print(' ', t[:96])
