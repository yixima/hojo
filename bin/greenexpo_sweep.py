# -*- coding: utf-8 -*-
"""GREEN×EXPO 2027（2027年国際園芸博覧会・横浜）の各県出展業務を全県で探す。
   会期2027年3〜9月。各県が前年度中に個別発注するため、毎月これを回す。"""
import re, html, json, time, subprocess, csv, urllib.parse
from concurrent.futures import ThreadPoolExecutor

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
# 表記ゆれが多い：「2027年国際園芸博覧会」「GREEN×EXPO 2027」「花博」「園芸博」
EXPO = re.compile(r'国際園芸博覧会|GREEN\s*[×xX]\s*EXPO|ｸﾞﾘｰﾝ|園芸博|花博|横浜花博')
# 発注案件であること（出展者募集・来場案内は除く）
CASE = re.compile(r'委託|業務|プロポーザル|企画提案|企画競争|企画競技|入札|公募|請負|事業者[のをに]?(募集|選定)')
SKIP = re.compile(r'入場券|チケット|来場|ボランティア|出展者募集|参加者募集|開催概要|とは')
HUB  = re.compile(r'入札|公募|調達|プロポーザル|契約|委託|募集|事業者|企画競争|企画提案|お知らせ|新着')

def fetch(u, t=22, tries=3):
    for _i in range(tries):
        try:
            r = subprocess.run(['curl', '-sSL', '-A', UA, '--max-time', str(t), '--compressed', '-k', u],
                               capture_output=True, timeout=t + 8)
            b = r.stdout.decode('utf-8', 'replace')
            if len(b) > 500: return b
        except Exception: pass
        if _i < tries - 1: time.sleep(2 ** _i)
    return ''

def anchors(base, s):
    out = []
    for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', s, re.S | re.I):
        t = html.unescape(re.sub(r'<[^>]+>', '', m.group(2)))
        t = re.sub(r'\s+', ' ', t).strip()
        if 4 <= len(t) <= 220: out.append((t, urllib.parse.urljoin(base, m.group(1))))
    return out

def work(item):
    pref, host = item
    hits, seen = [], set()
    # 各県のサイト内検索を叩く。パスは県ごとに違うので複数試す。
    queries = ['国際園芸博覧会', 'GREEN%C3%97EXPO']
    urls = []
    for q in queries:
        urls += [f'https://{host}/site/search.html?q={q}',
                 f'https://{host}/search.html?q={q}',
                 f'https://{host}/cgi-bin/search.cgi?q={q}']
    urls.append(f'https://{host}/')
    for u in urls:
        s = fetch(u)
        if not s: continue
        for t, link in anchors(u, s):
            if not EXPO.search(t): continue
            if SKIP.search(t) or not CASE.search(t): continue
            k = t[:60]
            if k in seen: continue
            seen.add(k); hits.append((pref, t, link))
    # トップから入札・公募ハブへ1段だけ降りる
    top = fetch(f'https://{host}/')
    if top:
        for t, link in anchors(f'https://{host}/', top):
            if not HUB.search(t) or host not in link: continue
            hs = fetch(link, 18, 1)
            if not hs: continue
            for t2, l2 in anchors(link, hs):
                if not EXPO.search(t2): continue
                if SKIP.search(t2) or not CASE.search(t2): continue
                k = t2[:60]
                if k in seen: continue
                seen.add(k); hits.append((pref, t2, l2))
    return pref, hits

PREFS = json.load(open('workflow/prefs.json'))
with ThreadPoolExecutor(max_workers=12) as ex:
    res = list(ex.map(work, PREFS.items()))

rows = []
for pref, hits in res:
    if hits: print(f'{pref}: {len(hits)}件', flush=True)
    for h in hits: print('   ', h[1][:76], flush=True)
    rows += hits
with open('data/greenexpo_20260828.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['都道府県', '案件名', 'URL']); w.writerows(rows)
print(f'\n該当 {len(rows)}件 / {sum(1 for _, h in res if h)}県')
