# -*- coding: utf-8 -*-
"""ビジネスチャンス・ナビにログインして画面を取る。

なぜ要るか
----------
2026-09-16、**トップの「入札・発注情報エリア」が回転表示である**ことが判明した。
朝8時に見えたねんりんピック2件（PRブース出展・宿泊輸送）と東京iCDCフォーラムは、
同日16時には消えていた。**締切はログイン後の画面にしかない。**
生島様より「毎回こんなことはできません」とのご指摘を受け、機械化した。

**認証情報はこのファイルにも、リポジトリのどこにも書かない。**
環境変数 `CN_USER` / `CN_PASS` から読む。無ければ何もせずに終わる。

    export CN_USER='...'; export CN_PASS='...'
    python3 bin/chancenavi.py            # ログインできるかだけ確かめる
    python3 bin/chancenavi.py <画面ID>   # 例: cdg0101/index

実測した作法（守らないとセッションが死ぬ）
------------------------------------------
1. `GET /bcnc/` でセッションを張る
2. `POST /bcnc/cab0101/validate` に `user_login` `user_pass`。
   **`X-Requested-With: XMLHttpRequest` が要る。**無いと通っても後段が「タイムアウト」になる
3. `GET /bcnc/caa0101`（マイページ）。ここで `id="token"` の値を取る
4. 以降の画面遷移は **POST**。`token` と `tmpTokenKey` を必ず付ける。
   **GET で画面IDを叩くと「タイムアウト」になる**
5. **1回でも想定外の遷移をするとセッションが即死する**（SBA9001／SBA9002）。
   失敗したら**入り直す**。同じセッションで試行錯誤しない

**解明した（2026-10-13）。案件検索の画面IDは次のとおり。**
生島様より認証情報を頂いてログインし、マイページの HTML と
`js/pages/caa0101.js`・`js/provider/common.js` を読んで確定した。
**開発者ツールは要らなかった。onclick の関数定義が外部JSに書いてある。**

| 画面ID | 中身 | 追加で送る値 |
|---|---|---|
| `caa0202` | **東京都の外郭団体等**（公社・TCVB の案件がここ） | なし |
| `caa0203` | 民間発注案件等 | なし |
| `caa0204` | 官公庁入札情報（東京都等） | なし |
| `caa0201` | 東京2020組織委員会 | なし |
| `sba2101` | 代理店募集商品 | `recruitmentExist=on` `initRecruitmentExist=on` |
| `sba0301` | 国・独立行政法人等入札情報の検索 | `pageKey=2` |
| `sba0303` | 案件一覧 | `pageKey=1` |
| `sba0501` | 案件一覧 | `pageKey=1` `proposalClassCode=1` |
| `cga0101` | 案件一覧 | `tocog_flag=0` `status=0` |
| `sba0403` / `sba0404` | 個別案件の詳細 | 案件番号 |
| `cga0201` | 個別案件の詳細 | 提案番号 |
| `sba0601` | 商品評価の個別ページ | 提案番号 |
| `sba0701` | 企業の検索 | なし |

**トークンは画面を開くたびに入れ替わる（2026-11-02 実測）。**
サーバは「最後に発行したもの」しか受け付けない。古い token を送ると
SBA9002「タイムアウト」になりセッションが死ぬ。**画面を開いたら、その応答の
`id="token"` を次に使う。**添付のダウンロードはバイナリ応答で新しい token を
発行しないので、詳細画面の token を使い回して何本でも落とせる。

**一覧は50件まで1ページで取れる（`limit=50`）。**ページ送りは要らない。
doPaging()（js/pages/cga0101.js）が post() に渡す data をそのまま送ればよい。
空の ArrayList の `getJsonString()` は `"[]"`（js/arraylist.js で実測）。

**添付資料は AJAX ではなく hidden `fileUploadArrayForBasic_hidden` の JSON にある。**
落とすのは POST `/bcnc/cga0201/download` に `key` `index` `flag`。1ファイル1本。

**`tmpTokenKey` は送らない。**本物の `post()`（common.js）は `token` だけを足す。
以前のこのファイルは `tmpTokenKey` を付けていたが、**サイトはそんな値を作っていない。**
余計な値を付けるのは「想定外の遷移」そのものである。
"""
import os
import re
import subprocess
import sys
import time
import uuid

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
BASE = 'https://www.chancenavi.jp/bcnc'
JAR = '/tmp/chancenavi_%d.jar' % os.getpid()


def _curl(url, data=None, ref=None, xhr=False):
    c = ['curl', '-sSL', '--http1.1', '-A', UA, '--max-time', '30',
         '--compressed', '-c', JAR, '-b', JAR]
    if ref:
        c += ['-H', 'Referer: ' + ref]
    if xhr:
        c += ['-H', 'X-Requested-With: XMLHttpRequest']
    if data is not None:
        for k, v in data:
            c += ['--data-urlencode', '%s=%s' % (k, v)]
    try:
        r = subprocess.run(c + [url], capture_output=True, timeout=60)
        return r.stdout.decode('utf-8', 'replace')
    except Exception:
        return ''


def _curl_bin(url, data=None, ref=None, out=None):
    """添付資料のように**本文がバイナリ**のものを受け取る。

    cga0201 の downloadFile(key, index, flag) は `/bcnc/cga0201/download` への
    POST で、post()（common.js）が token を足す。**1ファイル1リクエストである。**
    `-o` でファイルへ落とし、Content-Type と大きさを返す。
    """
    c = ['curl', '-sSL', '--http1.1', '-A', UA, '--max-time', '60',
         '--compressed', '-c', JAR, '-b', JAR, '-o', out,
         '-w', '%{http_code} %{content_type} %{size_download}']
    if ref:
        c += ['-H', 'Referer: ' + ref]
    if data is not None:
        for k, v in data:
            c += ['--data-urlencode', '%s=%s' % (k, v)]
    try:
        r = subprocess.run(c + [url], capture_output=True, timeout=90)
        return r.stdout.decode('utf-8', 'replace').strip()
    except Exception as e:
        return '0 - 0 (%s)' % e


def plain(h):
    b = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S | re.I)
    return ' '.join(re.sub(r'<[^>]+>', ' ', b).split())


def login():
    """ログインしてマイページのHTMLとトークンを返す。失敗したら (None, None)。"""
    u, p = os.environ.get('CN_USER'), os.environ.get('CN_PASS')
    if not u or not p:
        return None, None
    if os.path.exists(JAR):
        os.remove(JAR)
    _curl(BASE + '/')
    time.sleep(1)
    _curl(BASE + '/cab0101/validate',
          [('user_login', u), ('user_pass', p)], BASE + '/', xhr=True)
    time.sleep(1)
    my = _curl(BASE + '/caa0101', None, BASE + '/')
    m = re.search(r'id="token"[^>]*value="([^"]*)"', my)
    if not m or 'マイページ' not in plain(my)[:60]:
        return None, None
    return my, m.group(1)


# 画面IDごとに必要な値（2026-10-13、js/pages/caa0101.js から読み取った）
SCREENS = {
    'caa0202': ([], '東京都の外郭団体等'),
    'caa0203': ([], '民間発注案件等'),
    'caa0204': ([], '官公庁入札情報（東京都等）'),
    'caa0201': ([], '東京2020組織委員会'),
    'sba2101': ([('recruitmentExist', 'on'), ('initRecruitmentExist', 'on')], '代理店募集商品'),
    'sba0301': ([('pageKey', '2')], '国・独立行政法人等入札情報の検索'),
    'sba0303': ([('pageKey', '1')], '案件一覧'),
    'sba0501': ([('pageKey', '1'), ('proposalClassCode', '1')], '案件一覧'),
    'cga0101': ([('tocog_flag', '0'), ('status', '0')], '案件一覧'),
    'sba0701': ([], '企業の検索'),
}


def screen(sid, token, extra=None):
    """画面IDを POST で開く。**GET では開けない。**

    **`tmpTokenKey` は送らない。**本物の post()（common.js）は token だけを足す。
    画面ごとに要る値は SCREENS に持つ。無い値を足すのも、要る値を欠くのも
    「想定外の遷移」であり、セッションが即死する（SBA9001／SBA9002）。
    """
    need = SCREENS.get(sid.split('/')[0], ([], ''))[0]
    d = [('token', token)] + list(need) + (extra or [])
    return _curl(BASE + '/' + sid, d, BASE + '/caa0101')


def token_of(h):
    """画面のHTMLから次に使う token を取る。**使い回さない。**"""
    m = re.search(r'id="token"[^>]*value="([^"]*)"', h)
    return m.group(1) if m else None


# doPaging()（js/pages/cga0101.js）が post() に渡す data。欠けても余っても死ぬ。
_LIST_FIXED = [
    ('sort', 'desc'), ('status', '0'), ('tocog_flag', '0'),
    ('txt_free_word', ''), ('txt_acceptance_date_from', ''),
    ('txt_acceptance_date_to', ''), ('txt_bid_date_from', ''),
    ('txt_bid_date_to', ''), ('acceptedBefore', ''), ('bidding', ''),
    ('accepting', ''), ('resultPublishing', ''),
    ('examinationApplicationResultInput', ''), ('bidResultInput', ''),
    ('prepareResultPublished', ''), ('keywordRetrievalMethod', '1'),
    ('freeWordArray', '[]'), ('contractMethodArray', '[]'),
    ('proposalExecuteLocationPrefectturesArray', '[]'),
    ('proposalBusinessArray', '[]'),
    ('environmentalConsiderationArray', '[]'),
    ('responsibilityRightProhibitedMatterArray', '[]'),
    ('providerOrganizationArray', '[]'), ('recommendId', ''),
]


def search_list(token, limit=50, page=1):
    """案件一覧（cga0101）を limit 件まとめて取る。公示日の新しい順。"""
    d = ([('token', token), ('limit', str(limit))] + _LIST_FIXED
         + [('page', str(page))])
    return _curl(BASE + '/cga0101/index/search', d, BASE + '/caa0101')


def parse_list(h):
    """一覧HTMLから案件を読む。[{提案番号, 本文}] を返す。"""
    out = []
    for it in re.findall(r'<LI class="dataset-item">(.*?)</LI>', h,
                         flags=re.S | re.I):
        m = re.search(r"cga0201'\s*,\s*'(\d+)'", it)
        out.append({'提案番号': m.group(1) if m else '',
                    '本文': plain(it)})
    return out


def detail(pn, outdir=None):
    """案件詳細（cga0201）と添付資料を取る。**1回のログインで1件。**

    戻り値は (詳細HTML, [落としたファイルの説明])。
    outdir を渡すと添付をそこへ落とす。
    """
    import html as _h
    import json as _j
    my, t = login()
    if not t:
        return None, ['**ログインできなかった。**CN_USER / CN_PASS を確認すること。']
    s = screen('cga0101', t)
    if 'CGA0101' not in plain(s)[:20]:
        return None, ['一覧が開けなかった：' + plain(s)[:120]]
    t = token_of(s)
    _curl(BASE + '/cga0101/index/showProposalDetailInfo',
          [('token', t), ('proposalNumber', pn)], BASE + '/cga0101', xhr=True)
    d = _curl(BASE + '/cga0201',
              [('token', t), ('proposalNumber', pn)], BASE + '/cga0101')
    if 'CGA0201' not in plain(d)[:20]:
        return None, ['詳細が開けなかった：' + plain(d)[:120]]
    t = token_of(d)
    got = []
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        files = []
        for nm in ('fileUploadArrayForBasic_hidden',
                   'fileUploadArrayForDetail_hidden',
                   'answersFile_hidden', 'bidFile_hidden'):
            m = re.search(r'id="%s"[^>]*value="([^"]*)"' % nm, d)
            if m:
                try:
                    files += _j.loads(_h.unescape(m.group(1)) or '[]')
                except Exception:
                    pass
        for o in files:
            safe = re.sub(r'[^0-9A-Za-z._\u3041-\u30ff\u4e00-\u9fff\uff08\uff09\-]',
                          '_', o['name'])
            r = _curl_bin(BASE + '/cga0201/download',
                          [('token', t), ('key', str(o['key'])),
                           ('index', str(o['index'])), ('flag', str(o['flag']))],
                          BASE + '/cga0201', out=os.path.join(outdir, safe))
            got.append('%s  %s' % (o['name'], r))
    return d, got


def main():
    my, t = login()
    if not t:
        print('**ログインできなかった。**環境変数 CN_USER / CN_PASS を確認すること。')
        print('（設定していない場合、これは異常ではない。設定するまで何もしない）')
        return 1
    who = re.search(r'([^\s]+様)', plain(my))
    print('ログインできた：%s' % (who.group(1) if who else '（氏名を読めず）'))
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        h = search_list(t, n)
        open('/tmp/chancenavi_list.html', 'w', encoding='utf-8').write(h)
        for i, a in enumerate(parse_list(h), 1):
            print('%2d) [%s] %s' % (i, a['提案番号'], a['本文'][:150]))
        return 0
    if len(sys.argv) > 2 and sys.argv[1] == 'detail':
        pn = sys.argv[2]
        od = sys.argv[3] if len(sys.argv) > 3 else '/tmp/cn_%s' % pn
        d, got = detail(pn, od)
        if d is None:
            print('\n'.join(got)); return 2
        open('/tmp/chancenavi_cga0201_%s.html' % pn, 'w',
             encoding='utf-8').write(d)
        print(plain(d)[:120])
        for g in got:
            print('  ' + g)
        print('添付の保存先：%s' % od)
        return 0
    if len(sys.argv) > 1:
        sid = sys.argv[1]
        s = screen(sid, t)
        head = plain(s)[:110]
        print('%s → %s' % (sid, head))
        bad = ('タイムアウト' in head or '中断' in head or 'エラー' in head)
        if not bad:
            out = '/tmp/chancenavi_%s.html' % sid.replace('/', '_')
            open(out, 'w', encoding='utf-8').write(s)
            print('  保存：%s' % out)
        return 0 if not bad else 2
    print('■ 開ける画面（画面IDと中身）')
    for k, (need, label) in SCREENS.items():
        extra = ' '.join('%s=%s' % kv for kv in need)
        print('  %-9s %-24s %s' % (k, label, extra))
    print('使い方： python3 bin/chancenavi.py caa0202')
    print('        python3 bin/chancenavi.py list [件数]        # 案件一覧（既定50件）')
    print('        python3 bin/chancenavi.py detail <提案番号> [保存先]  # 詳細＋添付資料')
    return 0


if __name__ == '__main__':
    sys.exit(main())
