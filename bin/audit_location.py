# -*- coding: utf-8 -*-
"""**格付より先に所在地要件を確認したか**を全件検証して報告する（書き換えない）。

なぜ要るか（2026-10-08）
------------------------
`workflow/eligibility.md` には 2026-08-28 から
**[5]「市内業者限定」は資格の有無より先に効く／[9]「市内」には3つの意味がある／
台帳に載せる際は、格付より先に所在地要件を確認する**
と書いてあった。

それでも 2026-10-08 の朝、**応募資格を読まずに2件を「判断していただきたい」として出した。**
読んだら両方とも所在地で落ちた。
  ・第19回神戸ものづくり中小企業展示商談会（800万円）
    → 応募資格(1)「**神戸市内に本社**を置く企業又は団体であること」
  ・令和8年度ベトナムにおける青森県レセプション運営等業務（600万円）
    → 応募資格要件(1)「**ベトナム国及び**日本国内に…拠点を有すること」

**規則が文書にあって誰も実行しないなら、規則が無いのと同じである。**
だから検出器にする。`bin/rank.py` の格付は中身の相性だけを見ており、
**所在地の概念を一切持っていない**（実測：該当語0件）。

何を見るか
----------
締切が未来の行について、`資格要否`・`格付`・`状態` のどこかに
**所在地についての判定が書かれているか**を見る。書かれていなければ★を出す。
「書いてあるか」しか見ない。**中身の正しさは人が一次資料で確かめる。**

    python3 bin/audit_location.py          # 締切が未来の行を検証
    python3 bin/audit_location.py --all    # 全件
"""
import csv, io, os, re, sys, datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST = ZoneInfo('Asia/Tokyo')

# 所在地について「判定した」と認める書き方。**日付や金額と違い、言葉でしか書けない**
VERDICT = re.compile(
    r'所在地(要件|区分|で|の)|指定なし|市内に本社|市内本社|市内業者|準市内|'
    r'県内業者|市内に主たる|本店を有する|拠点を有する|拠点要件|'
    # 2026-10-09：岡山県の「県内に事務所又は事業所を有していること」が拾えなかった。
    # **言い回しは発注者ごとに違う。拾えない書き方は、判定していないのと同じに見える。**
    r'事業所を有|事務所を有|所在地は|県内に事務所|都内に所在|'
    r'所在地の指定(は)?(無|な)い|所在地要件(は)?(無|な)し|'
    r'欠格事由のみ|等級要件(は)?(無|な)')
# **領域外・本業外と決めた行**（bin/build_board.py の OUTSIDE と同じ語）
OUT = re.compile(r'領域外|対象外|業務範囲外|本業外')
# 一次資料に所在地の定めがあるのに見落としやすい語（参考表示用）
HINT = re.compile(r'市|区|県|町|村')


def day(s):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})$', (s or '').strip())
    if not m: return None
    try:
        return datetime.date(*map(int, m.groups()))
    except ValueError:
        return None


def bare_url(u):
    """**一次資料に戻れない行**か。URLが空、または組織のトップページだけなら True。

    2026-10-16 判明。所在地の判定が書けなかった3件は、**どれも URL が
    発注機関のトップページだけだった**（鹿児島県／浜松市／神戸市）。
    「読んでいない」のではなく、**読みに行く先が台帳に無かった。**
    台帳全体では47行がこの状態である。
    **戻れない記録は、記録していないのと同じである。**
    """
    u = (u or '').strip()
    if not u:
        return 'URLが空'
    try:
        from urllib.parse import urlparse
        q = urlparse(u)
    except Exception:
        return ''
    if q.path in ('', '/') and not q.query:
        return '組織のトップページだけ'
    return ''


def main():
    now = datetime.datetime.now(JST)
    today = now.date()
    print('基準日時 %s JST（実時刻）' % now.strftime('%Y-%m-%d %H:%M'))
    rows = list(csv.DictReader(io.open(os.path.join(ROOT, 'data/ledger.csv'),
                                       encoding='utf-8')))
    allf = '--all' in sys.argv
    tgt, ng, skipped = [], [], []
    for i, r in enumerate(rows, start=2):
        d = day(r.get('締切'))
        if not allf and not (d and d >= today):
            continue
        tgt.append(r)
        blob = ' '.join((r.get('資格要否') or '', r.get('格付') or '', r.get('状態') or ''))
        # **領域外と決めた案件に所在地の判定は要らない。**
        # ただし**黙って外さない。**数と件名を別に出す。
        # 黙って外す道具は、黙って見落とす（CLAUDE.md）。
        if OUT.search(r.get('状態') or ''):
            skipped.append((i, r, d))
            continue
        if not VERDICT.search(blob):
            ng.append((i, r, d))

    print('検証対象 %d件（%s）' % (len(tgt), '全件' if allf else '締切が未来の行'))
    if skipped:
        print('\n領域外として外した %d件（**黙って外さない。**所在地は問わない）：' % len(skipped))
        for i, r, d in skipped:
            print('    %4d行 %s / %s' % (i, (r['案件名'] or '')[:46], (r['発注機関'] or '')[:24]))
    if not ng:
        print('\n**全件に所在地の判定が書かれている。**')
    else:
        print('\n★**所在地の判定が書かれていない %d件。**'
              '格付より先に、一次資料の「応募資格」を読むこと' % len(ng))
        for i, r, d in ng:
            print('  %4d行 締切 %s %-6s %s / %s'
                  % (i, r.get('締切') or '未取得', r.get('締切時刻') or '',
                     r['案件名'][:48], r['発注機関'][:22]))
            print('        %s' % (r.get('URL') or '（URLなし）')[:108])
            bw = bare_url(r.get('URL'))
            if bw:
                print('        ★**一次資料に戻れない（%s）。'
                      '読んでいないのではなく、読みに行く先が台帳に無い**' % bw)

    allbare = [(i, r) for i, r in enumerate(rows, start=2) if bare_url(r.get('URL'))]
    if allbare:
        print('\n▲ **一次資料に戻れない行が %d件ある**（台帳 %d行中）。'
              'URLが空か、発注機関のトップページだけである。'
              '**戻れない記録は、記録していないのと同じである**'
              % (len(allbare), len(rows)))

    print('\n**この検査は「書いてあるか」しか見ない。**'
          '中身の正しさは一次資料で人が確かめる（CLAUDE.md）。')
    print('規則の出どころ＝workflow/eligibility.md [4][5][7][9]。'
          '**文書にあって実行されない規則は、無いのと同じである。**')
    return 0


if __name__ == '__main__':
    sys.exit(main())
