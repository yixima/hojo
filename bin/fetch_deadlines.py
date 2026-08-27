# -*- coding: utf-8 -*-
"""S/A案件の詳細ページを取得し、締切日と募集状態を推定する。"""
import csv, re, subprocess, json, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from zoneinfo import ZoneInfo
from datetime import datetime

TODAY = datetime.now(ZoneInfo('Asia/Tokyo')).date()   # CLAUDE.md: 日付は実時刻から
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

rows = [r for r in csv.DictReader(open('data/denominator_ranked_20260827.csv'))
        if r['適合度'] in ('S', 'A')]

CLOSED = re.compile(r'結果|終了|決定しました|選定|公表|審査結果')
# 令和8年9月15日 / 2026年9月15日 / 2026/9/15 / 9月15日
D1 = re.compile(r'令和\s*([0-9０-９元]+)\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日')
D2 = re.compile(r'(20[0-9０-９]{2})\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日')
D3 = re.compile(r'(20\d{2})[/\-\.](\d{1,2})[/\-\.](\d{1,2})')
# 締切を示す語の近傍だけを見る
NEAR = re.compile(r'(締切|締め切り|提出期限|申込期限|応募期限|受付[期終]|提出期間|'
                  r'参加申[込出]|質問[のを]?受付|申請期限|期限)')

def z2h(s): return s.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

def parse_dates(text):
    out = []
    for m in D1.finditer(text):
        y = m.group(1); y = 1 if y == '元' else int(z2h(y))
        try: out.append((m.start(), date(2018 + y, int(z2h(m.group(2))), int(z2h(m.group(3))))))
        except ValueError: pass
    for r in (D2, D3):
        for m in r.finditer(text):
            try: out.append((m.start(), date(int(z2h(m.group(1))), int(z2h(m.group(2))), int(z2h(m.group(3))))))
            except ValueError: pass
    return out

def work(r):
    res = dict(r); res['締切'] = ''; res['募集状態'] = ''
    try:
        html = subprocess.run(
            ['curl', '-sSL', '-A', UA, '--http1.1', '--max-time', '25', '--compressed', r['URL']],
            capture_output=True, timeout=40).stdout.decode('utf-8', 'ignore')
    except Exception:
        html = ''
    if not html:
        res['募集状態'] = '取得不可'; return res
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    cands = []
    for pos, d in parse_dates(text):
        if not (TODAY.year - 3 <= d.year <= TODAY.year + 3): continue
        win = text[max(0, pos - 60):pos + 20]
        if NEAR.search(win): cands.append(d)
    future = sorted(d for d in cands if d >= TODAY)
    if future:
        res['締切'] = future[0].isoformat(); res['募集状態'] = '募集中'
    elif CLOSED.search(r['案件名']):
        res['募集状態'] = '過年度（次回予測用）'
        past = sorted(cands)
        if past: res['締切'] = past[-1].isoformat()
    elif cands:
        res['締切'] = max(cands).isoformat(); res['募集状態'] = '締切超過'
    else:
        res['募集状態'] = '締切不明'
    return res

with ThreadPoolExecutor(max_workers=14) as ex:
    done = list(ex.map(work, rows))

cols = list(rows[0].keys()) + ['締切', '募集状態']
with open('data/denominator_SA_detail_20260827.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(done)

from collections import Counter
print('基準日', TODAY)
print(Counter(d['募集状態'] for d in done).most_common())
for d in sorted([x for x in done if x['募集状態'] == '募集中'], key=lambda x: x['締切']):
    print(f"  {d['締切']}  [{d['適合度']}] {d['組織']} {d['案件名'][:56]}")
