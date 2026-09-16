# -*- coding: utf-8 -*-
"""毎年開催地が持ち回る全国イベントの、主催者・実行委員会の発注を探す。

   これらは開催地が数年前に決まり、実行委員会が開催の1〜2年前から
   会場設営・催事企画・開会式運営・広報の委託を出す。
   「現在募集中」だけを見ていると、その全てを取り逃す。

   県サイトのサイト内検索はパスが県ごとに違い推測が当たらないため、
   検索エンジン（WebSearchで得たURL）と組織サイトのcurl巡回を併用する。
   本スクリプトは後者を担う。前者は runbook 手順2.8 の手順で行う。"""
import re, html, csv, time, subprocess, urllib.parse, yaml
from concurrent.futures import ThreadPoolExecutor

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
CASE = re.compile(r'委託|業務|プロポーザル|企画競争|企画提案|企画競技|入札|公募|請負|事業者[のをに]?(募集|選定)')
SKIP = re.compile(r'入場券|チケット|来場|ボランティア|出演者|参加者募集|作品募集|職員|採用')
HUB  = re.compile(r'入札|公募|調達|プロポーザル|契約|委託|募集|事業者|お知らせ|新着|情報')

def fetch(u, t=22, tries=3):
    for _i in range(tries):
        try:
            b = subprocess.run(['curl','-sSL','-A',UA,'--max-time',str(t),'--compressed','-k',u],
                               capture_output=True, timeout=t+8).stdout.decode('utf-8','replace')
            if len(b) > 400: return b
        except Exception: pass
        if _i < tries - 1: time.sleep(2 ** _i)
    return ''

def anchors(base, s):
    out = []
    for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', s, re.S|re.I):
        t = html.unescape(re.sub(r'<[^>]+>','',m.group(2))); t = re.sub(r'\s+',' ',t).strip()
        if 6 <= len(t) <= 220: out.append((t, urllib.parse.urljoin(base, m.group(1))))
    return out

def work(org):
    name, url = org['name'], org['url']
    host = urllib.parse.urlparse(url).netloc
    rows, seen = [], set()
    top = fetch(url)
    if not top: return name, 'fail', rows
    for t, link in anchors(url, top):
        if SKIP.search(t) or not CASE.search(t): continue
        k = t[:70]
        if k in seen: continue
        seen.add(k); rows.append((name, t, link, 'L1'))
    # 入札・公募ハブへ1段降りる
    hubs = list(dict.fromkeys([l for t, l in anchors(url, top)
                               if HUB.search(t) and host in l]))[:8]
    def deeper(h):
        s = fetch(h, 18, 1); got = []
        if not s: return got
        for t, l in anchors(h, s):
            if SKIP.search(t) or not CASE.search(t): continue
            got.append((name, t, l, 'L2'))
        return got
    with ThreadPoolExecutor(max_workers=6) as ex:
        for got in ex.map(deeper, hubs):
            for r in got:
                k = r[1][:70]
                if k in seen: continue
                seen.add(k); rows.append(r)
    return name, 'ok', rows

src = yaml.safe_load(open('workflow/sources.yaml'))
orgs = src.get('tier_national_events', {}).get('orgs', [])
orgs = [o for o in orgs if o.get('url')]
print(f'巡回対象 {len(orgs)}団体', flush=True)
with ThreadPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(work, orgs))

allr = []
for name, st, rows in res:
    print(f'{name}: {st} {len(rows)}件', flush=True)
    allr += rows
with open('data/national_events_20260828.csv','w',newline='') as f:
    w = csv.writer(f); w.writerow(['団体','案件名','URL','階層']); w.writerows(allr)
print(f'\n合計 {len(allr)}件')
