# -*- coding: utf-8 -*-
"""格付の穴を塞いだあと、**掃引ログ全体**を新しい格付で当て直し、締切を一次資料から引く。

なぜ要るか（2026-10-11）
------------------------
2026-10-10、`bin/rank.py` に会議体の語（セミナー・フォーラム・シンポジウム・講演会・
レセプション・懇談会・交流会）が1語も無く、`セミナー` が無条件でノイズ扱いだったことが判った。
**当社は催事・会議の運営会社であり、会議体の語を欠いていたのは分母の穴である。**

直したうえで掃引ログを当て直すと、**118件が新たに S/A になった。**
**直した検出器は、過去にさかのぼって当てないと、取り逃しは回収できない。**
エラーを直して終わりにすると、直す前に通り過ぎたものは永久に見えない。

出力＝data/regrade_YYYYMMDD.csv（**台帳は書き換えない。**確定は一次資料を読んで手で行う）

    python3 bin/regrade_backfill.py
    python3 bin/regrade_backfill.py --max 60
"""
import csv, io, os, re, sys, datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'bin'))
import rank
import triage                      # fetch / text_of / money_of / repair / find_detail を使う
import gatelib

JST = ZoneInfo('Asia/Tokyo')
DONE = triage.DONE

# 旧ルール（会議体の語が無く、セミナーが無条件ノイズ）を再現して「新たにS/A」を切り出す
OLD_EVENT = re.compile(r'イベント|催事|フェスティバル|式典|大会(の)?(運営|企画)|会場(運営|設営|装飾)')
OLD_NOISE = re.compile(
    r'js-links|リンク集|サービス提供者|'
    r'セミナー|講座|研修(受講)?|説明会(の(開催|案内))?|勉強会|ウェビナー|'
    r'受講者募集|参加者募集|来場者|出展者募集|出展募集|出展者を?募集|'
    r'商談会[へに]の?参加|バイヤー招へい|'
    r'アンケート|パブリックコメント|意見公募|職員(採用|募集)|会計年度任用|'
    r'指定管理者|工事|修繕|清掃|警備|印刷製本|車両|燃料|electricity|電気の?(需給|供給)')


def old_judge(n):
    if OLD_NOISE.search(n):
        return None
    kaigai = bool(rank.KAIGAI.search(n)); tenji = bool(rank.TENJI.search(n))
    kogei = bool(rank.KOGEI.search(n)); promo = bool(rank.PROMO.search(n))
    event = bool(OLD_EVENT.search(n)); kaso = bool(rank.KAISOTSU.search(n))
    if kaso and (tenji or event): return 'S'
    if kaigai and tenji: return 'S'
    if kaigai and kogei: return 'S'
    if tenji and (kogei or promo): return 'A'
    if kaigai and promo: return 'A'
    if event and (kogei or promo or kaigai): return 'A'
    if tenji or kaso: return 'A'
    return 'B' if (kaigai or kogei or promo or event) else None


def new_judge(n):
    if rank.NOISE.search(n) and not rank.NOISE_UNEI.search(n):
        return None, ''
    g, why = rank.grade(n)
    return g, why


def job(row):
    g, why, stamp, ch, title, link = row
    out = {'相性': g, '理由': why, '初観測': stamp[:10], 'チャネル': ch, '案件名': title,
           'URL': link, '締切': '', '締切種別': '', '金額': '', '金額_円': 0, '取得': ''}
    if not link:
        out['取得'] = 'リンクなし（ナビ等。手で開く必要あり）'
        return out
    link = triage.repair(link)
    out['URL'] = link
    raw, code = triage.fetch(link)
    if not raw or not (200 <= code < 300):
        out['取得'] = f'取得できず HTTP {code}'
        return out
    t = triage.text_of(raw, link)
    out['取得'] = 'ok'

    def read(txt):
        try:
            gs = gatelib.extract_gates(txt)
        except Exception:
            gs = []
        return gs, triage.money_of(txt)

    gates, v = read(t)
    if not gates or not v:
        d = triage.find_detail(link, raw, title)
        if d:
            raw2, c2 = triage.fetch(d)
            if raw2 and 200 <= c2 < 300:
                g2, v2 = read(triage.text_of(raw2, d))
                if g2 and not gates: gates = g2
                if v2 and not v: v = v2
                if g2 or v2:
                    out['URL'] = d
                    out['取得'] = 'ok（詳細を1段たどった）'
    if gates:
        gs = sorted(gates, key=lambda x: str(x[1]))
        out['締切種別'], d0 = gs[0][0], gs[0][1]
        out['締切'] = str(d0)
    if v:
        out['金額_円'] = v
        out['金額'] = f'{v:,}円'
    return out


def main():
    mx = 200
    if '--max' in sys.argv: mx = int(sys.argv[sys.argv.index('--max') + 1])
    now = datetime.datetime.now(JST)
    print('基準日時 %s JST（実時刻）' % now.strftime('%Y-%m-%d %H:%M'))

    seen = {}
    with io.open(os.path.join(ROOT, 'data/sweep_log.csv'), encoding='utf-8') as f:
        for r in csv.reader(f):
            if len(r) < 5 or r[0] == '観測日時': continue
            if r[4] != '未登録': continue
            if DONE.search(r[2]): continue
            if r[2] in seen: continue
            seen[r[2]] = (r[0], r[1], r[3])

    newly = []
    for t, (stamp, ch, link) in seen.items():
        n, why = new_judge(t)
        if n in ('S', 'A') and old_judge(t) not in ('S', 'A'):
            newly.append((n, why, stamp, ch, t, link))
    newly.sort(key=lambda x: (0 if x[0] == 'S' else 1, x[2]), reverse=False)
    print('掃引ログの未登録見出し（結果通知を除く） %d件' % len(seen))
    print('**格付の穴を塞いで新たに S/A になったもの %d件**' % len(newly))
    newly = newly[:mx]

    res = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, o in enumerate(ex.map(job, newly), 1):
            res.append(o)
            if i % 20 == 0: print('  …%d/%d 件を確認' % (i, len(newly)), flush=True)

    td = now.date()
    live, past = [], 0
    for r in res:
        if r['締切']:
            try:
                if datetime.date.fromisoformat(r['締切']) < td:
                    past += 1; continue
            except Exception:
                pass
        live.append(r)
    print('  締切が過去のものを %d件 外した（応募できない）' % past)
    live.sort(key=lambda r: (0 if r['相性'] == 'S' else 1, r['締切'] or '9999', -r['金額_円']))

    out = os.path.join(ROOT, 'data/regrade_%s.csv' % now.strftime('%Y%m%d'))
    with io.open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['相性', '理由', '初観測', '締切', '締切種別',
                                          '金額', '金額_円', '案件名', 'チャネル', 'URL', '取得'])
        w.writeheader(); w.writerows(live)

    ng = sum(1 for r in live if r['取得'] != 'ok' and not r['取得'].startswith('ok'))
    print('\n**締切が未来・または締切を取れなかったもの %d件**' % len(live))
    print('締切が取れた %d件 ／ 金額が取れた %d件 ／ 一次資料を取得できなかった %d件'
          % (sum(1 for r in live if r['締切']), sum(1 for r in live if r['金額_円']), ng))
    print('→ %s' % out)
    print('\n■ 締切が取れたもの（早い順）')
    for r in live:
        if not r['締切']: continue
        print('  [%s] %s %-10s %14s  %s' % (r['相性'], r['締切'], r['締切種別'][:10],
                                            r['金額'] or '金額未取得', r['案件名'][:52]))
    print('\n**台帳は書き換えていない。**確定は一次資料を読んで手で行う（CLAUDE.md）。')


if __name__ == '__main__':
    main()
