# -*- coding: utf-8 -*-
"""年次で装飾・設営委託を繰り返す発注者を、隔日で直接監視する。

   分母抽出で「山口14件・京都9件」のように反復が確認された発注者は、
   一覧を回すのではなく個別に追う。公告から締切までが7〜10日しかないため。"""
import re, html, csv, json, subprocess, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from zoneinfo import ZoneInfo

TODAY = datetime.now(ZoneInfo('Asia/Tokyo')).date()
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'

# 中核領域：装飾・設営・ブース・出展・展示会
CORE = re.compile(r'装飾|設営|施工|ブース|パビリオン|小間|出展|展示会|見本市|博覧会|'
                  r'会場構成|什器|物産展|商談会|フェア')
CASE = re.compile(r'委託|業務|プロポーザル|企画競争|企画提案|入札|公募|募集|請負|選定')
DONE = re.compile(r'結果|終了|決定|選定しました|公表')
HUB  = re.compile(r'入札|公募|調達|契約|委託|募集|事業者|お知らせ|新着|情報|プロポーザル')

TARGETS = [
    ('山口県産業技術センター系', 'yipf.or.jp',            14),
    ('公益財団法人京都産業21',   'www.ki21.jp',            9),
    ('公益財団法人大阪産業局',   'www.obda.or.jp',         3),
    ('静岡県産業振興財団',       'www.ric-shizuoka.or.jp',  2),
    ('ひょうご産業活性化センター','web.hyogo-iic.ne.jp',     2),
    ('わかやま産業振興財団',     'yarukiouendan.or.jp',     2),
]

def fetch(u, t=22, tries=2):
    for _ in range(tries):
        try:
            b = subprocess.run(['curl','-sSL','-A',UA,'--max-time',str(t),'--compressed','-k',u],
                               capture_output=True, timeout=t+8).stdout.decode('utf-8','replace')
            if len(b) > 400: return b
        except Exception: pass
    return ''

def anchors(base, s):
    out = []
    for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', s, re.S|re.I):
        t = html.unescape(re.sub(r'<[^>]+>','',m.group(2))); t = re.sub(r'\s+',' ',t).strip()
        if 6 <= len(t) <= 220: out.append((t, urllib.parse.urljoin(base, m.group(1))))
    return out

def work(item):
    name, host, past = item
    hits, seen = [], set()
    top = fetch(f'https://{host}/')
    if not top: return name, past, 'fail', hits
    pages = [f'https://{host}/']
    pages += list(dict.fromkeys([u for t, u in anchors(f'https://{host}/', top)
                                 if HUB.search(t) and host in u]))[:8]
    def scan(u):
        s = fetch(u, 18, 1); got = []
        if not s: return got
        for t, link in anchors(u, s):
            if not (CORE.search(t) and CASE.search(t)): continue
            got.append((t, link, bool(DONE.search(t))))
        return got
    with ThreadPoolExecutor(max_workers=6) as ex:
        for got in ex.map(scan, pages):
            for t, link, done in got:
                k = t[:70]
                if k in seen: continue
                seen.add(k); hits.append((t, link, done))
    return name, past, 'ok', hits

with ThreadPoolExecutor(max_workers=6) as ex:
    res = list(ex.map(work, TARGETS))

rows = []
print(f'基準日 {TODAY}\n')
for name, past, st, hits in res:
    live = [h for h in hits if not h[2]]
    print(f'■ {name}（過年度{past}件）: {st} — 現在の掲載 {len(hits)}件 うち募集中とみられる {len(live)}件')
    for t, link, done in hits[:12]:
        print(f'   {"済" if done else "●"} {t[:74]}')
        rows.append({'発注者': name, '案件名': t, 'URL': link, '状態': '結果・終了' if done else '募集中の可能性'})
    print()
with open('data/repeaters_20260828.csv','w',newline='') as f:
    w = csv.DictWriter(f, ['発注者','案件名','URL','状態']); w.writeheader(); w.writerows(rows)
print(f'合計 {len(rows)}件')
