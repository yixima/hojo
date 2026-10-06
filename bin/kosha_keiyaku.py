# -*- coding: utf-8 -*-
"""東京都中小企業振興公社の「契約情報」の表を読み、**受付中のものだけ**を締切つきで出す。

なぜ専用の道具が要るか（2026-10-05〜07 の実測）
------------------------------------------------
この表は1枚に令和8年度の全件（整理番号1〜64）が並び、
**最後の列の「受付中／終了」だけが、いま出せるかどうかを決めている。**
チャネル掃引（`bin/sweep_channels.py`）は見出しの a タグを拾う作りなので、
この表からは**64件すべてを等しく「未登録の見出し」として出してしまい、
そのうち63件が既に終了していることが分からない。**
実際 10/06 の掃引は当社領域9件を出したが、受付中はそのうち1件だけだった。
**読めない報告は、報告が無いのと同じである。**

なぜこの発注者が重要か
----------------------
東京手仕事と同じ発注者であり、**当社の本業（展示会パビリオン出展・フォーラム開催）が
毎年ここに出る。**しかも**東京都の等級要件が無い**
（選定の制限は5項目のみ。https://www.tokyo-kosha.or.jp/kosha/keiyaku/infomation.html）。
産業交流展2.6億円で当たった等級の壁とは別の入口である。

**希望申出の受付と仕様書はビジネスチャンス・ナビ上にしかない。**
この表から読めるのは件名・公表日・希望申出期間・受付状況だけで、**予定価格は読めない。**
`CN_USER`/`CN_PASS` が無いときは「読めなかった」と出す。黙って17時を当てない。

    python3 bin/kosha_keiyaku.py            # 受付中のものを出す
    python3 bin/kosha_keiyaku.py --all      # 終了分も出す（来年の予測根拠）
"""
import re, html, io, os, sys, csv, subprocess, datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST = ZoneInfo('Asia/Tokyo')
URL = 'https://www.tokyo-kosha.or.jp/kosha/keiyaku/'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
# 令和N年M月D日[H:MM] を拾う。**時刻は14:00が多いが、当てずに書いてあるものを採る**
WA = re.compile(r'令和(\d+)年(\d+)月(\d+)日\s*(\d{1,2})[:：](\d{2})')
WD = re.compile(r'令和(\d+)年(\d+)月(\d+)日')


def wa2date(y, m, d):
    """令和→西暦。令和1年＝2019年。"""
    return datetime.date(2018 + int(y), int(m), int(d))


def fetch():
    r = subprocess.run(['curl', '-sSL', '-A', UA, '-H', 'Accept: text/html',
                        '--max-time', '30', '--compressed',
                        '-w', '\n#H%{http_code}', URL],
                       capture_output=True, timeout=45)
    raw = r.stdout.decode('utf-8', 'replace')
    m = re.search(r'\n#H(\d{3})\s*$', raw)
    code = int(m.group(1)) if m else 0
    if m: raw = raw[:m.start()]
    return raw, code


def parse(s):
    """表の行を (整理番号, 件名, 公表日, 期間の文字列, 受付状況) にする。"""
    t = html.unescape(re.sub(r'<[^>]+>', '\n', re.sub(r'(?is)<(script|style).*?</\1>', ' ', s)))
    rows = [x.strip() for x in t.split('\n') if x.strip()]
    try:
        i = next(k for k, r in enumerate(rows) if re.match(r'契約情報\(令和\d+年度\)', r))
    except StopIteration:
        return []
    seg = rows[i:]
    out = []
    for j, r in enumerate(seg):
        if r not in ('受付中', '終了'):
            continue
        # 受付状況の直前5行が 整理番号・件名・公表日・期間(始)・期間(終)
        blk = seg[max(0, j - 5):j]
        if len(blk) < 5:
            continue
        no, name, pub = blk[0], blk[1], blk[2]
        span = blk[3] + blk[4]
        out.append((no, name, pub, span, r))
    return out


def main():
    now = datetime.datetime.now(JST)
    print('基準日時 %s JST（実時刻）' % now.strftime('%Y-%m-%d %H:%M'))
    s, code = fetch()
    if not s or not (200 <= code < 300):
        print('**一次資料を取得できなかった（HTTP %d）。「案件なし」ではない。**' % code)
        return 2
    items = parse(s)
    if not items:
        print('**表を読めなかった。ページの作りが変わった可能性がある。'
              '0件と報告してはいけない。**')
        return 2

    open_ = [x for x in items if x[4] == '受付中']
    done = [x for x in items if x[4] == '終了']
    print('契約情報 %d件（**受付中 %d ／ 終了 %d**）' % (len(items), len(open_), len(done)))

    print('\n■ いま出せるもの')
    if not open_:
        print('  なし（0件）。**表は読めている。**受付中の行が存在しない')
    for no, name, pub, span, _ in open_:
        # **期間の「終わり」を採る。最初の一致は「始まり」である。**
        # 2026-10-07 実測：`WA.search` で先頭を採ったため、
        # 「令和8年10月6日9:00～令和8年10月15日14:00」から 10/6 9:00 を拾い、
        # **受付中の案件を「残り -24時間」＝もう閉じたと表示していた。**
        # 閉じたと誤って言う検出器は、何も言わない検出器より悪い。
        ms = WA.findall(span)
        m = None
        if ms:
            g = ms[-1]
            class _M:            # findall の組を search と同じ形で扱う
                def __init__(s_, g_): s_.g = g_
                def group(s_, i): return s_.g[i - 1]
            m = _M(g)
        if m:
            d = wa2date(m.group(1), m.group(2), m.group(3))
            hh = '%02d:%s' % (int(m.group(4)), m.group(5))
            dl = datetime.datetime.combine(d, datetime.time(int(m.group(4)), int(m.group(5))),
                                           tzinfo=JST)
            left = dl - now
            h = int(left.total_seconds() // 3600)
            rest = ('**残り %d時間**' % h) if h < 72 else ('残り %d日' % (h // 24))
            print('  [%s] %s' % (no, name[:70]))
            print('       希望申出 %s %s　%s　（公表 %s）' % (d, hh, rest, pub))
            pm = WD.search(pub)
            if pm and wa2date(*pm.groups()) > d:
                print('       ★**自己矛盾：公表日より締切が早い。期間の読み違いを疑う**')
        else:
            print('  [%s] %s' % (no, name[:70]))
            print('       **希望申出の期限を読めなかった（%s）。既定値を当てない**' % span[:40])

    if '--all' in sys.argv:
        print('\n■ 終了したもの（来年の予測根拠）')
        for no, name, pub, span, _ in done:
            m = WD.findall(span)
            print('  [%s] %s … %s' % (no, name[:62], span[:46]))

    print('\n**予定価格と仕様書はこの表から読めない。**'
          'ビジネスチャンス・ナビ上にしかなく、CN_USER/CN_PASS が %s。'
          % ('設定済み' if os.environ.get('CN_USER') else '**未設定のため読めていない**'))
    print('**等級要件は無い。**選定の制限は5項目のみ'
          '（https://www.tokyo-kosha.or.jp/kosha/keiyaku/infomation.html）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
