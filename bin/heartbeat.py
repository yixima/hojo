# -*- coding: utf-8 -*-
"""**報告が止まったことを、止まっている側が気づけるようにする。**

なぜ要るか
----------
2026-09-09 10:04 から 2026-09-11 15:44 まで、**2日5時間40分にわたり報告が止まった。**
原因は、定期報告を `send_later` の単発予約の**鎖**でつないでいたこと。
鎖は1本つなぎ忘れた瞬間に切れ、**切れたことを誰も検知しない。**
その間に、おまつり歳時記の原本提出（9/9 13時）と、
GREEN×EXPO 学習プログラムの参加意向申出（9/11 17時・上限2,700万円）が動いていた。

対策は2つある。
1. **心拍（cron）**… `trig_013J6yq98fZPqmqdvcfdLmDs` が毎朝08:00 JSTに発火する。
   鎖と違い、繰り返しは自分で維持される
2. **不在の検知（dead man's switch）**… これ。
   **心拍そのものが止まったときに、止まったことが画面に出る。**
   外部の監視サービスは使わない。報告のたびに時刻を刻み、
   ボードの生成時に「前回の報告から何時間空いたか」を計算して出す

**警報は「何かが起きたこと」ではなく「起きるはずのことが起きなかったこと」で鳴る。**
これが監視の世界でいう dead man's switch であり、
「ジョブが落ちた」ではなく「ジョブが来なかった」を捕まえる唯一の型である。

使い方
------
    python3 bin/heartbeat.py --stamp   # 報告した。いまの時刻を刻む
    python3 bin/heartbeat.py --check   # 前回からの空白を表示する（空きすぎなら終了コード1）
"""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEAT = ROOT / 'data' / 'heartbeat.json'

# **この時間を超えて報告が無ければ異常とみなす。**
# 毎朝08:00の心拍に対し、1回飛ばしても36時間以内には次が来る。
LIMIT_HOURS = 36


def now():
    """**日時は必ず bin/today.sh から取る。**推測しない（CLAUDE.md 最重要）。"""
    s = subprocess.run([str(ROOT / 'bin' / 'today.sh')],
                       capture_output=True, text=True, check=True).stdout
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})', s)
    return datetime.datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]))


def load():
    if not BEAT.exists():
        return None
    try:
        d = json.loads(BEAT.read_text(encoding='utf-8'))
        return datetime.datetime.strptime(d['last_report'], '%Y-%m-%d %H:%M')
    except Exception:
        return None


def describe(n=None):
    """画面に出す1行を返す。(本文, 異常か) の組。"""
    n = n or now()
    last = load()
    if last is None:
        return '前回の報告：記録なし', True
    h = (n - last).total_seconds() / 3600
    d, hh = int(h // 24), int(h % 24)
    span = ('%d日%d時間' % (d, hh)) if d else ('%d時間' % hh)
    ok = h <= LIMIT_HOURS
    return ('前回の報告 %s ／ 空白 %s' % (last.strftime('%m-%d %H:%M'), span)), (not ok)


def main():
    n = now()
    if '--stamp' in sys.argv:
        BEAT.parent.mkdir(parents=True, exist_ok=True)
        BEAT.write_text(json.dumps({'last_report': n.strftime('%Y-%m-%d %H:%M')},
                                   ensure_ascii=False) + '\n', encoding='utf-8')
        print('報告時刻を記録した：%s' % n.strftime('%Y-%m-%d %H:%M'))
        return
    text, bad = describe(n)
    print('現在 %s' % n.strftime('%Y-%m-%d %H:%M'))
    print(text)
    if bad:
        print('**%d時間を超えて報告が途絶えている。'
              'その間に締切を迎えたものを名指しで報告すること。**' % LIMIT_HOURS)
        sys.exit(1)
    print('正常（しきい値 %d時間）' % LIMIT_HOURS)


if __name__ == '__main__':
    main()
