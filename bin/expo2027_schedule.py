# -*- coding: utf-8 -*-
"""協会案件のスケジュール表を正確に読む。
   本文の「２．参加に係る手続きの提出期限」は提案書の締切と混同されており
   当てにならない。dl.c-listTable3 の実スケジュールを読むこと。"""
import re, html, csv, subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from zoneinfo import ZoneInfo

T = datetime.now(ZoneInfo('Asia/Tokyo')).date()
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

def z2h(s): return s.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

def parse_date(s):
    m = re.search(r'(20[0-9０-９]{2})\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日', s)
    if not m: return None
    try: return date(int(z2h(m.group(1))), int(z2h(m.group(2))), int(z2h(m.group(3))))
    except ValueError: return None

def work(r):
    try:
        h = subprocess.run(['curl','-sSL','-A',UA,'--max-time','25','--compressed',r['URL']],
                           capture_output=True, timeout=40).stdout.decode('utf-8','ignore')
    except Exception:
        return r, []
    sched = []
    for g in re.findall(r'<div class="c-listTable__group">(.*?)</div>', h, re.S):
        dt = re.search(r'<dt>(.*?)</dt>', g, re.S)
        dds = [re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',d))).strip()
               for d in re.findall(r'<dd>(.*?)</dd>', g, re.S)]
        dds = [d for d in dds if d]
        if not dt or not dds: continue
        when = re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',dt.group(1)))).strip()
        sched.append((when, dds[-1], (dds[0] if len(dds) > 1 else '')))
    return r, sched

rows = list(csv.DictReader(open('data/expo2027_20260828.csv')))
DROP = re.compile(r'入札結果|開札結果|決定\]')
tgt = [r for r in rows if not DROP.search(r['案件名'])]
with ThreadPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(work, tgt))

out = []
print(f'基準日 {T}\n')
for r, sched in res:
    if not sched: continue
    name = re.sub(r'^[0-9.]+(委託等|工事)\s*', '', r['案件名'])
    # 最初に来る「締切」を応募の可否を決める期限とみなす
    gates = [(parse_date(w), lbl, tm) for w, lbl, tm in sched if '締切' in lbl or '期限' in lbl]
    gates = [(d, l, t) for d, l, t in gates if d]
    first = min(gates, key=lambda x: x[0]) if gates else None
    if not first: continue
    d, lbl, tm = first
    st = '応募可' if d >= T else '応募不可（期限超過）'
    print(f"{st:14} {d} {lbl}{('・'+tm) if tm else ''}  {name[:58]}")
    for w, l, t in sched[:8]:
        print(f"                 {w:22} {l}{('・'+t) if t else ''}")
    print()
    out.append({'案件名': name, '最初の関門': lbl, '期限': d.isoformat(), '時刻': tm,
                '可否': st, 'URL': r['URL']})
with open('data/expo2027_schedule_20260828.csv','w',newline='') as f:
    w = csv.DictWriter(f, ['案件名','最初の関門','期限','時刻','可否','URL'])
    w.writeheader(); w.writerows(out)
