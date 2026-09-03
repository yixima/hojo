# -*- coding: utf-8 -*-
"""台帳の締切が「関門（参加申込・参加表明）」か「提案書」かを検証し、**報告する**。

公募型プロポーザルは二段構えで、先に来るのは参加申込・参加表明である。
提案書の締切を台帳に入れていると、申込を逃した時点で応募資格を失う。

**このスクリプトは台帳を書き換えない。** 2026-08-28、自動で書き換える版を作って
実行したところ、公告日や前年度の日付を「参加表明締切」と誤認し、正しかった25件を壊した。
**候補を出すところまでが機械の仕事で、確定は一次資料を人が読んで行う。**

2026-09-04 の作り直し
----------------------
旧版は本文を `<[^>]+>` → 空白 で潰し、日付の**後方90字・前方25字**でラベルを探していた。
日本語のスケジュール表は「日付 → ラベル」の順に書かれるため、
**各日付が1行前のラベルを拾い、真の関門を取り落とした。**
福島県の案件で、参加申込 9/1 を捨て、企画提案書 9/4 を「参加表明」と報告し、
台帳（誤って 9/4）と一致したため **「ずれ」を出さずに黙って通した。**

作り直した点は3つ。
1. 解析を `bin/gatelib.py` に分け、**行構造を保ったまま**読む（`html_to_lines`）
2. **ラベルが読めない日付を捨てない。**「不明」として持ち、判定不能を「一致」に化けさせない
3. **対象を全件にする。**旧版は 格付 S・A の110件しか見ておらず、B・C・Dは素通りだった

    python3 bin/audit_gates.py            # 締切前の行だけ（既定）
    python3 bin/audit_gates.py --all      # 締切超過も含めて全件
"""
import csv
import io
import re
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gatelib import earliest_gate, extract_gates, html_to_lines  # noqa: E402

TODAY = datetime.now(ZoneInfo('Asia/Tokyo')).date()
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
ROOT = Path(__file__).resolve().parent.parent


def get(u, t=25):
    try:
        return subprocess.run(['curl', '-sSL', '-A', UA, '--max-time', str(t),
                               '--compressed', u],
                              capture_output=True, timeout=t + 10).stdout
    except Exception:
        return b''


def pdftext(b):
    try:
        from pypdf import PdfReader
        return '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(b)).pages[:15])
    except Exception:
        return ''


def text_of(raw, url):
    return pdftext(raw) if raw[:5] == b'%PDF-' else html_to_lines(raw.decode('utf-8', 'ignore'))


def work(r):
    """1行を検証して (行, 判定, 種別, 日付, 時刻, 抜粋) を返す。"""
    raw = get(r['URL'])
    if not raw:
        return r, '取得不可', None, None, None, ''
    t = text_of(raw, r['URL'])
    g = [x for x in extract_gates(t) if TODAY.year - 1 <= x[1].year <= TODAY.year + 2]
    if not g and raw[:5] != b'%PDF-':
        h = raw.decode('utf-8', 'ignore')
        for p in [urllib.parse.urljoin(r['URL'], m)
                  for m in re.findall(r'href="([^"]+\.pdf[^"]*)"', h, re.I)][:4]:
            g = [x for x in extract_gates(pdftext(get(p, 30)))
                 if TODAY.year - 1 <= x[1].year <= TODAY.year + 2]
            if g:
                break
    known = [x for x in g if x[0] != '不明']
    if not known:
        # **ここを「一致」にしない。**読めなかったことを、読めなかったと言う
        return r, '判定不能', None, None, None, ('日付%d件すべてラベル不明' % len(g)) if g else '日付なし'
    kind, d, tm = earliest_gate(known)
    snip = next((s for k, dd, t2, s in known if dd == d and k == kind), '')
    led = r['締切']
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', led or ''):
        return r, '台帳に締切なし', kind, d, tm, snip
    return r, ('一致' if led == d.isoformat() else 'ずれ'), kind, d, tm, snip


def main():
    rows = [r for r in csv.DictReader(open(ROOT / 'data' / 'ledger.csv', encoding='utf-8'))
            if r['URL'].startswith('http')
            and not any(k in r['状態'] for k in ('領域外', '対象外', '過年度'))]
    if '--all' not in sys.argv:
        rows = [r for r in rows
                if re.fullmatch(r'\d{4}-\d{2}-\d{2}', r['締切'] or '')
                and date.fromisoformat(r['締切']) >= TODAY]
    print('検証対象 %d件 / 基準日 %s\n' % (len(rows), TODAY), flush=True)

    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(work, rows))

    danger, unknown, other = [], [], []
    for r, st, kind, d, tm, snip in res:
        if st == 'ずれ' and d:
            diff = (date.fromisoformat(r['締切']) - d).days
            (danger if diff > 0 else other).append((r, kind, d, tm, diff, snip))
        elif st in ('判定不能', '取得不可', '台帳に締切なし'):
            unknown.append((r, st, snip))

    if danger:
        print('★ **台帳のほうが遅い＝関門を逃す。ここが危険である**')
        for r, kind, d, tm, diff, snip in sorted(danger, key=lambda x: -x[4]):
            print('  台帳 %s → 実際 %s %s（%s）%+d日  %s'
                  % (r['締切'], d, (tm.strftime('%H:%M') if tm else '  --  '), kind,
                     diff, r['案件名'][:40]))
            print('      根拠: %s' % snip[:66])
        print()
    if other:
        print('  台帳のほうが早い（安全側。ただし別の関門を見ている可能性）')
        for r, kind, d, tm, diff, snip in other:
            print('  台帳 %s → 実際 %s（%s）%+d日  %s'
                  % (r['締切'], d, kind, diff, r['案件名'][:40]))
        print()
    if unknown:
        print('  **読めなかったもの（一致ではない。目視が要る）** %d件' % len(unknown))
        for r, st, snip in unknown:
            print('  %-8s %-42s %s' % (st, r['案件名'][:42], snip[:28]))

    print('\n' + '=' * 62)
    print('★ %d件が危険 / %d件が読めない / 検証対象 %d件' % (len(danger), len(unknown), len(rows)))
    print('**台帳は書き換えていない。★を一次資料で確認し、手で直すこと。**')
    print('直したら `締切種別` と `締切確認日` の2列を必ず埋める。')


if __name__ == '__main__':
    main()
