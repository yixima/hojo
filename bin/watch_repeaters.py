# -*- coding: utf-8 -*-
"""年次で装飾・設営委託を繰り返す発注者を、隔日で直接監視する。

   分母抽出で「山口14件・京都9件」のように反復が確認された発注者は、
   一覧を回すのではなく個別に追う。公告から締切までが7〜10日しかないため。"""
import re, html, csv, json, time, subprocess, urllib.parse
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

# 個別ページから参加表明・提案書の期限を読む。
# 一覧のバッジは信用できない（やまぐち産業振興財団は終了表示を出さない）。
GATE = re.compile(r'参加(表明|意向申出|申[込出])[のに]?(受付|提出)?[のを]?(期限|締切)?|'
                  r'提案書[のを]?(提出)?(期限|締切)|申込(期限|締切)|提出期限|必着')
LATER = re.compile(r'提案書|企画提案書')

def z2h(x): return x.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

def page_dates(text):
    """締切語の近傍にある日付を (種別, 日付) で返す"""
    text = re.sub(r'\s+', ' ', text)
    out = []
    pats = [(r'令和\s*([0-9０-９元]+)\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日', True),
            (r'(20[0-9０-９]{2})\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日', False)]
    for pat, wareki in pats:
        for m in re.finditer(pat, text):
            g1 = m.group(1)
            y = (2018 + (1 if g1 == '元' else int(z2h(g1)))) if wareki else int(z2h(g1))
            try: d = date(y, int(z2h(m.group(2))), int(z2h(m.group(3))))
            except ValueError: continue
            win = text[max(0, m.start()-70):m.start()+20]
            if not GATE.search(win): continue
            out.append(('提案書' if LATER.search(win) else '参加表明', d))
    return out

def verdict(url):
    """個別ページを取得し、最も早い関門の日付で募集中かを判定する"""
    h = fetch(url, 20, 1)
    if not h: return '取得不可', None, ''
    t = re.sub(r'<[^>]+>', ' ', h)
    ds = [(k, d) for k, d in page_dates(t) if TODAY.year - 1 <= d.year <= TODAY.year + 2]
    if not ds: return '日付不明', None, ''
    kind, d = min(ds, key=lambda x: x[1])
    return ('募集中' if d >= TODAY else '締切済'), d, kind

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
    # 一覧で拾ったものを個別ページで確定させる
    def resolve(h):
        st, d, kind = verdict(h[1])
        return (h[0], h[1], h[2], st, d, kind)
    with ThreadPoolExecutor(max_workers=6) as ex:
        hits = list(ex.map(resolve, hits))
    return name, past, 'ok', hits

with ThreadPoolExecutor(max_workers=6) as ex:
    res = list(ex.map(work, TARGETS))

rows = []
print(f'基準日 {TODAY}\n')
for name, past, st, hits in res:
    live = [h for h in hits if h[3] == '募集中' and not h[2]]
    print(f'■ {name}（過年度{past}件）: {st} — 掲載 {len(hits)}件 / **募集中 {len(live)}件**')
    for t, link, done, st, d, kind in hits[:14]:
        mark = '●' if st == '募集中' else ('済' if st == '締切済' or done else '？')
        info = f'{d} {kind}' if d else st
        print(f'   {mark} {info:22} {t[:60]}')
        rows.append({'発注者': name, '案件名': t, 'URL': link,
                     '状態': '募集中' if st == '募集中' and not done else ('締切済' if st == '締切済' or done else st),
                     '期限': d.isoformat() if d else '', '関門': kind})
    print()
with open('data/repeaters_20260828.csv','w',newline='') as f:
    w = csv.DictWriter(f, ['発注者','案件名','URL','状態','期限','関門']); w.writeheader(); w.writerows(rows)
print(f'合計 {len(rows)}件')
