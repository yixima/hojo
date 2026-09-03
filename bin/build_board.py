#!/usr/bin/env python3
"""`data/ledger.csv` から公募ボード（`reports/dashboard.html`）を生成する。

なぜこれが要るか
----------------
ボードを手で書いていたため、**毎回セクションの並びが変わり、
古い記述が残り、読む側が「今どれを決めればいいのか」を探さねばならなかった。**
2026-09-03、生島様より「情報がランダムで見にくい」とのご指摘を受けて機械生成に切り替えた。

並びの原則（この順序を動かさない）
--------------------------------
1. **いま決める** — 締切7日以内で、応募できるもの。**これが唯一の判断面である**
2. **進行中** — 応募すると決めたもの
3. **まだ公告されていないが、必ず出る案件** — 状態欄が `【予測】` で始まるもの。
   **締切欄の日付は周期からの推定であって、確定日ではない**
4. **見ておく** — 締切8〜120日
5. **等級が壁になった案件** — 定期受付（9/14〜10/30）の判断材料
6. **次年度候補** — 締切超過・見送り。**前回の締切月ごとに束ねる**
7. **見送りの基準** — なぜ落としたかの物差し

残日数は `data-deadline` からブラウザ側で計算する。**数値を直書きしない**（CLAUDE.md）。

使い方
------
    python3 bin/build_board.py            # reports/dashboard.html を書き出す
    python3 bin/build_board.py --check    # 分類結果だけ表示（書き出さない）
"""
import csv
import datetime
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / 'data' / 'ledger.csv'
OUT = ROOT / 'reports' / 'dashboard.html'


def today():
    """**日付は必ず bin/today.sh から取る。**推測しない（CLAUDE.md 最重要）。"""
    s = subprocess.run([str(ROOT / 'bin' / 'today.sh')],
                       capture_output=True, text=True, check=True).stdout
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})', s)
    return (datetime.date(int(m[1]), int(m[2]), int(m[3])), '%s:%s' % (m[4], m[5]))


# ── 分類の語彙 ──────────────────────────────────────────
# 台帳の「状態」「資格要否」欄は日本語の文章である。機械判定できるよう、
# 実際に台帳で使われている表現だけを拾う。**新しい表現を足すときは台帳を grep して確かめる。**
NG = ('応募不可', '応募できない', '等級不足', 'D等級では不可', '単独応募不可',
      '間に合わない', 'C等級の当社は応募で')
GO = ('応募する', '申請する', '申請したい', '希望申請を出す', '出してみましょう',
      '参加意向申出を出す')
NO = ('見送り', '見合わせ')
OUTSIDE = ('領域外', '対象外', '業務範囲外', '本業外')


def classify(r):
    """1行を分類する。**状態欄の生島様のご決定を最優先する。**

    decided_go  応募・申請すると決めたもの
    decided_no  生島様が見送ると決めたもの
    rec_no      こちらから見送りを推奨し、まだご決定をいただいていないもの
    ng          資格・等級で応募できないもの
    out         領域外・本業外。判断の対象にならない
    forecast    まだ公告されていないが、周期から必ず出ると分かっているもの
    open        判断待ち
    """
    st = r['状態']
    shikaku = r['資格要否']
    blob = st + ' ' + shikaku
    if '【予測】' in st:
        # **まだ公告されていないが、周期から必ず出ると分かっている案件。**
        # 締切欄の日付は推定値であり、確定日ではない（状態欄に明記してある）
        return 'forecast'
    if '生島様' in st:
        if any(k in st for k in NO):
            return 'decided_no'
        if any(k in st for k in GO):
            return 'decided_go'
    if any(k in blob for k in NG):
        return 'ng'
    if any(k in blob for k in OUTSIDE):
        return 'out'
    if any(k in st for k in NO):
        return 'rec_no'
    return 'open'


def parse_date(s):
    s = (s or '').strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', s):
        return None
    return datetime.date(*map(int, s.split('-')))


def load():
    return list(csv.DictReader(open(LEDGER, encoding='utf-8')))


def esc(s):
    return html.escape(s or '')


def first_sentence(s, n=1):
    """状態欄の先頭 n 文を取る。状態欄は長いので、要点だけを表に出す。"""
    s = re.sub(r'\s+', ' ', s or '').strip()
    parts = re.split(r'(?<=。)', s)
    return ''.join(parts[:n]).strip()


def md(s):
    """**強調** と `コード` を HTML に変える。台帳の記述をそのまま活かすため。"""
    s = esc(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
    return s


# ── 仕分け ──────────────────────────────────────────────
WATCH_MAX = 120  # 「見ておく」の上限。これより先は次年度候補に寄せる


def buckets(rows, td):
    b = {'now': [], 'going': [], 'coming': [], 'watch': [], 'grade': [], 'next': [], 'out': []}
    for r in rows:
        d = parse_date(r['締切'])
        k = classify(r)
        left = (d - td).days if d else None
        rec = dict(r=r, d=d, left=left, k=k)

        if k == 'out':
            b['out'].append(rec)
            continue
        if k == 'decided_go' and (left is None or left >= 0):
            b['going'].append(rec)
            continue
        if k == 'forecast':
            b['coming'].append(rec)
            continue
        if k == 'ng' and left is not None and left >= 0 and '等級' in r['状態'] + r['資格要否']:
            # 生きている案件が等級で落ちた。**定期受付（9/14〜10/30）の判断材料になる**
            b['grade'].append(rec)
            continue
        if left is None or left < 0 or k in ('decided_no', 'rec_no', 'ng') or left > WATCH_MAX:
            b['next'].append(rec)
            continue
        b['now' if left <= 7 else 'watch'].append(rec)

    far = datetime.date(2099, 1, 1)
    for key, v in b.items():
        if key == 'next':
            # 次年度候補は「来年いつ見るか」で並べる。年をまたいで月日だけを見る
            v.sort(key=lambda x: ((x['d'] or far).month, (x['d'] or far).day))
        else:
            v.sort(key=lambda x: (x['d'] or far))
    return b


# ── 描画 ────────────────────────────────────────────────
PILL = {
    'open': ('p-crit', '判断待ち'),
    'forecast': ('p-warn', '公告待ち'),
    'decided_go': ('p-ok', '申請すると決定'),
    'decided_no': ('p-off', '見送り決定'),
    'rec_no': ('p-warn', '見送りを推奨'),
    'ng': ('p-off', '資格で応募不可'),
    'out': ('p-off', '対象外'),
}


def card(rec, lead=False):
    r = rec['r']
    cls, label = PILL[rec['k']]
    o = ['<article class="card%s">' % (' lead' if lead else '')]
    o.append('<div class="chead"><div class="ctitle"><h3>%s</h3><div class="org">%s ／ %s</div></div>'
             '<span class="pill %s">%s</span></div>' %
             (esc(r['案件名']), esc(r['発注機関']), esc(r['応募形態'] or '—'), cls, label))
    if rec['d']:
        o.append('<div class="dl" data-deadline="%s"><div class="days"></div>'
                 '<div class="bar"><i></i></div><div class="date">%s 締切</div></div>'
                 % (rec['d'].isoformat(), rec['d'].isoformat()))
    facts = [('種別', r['種別']), ('予定価格', r['予定価格']), ('格付・等級', r['格付']),
             ('資格', r['資格要否']), ('初報', r['初報日'])]
    o.append('<dl class="facts">')
    for k, v in facts:
        o.append('<div><dt>%s</dt><dd>%s</dd></div>' % (esc(k), md(v) or '—'))
    o.append('</dl>')
    if r['状態'].strip():
        o.append('<p class="note">%s</p>' % md(r['状態']))
    if r['URL'].strip().startswith('http'):
        o.append('<p class="src"><a href="%s" target="_blank" rel="noopener">%s</a></p>'
                 % (esc(r['URL']), esc(r['URL'][:78])))
    o.append('</article>')
    return '\n'.join(o)


def table(recs, cols):
    """cols = [(見出し, 値を作る関数, td のクラス), ...]"""
    o = ['<div class="scroll"><table><thead><tr>']
    o += ['<th>%s</th>' % esc(c[0]) for c in cols]
    o.append('</tr></thead><tbody>')
    for rec in recs:
        o.append('<tr>')
        for _, fn, cl in cols:
            o.append('<td%s>%s</td>' % (' class="%s"' % cl if cl else '', fn(rec)))
        o.append('</tr>')
    o.append('</tbody></table></div>')
    return '\n'.join(o)


def section(num, title, count, desc, body):
    return ('<section><div class="shead"><h2>%s. %s</h2><span class="n">%s</span></div>'
            '<p class="sdesc">%s</p><div class="rule"></div>%s</section>'
            % (num, esc(title), esc(count), desc, body))


def days_cell(rec):
    if rec['left'] is None:
        return '<span style="color:var(--muted)">—</span>'
    if rec['left'] < 0:
        return '<span style="color:var(--muted)">超過</span>'
    return '<span class="dl" data-deadline="%s"><span class="days" style="font-size:14px"></span></span>' % rec['d'].isoformat()


def build(rows, td, now_hm):
    b = buckets(rows, td)
    # **本命は台帳の状態欄で宣言する。**ここに案件名を書かない（毎回の書き換えを避ける）
    LEAD = ('拾い物', '本命', 'いちばん')
    o = []

    # ── 見出し ──
    o.append('<header class="mast"><div><h1>公募案件ボード</h1>'
             '<div class="sub">一般社団法人ジャパンプロモーション ／ 補助金・企画競争の巡回結果'
             '<br>この画面は <code>data/ledger.csv</code> から <code>bin/build_board.py</code> が生成しています</div></div>'
             '<div class="stamp"><div>生成<b>%s</b></div><div>台帳<b>%d</b></div>'
             '<div>いま決める<b>%d</b></div><div>進行中<b>%d</b></div></div></header>'
             % (td.strftime('%m.%d'), len(rows), len(b['now']), len(b['going'])))

    # ── 冒頭 ──
    lede = ['<div class="lede">']
    lede.append('<p><strong>%s %s 現在。</strong>台帳 %d件のうち、'
                '<b>いま判断が要るものが %d件</b>、進行中が %d件です。'
                'この画面は上から順に「決める → 進めている → 見ておく → 来年」で並べてあります。'
                '<b>1番の節だけ見れば、今日決めることは足ります。</b></p>'
                % (td.strftime('%Y年%-m月%-d日'), now_hm, len(rows), len(b['now']), len(b['going'])))
    if b['now']:
        items = []
        for rec in b['now'][:5]:
            items.append('<li><span class="dl" data-deadline="%s"><b class="days" style="font-size:15px"></b></span>'
                         ' ／ %s <span style="color:var(--muted)">（%s）</span></li>'
                         % (rec['d'].isoformat(), esc(rec['r']['案件名'][:46]), esc(rec['r']['発注機関'])))
        lede.append('<p><strong>締切が近い順に。</strong></p><ul style="margin:0 0 10px;padding-left:20px">%s</ul>'
                    % ''.join(items))
    priced = [x for x in b['now'] + b['going'] + b['coming'] + b['grade']
              if any(k in x['r']['予定価格'] for k in ('前年度', '令和', '【推定】', '万円'))]
    if priced:
        lede.append('<p><strong>過去の落札額を調べました。</strong>'
                    'いま判断が要る案件と、等級で落ちた案件のうち <b>%d件</b>について、'
                    '前年度の同種案件の落札金額・落札者・応札者数を各カードの「予定価格」欄に入れてあります。'
                    '<b>東京都は発注予定表に予定価格を出しませんが、開札済みの案件は'
                    '入札経過調書に落札額と全入札者の入札額が載ります。</b>'
                    '年次で反復する案件なら、前年度の落札額がそのまま今年度の目安になります。</p>'
                    % len(priced))
    if b['grade']:
        lede.append('<p><strong>等級で届かなかった案件が、いま %d件あります。</strong>'
                    'いずれも中身は御社の本業です。<b>9月14日に始まる東京都の定期受付が、'
                    'この壁を動かせる唯一の機会です。</b>4番の節にまとめました。</p>' % len(b['grade']))
    lede.append('<p><strong>巡回について。</strong>自動巡回は週1回（毎週月曜8時）です。'
                'ところが東京都の希望申請期間は<b>5〜7日しかありません</b>。'
                '<b>週次のままでは窓を丸ごと逃す周期にあります。</b>'
                '隔日への変更をご検討ください（報告書 <code>docs/report_junkai_20260903.md</code>）。</p>')
    lede.append('</div>')
    o.append(''.join(lede))

    # ── 1. いま決める ──
    if b['now']:
        cards = []
        for rec in b['now']:
            cards.append(card(rec, lead=any(k in rec['r']['状態'] for k in LEAD)))
        body = '\n'.join(cards)
    else:
        body = '<p class="note">締切7日以内で応募できる案件はありません。</p>'
    o.append(section(1, 'いま決める', '%d件' % len(b['now']),
                     '<b>締切まで7日以内で、資格のうえで応募できるもの</b>だけを置いています。'
                     '資格で落ちたもの・見送ると決めたものはここに出しません。'
                     '<b>この節が唯一の判断面です。</b>', body))

    # ── 2. 進行中 ──
    if b['going']:
        o.append(section(2, '進行中', '%d件' % len(b['going']),
                         '申請すると決めたもの。<b>作業が止まっていないかを見る節です。</b>',
                         '\n'.join(card(rec) for rec in b['going'])))

    # ── 3. 公告待ち ──
    if b['coming']:
        o.append(section(3, 'まだ公告されていないが、必ず出る案件',
                         '%d件' % len(b['coming']),
                         '過去の公告周期から、出ることが分かっているもの。'
                         '<b>カードの日付は周期からの推定であって、確定した締切ではありません。</b>'
                         '公告を待ってから準備を始めると間に合わない案件を、ここに置きます。',
                         '\n'.join(card(rec, lead=True) for rec in b['coming'])))

    # ── 4. 見ておく ──
    if b['watch']:
        cols = [('残り', days_cell, 'd'),
                ('締切', lambda x: x['d'].isoformat(), 'd'),
                ('案件名', lambda x: esc(x['r']['案件名']), ''),
                ('発注機関', lambda x: esc(x['r']['発注機関']), ''),
                ('金額', lambda x: md(x['r']['予定価格']), ''),
                ('状態', lambda x: md(first_sentence(x['r']['状態'])), '')]
        o.append(section(4, '見ておく', '%d件' % len(b['watch']),
                         '締切まで8〜%d日。<b>まだ決めなくてよいが、準備の要否だけ見ておくもの。</b>'
                         % WATCH_MAX, table(b['watch'], cols)))

    # ── 5. 等級の壁 ──
    if b['grade']:
        cols = [('締切', lambda x: x['d'].isoformat(), 'd'),
                ('案件名', lambda x: esc(x['r']['案件名']), ''),
                ('発注機関', lambda x: esc(x['r']['発注機関']), ''),
                ('要求等級', lambda x: esc(x['r']['格付']), 'g'),
                ('過去の落札額', lambda x: md(x['r']['予定価格']), '')]
        o.append(section(5, '等級が壁になった案件', '%d件' % len(b['grade']),
                         '<b>種目は登録済みなのに、受付等級が届かず応募できなかったもの。</b>'
                         '東京都の定期受付は <b>9月14日〜10月30日</b>。'
                         '<b>ここに並んだ件数と中身が、等級引上げを申請するかどうかの材料になります。</b>',
                         table(b['grade'], cols)))

    # ── 6. 次年度候補 ──
    if b['next']:
        cols = [('前回の締切', lambda x: x['d'].isoformat() if x['d'] else '—', 'd'),
                ('案件名', lambda x: esc(x['r']['案件名']), ''),
                ('発注機関', lambda x: esc(x['r']['発注機関']), ''),
                ('種別', lambda x: esc(x['r']['種別']), ''),
                ('落とした理由・状態', lambda x: md(first_sentence(x['r']['状態'])), '')]
        groups = {}
        for rec in b['next']:
            groups.setdefault(rec['d'].month if rec['d'] else 0, []).append(rec)
        # 来月から順に12か月まわす。**来年その月に何を見に行くかの順に並べる**
        order = [(td.month + i - 1) % 12 + 1 for i in range(12)] + [0]
        blocks = []
        for mo in order:
            if mo not in groups:
                continue
            g = groups[mo]
            name = '%d月に見に行く' % mo if mo else '時期が決まっていないもの'
            blocks.append('<details%s><summary>%s<span class="cnt">%d件</span></summary>%s</details>'
                          % (' open' if mo == (td.month % 12) + 1 else '',
                             esc(name), len(g), table(g, cols)))
        o.append(section(6, '次年度候補', '%d件' % len(b['next']),
                         '<b>締切が過ぎたもの・見送ると決めたもの・資格が届かなかったものを、'
                         'すべてここに寄せています。</b>公募は毎年ほぼ同じ時期に出るので、'
                         '<b>前回の締切月ごとにまとめました。来年その月が来たら、この束を開いて発注者を見に行きます。</b>'
                         '来月の束だけ開いてあります。', ''.join(blocks)))

    # ── 7. 見送りの基準 ──
    o.append(section(7, '見送りの基準', 'eligibility.md [15]〜[18]',
                     'なぜ落としたかの物差し。<b>この4つに当たる案件は、種目と等級が合っていても取りません。</b>',
                     CRITERIA))

    o.append('<div class="foot"><h3>この画面の作り方</h3><ul>'
             '<li>元データは <code>data/ledger.csv</code>（%d行）。'
             '<code>python3 bin/build_board.py</code> で作り直します</li>'
             '<li>残日数は閲覧時にブラウザ側で計算しています。'
             '<b>数値は直書きしていません</b>（CLAUDE.md 最重要）</li>'
             '<li>領域外・本業外として判断の対象から外したものが %d件あります。'
             '台帳には残していますが、この画面には出しません</li>'
             '</ul></div>' % (len(rows), len(b['out'])))
    return b, '\n'.join(o)


CRITERIA = """
<div class="card">
<p class="note"><b>[15] 施工単体は取らない。</b>運営・総合プロデュース・海外が当社の強み。
ブース装飾や設営だけの案件は、施工会社が価格で取る。</p>
<p class="note"><b>[16] 補助金と入札は判定軸が別。</b>補助金に入札参加資格は要らない。
補助金で律速になるのは <b>GビズIDプライム</b>である。</p>
<p class="note"><b>[17] 種目と等級が合っただけで「応募可」と報告しない。</b>
判定は ①種目 → ②等級 → <b>③仕様書で実行条件と価格の前提を読む</b> → ④判断を仰ぐ、の順。
仕様書で必ず見る5点：実施日と会場数／受託者が立て替える費目／
<b>金額が明示されていない費目がないか</b>／人員要件／準備期間。</p>
<p class="note flag"><b>[18] 価格勝負だけの案件は取らない。</b>
①企画・構成を発注者が全部決めている ②固定費比率が高い
③過去の入札で1位と2位の差が数%以内 ④価格のみで決まる。
<b>Tokyo DX/AX はこの4つ全部に当たった</b>（会場費877.7万円が全社共通の固定費、
前年は23社指名で1位と2位の差が1.4%）。</p>
</div>
"""


# ── 雛形 ────────────────────────────────────────────────
# 配色は江戸紫（東京手仕事のイメージカラー）。既存ボードの意匠をそのまま引き継ぐ。
HEAD = r"""<title>ジャパンプロモーション公募ボード</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;700&family=Zen+Kaku+Gothic+New:wght@400;500;700&family=Roboto+Mono:wght@400;500&display=swap">

<style>
/* ── 江戸紫を軸にした配色。東京手仕事のイメージカラーに由来 ───────── */
:root{
  --ground:#FAF8FC;
  --surface:#FFFFFF;
  --surface-2:#F4F1F7;
  --ink:#1C1722;
  --ink-2:#4A4356;
  --muted:#7A7288;
  --line:#E5E0EC;
  --line-strong:#CFC7DC;
  --accent:#664A9E;        /* 江戸紫 */
  --accent-soft:#EFE9F8;
  --crit:#A82C46;          /* 茜 */
  --crit-soft:#FBEBEE;
  --warn:#9C6612;          /* 琥珀 */
  --warn-soft:#FBF2E2;
  --ok:#276B52;            /* 常磐 */
  --ok-soft:#E5F2EC;
  --off:#8A8398;
  --off-soft:#F0EEF3;
  --shadow:0 1px 2px rgba(28,23,34,.05), 0 8px 24px -12px rgba(28,23,34,.18);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ground:#141119;
    --surface:#1D1926;
    --surface-2:#251F31;
    --ink:#EFEBF5;
    --ink-2:#C3BBD2;
    --muted:#918AA1;
    --line:#302941;
    --line-strong:#453B59;
    --accent:#B49AE4;
    --accent-soft:#2A2140;
    --crit:#F0899E;
    --crit-soft:#3A1F28;
    --warn:#E3B166;
    --warn-soft:#372A16;
    --ok:#79C7A6;
    --ok-soft:#173328;
    --off:#8B8399;
    --off-soft:#262130;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6);
  }
}
:root[data-theme="dark"]{
  --ground:#141119;
  --surface:#1D1926;
  --surface-2:#251F31;
  --ink:#EFEBF5;
  --ink-2:#C3BBD2;
  --muted:#918AA1;
  --line:#302941;
  --line-strong:#453B59;
  --accent:#B49AE4;
  --accent-soft:#2A2140;
  --crit:#F0899E;
  --crit-soft:#3A1F28;
  --warn:#E3B166;
  --warn-soft:#372A16;
  --ok:#79C7A6;
  --ok-soft:#173328;
  --off:#8B8399;
  --off-soft:#262130;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -12px rgba(0,0,0,.6);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:"Zen Kaku Gothic New","Hiragino Kaku Gothic ProN","Yu Gothic",system-ui,sans-serif;
  font-size:15px; line-height:1.75; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1060px; margin:0 auto; padding:0 22px 80px}

/* ── 見出し ───────────────────────────────────────────── */
.mast{
  border-bottom:1px solid var(--line);
  padding:38px 0 24px; margin-bottom:34px;
  display:flex; flex-wrap:wrap; gap:20px 32px; align-items:flex-end; justify-content:space-between;
}
.mast h1{
  font-family:"Shippori Mincho",serif; font-weight:700;
  font-size:clamp(26px,4vw,36px); line-height:1.3; margin:0;
  letter-spacing:.02em; text-wrap:balance;
}
.mast .sub{color:var(--muted); font-size:13.5px; margin-top:6px}
.stamp{
  display:flex; gap:26px; font-size:12.5px; color:var(--muted);
}
.stamp b{display:block; font-family:"Roboto Mono",monospace; font-size:19px;
  color:var(--ink); font-weight:500; font-variant-numeric:tabular-nums; line-height:1.2}

/* ── 冒頭の判断 ───────────────────────────────────────── */
.lede{
  background:var(--surface); border:1px solid var(--line);
  border-left:3px solid var(--accent);
  border-radius:3px; padding:22px 26px; margin-bottom:40px; box-shadow:var(--shadow);
}
.lede p{margin:0 0 10px; max-width:66ch}
.lede p:last-child{margin-bottom:0}
.lede strong{color:var(--accent); font-weight:700}

/* ── セクション ───────────────────────────────────────── */
section{margin-bottom:44px}
.shead{display:flex; align-items:baseline; gap:12px; margin-bottom:4px; flex-wrap:wrap}
.shead h2{
  font-family:"Shippori Mincho",serif; font-size:19px; font-weight:700;
  margin:0; letter-spacing:.03em;
}
.shead .n{
  font-family:"Roboto Mono",monospace; font-size:12px; color:var(--muted);
  font-variant-numeric:tabular-nums;
}
.sdesc{color:var(--muted); font-size:13px; margin:0 0 18px; max-width:66ch}
.rule{height:1px; background:var(--line); margin:0 0 18px}

/* ── 案件カード ───────────────────────────────────────── */
.card{
  background:var(--surface); border:1px solid var(--line); border-radius:3px;
  padding:20px 22px; margin-bottom:14px; box-shadow:var(--shadow);
  display:grid; gap:14px;
}
.card.lead{border-color:var(--accent); border-width:1px 1px 1px 3px}
.chead{display:flex; gap:12px; align-items:flex-start; flex-wrap:wrap}
.grade{
  flex:none; width:30px; height:30px; border-radius:2px;
  display:grid; place-items:center;
  font-family:"Roboto Mono",monospace; font-weight:500; font-size:14px;
  background:var(--accent-soft); color:var(--accent); border:1px solid var(--accent);
}
.grade.b{background:var(--off-soft); color:var(--ink-2); border-color:var(--line-strong)}
.grade.c{background:transparent; color:var(--muted); border-color:var(--line-strong)}
.ctitle{flex:1 1 300px; min-width:0}
.ctitle h3{
  margin:0; font-size:16px; font-weight:700; line-height:1.5; text-wrap:balance;
}
.ctitle .org{color:var(--muted); font-size:12.5px; margin-top:3px}

/* ── ステータス表示 ───────────────────────────────────── */
.pill{
  display:inline-flex; align-items:center; gap:6px; flex:none;
  padding:3px 10px; border-radius:2px; font-size:11.5px; font-weight:700;
  letter-spacing:.06em; border:1px solid;
}
.p-crit{background:var(--crit-soft); color:var(--crit); border-color:var(--crit)}
.p-warn{background:var(--warn-soft); color:var(--warn); border-color:var(--warn)}
.p-ok{background:var(--ok-soft); color:var(--ok); border-color:var(--ok)}
.p-off{background:var(--off-soft); color:var(--off); border-color:var(--line-strong)}

/* ── 締切カウンタ ─────────────────────────────────────── */
.dl{display:flex; align-items:center; gap:14px; flex-wrap:wrap}
.dl .days{
  font-family:"Roboto Mono",monospace; font-variant-numeric:tabular-nums;
  font-size:26px; font-weight:500; line-height:1; color:var(--ink);
}
.dl .days.urgent{color:var(--crit)}
.dl .days small{font-size:12px; color:var(--muted); margin-left:3px; font-weight:400}
.dl .date{font-size:12.5px; color:var(--muted); font-family:"Roboto Mono",monospace}
.bar{flex:1 1 160px; height:4px; background:var(--surface-2); border-radius:2px; overflow:hidden; min-width:100px}
.bar i{display:block; height:100%; background:var(--accent); border-radius:2px}
.bar i.urgent{background:var(--crit)}

/* ── 明細表 ───────────────────────────────────────────── */
.facts{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:2px; background:var(--line); border:1px solid var(--line); border-radius:2px; overflow:hidden;
}
.facts div{background:var(--surface); padding:9px 12px}
.facts dt{font-size:11px; color:var(--muted); letter-spacing:.06em; margin-bottom:2px}
.facts dd{margin:0; font-size:13.5px; font-weight:500; font-variant-numeric:tabular-nums}
.note{font-size:13.5px; color:var(--ink-2); margin:0; max-width:70ch}
.note b{color:var(--ink)}
.note.flag{
  background:var(--warn-soft); border-left:2px solid var(--warn);
  padding:10px 14px; border-radius:0 2px 2px 0; color:var(--ink-2);
}
.src{font-size:12px}
.src a{color:var(--accent); text-decoration:none; border-bottom:1px solid var(--line-strong)}
.src a:hover,.src a:focus-visible{border-bottom-color:var(--accent)}
a:focus-visible{outline:2px solid var(--accent); outline-offset:3px; border-radius:1px}

/* ── 一覧表 ───────────────────────────────────────────── */
.scroll{overflow-x:auto; border:1px solid var(--line); border-radius:3px; background:var(--surface)}
table{border-collapse:collapse; width:100%; font-size:13px; min-width:640px}
th,td{padding:9px 14px; text-align:left; border-bottom:1px solid var(--line); vertical-align:top}
th{
  font-size:11px; letter-spacing:.08em; color:var(--muted); font-weight:700;
  background:var(--surface-2); white-space:nowrap;
}
tbody tr:last-child td{border-bottom:none}
td.d{font-family:"Roboto Mono",monospace; font-variant-numeric:tabular-nums; white-space:nowrap; color:var(--ink-2)}
td.g{font-family:"Roboto Mono",monospace; color:var(--muted); text-align:center}
.star{color:var(--accent); font-weight:700}

/* ── 巡回記録 ─────────────────────────────────────────── */
.foot{border-top:1px solid var(--line); padding-top:22px; margin-top:52px; font-size:12.5px; color:var(--muted)}
.foot h3{font-family:"Shippori Mincho",serif; font-size:14px; color:var(--ink); margin:0 0 10px; letter-spacing:.04em}
.foot ul{margin:0; padding-left:18px}
.foot li{margin-bottom:4px}
@media (max-width:560px){
  .stamp{gap:18px}
  .card{padding:16px}
}
.note.dec-go{border-left:3px solid #1f7a3d;background:rgba(31,122,61,.07)}
.note.dec-no{border-left:3px solid #8a8f98;background:rgba(138,143,152,.07)}

/* ── 次年度候補の月ごとの束 ─────────────────────────── */
details{border:1px solid var(--line); border-radius:3px; background:var(--surface); margin-bottom:8px}
details[open]{box-shadow:var(--shadow)}
summary{
  cursor:pointer; padding:11px 16px; font-weight:700; font-size:14px;
  display:flex; align-items:center; gap:10px; list-style:none;
}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸"; color:var(--accent); font-size:11px}
details[open] summary::before{content:"▾"}
details[open] summary{border-bottom:1px solid var(--line)}
summary .cnt{
  font-family:"Roboto Mono",monospace; font-size:11.5px; color:var(--muted); font-weight:400;
}
details .scroll{border:none; border-radius:0}
</style>"""

# 残日数はここで計算する。**HTML に数値を書かない**
TAIL = r"""<script>
(function(){
  // 残日数は閲覧時に計算する。数値の直書きをやめ、日付の陳腐化を防ぐ。
  var JST=9*60;
  function todayJST(){
    var n=new Date();
    var utc=n.getTime()+n.getTimezoneOffset()*60000;
    var j=new Date(utc+JST*60000);
    return new Date(j.getFullYear(),j.getMonth(),j.getDate());
  }
  var t=todayJST();
  document.querySelectorAll('.dl[data-deadline]').forEach(function(el){
    var p=el.getAttribute('data-deadline').split('-');
    var d=new Date(+p[0],+p[1]-1,+p[2]);
    var days=Math.round((d-t)/86400000);
    var box=el.querySelector('.days'), bar=el.querySelector('.bar i');
    if(!box) return;
    var label=days<0?'超過':(days===0?'本日':days);
    box.innerHTML=label+(days>0?'<small>日</small>':'');
    var urgent=days<=7;
    box.classList.toggle('urgent',urgent);
    if(bar){
      var pct=days<0?100:Math.max(4,Math.min(100,Math.round((1-days/60)*100)));
      bar.style.width=pct+'%';
      bar.classList.toggle('urgent',urgent);
    }
    var pill=el.closest('.card') && el.closest('.card').querySelector('.pill');
    if(pill && days<0){ pill.textContent='締切超過'; pill.className='pill p-off'; }
  });
  // ヘッダーに閲覧日を表示
  var st=document.querySelector('.stamp');
  if(st){
    var n=new Date(), utc=n.getTime()+n.getTimezoneOffset()*60000, j=new Date(utc+JST*60000);
    var pad=function(x){return (x<10?'0':'')+x;};
    var el=document.createElement('div');
    el.innerHTML='閲覧日<b>'+pad(j.getMonth()+1)+'.'+pad(j.getDate())+'</b>';
    st.appendChild(el);
  }
})();
</script>
"""


def main():
    td, hm = today()
    rows = load()
    b, body = build(rows, td, hm)
    if '--check' in sys.argv:
        for k in ('now', 'going', 'coming', 'watch', 'grade', 'next', 'out'):
            print('%-6s %3d' % (k, len(b[k])))
        total = sum(len(b[k]) for k in
                    ('now', 'going', 'coming', 'watch', 'grade', 'next', 'out'))
        print('合計   %3d / 台帳 %d' % (total, len(rows)))
        assert total == len(rows), '**仕分けで行が落ちている**'
        return
    OUT.write_text(HEAD + '\n\n<div class="wrap">\n' + body + '\n</div>\n\n' + TAIL,
                   encoding='utf-8')
    print('%s を書き出しました（%s 現在・台帳%d行）' % (OUT, td, len(rows)))
    print('いま決める %d / 進行中 %d / 公告待ち %d / 見ておく %d / 等級の壁 %d / 次年度 %d / 対象外 %d'
          % (len(b['now']), len(b['going']), len(b['coming']), len(b['watch']),
             len(b['grade']), len(b['next']), len(b['out'])))


if __name__ == '__main__':
    main()
