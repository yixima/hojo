#!/usr/bin/env python3
"""台帳の締切から残日数を実時刻ベースで計算する。
使い方: python3 bin/days_left.py [--update]
  --update を付けると data/ledger.csv の「状態」列の締切超過を自動更新する。
日付は datetime.now() から取得するため、ハードコードによるズレが起きない。"""
import csv,sys,re
from datetime import datetime
from zoneinfo import ZoneInfo
TODAY=datetime.now(ZoneInfo('Asia/Tokyo')).date()
P='data/ledger.csv'
rows=list(csv.DictReader(open(P)))
hdr=list(rows[0].keys()) if rows else []
live=[];past=[];unknown=0
for r in rows:
    d=(r.get('締切') or '').strip()
    m=re.match(r'^(\d{4})-(\d{2})-(\d{2})$',d)
    if not m: unknown+=1; continue
    from datetime import date
    dt=date(int(m.group(1)),int(m.group(2)),int(m.group(3)))
    n=(dt-TODAY).days
    (live if n>=0 else past).append((n,dt,r))
live.sort(key=lambda x:x[0])
print(f"基準日: {TODAY}（実時刻から取得）")
print(f"締切前 {len(live)}件 / 締切超過 {len(past)}件 / 日付不明 {unknown}件\n")
for n,dt,r in live:
    mark='【本日】' if n==0 else ('【至急】' if n<=7 else ('【要着手】' if n<=21 else '      '))
    print(f"{mark} 残{n:>3}日 {dt} [{r.get('格付','-'):>2}] {r.get('案件名','')[:50]} / {r.get('発注機関','')[:20]}")
if '--update' in sys.argv:
    ch=0
    for n,dt,r in past:
        st=r.get('状態','')
        if '締切超過' not in st and '今回不可' not in st and '営業機会' not in st and '終了' not in st and '対象外' not in st:
            r['状態']=f"締切超過（旧: {st}）"; ch+=1
    if ch:
        with open(P,'w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=hdr); w.writeheader(); w.writerows(rows)
        print(f"\n状態を更新: {ch}件を「締切超過」へ")
    else: print("\n状態の更新: なし")
