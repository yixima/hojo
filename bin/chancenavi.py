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


def main():
    my, t = login()
    if not t:
        print('**ログインできなかった。**環境変数 CN_USER / CN_PASS を確認すること。')
        print('（設定していない場合、これは異常ではない。設定するまで何もしない）')
        return 1
    who = re.search(r'([^\s]+様)', plain(my))
    print('ログインできた：%s' % (who.group(1) if who else '（氏名を読めず）'))
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
    return 0


if __name__ == '__main__':
    sys.exit(main())
