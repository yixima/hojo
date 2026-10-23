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

# ── 3.15 前段関門の欄の日付を読めているか ──────────────────
# 2026-10-06 判明。前段関門の欄は日付だけでなく「何を・どこへ出すのか」まで書く欄で、
# 持続化補助金 第20回は
# 「事業支援計画書（様式4）の発行受付締切 2026-12-04（商工会・商工会議所）。
#   ここが実質の期限」
# と書かれていた。`parse_day` は先頭だけを見るため日付が取れず、
# **申請締切 12/15 より11日早い本当の関門 12/4 が、60日以内の予告に1件も出ていなかった。**
# 毎朝の報告の指示は「前段関門があるならその日付を必ず併記する」である。
# **指示はあったが、道具が日付を読めていなかった。**
# 台帳の締切欄に自由文を入れて最重点案件が消えた件（2026-09-21）と同じ型である。
_pg = importlib.import_module('programs')
check('前段関門は文中の日付も拾う',
      str(_pg.find_day('事業支援計画書（様式4）の発行受付締切 2026-12-04（商工会・商工会議所）。'
                       'ここが実質の期限')), '2026-12-04')
check('前段関門に日付が無ければ None',
      _pg.find_day('電子証明書・決算書'), None)
check('締切と公募開始は先頭だけを見る（備考の年号を関門にしない）',
      _pg.parse_day('公募要領第8版(2026-07-21改版) で確認'), None)
check('持続化の様式4 12/04 が予告に出る',
      any(d == __import__('datetime').date(2026, 12, 4)
          for _, d, lb, nm, _g in _pg.check(_pg.load(), _pg.today(), False)[2]
          if lb == '前段関門'), True)

# ── 3.16 期間の「終わり」を締切として採っているか ────────────
# 2026-10-07 判明。公社の契約情報の希望申出期間は
# 「令和8年10月6日9:00～令和8年10月15日14:00」のように1つの欄に2つの日時が入る。
# `re.search` で先頭を採ると**始まり**を拾い、受付中の案件を
# 「残り -24時間」＝もう閉じた、と表示していた。
# **閉じたと誤って言う検出器は、何も言わない検出器より悪い。**
# 判断面から案件が1件消えるのに、画面には何の異常も出ない。
_kk = os.path.join(ROOT, 'bin/gaikaku_keiyaku.py')
check('外郭団体の契約情報を読む道具がある', os.path.exists(_kk), True)
_ks = io.open(_kk, encoding='utf-8').read()
check('期間は全件を採り、最後を締切にする', 'gates(span)' in _ks and 'gs[-1]' in _ks, True)
check('先頭を採る書き方が残っていない',
      bool(_re.search(r'(WAREKI|SEIREKI|WA)\.search\(span\)', _ks)), False)
check('公表日より早い締切は自己矛盾として申告する', '自己矛盾：公表日より締切が早い' in _ks, True)
check('表が読めなかったときに0件と言わない', '0件と報告してはいけない' in _ks, True)
check('認証情報が無いことを明記する', 'CN_USER' in _ks, True)
# 道具そのものを動かして、終わりの日時を採れることを確かめる（ネットワーク不要）
sys.path.insert(0, os.path.join(ROOT, 'bin'))
_kkm = importlib.import_module('gaikaku_keiyaku')
_span = '令和8年10月6日9:00～令和8年10月15日14:00'
_g = _kkm.gates(_span)
check('和暦の期間から2つの日時を取り出せる', len(_g), 2)
check('和暦の終わりは 2026-10-15 14:00',
      (str(_g[-1][0]), _g[-1][1], _g[-1][3]), ('2026-10-15', 14, True))
# TCVB は西暦で「12時」と書く。**片方しか読めない道具は、もう片方を静かに落とす。**
_g2 = _kkm.gates('2026年08月26日 ～ 2026年10月09日12時')
check('西暦「○時」の期間も読める（時刻の無い始まりも拾う）', len(_g2), 2)
check('西暦の終わりは 2026-10-09 12:00',
      (str(_g2[-1][0]), _g2[-1][1], _g2[-1][3]), ('2026-10-09', 12, True))
# **時刻が書いていなければ、書いていないと言う。17時を当てない**
check('時刻の無い日付は「時刻が書いてある」と言わない',
      _kkm.gates('2026年10月09日')[-1][3], False)
check('時刻未確認を画面に出す', '時刻未確認' in _ks, True)
check('対象は2団体以上', len(_kkm.SITES) >= 2, True)
check('TCVB が対象に入っている', any('tcvb' in u for _n, u, _h in _kkm.SITES), True)
check('ナビに入れなくても仕様書を取り寄せられる旨を書いている',
      'keiyaku@tcvb.or.jp' in _ks, True)
check('令和の換算（令和1年＝2019年）', str(_kkm.wa2date(1, 5, 1)), '2019-05-01')

# ── 3.17 格付より先に所在地要件を見ているか ──────────────────
# 2026-10-08 判明。`workflow/eligibility.md` には 8/28 から
# **[5]「市内業者限定」は資格の有無より先に効く／[9]「市内」には3つの意味がある／
# 台帳に載せる際は、格付より先に所在地要件を確認する**と書いてあった。
# それでも同日朝、**応募資格を読まずに2件を「判断していただきたい」として出した。**
# 読んだら両方とも所在地で落ちた＝神戸ものづくり（800万円・「神戸市内に本社」）／
# 青森県ベトナムレセプション（600万円・「ベトナム国及び日本国内に拠点」）。
# **規則が文書にあって誰も実行しないなら、規則が無いのと同じである。**
# `bin/rank.py` の格付は中身の相性だけを見ており、所在地の概念を持たない。
_al = os.path.join(ROOT, 'bin/audit_location.py')
check('所在地要件の検出器がある', os.path.exists(_al), True)
_als = io.open(_al, encoding='utf-8').read()
check('検出器は台帳を書き換えない', 'DictWriter' in _als, False)
check('検出器は規則の出どころを示す', 'eligibility.md' in _als, True)
_alm = importlib.import_module('audit_location')
check('「神戸市内に本社」を判定済みと認める',
      bool(_alm.VERDICT.search('応募資格(1)「神戸市内に本社を置く企業又は団体であること」')), True)
check('「ベトナム国及び日本国内に…拠点を有する」を判定済みと認める',
      bool(_alm.VERDICT.search('ベトナム国及び日本国内に本店、支店または営業所等といった拠点を有すること')), True)
check('「所在地区分：指定なし」を判定済みと認める',
      bool(_alm.VERDICT.search('所在地区分は指定なし')), True)
check('中身の相性だけ書いた行は未判定として鳴る',
      bool(_alm.VERDICT.search('S。展示会の設営運営は当社の本業')), False)
check('rank.py は所在地の概念を持たない（だから別の検出器が要る）',
      bool(_re.search(r'所在地|市内に本社',
           io.open(os.path.join(ROOT, 'bin/rank.py'), encoding='utf-8').read())), False)

# ── 3.18 「セミナー・フォーラムの運営」を当社領域から外していないか ────
# 2026-10-10 判明。公社が同じ日に
#   …東京展開セミナー運営業務委託(インド)／同(シンガポール)
# を出したが、**毎朝の報告（S/A だけを出す）には1件も現れなかった。**
# 原因は2つ。
# ① `bin/rank.py` の DOMAIN['イベント運営'] に**会議体の語が無かった**
#    （セミナー・フォーラム・シンポジウム・講演会・レセプション）。
#    海外×セミナー運営は当社の本業だが、格付Bに落ちていた。
# ② NOISE に `セミナー` が無条件で入っており、**発注案件そのものを捨てる作りだった。**
#    ノイズにしたいのは「受講者を募るお知らせ」であって「運営を委託する公募」ではない。
# **当社は催事・会議の運営会社である。会議体の語を欠いていたのは分母の穴である。**
# 見つけたのは `bin/gaikaku_keiyaku.py`（格付に関係なく受付中を全件出す）だった。
#
# **なお、最初はこれを「件名を70字で切る重複キーのせい」と疑ったが、誤りだった。**
# 実測すると当該件名は50字で、切り詰めは起きていない。
# 切り詰め自体は将来の危険なので外したが、**今回の見落ちの原因ではない。**
_rk = importlib.import_module('rank')
def _judge(n):
    if _rk.NOISE.search(n) and not _rk.NOISE_UNEI.search(n):
        return '除外'
    return _rk.grade(n)[0]
check('海外×セミナー運営は S か A',
      _judge('令和8年度「海外企業とのイノベーション創出支援事業」に係る'
             '東京展開セミナー運営業務委託(インド)') in ('S', 'A'), True)
check('フォーラム開催の業務委託は S か A',
      _judge('令和8年度「BCP策定推進フォーラム」開催に係る業務委託') in ('S', 'A'), True)
check('セミナー運営のプロポーザルは S か A',
      _judge('令和8年度観光セミナー運営業務に係る公募型プロポーザル') in ('S', 'A'), True)
# 逆に、受講者向けのお知らせは拾わない（**緩めすぎると報告が読めなくなる**）
check('受講者募集は除外する', _judge('DX推進セミナー受講者募集のお知らせ'), '除外')
check('開催案内は除外する', _judge('創業セミナーの開催案内'), '除外')
check('説明会の開催告知は除外する', _judge('中小企業向け研修の説明会を開催します'), '除外')
check('会議体の語が DOMAIN に入っている',
      bool(_rk.DOMAIN['イベント運営'].search('フォーラム')) and
      bool(_rk.DOMAIN['イベント運営'].search('セミナー')) and
      bool(_rk.DOMAIN['イベント運営'].search('シンポジウム')), True)

# ── 3.19 件名を切り詰めて重複キーにしていないか（将来の危険を閉じる）────
# 70字を超える件名で、**国名や回次が末尾にある場合**に2件目以降が静かに消える。
# 当社の仕事は海外案件であり、国名こそが見分けどころである。
_TRUNC = _re.compile(r'k\s*=\s*(?:r\[\d+\]|t2?)\[:\d+\]')
for _p in ('bin/triage.py', 'bin/denom.py', 'bin/greenexpo_sweep.py',
           'bin/expo2027.py', 'bin/sweep_channels.py'):
    _f = os.path.join(ROOT, _p)
    if not os.path.exists(_f): continue
    check('%s は件名を切り詰めて重複キーにしない' % _p,
          bool(_TRUNC.search(io.open(_f, encoding='utf-8').read())), False)
check('切り詰めがあれば見つけられる', bool(_TRUNC.search('        k = r[2][:60]')), True)
_long = '令和8年度' + 'あ' * 70
check('70字で切ると末尾の違いが消える',
      len({(_long + '(インド)')[:70], (_long + '(シンガポール)')[:70]}), 1)
check('全文なら残る', len({_long + '(インド)', _long + '(シンガポール)'}), 2)

# ── 3.20 ナビの認証情報をリポジトリに書いていないか ──────────────
# 2026-10-13、生島様よりビジネスチャンス・ナビの認証情報を頂いた。
# **本リポジトリは公開（public）である。**過去に会話原文の流出事故が起きている。
# 認証情報は環境変数 CN_USER / CN_PASS からのみ読み、
# **ファイルにも、データにも、コミットにも残さない**（CLAUDE.md）。
# この検査は「それらしい文字列が木に無いこと」を見張る。
# **1回でも入れば、履歴からは消せない。**
# 値が本物らしいときだけ鳴らす。**docstring の `'...'` のような置き換え例では鳴らさない。**
# 鳴りすぎる検査は、すぐに無視されるようになる。
_LEAK = _re.compile(r'japanpro\w*2015'
                    r'|(?:CN_PASS|CN_USER|user_pass|user_login)\s*=\s*'
                    r'["\'](?![.<{]|your|xxx|dummy|\s*["\'])[A-Za-z0-9@._%+-]{4,}["\']')
_skip = {'.git', '__pycache__', 'node_modules'}
_hits = []
for _dp, _dn, _fn in os.walk(ROOT):
    _dn[:] = [d for d in _dn if d not in _skip]
    for _f in _fn:
        if _f.endswith(('.pyc', '.png', '.jpg', '.pdf', '.zip', '.xlsx')): continue
        # **この検査ファイル自身は除く。**検出器が鳴ることを示すための見本
        # （`export CN_PASS='himitsu'`）を持っているので、自分を数えると必ず鳴る。
        # **鳴りっぱなしの検査は、無視されるようになる。**
        if _f == 'test_watchdog.py': continue
        _fp = os.path.join(_dp, _f)
        try:
            _t = io.open(_fp, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        if _LEAK.search(_t):
            _hits.append(os.path.relpath(_fp, ROOT))
check('リポジトリに認証情報の平文が無い', _hits, [])
# 検出器そのものの検出：入っていれば見つけられること
check('平文があれば見つけられる',
      bool(_LEAK.search("export CN_PASS='himitsu'")), True)
check('環境変数から読む書き方は鳴らさない',
      bool(_LEAK.search("os.environ.get('CN_PASS')")), False)
check('docstring の例（値なし）は鳴らさない',
      bool(_LEAK.search("export CN_USER='...'; export CN_PASS='...'")), False)
# ナビの道具が認証情報をファイルに書かないこと
for _p in ('bin/chancenavi.py', 'bin/chancenavi_anken.py'):
    _f = os.path.join(ROOT, _p)
    if not os.path.exists(_f): continue
    _s = io.open(_f, encoding='utf-8').read()
    check('%s は環境変数からしか認証情報を読まない' % _p,
          "os.environ.get('CN_USER')" in _s or 'CN_USER' in _s, True)
    check('%s は認証情報をファイルへ書かない' % _p,
          bool(_re.search(r'(open|write)\([^)]*CN_(USER|PASS)', _s)), False)

# ── 3.21 件名の取り出しを長さで決めていないか ──────────────────
# 2026-10-14 実測。公社の契約情報の整理番号66 は
#   件名「ノート型パソコンの借入」（11字）
#   期間「令和8年10月13日9:00～」（15字）
# で、**いちばん長い行を件名にしていたため日付を件名として報告した。**
# 先頭から採るように直すと、今度は表の見出しの残り「情報」を件名にした（整理番号68）。
# **除いてから選ぶ。順序だけでも長さだけでも間違える。**
# **案件名を取り違える道具は、黙っている道具より悪い。**名前は判断の入口である。
_gk = io.open(os.path.join(ROOT, 'bin/gaikaku_keiyaku.py'), encoding='utf-8').read()
check('件名は日付らしい行を除いてから選ぶ', 'DATEISH' in _gk, True)
check('件名を max(blk, key=len) で選んでいない',
      bool(_re.search(r'max\(blk,\s*key=len\)', _gk)), False)
check('表の見出しの残りを件名にしない', "'情報'" in _gk, True)
_gkm = importlib.import_module('gaikaku_keiyaku')
_DATEISH = _re.compile(r'^(?:令和\d+年\d+月\d+日|\d{4}年\d{1,2}月\d{1,2}日)'
                       r'\s*(?:\d{1,2}(?:[:：]\d{2}|時)?)?\s*[～~]?$')
check('「令和8年10月13日9:00～」は日付として外れる',
      bool(_DATEISH.match('令和8年10月13日9:00～')), True)
check('「ノート型パソコンの借入」は日付ではない',
      bool(_DATEISH.match('ノート型パソコンの借入')), False)
check('「2026年10月09日12時」も日付として外れる',
      bool(_DATEISH.match('2026年10月09日12時')), True)

# ── 3.22 ナビの一覧を黙って切り捨てていないか ─────────────────
# 2026-10-15 判明。検索の送りで状態の絞り込みを**空**にしていたため、
# 絞り込みが全部外れ、**件数表示が 11,088件**になっていた
# （画面の「入札参加可能」は32件）。1ページ50件なので、
# **11,088件のうち先頭50件だけを見て「当社領域4件」と報告していた。**
# BCP策定推進フォーラムは2ページ目にあり、
# **Care Show Japan 2027（本日17時締切・当社の中核）は見えていなかった。**
# 公示は10/1で、**2週間気づかなかった。**
# **黙って切り捨てる道具は、黙って見落とす。**
# 直しかた＝画面が持つ `*Hidden`（acceptedBefore=on／accepting=on／他 off）を
# そのまま渡す。読めた件数が総数に届かなければ★で申告する。
_ca = io.open(os.path.join(ROOT, 'bin/chancenavi_anken.py'), encoding='utf-8').read()
check('状態の絞り込みを画面から読んで渡す',
      bool(_re.search(r'id="%sHidden"', _ca)) and 'acceptedBefore' in _ca, True)
check('絞り込みを空で送っていない',
      bool(_re.search(r"\('acceptedBefore', ''\)", _ca)), False)
check('読めた件数が総数に届かなければ申告する', '切り捨てている' in _ca, True)
check('0件を「無い」と言わない', '読めなかった' in _ca, True)

# ── 3.23 道具が「無い」と言い続けていないか ───────────────────
# 2026-10-13 に訂正した事実：**公社の案件には東京都の等級要件がある。**
# 営業種目「120 催事関係業務」の登録と「格付C」以上を求めるのが通例で、
# 要件は案件ごとの「01_契約情報.pdf」に書かれ、**ナビ上にしかない。**
# それでも `bin/gaikaku_keiyaku.py` は 10/16 まで毎日
# 「**等級要件は無い。**公社の選定の制限は5項目のみ」と**印字し続けていた。**
# **訂正を台帳に書いても、道具が古い結論を刷り続けるなら訂正していない。**
# 根拠にしていた「選定の制限」5項目は**指名業者に選定されない事由**であって、
# 希望申出要件ではない。**読めないものを「無い」と言ってはならない。**
check('公社に「等級要件は無い」と断言していない',
      bool(_re.search(r'\*\*等級要件は無い。\*\*公社の選定の制限', _gk)), False)
check('公社の等級要件（格付C以上・種目120）を印字する',
      '格付C' in _gk and '120' in _gk, True)
check('要件の出どころ（01_契約情報.pdf）を示す', '01_契約情報' in _gk, True)
check('認証情報が設定済みなら読み方を示す', '--files' in _gk, True)
check('未設定なら黙って飛ばさない', '黙って飛ばさない' in _gk, True)

# ── 3.24 添付資料を落とす道具が、落とせたふりをしないか ──────────
# 2026-10-16、`--files` を足した。downloadFile(key,index,flag) への POST で、
# **token は開いた cga0201 から取り直す**（前の画面の token では SBA9001 で死ぬ）。
# HTTP 200 でも中身がエラーHTMLのことがあるため、**大きさも見る。**
check('添付の取得は cga0201/download へ POST する',
      "'/cga0201/download'" in _ca, True)
check('token を cga0201 の画面から取り直す',
      bool(_re.search(r"tok2 = m\.group\(1\)", _ca)), True)
check('HTTP 200 だけで成功と言わない', 'size > 1000' in _ca, True)
check('落とせなかった件数を申告する', '落とせていない' in _ca, True)

# ── 3.25 ページ送りの上限が、固定値で切り捨てていないか ──────────
# 2026-10-16 実測。`page >= 20` で止めていたため、結果公表済み1,507件のうち
# **先頭1,000件（20ページ×50件）しか読めていなかった。507件を落としていた。**
# 入札参加可能は32件で1ページに収まるため、**この上限は一度も鳴らなかった。**
# **鳴らない上限は、上限が無いのと同じに見える。**
check('送りの上限を総数から決める', 'need = (total + 49) // 50' in _ca, True)
# **経緯の説明文に `page >= 20` と書くので、コメント行を除いてから見る。**
_ca_code = '\n'.join(l for l in _ca.split('\n') if not l.lstrip().startswith('#'))
check('固定の page >= 20 で止めていない',
      bool(_re.search(r'or page >= 20\s*:', _ca_code)), False)

# ── 3.26 判定語を状態欄の全文から拾っていないか ──────────────────
# 2026-10-16 実測の事故。公社の「東京展開セミナー運営業務委託（インド）／（シンガポール）」は
# **応募可・10/20 14:00 が関門**だが、同じ状態欄の後ろに
# 「整理番号65（Webサイトの保守）も出たが**当社の領域外**とみなした」と
# **別の案件のことを書いていた。**classify() が状態欄の全文を部分一致で見ていたため、
# この2件が `out`（対象外）に落ち、**公募ボードの「いま決める」に1度も出なかった。**
# 日次の残日数一覧には【至急】残4日と出ていたのに、判断面には無かった。
# **数字が出る場所と、判断する場所が食い違っていた。**
# 直しかた＝判定は状態欄の**先頭の一句**（「／」より前）だけで読む。
# **後ろにある判定語は使わないが、`--check` で必ず申告する。**
_bb = io.open(os.path.join(ROOT, 'bin/build_board.py'), encoding='utf-8').read()
_bbm = importlib.import_module('build_board')
check('判定は状態欄の先頭の一句だけで読む', '_verdict_head' in _bb, True)
check('状態欄の全文を判定に使っていない',
      bool(_re.search(r'blob = st \+ ', _bb)), False)
_row_ok = {'状態': '**海外（インド）でのセミナー運営＝当社の本業。**公表 令和8年10月9日'
                  '／整理番号65（Webサイトの保守）も出たが当社の領域外とみなした',
           '資格要否': '**所在地要件は無い**'}
check('後ろに「領域外」があっても対象外にしない',
      _bbm.classify(_row_ok), 'open')
_row_out = {'状態': '領域外（当社の業務範囲外）', '資格要否': '要確認'}
check('先頭に「領域外」があれば対象外にする',
      _bbm.classify(_row_out), 'out')
_row_ng = {'状態': '**応募不可（所在地要件）。**告示第11533号で確認した'
                  '／他の要件は満たせる', '資格要否': '応募不可（所在地要件）'}
check('先頭の「応募不可」は効く', _bbm.classify(_row_ng), 'ng')
check('後ろの判定語を申告する道具がある', 'def tail_verdicts' in _bb, True)
check('申告が --check だけで止まっていない（毎回出す）',
      _bb.index('tail_verdicts(rows)') < _bb.index("if '--check' in sys.argv:\n        for k in"), True)
# ── 3.28 落札額を読む道具が、書式の違いで黙って0件にならないか ─────────
# 2026-10-16 判明。**予定価格が非公表でも、終わった案件の「入札経過調書」に
# 落札者名・落札金額・全入札者の入札額がそのまま載っている。**
# ナビの結果公表済み1,523件の中にあり、**一度も読んでいなかった。**
# 仕様書に金額が無いことは、金額が分からないことと同じではなかった。
# 書式は発注者ごとに違う（実測7種）。**1つの型だけ見ていると「読めない」で終わる。**
# ここは本文の文字列を渡して試す。**ネットワークもPDFも要らない。**
_sb = io.open(os.path.join(ROOT, 'bin/chancenavi_souba.py'), encoding='utf-8').read()
_sbm = importlib.import_module('chancenavi_souba')
_P = _sbm.parse_chosho

# 型1 都産技研（様式7）。ラベルを先に全部並べ、値を後に出す
_t1 = ('落札者氏名 落札金額（税込）\n第一回入札金\n3,075,200円\n8,250,000円\n'
       '株式会社日広通信社\n3,382,720円（うち消費税及び地方消費税　307,520円）\n'
       '入札者氏名\n株式会社日広通信社 落札\n株式会社ステージ')
check('型1：税込と消費税が並ぶ書式の金額', _P(_t1)[1], 3382720)
check('型1：落札者は「<法人名> 落札」から取る', _P(_t1)[0], '株式会社日広通信社')
check('型1：消費税額を入札額に混ぜない', 307520 in _P(_t1)[3], False)

# 型2 東京都公立大学法人。ラベルの文字の間に空白／円ではなく ¥
_t2 = ('落 札 者 氏 名 株式会社コイヌマ ¥26,235,000\n'
       '入 札 者 氏 名 第 １ 回 入 札 金 額\n株式会社コイヌマ ¥23,850,000\n'
       '幸和商事株式会社 ¥24,000,000')
check('型2：ラベルの空白を落として読む', _P(_t2)[1], 26235000)
check('型2：落札者を取れる', _P(_t2)[0], '株式会社コイヌマ')

# 型3 農林水産振興財団。円も ¥ も付かない／法人名の冠が後ろ
_t3 = ('落札者名 TSP東日本株式会社 落札金額\n 円  うち消費税及び  円\n'
       '5,698,000  地方消費税額 518,000\n入札者氏名 第1回入札\n'
       'TSP東日本株式会社 5,180,000 落札\n株式会社セレスポ 5,720,663')
check('型3：円も ¥ も無い金額を読む', _P(_t3)[1], 5698000)
check('型3：冠が後ろに付く法人名を読む', _P(_t3)[0], 'TSP東日本株式会社')
check('型3：行をまたぐ地方消費税額を除く', 518000 in _P(_t3)[3], False)

# 型4 都立病院機構。pypdf が ¥ をバックスラッシュとして出す
_t4 = ('落札者 株式会社ツクルス 落札金額\n' + chr(92) + '11,550,000-\n'
       'うち消費税及び地方消費税　¥1,050,000-\n株式会社ツクルス ¥10,500,000 落札')
check('型4：バックスラッシュを ¥ として扱う', _P(_t4)[1], 11550000)

# 型5 人材支援事業団。**「落札金額」の直後に消費税相当額が並ぶ**
_t5 = ('落札者氏名 落札金額 ¥268,000\n(株)ブレインワークス ¥2,948,000\n'
       '入 札 者 氏 名 第 １ 回入札金額\n(株)ブレインワークス 2,680,000 落札\n'
       '(株)ツクルス 3,053,000\n（うち消費税相当額 ）')
check('型5：税込が最低入札額より小さければ訂正する', _P(_t5)[1], 2948000)
check('型5：訂正したことを黙らない', '訂正した' in _P(_t5)[4], True)

# 型6 GovTech東京。「決定業者 決定金額（税抜）」／間に住所の数字が入る
_t6 = ('一般財団法人GovTech東京\n経過調書\n決定業者 決定金額\n（税抜）\n'
       '株式会社第一文眞堂\n東京都 港区芝大門１－３－１６\n34,580,000円\n参加事業者名')
check('型6：住所の数字で止まらずに金額を読む', _P(_t6)[1], 34580000)
check('型6：税区分を税抜と読む', _P(_t6)[5], '税抜')

# 型7 福祉保健財団。入札ではなくプロポーザルの「実施報告書」。見積金額（税抜）
_t7 = ('企画コンペ・プロポーザル審査委員会 実施報告書\n'
       '株式会社エイデル研究所の提案が優れていると判断された。\n'
       '６ 見積金額\n３５，４７０，０００円（税抜）')
check('型7：プロポーザルの見積金額を読む', _P(_t7)[1], 35470000)
check('型7：全角の数字とカンマを読む', _P(_t7)[5], '税抜')
check('型7：「○○の提案が」から落札者を取る', _P(_t7)[0], '株式会社エイデル研究所')

# 型8 農林水産振興財団（令和6年度）。**ラベルと値の間に改行と日付が入る／
# 消費税額が税込額より先に出る。**入札額の一覧がPDFの文字として出ない
_t10 = ('落札金額\n円\n令和6年7月26日\n円\n357,000\nうち消費税及び\n地方消費税額\n'
        '備考\n記事\n本件入札金額は、消費税抜きの金額である。\n'
        '令和6年度東京農林水産フェア運営等業務委託\n3,927,000落札者名 株式会社自然堂')
check('型8：改行と日付をまたいで金額を読む', _P(_t10)[1], 3927000)
check('型8：消費税額（税込の11分の1）から直す', '11倍' in _P(_t10)[4], True)
check('型8：落札者を取れる', _P(_t10)[0], '株式会社自然堂')
check('型8：訂正前の数を入札額に残さない', _P(_t10)[3], [])
# **「（うち消費税相当額 ）」と金額が空の書式がある。**空のままこの型に当てると
# 無関係な入札額を落札金額にしてしまう（型5 で 3,053,000 を拾った）
check('うち消費税のあとに数が無ければその型を使わない', _P(_t5)[1], 2948000)

# 不課税。**1.1倍の検査をかけると正しい値を「読めない」と言ってしまう**
_t8 = ('落札者氏名 落札金額（税込）\n3,172,237円\n4,350,000円\n'
       'エーエムシー東京株式会社\n3,172,237円（不課税）\n'
       '入札者氏名\nエーエムシー東京株式会社 落札\n株式会社東京ビッグサイト')
check('不課税は1.1倍の検査をしない', _P(_t8)[1], 3172237)

# 不調。**「読めない」ではない。結果である**
_t9 = ('落 札 者 氏 名 契約不調 契約不調\n入 札 者 氏 名\n'
       '株式会社モスコム ¥15,000,000 不参\n'
       '予定価格内での応札がなかったため、不調とする。')
check('契約不調を「読めない」に混ぜない', '契約不調' in _P(_t9)[4], True)
check('不調は金額0で返す', _P(_t9)[1], 0)

# 冠だけを氏名として出さない
check('「株式会社」だけを落札者にしない',
      _P('決定業者 決定金額\n株式会社\n1,000,000円')[0], '')
check('1件ごとに入り直す（SBA900x 対策）', 'C.login()' in _sb.split('for g, why, r in tgt')[1], True)
check('読めなかった件数を申告する', '黙って飛ばさない' in _sb, True)
check('0件を「相場が無い」と言わない', '読めていない' in _sb, True)

# ── 3.29 掃引の見出し抽出が、1件を丸ごと捨てていないか ──────────────
# 2026-10-17 実測。園芸博協会の
# 「2027年国際園芸博覧会協会 お問い合わせ窓口運営業務委託の一般競争入札について」
# （当社領域・公示10/16・**前段関門が10/20 17:00**）が**1度も記録されていなかった。**
# 原因は2つ。
# (a) 一覧の `<a>` の中が「2026.10.16」「委託等」「件名」の3要素に割れており、
#     **href は日付の行に付き、件名の行には付かなかった。**
#     掃引ログには件名が残るので取れているように見えるが、
#     **その件名からは二度と一次資料へ辿れない。**
#     さらに「2026.10.16 委託等」自体が見出しとして記録され、
#     **同じ日に2件出ると `norm()` が一致して重複除去で片方が丸ごと消えていた。**
# (b) **ナビゲーションを落とすためのノイズ語「お問い合わせ」が、
#     業務そのものの語と衝突していた。**2026-10-10 に rank.py で
#     「セミナー」が「東京展開セミナー運営業務委託」を殺したのと同じ型である。
# **落としたいのは案内のリンクであって、発注そのものではない。**
_sw = io.open(os.path.join(ROOT, 'bin/sweep_channels.py'), encoding='utf-8').read()
_swm = importlib.import_module('sweep_channels')
check('リンクの続きの行へ href を引き継ぐ', 'carry_n' in _sw, True)
check('日付と区分だけの行を見出しにしない', 'LABEL' in _sw, True)
check('重複除去の鍵に href を入れる', "k = (norm(ln), href)" in _sw, True)
check('発注を示す語があればノイズ語で落とさない', 'ORDER' in _sw, True)

_html = ('<ul><li><a href="/contract/detail/A.html"><span class="date">2026.10.16</span>'
         '<span class="cat">委託等</span>'
         '<h2><span>2027年国際園芸博覧会協会　お問い合わせ窓口運営業務委託の一般競争入札について</span></h2>'
         '</a></li>'
         '<li><a href="/contract/detail/B.html"><span class="date">2026.10.16</span>'
         '<span class="cat">委託等</span>'
         '<h2><span>２０２７年国際園芸博覧会 主催者催事 ナイトパレードにかかる制作・管理運営業務委託の公募型プロポーザルについて</span></h2>'
         '</a></li></ul>')
_got = _swm.titles(_html)
_names = [x[0] for x in _got]
_hrefs = dict(_got)
check('同じ日に2件出ても両方拾う', len(_got), 2)
check('「お問い合わせ窓口運営業務委託」を捨てない',
      any('お問い合わせ窓口運営業務委託' in n for n in _names), True)
check('件名に正しい href が付く',
      [h for n, h in _got if 'お問い合わせ窓口' in n], ['/contract/detail/A.html'])
check('2件目にも正しい href が付く',
      [h for n, h in _got if 'ナイトパレード' in n], ['/contract/detail/B.html'])
check('「2026.10.16 委託等」を見出しにしない',
      any(_swm.LABEL.fullmatch(n) for n in _names), False)
# **本物の案内リンクは、これまでどおり落ちる**
# **救済は案内のリンクとの衝突だけ。結果の公表は救済しない。**
# 2026-10-17：ORDER の救済を入れた直後、「審査結果について」「選定結果を
# お知らせします」「入札結果」までが当社領域の新規として上がり、
# **本日の新規が2件から24件に膨らんだ。**中身は大半が終わった案件だった。
# **判断面を結果で埋めてはならない。**結果は来年の予測にだけ使う。
check('「最優秀提案事業者決定」は救済しない',
      _swm.titles('<li><a href="/x.html">【最優秀提案事業者決定】'
                  '情報管理センター管理運営業務委託の公募型プロポーザルについて</a></li>'), [])
check('「審査結果について」は救済しない',
      _swm.titles('<li><a href="/x.html">こども健康会議運営業務委託'
                  '企画提案競技の審査結果について</a></li>'), [])
check('「入札結果」は救済しない',
      _swm.titles('<li><a href="/x.html">【入札結果】2026年度 屋内出展施設'
                  '運営管理業務の一般競争入札について</a></li>'), [])
check('「（公開終了しました）」のフォームは救済しない',
      _swm.titles('<li><a href="/x.html">フォーム名： 令和8年度内定者交流会'
                  '実施業務企画提案書提出フォーム （公開終了しました）</a></li>'), [])
check('閉じたものを救済しない仕組みがある', 'HARD_NOT' in _sw, True)
check('ナビゲーションの「お問い合わせ」は落ちる',
      _swm.titles('<li><a href="/contact/">お問い合わせ窓口のご案内はこちら</a></li>'), [])


# ── 3.30 判定語に国名が無いために、海外案件を落としていないか ──────────
# 2026-10-19 実測。宮崎県（九州3県合同）の
# 「九州3県合同**米国向け**焼酎プロモーション事業業務」（企画コンペ・890万円・
# **前段関門 10/23 17:00**）が、**格付Bに落ちて毎朝の報告に出なかった。**
# 原因は分母の語の穴が2つ重なったこと。
#   ・海外展開に「海外」「国際」「輸出」はあるが、**国名が1つも無かった。**
#     **発注者は「海外」と書かない。行き先の国名を書く。**
#   ・工芸・地域産品に「焼酎」が無かった（酒類の語が1つも無かった）
# 結果、当たったのは「プロモーション」だけで、1領域＝周辺領域（B）になった。
# 2026-10-10 の「セミナー」、2026-10-17 の「お問い合わせ」と同じ型である。
# **当社の本業の語が分母に無いことは、その案件が永久に見えないことを意味する。**
_rk = io.open(os.path.join(ROOT, 'bin/rank.py'), encoding='utf-8').read()
_rkm = importlib.import_module('rank')
# **語の有無は、ファイルの文字列ではなく正規表現そのものに訊く。**
# 2026-10-20、`'サミット' in _rk` という書き方で検査していたため、
# **正規表現から「サミット」を抜いても、注釈に同じ語が残っていて検査が通った。**
# 鳴らない検出器は、検出器が無いのと同じである。語は道具に当てて確かめる。
check('海外展開の語に国名がある',
      bool(_rkm.KAIGAI.search('米国')) and bool(_rkm.KAIGAI.search('ニューヨーク')), True)
check('地域産品の語に酒類がある',
      bool(_rkm.KOGEI.search('焼酎')) and bool(_rkm.KOGEI.search('日本酒')), True)
check('米国向け焼酎プロモーションがS/Aに上がる',
      _rkm.grade('「九州3県合同米国向け焼酎プロモーション事業業務」'
                 'に係る企画提案競技の実施について')[0] in ('S', 'A'), True)
# **紛れる語を拾っていないか。**「タイ」は「タイヤ」、「インド」は「インドア」に紛れる
check('「タイヤ交換業務委託」を拾わない', _rkm.grade('タイヤ交換業務委託')[0], None)
check('「屋内インドア施設の清掃業務委託」を拾わない',
      _rkm.grade('屋内インドア施設の清掃業務委託')[0], None)
check('「タイ企業との商談会」は拾う',
      _rkm.grade('令和8年度 海外展開総合支援事業 タイ企業との商談会 設営・運営等業務委託')[0]
      in ('S', 'A'), True)


# ── 3.31 分母に「会議体の総称」と「広域名」が無いために落としていないか ──
# 2026-10-20 実測。語の穴を塞いで掃引ログ 5,783件を当て直すと9件が新たにS/Aになり、
# **うち3件は締切が未来の、上限3,984万円・3,000万円・641万円の案件だった。**
#   ・愛知県／第60回**アジア**開発銀行年次総会 愛知・名古屋支援実行委員会の2件。
#     「アジア」が広域名として無く、「年次**総会**」も会議体の語に無かった。
#   ・宮崎県／2027日台観光**サミット**in宮崎。「サミット」が会議体の語に無かった。
#   ・秋田県／「**中国**情報発信業務委託」。「中国」が無かった。
# **発注者は催事の種類を「イベント」とは書かない。「総会」「サミット」と書く。**
# 2026-10-10 の「セミナー」、10-17 の「お問い合わせ」、10-19 の「米国」と同じ型である。
check('海外展開の語に広域名がある',
      bool(_rkm.KAIGAI.search('アジア')) and bool(_rkm.KAIGAI.search('アフリカ')), True)
check('会議体の語に総会とサミットがある',
      bool(_rkm.EVENT.search('総会')) and bool(_rkm.EVENT.search('サミット')), True)
check('アジア開発銀行年次総会の案件がS/Aに上がる',
      _rkm.grade('「第60回アジア開発銀行年次総会の参加者を対象としたエクスカーション'
                 '及び会場内外文化体験プログラム 実施計画策定・準備業務」の業務委託先を募集します'
                 )[0] in ('S', 'A'), True)
check('日台観光サミットの案件がS/Aに上がる',
      _rkm.grade('2027日台観光サミットin宮崎実施計画策定・開催支援事業業務委託'
                 '企画提案競技（プロポーザル方式）の実施について')[0] in ('S', 'A'), True)
check('中国情報発信業務がS/Aに上がる',
      _rkm.grade('中国情報発信業務委託に係る企画提案競技を実施します。')[0] in ('S', 'A'), True)
# **紛れる語を拾っていないか。**「中国」は「中国地方」「中国四国」に紛れる。
# ここを緩めると、国の地方整備局・県の広域連携の工事が大量に当社の領域へ流れ込む。
check('「中国地方整備局の道路改良工事」を拾わない',
      _rkm.grade('中国地方整備局 道路改良工事の一般競争入札公告')[0], None)
check('「中国四国農政局の庁舎清掃」を拾わない',
      _rkm.grade('中国四国農政局 庁舎清掃業務委託の一般競争入札')[0], None)


# ── 3.32 制度台帳の「状態」の語が、制度を予告から黙って消していないか ──
# 2026-10-21 実測。熊本市物産展等出展支援事業補助金（締切 11/20・残り30日）を
# 状態「公募中」で書いたところ、**60日以内の予告に1行も出ず、**
# 見出しの件数が「廃止・統合 2→3」に増えただけだった。**名前は誰も言わない。**
# `programs.py` は状態が「現存」で始まる行だけを生きているものとして扱うため、
# **「現存」の2文字を外すだけで制度が1つ見えなくなる。**
# 「0件だった」ではなく「その行が勘定に入らなかった」型の事故である。
_pg = importlib.import_module('programs')
_now = _pg.today()
_base = {'制度ID': 'x', '制度名': 'テスト制度', '所管': 'テスト省',
         '種別': '補助金', '当社の立ち位置': '支援側', '根拠URL': 'https://example.com',
         '最終確認日': _now.isoformat(), '締切': (_now + __import__('datetime').timedelta(days=30)).isoformat(),
         '前段関門': '', '公募開始': '', '次回見込み': '', '補助率': '', '上限額': '', '備考': ''}


def _audit(state):
    r = dict(_base); r['状態'] = state
    hard, soft, soon = _pg.check([r], _now)
    return hard, soon


check('状態「現存」は予告に出る', len(_audit('現存')[1]), 1)
check('状態「現存（公募中）」も予告に出る', len(_audit('現存（公募中）')[1]), 1)
# **ここが本体。**生きている制度を曖昧な語で書いたら、黙って消すのではなく止める
check('状態「公募中」は止まる（黙って消さない）', len(_audit('公募中')[0]) >= 1, True)
check('状態「受付中」は止まる', len(_audit('受付中')[0]) >= 1, True)
# 終わったことを明言する語は、止めずに予告から外す
check('状態「廃止（統合）」は止まらない', len(_audit('廃止（ものづくり補助金へ統合）')[0]), 0)
check('状態「廃止」は予告に出ない', len(_audit('廃止')[1]), 0)
check('状態「終了」は予告に出ない', len(_audit('終了（後継あり）')[1]), 0)


# ── 3.33 救済が行きすぎて、清掃・警備・工事を当社の領域に上げていないか ──
# 2026-10-24 実測。2026-10-10 に「セミナー運営業務委託」を取り戻すために入れた
# 「委託・入札の語があれば救済する」仕組みが、**発注案件の件名にはほぼ必ず
# 「委託」か「入札」が入る**ために効きすぎていた。
# 「国際園芸博覧会 **会場警備**業務委託の一般競争入札」が S に上がり、
# 掃引ログ6,089件のうち10件がこの型で毎日の報告に混ざっていた。
# **取りこぼしの逆（拾いすぎ）も、報告を読めなくして取りこぼしを作る。**
check('固いノイズの語を持っている', 'HARD_NOISE' in _rk, True)
check('「会場警備業務委託」は領域外', _rkm.grade('国際園芸博覧会 会場警備業務委託')[0], None)
check('「機械警備業務委託の一般競争入札」は領域外',
      _rkm.grade('２０２７年国際園芸博覧会協会 会場管理棟事務所等機械警備業務委託の一般競争入札について')[0], None)
check('「道路改良工事」は領域外',
      _rkm.grade('国際園芸博覧会 上川井瀬谷１号線ほか3か所道路改良工事に関する入札公告')[0], None)
check('「清掃工場建設工事」は領域外', _rkm.grade('千葉市新清掃工場建設工事建築工事等施工監理業務委託')[0], None)
check('「賓客車両運行管理業務委託」は領域外', _rkm.grade('２０２７年国際園芸博覧会賓客車両運行管理業務委託')[0], None)
# **ただし当社の語を伴うものは落とさない。**ここを雑にすると本業を捨てる
check('「通信サービスの提供等委託契約」は領域外',
      _rkm.grade('２０２７年国際園芸博覧会協会 通信サービスの提供等委託契約の一般競争入札について')[0], None)
check('「落雷抑制型避雷針の賃貸借契約」は領域外',
      _rkm.grade('2026年度 国際園芸博覧会落雷抑制型避雷針の賃貸借契約の一般競争入札について')[0], None)
check('「展示装飾工事及び会場設営業務委託」はS/A',
      _rkm.grade('展示装飾工事及び会場設営業務委託')[0] in ('S', 'A'), True)
check('「ブース装飾等の業務委託」はS/A',
      _rkm.grade('海外展示会出展に伴うブース装飾等の業務委託')[0] in ('S', 'A'), True)


print('\n%d件成功 / %d件失敗' % (ok, fail))
sys.exit(1 if fail else 0)
