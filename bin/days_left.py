#!/usr/bin/env python3
"""台帳の締切から残り時間を実時刻ベースで計算する。

使い方: python3 bin/days_left.py [--update]
  --update を付けると data/ledger.csv の「状態」列の締切超過を自動更新する。

**締切は「日」ではなく「日時」である。**2026-09-03 22時、当日16時に受付を
終えた案件をこのスクリプトが【本日】と表示していた。台帳の `締切時刻` 列を読み、
空のときは 17:00（公的機関の必着の目安）を当てて、推定であることを明示する。
"""
import csv
import re
import sys
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

NOW = datetime.now(ZoneInfo('Asia/Tokyo')).replace(tzinfo=None)
DEFAULT_CLOSE = time(17, 0)
P = 'data/ledger.csv'
rows = list(csv.DictReader(open(P, encoding='utf-8')))
hdr = list(rows[0].keys()) if rows else []

live, past, unknown = [], [], 0
for r in rows:
    m = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})', (r.get('締切') or '').strip())
    if not m:
        unknown += 1
        continue
    hm = re.fullmatch(r'(\d{1,2}):(\d{2})', (r.get('締切時刻') or '').strip())
    exact = bool(hm)
    at = datetime(int(m[1]), int(m[2]), int(m[3]),
                  int(hm[1]) if hm else DEFAULT_CLOSE.hour,
                  int(hm[2]) if hm else DEFAULT_CLOSE.minute)
    (live if at > NOW else past).append((at, exact, r))
live.sort(key=lambda x: x[0])

print('基準日時: %s JST（実時刻から取得）' % NOW.strftime('%Y-%m-%d %H:%M'))
print('受付中 %d件 / 受付終了 %d件 / 日付不明 %d件\n' % (len(live), len(past), unknown))
for at, exact, r in live:
    d = at - NOW
    if d < timedelta(hours=48):
        left = '残%3d時間' % (d.days * 24 + d.seconds // 3600)
        mark = '【至急】'
    else:
        left = '残%3d日  ' % d.days
        mark = '【至急】' if d.days <= 7 else ('【要着手】' if d.days <= 21 else '        ')
    print('%s %s %s%s [%2s] %s / %s'
          % (mark, left, at.strftime('%Y-%m-%d %H:%M'), '' if exact else '?',
             r.get('格付', '-'), r.get('案件名', '')[:46], r.get('発注機関', '')[:18]))

miss = [r for at, e, r in live if not e]
if miss:
    print('\n**締切時刻が未確認のものが %d件ある。「?」を付けた行は17時とみなして'
          '計算しており、実際にはもっと早く閉まる。**' % len(miss))

if '--update' in sys.argv:
    ch = 0
    for at, exact, r in past:
        st = r.get('状態', '')
        if not any(k in st for k in ('締切超過', '今回不可', '営業機会', '終了', '対象外')):
            r['状態'] = '締切超過（旧: %s）' % st
            ch += 1
    if ch:
        with open(P, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=hdr, lineterminator='\n')
            w.writeheader()
            w.writerows(rows)
        print('\n状態を更新: %d件を「締切超過」へ' % ch)
    else:
        print('\n状態の更新: なし')
