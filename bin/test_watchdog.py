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

print('\n%d件成功 / %d件失敗' % (ok, fail))
sys.exit(1 if fail else 0)
