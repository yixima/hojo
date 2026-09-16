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

**未解明：案件検索の画面IDが分かっていない。**
確認できた画面＝caa0101 マイページ／caa0105 自社情報設定／cdf0101 おすすめ案件通知設定／
cdg0101 お気に入り登録案件一覧／cdg0102 お気に入り登録企業・商品一覧／cea0101 問い合わせ。
**「受注したい（案件を探す）」はタブ内の JavaScript から開くため、URL が HTML に出てこない。**
ブラウザの開発者ツールで1回だけ実際の遷移先を見れば確定する。
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


def screen(sid, token, extra=None):
    """画面IDを POST で開く。**GET では開けない。**"""
    d = [('token', token), ('tmpTokenKey', uuid.uuid4().hex)] + (extra or [])
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
    print('**案件検索の画面IDは未解明。**docstring の「未解明」を参照。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
