# -*- coding: utf-8 -*-
"""制度台帳 `data/programs.csv` を検査して報告する。**書き換えない。**

なぜ要るか
----------
2026-09-15、生島様から6つの支援制度を示され、**そのうち3つを持っていなかった**
（ものづくり補助金グローバル枠・日本公庫 海外展開資金・持続化補助金第20回）。
さらに **廃止された JAPANブランド育成支援等事業が、架空の締切つきで
`workflow/report-template.md` に残っていた。**

原因は1つである。**母集団を「巡回で見つけたもの」で定義していた。**
見つけたものしか記録しない設計では、**見落としは定義上検出できない。**
「あるはずのものが無い」と言うには、先に「あるはず」の一覧が要る。それがこの台帳である。

検査するもの
------------
1. **一次資料をいつ読んだか**（`最終確認日`）。空、または STALE_DAYS を超えたら鳴る
2. **現存と書いてあるのに根拠URLが死んでいないか**（`--net` のときだけ実際に叩く）
3. **次回見込みが過去になっていないか**（予測が腐る）
4. **前段関門が締切より後になっていないか**（自己矛盾。§3-14）
5. **必須列の空欄**
6. **締切・前段関門が LEAD_DAYS 以内に迫っているもの**を予告として出す

    python3 bin/programs.py          # 検査して報告（ネットワーク不要）
    python3 bin/programs.py --net    # 根拠URLの生死も見る
    python3 bin/programs.py --soon   # 迫っているものだけ

終了コード 2＝直さないと先に進めない違反がある。
"""
import csv
import datetime
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, 'data', 'programs.csv')

STALE_DAYS = 90      # 一次資料を読み直す間隔。制度は年度で変わる
LEAD_DAYS = 60       # 何日前から予告するか
REQUIRED = ['制度ID', '制度名', '所管', '種別', '当社の立ち位置', '状態', '根拠URL']
ALIVE = '現存'


def today():
    """**日付は bin/today.sh からのみ取る。**推測しない（CLAUDE.md 最重要）。"""
    out = subprocess.check_output([os.path.join(ROOT, 'bin', 'today.sh')]).decode()
    return datetime.datetime.strptime(out.split()[0], '%Y-%m-%d').date()


def parse_day(s):
    """先頭の YYYY-MM-DD だけを見る。YYYY-MM までしか無いものは月末とみなさない。"""
    s = (s or '').strip()
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def load():
    with io.open(CSV, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def url_alive(url):
    """生きているか。**落ちていることの証拠が取れたときだけ False を返す。**
    取得できなかった（タイムアウト等）は None＝判定不能。不明を「廃止」に化けさせない。"""
    try:
        p = subprocess.run(
            ['curl', '-sSL', '--http1.1', '-o', '/dev/null', '-w', '%{http_code}',
             '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
             '--max-time', '25', '--compressed', url],
            capture_output=True, timeout=40)
        code = p.stdout.decode().strip()
    except Exception:
        return None
    if not code.isdigit():
        return None
    c = int(code)
    if c in (404, 410):
        return False
    if 200 <= c < 400:
        return True
    return None


def check(rows, now, net=False):
    hard, soft, soon = [], [], []
    seen = {}
    for i, r in enumerate(rows, start=2):
        name = r['制度名'] or '(名称なし)'

        for col in REQUIRED:
            if not (r.get(col) or '').strip():
                hard.append((i, name, '必須列が空：%s' % col))

        pid = (r.get('制度ID') or '').strip()
        if pid in seen:
            hard.append((i, name, '制度IDの重複：%s（%d行目と同じ）' % (pid, seen[pid])))
        seen[pid] = i

        alive_row = r['状態'].startswith(ALIVE)

        # 1. 一次資料をいつ読んだか
        last = parse_day(r.get('最終確認日'))
        if alive_row:
            if last is None:
                hard.append((i, name, '**最終確認日が空。一次資料を自分で読んでいない**'))
            else:
                gap = (now - last).days
                if gap > STALE_DAYS:
                    soft.append((i, name, '一次資料を %d日確認していない（しきい値%d日）'
                                 % (gap, STALE_DAYS)))

        # 3. 次回見込みが過去
        nxt = parse_day(r.get('次回見込み'))
        if nxt and nxt < now:
            soft.append((i, name, '次回見込み %s が過ぎている。予測が腐っている' % nxt))

        # 4. 前段関門と締切の前後（自己矛盾）
        dl = parse_day(r.get('締切'))
        gate = parse_day(r.get('前段関門'))
        if dl and gate and gate > dl:
            hard.append((i, name, '前段関門 %s が締切 %s より後になっている' % (gate, dl)))

        # 6. 迫っているもの
        for label, d in (('締切', dl), ('前段関門', gate), ('公募開始', parse_day(r.get('公募開始')))):
            if d and alive_row and 0 <= (d - now).days <= LEAD_DAYS:
                soon.append(((d - now).days, d, label, name, r.get('前段関門', '')))

        # 2. URLの生死
        if net and alive_row and r['根拠URL'].startswith('http'):
            a = url_alive(r['根拠URL'])
            if a is False:
                hard.append((i, name, '状態が「現存」だが根拠URLが 404/410：%s' % r['根拠URL']))
            elif a is None:
                soft.append((i, name, '根拠URLの生死を**判定できなかった**（取得失敗）。'
                                      '生きているとみなしていない'))
    soon.sort()
    return hard, soft, soon


def main():
    net = '--net' in sys.argv
    only_soon = '--soon' in sys.argv
    rows = load()
    now = today()
    hard, soft, soon = check(rows, now, net)

    alive = [r for r in rows if r['状態'].startswith(ALIVE)]
    print('制度台帳 %d件（現存 %d／廃止・統合 %d）／基準日 %s'
          % (len(rows), len(alive), len(rows) - len(alive), now))

    if soon:
        print('\n■ %d日以内に動きがあるもの' % LEAD_DAYS)
        for d, day, label, name, gate in soon:
            print('  残り%3d日  %s %-6s  %s' % (d, day, label, name[:44]))
            if label == '締切' and gate:
                print('            ↑前段関門：%s' % gate[:90])
    else:
        print('\n■ %d日以内に動きがあるもの：なし' % LEAD_DAYS)

    if only_soon:
        return 0

    if hard:
        print('\n★ 直さないと先に進めない（%d件）' % len(hard))
        for i, name, msg in hard:
            print('  %4d行 %-40s %s' % (i, name[:40], msg))
    if soft:
        print('\n▲ 確認が要る（%d件）' % len(soft))
        for i, name, msg in soft:
            print('  %4d行 %-40s %s' % (i, name[:40], msg))
    if not hard and not soft:
        print('\n違反なし。')

    print('\n**この検査は「台帳に書いてある制度」しか見ない。**')
    print('**台帳に無い制度は、ここでは永久に見つからない。**'
          ' 母集団の網羅は `bin/sweep_channels.py` が担う。')
    return 2 if hard else 0


if __name__ == '__main__':
    sys.exit(main())
