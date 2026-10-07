# -*- coding: utf-8 -*-
"""東京都の外郭団体の「契約情報」の表を読み、**受付中のものだけ**を締切つきで出す。

対象（いずれも整理番号・公表日・件名・希望申出期間・受付状況の表を自社サイトに持つ）
  ・公益財団法人東京都中小企業振興公社
  ・公益財団法人東京観光財団（TCVB）

なぜ専用の道具が要るか（2026-10-05〜08 の実測）
------------------------------------------------
この表は1枚に年度の全件が並び、
**最後の列の「受付中／終了」だけが、いま出せるかどうかを決めている。**
チャネル掃引（`bin/sweep_channels.py`）は見出しを拾う作りなので、
この表からは**全件を等しく「未登録の見出し」として出してしまい、
そのほとんどが既に終了していることが分からない。**
10/06 の掃引は公社から当社領域9件を出したが、受付中はそのうち1件だけだった。
**読めない報告は、報告が無いのと同じである。**

なぜこの発注者たちが重要か
--------------------------
**東京都の等級要件が無い。**公社の「選定の制限」は5項目のみ
（https://www.tokyo-kosha.or.jp/kosha/keiyaku/infomation.html）。
産業交流展2.6億円で当たった等級の壁とは別の入口である。
そして**当社の本業（展示会パビリオン出展・フォーラム開催・観光プロモーション）が
毎年ここに出る。**公社は東京手仕事の発注者でもある。

**希望申出の受付と仕様書はビジネスチャンス・ナビ上にしかない。**
この表から読めるのは件名・公表日・希望申出期間・受付状況だけで、**予定価格は読めない。**
ただし **TCVB は「ご登録前に仕様書等を確認されたい場合は keiyaku@tcvb.or.jp まで」
と明記しており、メールで仕様書を取り寄せられる。**ナビに入れなくても中身は読める。

    python3 bin/gaikaku_keiyaku.py            # 受付中のものを出す
    python3 bin/gaikaku_keiyaku.py --all      # 終了分も出す（来年の予測根拠）
"""
import re, html, io, os, sys, subprocess, datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST = ZoneInfo('Asia/Tokyo')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

SITES = [
    ('東京都中小企業振興公社', 'https://www.tokyo-kosha.or.jp/kosha/keiyaku/',
     r'契約情報\(令和\d+年度\)'),
    ('東京観光財団（TCVB）', 'https://www.tcvb.or.jp/jp/agreement/2026/',
     r'^(契約情報|整理番号)$'),
]

# 和暦「令和8年10月15日14:00」と 西暦「2026年10月09日12時」の両方を読む。
# **片方しか読めない道具は、もう片方の案件を静かに落とす。**
# 和暦「令和8年10月15日14:00」と 西暦「2026年10月09日12時」の両方を読む。
# **片方しか読めない道具は、もう片方の案件を静かに落とす。**
# **時刻の無い日付も拾う。**拾わないと、期間の「終わり」が時刻付きでないときに
# 始まりを締切と取り違える（2026-10-07 にその取り違えを実測した）。
WAREKI = re.compile(r'令和(\d+)年(\d+)月(\d+)日\s*(?:(\d{1,2})(?:[:：](\d{2})|時))?')
SEIREKI = re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(?:(\d{1,2})(?:[:：](\d{2})|時))?')
PUB_W = re.compile(r'令和(\d+)年(\d+)月(\d+)日')
PUB_S = re.compile(r'(\d{4})年(\d{1,2})月(\d{1,2})日')


def wa2date(y, m, d):
    """令和→西暦。令和1年＝2019年。"""
    return datetime.date(2018 + int(y), int(m), int(d))


def gates(span):
    """期間の文字列から (日付, 時, 分, 時刻が書いてあるか) を**出現順に全部**返す。

    **最後の一つが締切である。最初の一つは受付の始まりである。**
    2026-10-07 実測：先頭を採ったため、受付中の案件を
    「残り -24時間」＝もう閉じた、と表示した。
    **閉じたと誤って言う検出器は、何も言わない検出器より悪い。**
    判断面から案件が1件消えるのに、画面には何の異常も出ない。

    時刻が書いていない日付も返す。**既定値を黙って当てない**（CLAUDE.md）。
    呼ぶ側が「時刻未確認」と画面に出す。
    """
    out = []
    for pat, wa in ((WAREKI, True), (SEIREKI, False)):
        for m in pat.finditer(span):
            d = (wa2date(*m.group(1, 2, 3)) if wa
                 else datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
            if m.group(4) is None:
                out.append((d, 0, 0, False))
            else:
                out.append((d, int(m.group(4)), int(m.group(5) or 0), True))
        if out:
            return out
    return out


def fetch(url):
    r = subprocess.run(['curl', '-sSL', '-A', UA, '-H', 'Accept: text/html',
                        '--max-time', '30', '--compressed',
                        '-w', '\n#H%{http_code}', url],
                       capture_output=True, timeout=45)
    raw = r.stdout.decode('utf-8', 'replace')
    m = re.search(r'\n#H(\d{3})\s*$', raw)
    code = int(m.group(1)) if m else 0
    if m: raw = raw[:m.start()]
    return raw, code


def parse(s, head):
    """表の行を (整理番号, 件名, 公表日, 期間, 受付状況) にする。

    受付状況の行から**上に遡って**組み立てる。列数は団体で違い、
    期間が1行のところ（TCVB）と2行に割れるところ（公社）がある。
    """
    t = html.unescape(re.sub(r'<[^>]+>', '\n', re.sub(r'(?is)<(script|style).*?</\1>', ' ', s)))
    rows = [x.strip() for x in t.split('\n') if x.strip()]
    try:
        i = next(k for k, r in enumerate(rows) if re.match(head, r))
    except StopIteration:
        return []
    seg = rows[i:]
    out = []
    for j, r in enumerate(seg):
        if r not in ('受付中', '終了'):
            continue
        blk = seg[max(0, j - 6):j]
        # 整理番号＝数字だけの行のうち、いちばん後ろのもの
        no = next((x for x in reversed(blk) if re.fullmatch(r'\d{1,4}', x)), '?')
        # 期間＝「～」を含む行、または日時を2つ含む連結
        span = ''
        for k in range(len(blk) - 1, -1, -1):
            cand = blk[k] + (blk[k + 1] if k + 1 < len(blk) else '')
            if len(gates(cand)) >= 1:
                span = cand
                break
        # 件名＝いちばん長い行
        name = max(blk, key=len) if blk else ''
        pub = next((x for x in blk if PUB_S.fullmatch(x) or PUB_W.fullmatch(x)), '')
        out.append((no, name, pub, span, r))
    return out


def main():
    now = datetime.datetime.now(JST)
    print('基準日時 %s JST（実時刻）' % now.strftime('%Y-%m-%d %H:%M'))
    bad = 0
    for org, url, head in SITES:
        print('\n──── %s' % org)
        s, code = fetch(url)
        if not s or not (200 <= code < 300):
            print('  **一次資料を取得できなかった（HTTP %d）。「案件なし」ではない。**' % code)
            bad += 1
            continue
        items = parse(s, head)
        if not items:
            print('  **表を読めなかった。ページの作りが変わった可能性がある。'
                  '0件と報告してはいけない。**')
            bad += 1
            continue
        open_ = [x for x in items if x[4] == '受付中']
        print('  契約情報 %d件（**受付中 %d ／ 終了 %d**）'
              % (len(items), len(open_), len(items) - len(open_)))
        if not open_:
            print('  いま出せるもの：なし（0件）。**表は読めている**')
        for no, name, pub, span, _ in open_:
            gs = gates(span)
            print('  [%s] %s' % (no, name[:68]))
            if not gs:
                print('       **希望申出の期限を読めなかった（%s）。既定値を当てない**'
                      % span[:44])
                continue
            d, hh, mm, known = gs[-1]          # **最後が締切**
            dl = datetime.datetime.combine(d, datetime.time(hh, mm), tzinfo=JST)
            h = int((dl - now).total_seconds() // 3600)
            rest = ('**残り %d時間**' % h) if h < 72 else ('残り %d日' % (h // 24))
            hhmm = ('%02d:%02d' % (hh, mm)) if known else '**時刻未確認**'
            print('       希望申出 %s %s　%s　（公表 %s）' % (d, hhmm, rest, pub))
            pm = PUB_W.search(pub) or PUB_S.search(pub)
            if pm:
                pd = (wa2date(*pm.groups()) if '令和' in pub
                      else datetime.date(*map(int, pm.groups())))
                if pd > d:
                    print('       ★**自己矛盾：公表日より締切が早い。期間の読み違いを疑う**')
        if '--all' in sys.argv:
            for no, name, pub, span, st in items:
                if st == '終了':
                    print('    （終）[%s] %s … %s' % (no, name[:56], span[:40]))

    print('\n**予定価格と仕様書はこれらの表から読めない。**'
          'ビジネスチャンス・ナビ上にしかなく、CN_USER/CN_PASS が %s。'
          % ('設定済み' if os.environ.get('CN_USER') else '**未設定のため読めていない**'))
    print('**ただし TCVB はメールで仕様書を送ってくれる**（keiyaku@tcvb.or.jp）。'
          'ナビに入れなくても中身は読める')
    print('**等級要件は無い。**公社の選定の制限は5項目のみ'
          '（https://www.tokyo-kosha.or.jp/kosha/keiyaku/infomation.html）')
    return 2 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
