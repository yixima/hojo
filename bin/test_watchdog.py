# -*- coding: utf-8 -*-
"""見落とし検出器の回帰テスト。**ネットワークを使わない。**

なぜ要るか
----------
2026-09-15、**TOKYO LIGHTS 2027・SusHi Tech Tokyo 2027・Delicious Museum 2027・
多摩の森 の4件を丸ごと取り逃していた**ことが判明した。
検出器を作っただけでは同じことが起きる。**落ちるべきものをわざと作り、
実際に落ちることを確かめる**（マニュアル L0 §2 型A）。

    python3 bin/test_watchdog.py
"""
import csv
import datetime
import io
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'bin'))

ok = fail = 0


def check(name, got, want):
    global ok, fail
    if got == want:
        ok += 1
        print('  OK   %s' % name)
    else:
        fail += 1
        print('  NG   %s\n       得た値 %r\n       期待値 %r' % (name, got, want))


def rows_of(path):
    with io.open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


# ── 1. 制度台帳の検査が、壊した行で鳴るか ───────────────────
import programs  # noqa: E402

NOW = datetime.date(2026, 9, 15)
BASE = dict(制度ID='x', 制度名='試験用', 所管='試験', 種別='補助金',
            当社の立ち位置='申請者', 状態='現存', 根拠URL='https://example.invalid/',
            補助率='', 上限額='', 公募開始='', 締切='', 前段関門='',
            次回見込み='', 最終確認日='2026-09-01', 備考='')


def one(**kw):
    r = dict(BASE)
    r.update(kw)
    return [r]


h, s, soon = programs.check(one(), NOW)
check('正常な行では鳴らない', (len(h), len(s)), (0, 0))

h, s, soon = programs.check(one(最終確認日=''), NOW)
check('最終確認日が空→止める', len(h) >= 1, True)

h, s, soon = programs.check(one(最終確認日='2026-01-01'), NOW)
check('一次資料が古い→注意', any('確認していない' in m for _, _, m in s), True)

h, s, soon = programs.check(one(締切='2026-10-01', 前段関門='2026-10-20'), NOW)
check('前段関門が締切より後→止める', any('より後' in m for _, _, m in h), True)

h, s, soon = programs.check(one(次回見込み='2026-08-01'), NOW)
check('次回見込みが過去→注意', any('過ぎている' in m for _, _, m in s), True)

h, s, soon = programs.check(one(所管=''), NOW)
check('必須列が空→止める', any('必須列が空' in m for _, _, m in h), True)

h, s, soon = programs.check(one(制度名='近い', 締切='2026-10-01'), NOW)
check('締切が60日以内→予告に出る', [x[2] for x in soon], ['締切'])

h, s, soon = programs.check(one(締切='2027-06-01'), NOW)
check('遠い締切は予告に出さない', soon, [])

# **廃止と書いた行は、未確認でも鳴らせない。**鳴ると、廃止の記録を消したくなる
h, s, soon = programs.check(one(状態='廃止（統合）', 最終確認日=''), NOW)
check('廃止の行は未確認でも鳴らさない', (len(h), len(s)), (0, 0))

# ── 2. 実データが検査を通るか ───────────────────────────
real = rows_of(os.path.join(ROOT, 'data', 'programs.csv'))
ids = [r['制度ID'] for r in real]
check('制度IDが重複していない', len(ids), len(set(ids)))
check('廃止した制度を台帳から消していない',
      any(not r['状態'].startswith('現存') for r in real), True)

# ── 3. 掃引が「台帳に無いもの」を本当に見つけるか ──────────────
import sweep_channels as sw  # noqa: E402

LEDGER = os.path.join(ROOT, 'data', 'ledger.csv')
led = rows_of(LEDGER)
keys = {sw.norm(r['案件名']) for r in led}

known_name = 'TOKYO LIGHTS 2027企画・運営等業務委託'
check('台帳にある案件は「既知」と判定する', sw.known(sw.norm(known_name), keys), True)

# **わざと台帳から消す。**消したら未登録として出なければならない
keys_broken = {k for k in keys if 'TOKYOLIGHTS' not in k.upper().replace(' ', '')}
check('台帳から消すと「未登録」に変わる',
      sw.known(sw.norm(known_name), keys_broken), False)

# 前後が削れた表記でも取りこぼさない
check('前後が削れた表記でも既知と分かる',
      sw.known(sw.norm('【全国】TOKYO LIGHTS 2027企画・運営等業務委託 事業者の募集'), keys), True)

# 見出しの拾い方
html = ('<ul><li>【全国】TOKYO LIGHTS 2027企画・運営等業務委託 事業者の募集</li>'
        '<li>採択者一覧を公開しました</li>'
        '<li>入札・発注案件を探したい</li>'
        '<li>令和８年度東京ｉＣＤＣフォーラム運営業務委託</li></ul>')
t = sw.titles(html)
check('案件だけを拾い、採択結果や導線を捨てる', len(t), 2)

# ── 3.5 締切を取れていない新規案件が、来年の束に隠れないか ─────
# 2026-09-16、チャネル掃引で見つけた3件は締切が未取得だった。
# 日付が無い行は従来「次年度候補」へ落ち、**いま動いている案件が来年の束に隠れた。**
import datetime as _dt  # noqa: E402
import build_board as bb  # noqa: E402

_base = {k: '' for k in ('初報日', '案件名', '発注機関', '種別', '締切', '締切時刻',
                         '締切種別', '締切確認日', '予定価格', '格付', '応募形態',
                         '資格要否', '状態', 'URL')}


def _row(**kw):
    r = dict(_base)
    r.update(kw)
    return r


_now = _dt.datetime(2026, 9, 16, 8, 0)
b = bb.buckets([_row(案件名='締切が無い新規', 状態='**締切未取得。**掃引で発見')], _now)
check('締切未取得は確認面に出る（次年度候補に隠さない）',
      (len(b['unverified']), len(b['next'])), (1, 0))

b = bb.buckets([_row(案件名='ただの日付なし', 状態='新規')], _now)
check('ふつうの日付なしは従来どおり次年度候補', len(b['next']), 1)

b = bb.buckets([_row(案件名='締切未取得だが終了', 締切='2026-09-01', 締切時刻='17:00',
                     状態='**締切未取得。**掃引で発見')], _now)
check('締切未取得でも受付が終わっていれば確認面に出さない', len(b['unverified']), 0)

# ── 3.6 掃引がリンクを持ち帰り、観測を保存するか ─────────────
# 2026-09-16、チャンスナビのトップが**回転表示**であることが判明した。
# 見出しを標準出力に流すだけでは、回転で消えたものは二度と辿れない。
h2 = ('<ul><li><a href="/bcn/detail/123">令和8年度なんとか運営業務委託</a></li>'
      '<li><a href="https://example.jp/x">別件の業務委託の募集</a></li></ul>')
t2 = sw.titles(h2)
check('見出しと一緒にリンクを持ち帰る', [x[1] for x in t2],
      ['/bcn/detail/123', 'https://example.jp/x'])
check('相対リンクを絶対URLにする',
      sw.absolutize('https://www.chancenavi.jp/bcn/', '/bcn/detail/123'),
      'https://www.chancenavi.jp/bcn/detail/123')
check('javascript: は辿れないので捨てる',
      sw.absolutize('https://x.jp/a/', 'javascript:void(0);'), '')
check('絶対URLはそのまま', sw.absolutize('https://x.jp/a/', 'https://y.jp/b'), 'https://y.jp/b')

# ── 3.7 締切欄の自由文を見つけるが、止めはしないか ───────────
# 2026-09-16、枝 znmhfx から引き継いだ監視対象4件が「2027-02〜03（予測）」と
# 書かれており、日付として読めず**来年の束に隠れた。**
# 一方「未確認」と書かれた行は61件あり、次年度候補にあるのが正しい。
# **見つけるが止めない。**止めると一括書き換えを誘発する（実際にやって戻した）。
_ng, _free = bb.audit_ledger([
    _row(案件名='予測', 締切='2027-05（予測）'),
    _row(案件名='未確認', 締切='未確認'),
    _row(案件名='正常', 締切='2026-10-01'),
])
check('自由文の締切を見つける', sorted(v for _, v in _free),
      ['2027-05（予測）', '未確認'])
check('自由文では止めない（ngに入れない）', _ng, [])

_ng, _free = bb.audit_ledger([_row(案件名='日時混入', 締切='2026-09-29 17:00')])
check('締切欄への日時の混入は止める', len(_ng), 1)

# 【予測】の行は、締切が無くても「公告待ち」に出る（次年度候補に落とさない）
b = bb.buckets([_row(案件名='予測もの', 状態='【予測】まだ公告されていない')], _now)
check('【予測】は締切が無くても公告待ちに出る', (len(b['coming']), len(b['next'])), (1, 0))

# ── 3.8 列名そのものの破壊（BOM）を捕まえるか ─────────────
# 2026-09-16、枝の統合で BOM（U+FEFF）がヘッダ先頭に入り、`r['初報日']` が
# KeyError になった。**板は初報日を読まないため平然と動き、どの検査も鳴らなかった。**
_bom = dict(_base)
_bom['\ufeff初報日'] = _bom.pop('初報日')
_ng, _free = bb.audit_ledger([_bom])
check('BOM混入を止める', any('列が想定と違う' in m for _, m, _ in _ng), True)

_ng, _free = bb.audit_ledger([_row(案件名='正常')])
check('正常な列では鳴らない', [m for _, m, _ in _ng], [])

# ── 3.9 日付を JST で採っているか（沈黙する検出器の検出） ─────
# 2026-09-21 判明。`bin/sweep_channels.py` が観測日時を naive な
# `datetime.now()` で刻んでいた。コンテナは UTC なので、毎朝 08:0x JST の掃引は
# **「前日 23:0x」として記録されていた。**
# その結果、「本日（JSTの日付）はじめて見た見出し」を数えると**常に0件**になる。
# 0件は「新規が無かった」ではなく「その日付の行が1つも無い」という意味で、
# 3日続けて「新規0件」と報告していたが、実際には 12件・1件・2件あった。
# **鳴らない検出器は、検出器が無いのと同じである。**
_TZ_SRC = [
    ('bin/sweep_channels.py', '観測日時（data/sweep_log.csv に刻む）'),
    ('workflow/awards_pportal.py', '落札実績の出力ファイル名'),
    ('bin/greenexpo_sweep.py', 'GREEN×EXPO 掃引の出力ファイル名'),
]
import re as _re
for _f, _why in _TZ_SRC:
    _t = io.open(os.path.join(ROOT, _f), encoding='utf-8').read()
    # コメント行は除く。**事故の経緯を書いた注釈まで検出すると、
    # 注釈を消すほうへ圧力がかかる。**残すべきは注釈で、直すべきはコードである。
    _t = '\n'.join(l for l in _t.split('\n') if not l.lstrip().startswith('#'))
    # 日付を作る式に、タイムゾーンの指定が無いものが残っていないか
    _naive = [m.group(0) for m in
              _re.finditer(r'datetime\.now\(\s*\)|date\.today\(\s*\)', _t)]
    check('%s は日付を JST で採る（%s）' % (_f, _why), _naive, [])

# 検出器そのものが効いているか：わざと naive な式を混ぜたら見つかること
_fake = "x = datetime.now()\n"
check('naive な now() を見つけられる',
      bool(_re.search(r'datetime\.now\(\s*\)', _fake)), True)

# ── 3.10 取得の成否を HTTP ステータスで見ているか ───────────────
# 2026-10-05 判明。`bin/greenexpo_sweep.py` は本文が500バイトを超えれば
# 「取得できた」と見なしていた。**自治体の404ページは数十KBのHTMLなので、
# 長さでは本物と区別できない。**
# そのため「サイト内検索の経路が通らなかった県」を数える仕組みを入れた直後の実測が
# 「2県」と出た。HTTPコードを別に測ると**29県**だった。
# **都合のよい数を返す検査は、検査が無いのと同じである。**
# 直したうえで 23県。神奈川県の GREEN×EXPO 賓客等接遇業務委託（上限4億337万円・
# 等級要件なし）を、参加意思表明 9/24 15時が閉じた11日後に検出した件の原因である。
_ge = io.open(os.path.join(ROOT, 'bin/greenexpo_sweep.py'), encoding='utf-8').read()
check('greenexpo_sweep に fetch2（ステータスを返す取得）がある',
      'def fetch2(' in _ge, True)
check('検索経路は 2xx のみ数える',
      bool(_re.search(r'if 200 <= code < 300: reach\[.search.\] \+= 1', _ge)), True)
check('経路が死んだ県を申告する',
      '検索経路が1つも通らなかった県' in _ge, True)
# 検出器そのものの検出：ガードを外したら見つけられること
check('ガードが無ければ見つけられる',
      bool(_re.search(r'if 200 <= code < 300', "reach['search'] += 1")), False)

# ── 3.11 TLS検証を切っていないか ────────────────────────────
# 2026-10-05 判明。curl を呼ぶ8本すべてが `-k`（証明書の検証を省く）を付けていた。
# この環境の決めごとは「TLS検証は決して切らない」である（/root/.ccr/README.md）。
# 外して実測したところ、**どのサイトも 200 を返した。**つまり必要ではなかった。
# `-k` は中間者を見分けられなくするだけでなく、**証明書の不備という異常を
# 黙って飲み込む。**鳴らない検出器と同じ型である。
_curl_users = ['bin/sweep_channels.py', 'bin/fetchlib.py', 'bin/triage.py',
               'bin/discover_channels.py', 'bin/follow_channels.py',
               'bin/greenexpo_sweep.py', 'bin/jgrants_sweep.py',
               'bin/retry_unreached.py', 'bin/national_events_sweep.py',
               'bin/watch_repeaters.py']
for _p in _curl_users:
    _f = os.path.join(ROOT, _p)
    if not os.path.exists(_f): continue
    _s = io.open(_f, encoding='utf-8').read()
    check('%s は TLS検証を切っていない（-k が無い）' % _p,
          ("'-k'" in _s) or ('"-k"' in _s), False)
# 検出器そのものの検出：`-k` があれば見つけられること
check('-k があれば見つけられる', "'-k'" in "['curl', '-sSL', '-k', u]", True)

# ── 3.12 相対URLの解決を自前で書いていないか ──────────────────
# 2026-10-05 判明。`absolutize()` が `base.rsplit('/',1)[0] + '/' + href.lstrip('./')`
# と書いていた。**`lstrip('./')` は `../../../../` の「上へ4つ」をただ削り落とす。**
# その結果
# `/kensei/nyuusatsu/compe/sanka/kensei/nyuusatsu/compe/sanka/1099190.html`
# のような経路の二重URLが生まれ、**掃引ログには見出しが残るので「取れている」
# ように見えるのに、開くと必ず404になる。**
# 篩分け（triage.py）の「一次資料を取得できなかった54件」のうち38本がこれだった。
# プロトコル相対リンク（`//host/...`）も二重ホストになっていた。
# **URLの解決は urljoin に任せる。自前の連結に戻さない。**
_sw = io.open(os.path.join(ROOT, 'bin/sweep_channels.py'), encoding='utf-8').read()
check('absolutize は urljoin を使う', 'urllib.parse.urljoin' in _sw, True)
check('absolutize に自前の連結が残っていない',
      bool(_re.search(r"lstrip\(['\"]\./['\"]\)", _sw)), False)
sys.path.insert(0, os.path.join(ROOT, 'bin'))
import importlib
_sc = importlib.import_module('sweep_channels')
check('プロトコル相対リンクを正しく解く',
      _sc.absolutize('https://a.jp/b/', '//c.jp/d.html'), 'https://c.jp/d.html')
check('上へ戻る相対リンクを正しく解く',
      _sc.absolutize('https://www.pref.iwate.jp/kensei/nyuusatsu/compe/sanka/1102077.html',
                     '../../../../kensei/nyuusatsu/compe/sanka/1099190.html'),
      'https://www.pref.iwate.jp/kensei/nyuusatsu/compe/sanka/1099190.html')

# ── 3.13 篩分けは壊れたURLを直し、詳細を1段たどるか ─────────────
# 既に積んだ掃引ログの壊れたURLは直らない。**読む側でも直す。**
# また、掃引が拾うリンクは一覧ページが多く、**締切と金額は詳細ページにしかない。**
_tr = importlib.import_module('triage')
check('triage は経路の二重を直す',
      _tr.repair('https://www.pref.iwate.jp/kensei/nyuusatsu/compe/sanka/'
                 'kensei/nyuusatsu/compe/sanka/1099190.html'),
      'https://www.pref.iwate.jp/kensei/nyuusatsu/compe/sanka/1099190.html')
check('triage はホストの二重を直す',
      _tr.repair('https://x.jp//x.jp/a/b.html'), 'https://x.jp/a/b.html')
check('triage は正しいURLを壊さない',
      _tr.repair('https://a.jp/b/c/d.html'), 'https://a.jp/b/c/d.html')
check('triage は詳細を1段たどる', 'def find_detail(' in
      io.open(os.path.join(ROOT, 'bin/triage.py'), encoding='utf-8').read(), True)
check('別件のリンクを拾わない（一致が半分未満なら採らない）',
      _tr.find_detail('https://a.jp/list.html',
                      b'<html><a href="/zzz.html">\xe5\x85\xa8\xe3\x81\x8f\xe5\x88\xa5\xe3\x81\xae'
                      b'\xe6\xa1\x88\xe4\xbb\xb6\xe3\x81\xa7\xe3\x81\x99\xe3\x81\xaa</a></html>',
                      '令和8年度観光誘客promotion業務委託の企画提案を募集します'), '')

# ── 3.14 「届かない」の申告が当て推量でないか ──────────────────
# 2026-10-05 判明。候補パス37本を当てに行った道具が「26自治体に届かない」と報告した。
# 同じ26ホストのトップを HTTP コードで実測すると**20が200を返した。**
# **届かなかったのはネットワークではなく、こちらのURLの当て推量だった。**
# サイト自身が張っているリンクを2段たどると17自治体に届いた（神奈川県を含む）。
# **自分の当て推量の失敗を、相手のせいにして申告していた。**
check('リンクをたどる道具がある',
      os.path.exists(os.path.join(ROOT, 'bin/follow_channels.py')), True)
_fo = io.open(os.path.join(ROOT, 'bin/follow_channels.py'), encoding='utf-8').read()
check('たどる道具は2段たどる', 'lv2' in _fo and 'HUB2' in _fo, True)
check('たどる道具は案件行3件以上のURLだけ採る', 'if n >= 3' in _fo, True)
check('たどる道具は届かなかった自治体を名指しする', 'それでも届かない自治体' in _fo, True)

# ── 4. 台帳の件数が減っていないか（破壊の検出） ─────────────
check('台帳が空でない', len(led) > 200, True)

print('\n%d件成功 / %d件失敗' % (ok, fail))
sys.exit(1 if fail else 0)
