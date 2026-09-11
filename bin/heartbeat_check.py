#!/usr/bin/env python3
"""定期巡回の心拍検査。ボード（reports/dashboard.html）の生成時刻と、台帳の最終コミット時刻を実測し、
しきい値より古ければ非ゼロで終了する。定期処理が「静かに止まる」ことを機械で検出するための道具。

使い方:
  python3 bin/heartbeat_check.py            # 既定: ボード 26時間・台帳 8日
  python3 bin/heartbeat_check.py --board-hours 26 --ledger-days 8
出力は人が読む1〜3行。判定は終了コード（0=正常、2=停止の疑い）。
"""
import re, sys, subprocess, datetime, argparse, zoneinfo, pathlib
JST = zoneinfo.ZoneInfo('Asia/Tokyo')
ap = argparse.ArgumentParser()
ap.add_argument('--board-hours', type=float, default=26)
ap.add_argument('--ledger-days', type=float, default=8)
a = ap.parse_args()
now = datetime.datetime.now(JST)
root = pathlib.Path(__file__).resolve().parent.parent
bad = []
# 1. ボードの生成時刻（HTML内の「生成<b>MM.DD HH:MM」）
html = (root / 'reports/dashboard.html').read_text(encoding='utf-8', errors='replace')
m = re.search(r'生成<b>(\d\d)\.(\d\d) (\d\d):(\d\d)', html)
if not m:
    bad.append('ボードに生成時刻が無い'); board_age = None
else:
    mo, d, h, mi = map(int, m.groups())
    y = now.year if (mo, d) <= (now.month, now.day) else now.year - 1
    gen = datetime.datetime(y, mo, d, h, mi, tzinfo=JST)
    board_age = (now - gen).total_seconds() / 3600
    print(f'ボード生成: {gen:%Y-%m-%d %H:%M} JST（{board_age:.1f} 時間前）')
    if board_age > a.board_hours:
        bad.append(f'ボードが {board_age:.0f} 時間更新されていない（しきい値 {a.board_hours:.0f} 時間）')
# 2. 台帳の最終コミット
try:
    ts = subprocess.check_output(['git', 'log', '-1', '--format=%cI', '--', 'data/ledger.csv'], cwd=root, text=True).strip()
    last = datetime.datetime.fromisoformat(ts).astimezone(JST)
    age_d = (now - last).total_seconds() / 86400
    print(f'台帳の最終コミット: {last:%Y-%m-%d %H:%M} JST（{age_d:.1f} 日前）')
    if age_d > a.ledger_days:
        bad.append(f'台帳が {age_d:.0f} 日更新されていない（しきい値 {a.ledger_days:.0f} 日）')
except Exception as e:
    bad.append(f'台帳のコミット時刻を取れない: {e}')
print(f'基準日時: {now:%Y-%m-%d %H:%M} JST')
if bad:
    print('【停止の疑い】' + '／'.join(bad)); sys.exit(2)
print('正常')
