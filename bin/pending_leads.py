# -*- coding: utf-8 -*-
"""掃引で見たのに台帳へ入っていない「当社の領域の見出し」を、片付くまで出し続ける。

なぜ要るか
----------
**2026-11-07、秋田県「あきたの工芸品の魅力発信！プラットフォーム構築事業」
（377万円・応募可・当社の本業）を9日間ほったらかしていた。**
見出しは 2026-10-30 の掃引から毎日 `data/sweep_log.csv` に記録されていた。
一次資料を1度も開かず、台帳にも入れていなかった。

原因は掃引の作りである。`bin/sweep_channels.py` が出すのは
**「本日はじめて見た見出し」**だけで、その日に拾わなければ二度と画面に出ない。
**見落としは、見えなかったから起きたのではない。1日だけ見えて、消えたから起きた。**

これは 2026-09-21 の「0件は『無かった』ではなく『その日付の行が存在しない』」と
同じ型である。**鳴ったあと黙る検出器は、鳴らない検出器とあまり変わらない。**

何をするか
----------
`data/sweep_log.csv` の全見出しのうち、

1. `bin/rank.py` の `grade()` が S または A と判定し（＝当社の領域）、
2. `data/ledger.csv` のどの案件名とも一致せず、
3. 終わった告知・過年度のものでもない

ものを、**初めて見た日の古い順に**出す。片付ける方法は2つしかない。

- 一次資料を開いて台帳へ入れる（応募可でも不可でも、入れれば消える）
- `data/leads_ignored.csv` に見出しと理由を書く（領域外と判断したものの置き場）

**「あとで見る」という状態を作らない。**出たものは、その日のうちにどちらかにする。

    python3 bin/pending_leads.py            # 未処理の一覧
    python3 bin/pending_leads.py --days 14  # 初見から14日以上たったものだけ
"""
import argparse
import csv
import datetime
import io
import os
import re
import sys
import unicodedata
import zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# **rank.py は読み込んだだけで集計を標準出力へ流す。**
# この道具の出力に混ざると、何件が未処理なのかが読めなくなるので黙らせる。
_stdout = sys.stdout
try:
    sys.stdout = io.StringIO()
    import rank  # noqa: E402
finally:
    sys.stdout = _stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP = os.path.join(ROOT, 'data', 'sweep_log.csv')
LEDGER = os.path.join(ROOT, 'data', 'ledger.csv')
IGNORED = os.path.join(ROOT, 'data', 'leads_ignored.csv')
JST = zoneinfo.ZoneInfo('Asia/Tokyo')

# **終わった告知と過年度のものは、未処理ではない。**
# ここは bin/sa_backlog.py と同じ考えで書く（あちらは S/A の積み残し用）。
DONE = re.compile(r'入札結果|落札|選定結果|結果[のを]?公表|採択結果|審査結果|'
                  r'質問[^、。]{0,8}回答|質問について|募集終了|受付終了|公募終了|'
                  r'中止|取りやめ|延期のお知らせ')
PAST = re.compile(r'令和[1-7]年度|平成|20(1[0-9]|2[0-5])(年度?|\b)')


def norm(s):
    """比較用に潰す。全角半角・大小・記号・空白の違いで取りこぼさない。"""
    s = unicodedata.normalize('NFKC', s or '').casefold()
    return re.sub(r'[\s　・,，、。．\.\-−ー―~〜/／()（）【】「」\[\]！!？?]', '', s)


def _rows(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(io.open(path, encoding='utf-8')))


def pending(min_days=0, today=None):
    """未処理の見出しを、初見の古い順に返す。"""
    today = today or datetime.datetime.now(JST).date()

    ledger = {norm(r['案件名']) for r in _rows(LEDGER)}
    ignored = {norm(r['見出し']) for r in _rows(IGNORED)}

    first, last, info = {}, {}, {}
    for r in _rows(SWEEP):
        h = (r.get('見出し') or '').strip()
        if not h:
            continue
        d = (r.get('観測日時') or '')[:10]
        k = norm(h)
        if k not in first or d < first[k]:
            first[k] = d
        if k not in last or d > last[k]:
            last[k] = d
            info[k] = (h, r.get('チャネルID', ''), r.get('リンク', ''))

    out = []
    for k, d0 in first.items():
        if k in ledger or k in ignored:
            continue
        h, ch, url = info[k]
        if DONE.search(h) or PAST.search(h):
            continue
        g, why = rank.grade(h)
        if g not in ('S', 'A'):
            continue
        try:
            age = (today - datetime.date.fromisoformat(d0)).days
        except ValueError:
            age = 0
        if age < min_days:
            continue
        out.append({'初見': d0, '最後に見た': last[k], '経過日数': age,
                    '格': g, '理由': why, '見出し': h,
                    'チャネルID': ch, 'リンク': url})
    out.sort(key=lambda r: (r['初見'], r['格']))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=0,
                    help='初見からこの日数以上たったものだけ出す')
    a = ap.parse_args()

    rows = pending(a.days)
    today = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M')
    print('基準日時: %s JST' % today)
    if not rows:
        print('未処理の見出しは無い。')
        print('**ただし「0件」は、検出器が動いていることを確かめてから信じること。**')
        return 0

    print('**掃引で見たのに、台帳にも leads_ignored.csv にも無い見出し：%d件**' % len(rows))
    print('（当社の領域＝S または A と判定されたものだけ。終わった告知と過年度は除く）')
    print()
    for r in rows:
        mark = '★' if r['経過日数'] >= 3 else '  '
        print('%s [%s] 初見 %s（%d日前）  %s' %
              (mark, r['格'], r['初見'], r['経過日数'], r['見出し'][:76]))
        print('      %s  %s' % (r['理由'], r['リンク'][:100]))
    print()
    print('**片付けかたは2つだけ。**一次資料を開いて台帳へ入れるか、')
    print('領域外と判断したなら data/leads_ignored.csv に見出しと理由を書く。')
    print('**「あとで見る」という状態を作らない。**')
    old = [r for r in rows if r['経過日数'] >= 3]
    if old:
        print()
        print('★ **初見から3日以上たっているものが %d件ある。**' % len(old))
        print('   2026-11-07、秋田県の工芸品プラットフォーム（377万円・応募可・当社の本業）を')
        print('   9日間ほったらかしていた。**日数が伸びているものから開く。**')
    return 0


if __name__ == '__main__':
    sys.exit(main())
