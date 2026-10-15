# -*- coding: utf-8 -*-
"""落札額の相場表（`reports/souba.html`）を `data/chancenavi_souba_*.csv` から作る。

**手で書かない。**公募ボードと同じ作法である（CLAUDE.md）。
相場は案件の種類ごとに分けて出す。**ひとつの中央値に混ぜてはならない。**
什器の購入（7,124万円）と展示会出展の装飾（338万円）を同じ列に並べると、
**どちらの数字も判断に使えなくなる。**
"""
import csv
import datetime
import glob
import html
import io
import os
import re
import statistics
import sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST = ZoneInfo('Asia/Tokyo')
OUT = os.path.join(ROOT, 'reports/souba.html')

# **並べる順は「当社の本業に近い順」である。**什器は最後。
GROUPS = [
    ('展示会への出展（企画運営・装飾）',
     r'展示会|出展|ブース出展|パビリオン|EXPO|CEATEC|H\.C\.R|ギフト・?ショー|'
     r'ケアウィーク|化粧品開発展|Airshow|商談会',
     '当社の中核。公社・都産技研が毎年出す型で、Care Show Japan 2027 や '
     'SXSW のブース装飾と同じ列に並ぶ'),
    ('セミナー・講演会・会議の運営',
     r'セミナー|講習|講演|フォーラム|会議運営|推進会議|コンテスト|サイエンスフェア|'
     r'個別相談|動画セミナー|配信',
     '公社の「東京展開セミナー運営業務委託（インド／シンガポール）」と同じ型'),
    ('フェア・イベントの運営',
     r'フェア|イベント|交流会|祭|設営・撤去',
     '東京農林水産フェアは令和4年度から毎年出ている。**同じ業務で3,795,000円→'
     '3,839,000円→3,927,000円→5,698,000円**と推移している'),
    ('施設の管理・運営',
     r'管理運営|宿泊室|清掃|会館',
     '当社の領域ではない。判定器（bin/rank.py）が拾ったものをそのまま載せている'),
    ('什器・物品の購入／借入',
     r'什器|購入|買入|借入|レンタル|LAN配線',
     '**当社の領域ではない。**判定器が「什器」を展示・出展の語として拾っている。'
     '取りこぼしを防ぐため落とさず、ここに分けて置く'),
]

PAL = '''/* 版面：藍の罫線と朱の訂正印。入札経過調書そのものの配色にする */
:root{
  --ground:#F7F5F0;      /* 生成りの和紙 */
  --surface:#FFFFFF;
  --surface-2:#EFEDE6;
  --ink:#1A1A17;
  --ink-2:#4A4942;
  --muted:#7C7A70;
  --line:#DDDAD0;
  --line-strong:#C3BFB2;
  --accent:#1F3A5F;      /* 藍 */
  --accent-soft:#E6EBF2;
  --mark:#A5321E;        /* 朱（訂正・注意） */
  --mark-soft:#F8EAE6;
  --ok:#2A6049;
  --ok-soft:#E4EFE9;
  --shadow:0 1px 2px rgba(26,26,23,.05), 0 10px 28px -16px rgba(26,26,23,.22);
  color-scheme:light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ground:#13151A; --surface:#1B1E25; --surface-2:#232832;
    --ink:#EDEAE3; --ink-2:#C2BEB3; --muted:#8C897F;
    --line:#2C313B; --line-strong:#434A57;
    --accent:#8FB3DC; --accent-soft:#1D2735;
    --mark:#E89A86; --mark-soft:#36211C;
    --ok:#7FBFA2; --ok-soft:#17291F;
    --shadow:0 1px 2px rgba(0,0,0,.45), 0 10px 28px -16px rgba(0,0,0,.7);
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --ground:#13151A; --surface:#1B1E25; --surface-2:#232832;
  --ink:#EDEAE3; --ink-2:#C2BEB3; --muted:#8C897F;
  --line:#2C313B; --line-strong:#434A57;
  --accent:#8FB3DC; --accent-soft:#1D2735;
  --mark:#E89A86; --mark-soft:#36211C;
  --ok:#7FBFA2; --ok-soft:#17291F;
  --shadow:0 1px 2px rgba(0,0,0,.45), 0 10px 28px -16px rgba(0,0,0,.7);
  color-scheme:dark;
}'''


def yen(n):
    return '{:,}'.format(int(n))


def esc(s):
    return html.escape(s or '')


def load():
    fs = sorted(glob.glob(os.path.join(ROOT, 'data/chancenavi_souba_*.csv')))
    if not fs:
        print('**data/chancenavi_souba_*.csv が無い。'
              '先に `python3 bin/chancenavi_souba.py` を実行すること。**')
        sys.exit(1)
    return fs[-1], list(csv.DictReader(io.open(fs[-1], encoding='utf-8')))


def main():
    now = datetime.datetime.now(JST)
    src, rows = load()
    for r in rows:
        r['_v'] = int(r['落札・見積金額'])
    used, groups = set(), []
    for name, pat, lead in GROUPS:
        g = [r for r in rows
             if r['提案番号'] not in used and re.search(pat, r['案件名'])]
        for r in g:
            used.add(r['提案番号'])
        if g:
            groups.append((name, lead, sorted(g, key=lambda x: x['_v'])))
    rest = [r for r in rows if r['提案番号'] not in used]
    if rest:
        groups.append(('そのほか', '上の分け方に入らなかったもの。**黙って捨てない**',
                       sorted(rest, key=lambda x: x['_v'])))

    b = []
    b.append('<header class="mast"><div>')
    b.append('<div class="eyebrow">ビジネスチャンス・ナビ 結果公表済み案件</div>')
    b.append('<h1>東京都外郭団体の落札額</h1>')
    b.append('<p class="sub">予定価格は公表されない。<b>落札額は、終わった案件の'
             '「入札経過調書」に書いてある。</b>一般社団法人ジャパンプロモーション</p>')
    b.append('</div><div class="stamp">')
    b.append('<div>基準<b>%s</b></div>' % now.strftime('%m.%d %H:%M'))
    b.append('<div>読めた案件<b>%d</b></div>' % len(rows))
    b.append('<div>発注組織<b>%d</b></div>'
             % len(set(r['発注組織'] for r in rows)))
    b.append('</div></header>')

    b.append('<div class="lede"><p class="big">金額が分からないと思っていたのは、'
             '<strong>見ていた場所が違っていたからです。</strong></p>'
             '<p>公社も都産技研も、仕様書を最後まで読んでも金額を1字も書きません。'
             'けれど<b>結果が公表された案件の「案件（詳細）」には入札経過調書が付いており、'
             '落札者名・落札金額・全入札者の入札額がそのまま載っています。</b>'
             'ナビの結果公表済みは1,523件あり、今まで一度も開いていませんでした。</p>'
             '<p class="fine">出どころ＝<code>%s</code>／'
             'この画面は <code>bin/build_souba.py</code> が作っています。手で書いていません。'
             '<b>金額は調書の記載そのままで、推計は1件もありません。</b></p></div>'
             % esc(os.path.basename(src)))

    for name, lead, g in groups:
        v = [r['_v'] for r in g]
        med = int(statistics.median(v))
        b.append('<section><div class="shead"><h2>%s</h2>'
                 '<span class="n">%d件</span></div>' % (esc(name), len(g)))
        b.append('<p class="sdesc">%s</p>' % lead.replace('**', ''))
        b.append('<div class="nums"><div><dt>中央値</dt><dd class="key">%s<small>円</small></dd></div>'
                 '<div><dt>最小</dt><dd>%s<small>円</small></dd></div>'
                 '<div><dt>最大</dt><dd>%s<small>円</small></dd></div></div>'
                 % (yen(med), yen(v[0]), yen(v[-1])))
        hi = v[-1] or 1
        b.append('<div class="scroll"><table><thead><tr>'
                 '<th>金額</th><th>規模</th><th>落札者</th>'
                 '<th>件名</th><th>発注</th><th>入札</th></tr></thead><tbody>')
        for r in g:
            w = max(2, round(r['_v'] * 100.0 / hi))
            zei = r['税区分'] or '区分不明'
            note = r.get('注記') or ''
            n = r.get('入札額の件数（＝入札者数）') or r.get('他の入札者数') or '0'
            b.append('<tr>')
            b.append('<td class="d"><b>%s</b><div class="zei %s">%s</div></td>'
                     % (yen(r['_v']), 'warn' if zei != '税込' else '', esc(zei)))
            b.append('<td class="barcell"><span class="bar"><i style="width:%d%%"></i></span></td>' % w)
            b.append('<td class="who">%s</td>'
                     % (esc(r['落札者']) if r['落札者']
                        else '<span class="unk">氏名を読めず</span>'))
            b.append('<td class="nm">%s%s</td>'
                     % (esc(r['案件名']),
                        ('<div class="note">▲ %s</div>' % esc(note)) if note else ''))
            b.append('<td class="org">%s</td>' % esc(r['発注組織']))
            b.append('<td class="d bid">%s<small>者</small>%s</td>'
                     % (esc(str(n)),
                        ('<div class="seq">%s</div>'
                         % esc(' / '.join(yen(x) for x in
                                          (r['入札額の並び'] or '').split(' / ')[:6]
                                          if x.strip().isdigit()
                                          or x.replace(',', '').isdigit()))
                         if r.get('入札額の並び') else '')))
            b.append('</tr>')
        b.append('</tbody></table></div></section>')

    b.append('<div class="foot"><h3>読み方の注意</h3><ul>'
             '<li><b>税区分を必ず見てください。</b>「税抜」と書いた行は、'
             '1.1倍すると税込になります。調書の書式は発注者ごとに違います</li>'
             '<li><b>「入札」の欄は、調書に載っていた入札額の件数です。</b>'
             '辞退・不参は金額が書かれないため、この数に入りません。'
             '実際の参加者はこれより多いことがあります</li>'
             '<li>▲ の行は、道具が金額を訂正したものです。'
             '<b>調書の「落札金額」の直後に消費税額が並ぶ書式があり、'
             'そのままだと消費税額を落札額として読んでしまいます。</b>'
             '税込額は消費税額の11倍である、という関係で直しています</li>'
             '<li><b>契約不調（落札者なし）は、この表に入れていません。</b>'
             '「読めなかった」ではなく結果なので、別に数えています</li>'
             '</ul></div>')

    head = ('<title>東京都外郭団体の落札額</title>\n'
            '<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            'family=Shippori+Mincho:wght@500;700&family=Zen+Kaku+Gothic+New:'
            'wght@400;500;700&family=Roboto+Mono:wght@400;500&display=swap">\n'
            '<style>\n' + PAL + CSS + '\n</style>\n')
    io.open(OUT, 'w', encoding='utf-8').write(
        head + '\n<div class="wrap">\n' + '\n'.join(b) + '\n</div>\n')
    print('%s を書き出しました（%s 現在・%d件）'
          % (OUT, now.strftime('%Y-%m-%d %H:%M'), len(rows)))
    for name, lead, g in groups:
        print('  %-24s %2d件  中央値 %s円'
              % (name, len(g), yen(int(statistics.median([r['_v'] for r in g])))))
    return 0


CSS = '''
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:"Zen Kaku Gothic New","Hiragino Kaku Gothic ProN","Yu Gothic",system-ui,sans-serif;
  font-size:15px;line-height:1.75;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;
  padding-left:max(16px,env(safe-area-inset-left,0px));
  padding-right:max(16px,env(safe-area-inset-right,0px));
  padding-block:0 72px}
.mast{display:flex;flex-wrap:wrap;gap:18px 32px;align-items:flex-end;
  justify-content:space-between;border-bottom:2px solid var(--accent);
  padding-block:36px 20px;margin-bottom:30px}
.eyebrow{font-size:11.5px;letter-spacing:.14em;color:var(--accent);font-weight:700}
.mast h1{font-family:"Shippori Mincho",serif;font-weight:700;margin:.18em 0 0;
  font-size:clamp(25px,4vw,35px);line-height:1.28;letter-spacing:.02em;text-wrap:balance}
.mast .sub{color:var(--muted);font-size:13px;margin:7px 0 0;max-width:60ch}
.mast .sub b{color:var(--ink-2)}
.stamp{display:flex;gap:24px;font-size:11.5px;color:var(--muted);flex-wrap:wrap}
.stamp b{display:block;font-family:"Roboto Mono",monospace;font-size:18px;
  color:var(--ink);font-weight:500;font-variant-numeric:tabular-nums;line-height:1.2}
.lede{background:var(--surface);border:1px solid var(--line);
  border-left:3px solid var(--accent);border-radius:2px;
  padding:20px 24px;margin-bottom:40px;box-shadow:var(--shadow)}
.lede p{margin:0 0 10px;max-width:68ch}
.lede p:last-child{margin-bottom:0}
.lede .big{font-size:17px;line-height:1.7}
.lede strong{color:var(--accent);font-weight:700}
.lede .fine{font-size:12px;color:var(--muted)}
code{font-family:"Roboto Mono",monospace;font-size:.88em;
  background:var(--surface-2);padding:1px 5px;border-radius:2px}
section{margin-bottom:44px}
.shead{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:3px}
.shead h2{font-family:"Shippori Mincho",serif;font-size:19px;font-weight:700;
  margin:0;letter-spacing:.03em}
.shead .n{font-family:"Roboto Mono",monospace;font-size:12px;color:var(--muted);
  font-variant-numeric:tabular-nums}
.sdesc{color:var(--muted);font-size:13px;margin:0 0 14px;max-width:70ch}
.nums{display:flex;gap:2px;background:var(--line);border:1px solid var(--line);
  border-radius:2px;overflow:hidden;margin-bottom:14px;flex-wrap:wrap}
.nums>div{background:var(--surface);padding:9px 16px;flex:1 1 130px;min-width:0}
.nums dt{font-size:10.5px;letter-spacing:.1em;color:var(--muted)}
.nums dd{margin:0;font-family:"Roboto Mono",monospace;font-size:17px;font-weight:500;
  font-variant-numeric:tabular-nums}
.nums dd.key{color:var(--accent);font-size:21px}
.nums dd small{font-size:11px;color:var(--muted);margin-left:2px;font-weight:400}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:2px;
  background:var(--surface);box-shadow:var(--shadow)}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:860px}
th,td{padding:10px 13px;text-align:left;border-bottom:1px solid var(--line);
  vertical-align:top}
th{font-size:10.5px;letter-spacing:.1em;color:var(--muted);font-weight:700;
  background:var(--surface-2);white-space:nowrap}
tbody tr:last-child td{border-bottom:none}
td.d{font-family:"Roboto Mono",monospace;font-variant-numeric:tabular-nums;
  white-space:nowrap}
td.d b{font-size:14.5px}
.zei{font-size:10px;letter-spacing:.06em;color:var(--muted);margin-top:2px}
.zei.warn{color:var(--mark);font-weight:700}
.barcell{width:110px;min-width:90px}
.bar{display:block;height:5px;background:var(--surface-2);border-radius:3px;
  overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent);border-radius:3px}
td.who{font-size:12.5px;color:var(--ink-2);max-width:17ch}
.unk{color:var(--mark);font-size:11.5px}
td.nm{min-width:0;max-width:40ch}
.note{margin-top:4px;font-size:11.5px;color:var(--mark);
  background:var(--mark-soft);padding:5px 9px;border-radius:2px;
  border-left:2px solid var(--mark)}
td.org{font-size:11.5px;color:var(--muted);max-width:16ch}
td.bid small{font-size:10px;color:var(--muted);margin-left:1px}
.seq{font-size:10.5px;color:var(--muted);margin-top:3px;max-width:22ch;
  white-space:normal;line-height:1.5}
.foot{border-top:1px solid var(--line);padding-top:22px;margin-top:8px;
  font-size:12.5px;color:var(--muted)}
.foot h3{font-family:"Shippori Mincho",serif;font-size:14px;color:var(--ink);
  margin:0 0 10px;letter-spacing:.04em}
.foot ul{margin:0;padding-left:18px}
.foot li{margin-bottom:6px;max-width:74ch}
.foot b{color:var(--ink-2)}
a:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
@media (max-width:560px){
  .stamp{gap:16px}
  .lede{padding:16px}
}
'''

if __name__ == '__main__':
    sys.exit(main())
