# -*- coding: utf-8 -*-
"""巡回スクリプト共通の取得処理。

   **なぜリトライが要るか（2026-08-28）**
   岡山県のサイトは、同じURLが 000（0バイト）を返したり 200 を返したりする。
   1回で諦めると「取得不可」と誤って記録し、巡回できるはずの県を
   永久に諦めることになる。3回試せばほぼ通った。

   恒常的に遮断されている巡回先（岐阜県・山梨県・えひめ産業振興財団・
   岡山県産業振興財団）は sources.yaml の blocked_sources にある。
   断続的に失敗するだけの巡回先は flaky_sources にある。**両者を混同しない。**
"""
import subprocess, time

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0 Safari/537.36')

def fetch_bytes(url, timeout=22, tries=3, min_size=500, headers=None):
    """成功するまで最大 tries 回試す。待ち時間は 1秒 → 2秒 → 4秒。

    min_size に満たない応答は失敗とみなす。
    0バイトや、エラーページだけが返るケースを拾うため。
    """
    args = ['curl', '-sSL', '-A', UA, '--max-time', str(timeout), '--compressed', '-k']
    for h in (headers or []):
        args += ['-H', h]
    for i in range(tries):
        try:
            r = subprocess.run(args + [url], capture_output=True, timeout=timeout + 10)
            if len(r.stdout) >= min_size:
                return r.stdout
        except Exception:
            pass
        if i < tries - 1:
            time.sleep(2 ** i)
    return b''

def fetch(url, timeout=22, tries=3, min_size=500, headers=None):
    """本文を文字列で返す。取れなければ空文字。"""
    return fetch_bytes(url, timeout, tries, min_size, headers).decode('utf-8', 'replace')

def title_of(html):
    """岡山県のようにメニューが本文より前に大量に入るサイトでは、
       <title> を見るのが状態判定の最短路。
       「結果の公表」「終了」が入っていれば締切済みと判断できる。"""
    import re
    m = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''
