#!/usr/bin/env python3
"""東京都電子調達システム「入札情報サービス」の発注予定情報を取る。

なぜこれが要るか
----------------
東京都生活文化スポーツ局のサイトは Liferay 製の SPA で、本文が静的HTMLに
含まれない。curl でも Chromium でも一覧が読めない。
**だが発注情報そのものは、財務局の電子調達システムに集まる。**
2027年度の国民文化祭、2028年度のねんりんピックの発注も、ここに出る。

p-portal と違い、**ここは POST が通る。**
2026-08-28 に到達手順を確立した。要点は3つ。

1. 文字コードは **Windows-31J（CP932）**。UTF-8 で投げると化けて0件になる
2. **`allBureauFlag=1` が必須。** これがないと「該当なし」しか返らない。
   件名文字列だけ入れても駄目で、ここで半日溶かしかけた
3. 検索は2段階。まず page=4,act=1 で検索し、
   次に **同じセッションで page=4,act=3** を投げると一覧が返る。
   200件を超えると間に確認画面が挟まるが、act=3 はそれも兼ねる

**件名文字列で絞ってはいけない。** 「催事」で検索すると0件になる。
「催事関係業務」は件名ではなく**営業種目の欄**に入っているためである。
全件を取ってから営業種目で絞ること。既定の動作がそれになっている。

使い方
------
    python3 bin/tokyo_procurement.py            # 当社に該当する種目だけ
    python3 bin/tokyo_procurement.py --all      # 全件
"""
import html
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

BASE = 'https://www.e-procurement.metro.tokyo.lg.jp'
URL = BASE + '/SrvPublish'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
      'AppleWebKit/537.36')
JAR = Path('/tmp/tokyo_procurement.cookie')

# 空で送らないとサーバが「契約番号－年度が不正」で弾く項目
BLANK = """gyosyuCd gyosyuNm constKbnCd selectConst syumokuCd syumokuNm itemKbnCd
selectItem hConstRatingA hConstRatingB hConstRatingC hConstRatingD hConstRatingE
hConstRatingX hConstRatingNon hJvUmu bureauCd bureauNm divisionCd sectionCd
bureauKbnCd selectBureau keiyakuNoNendo keiyakuNoRenban keiyakuNoUnderNendo
keiyakuNoUnderRenban hkeiyakuNoNendo hkeiyakuNoRenban hkeiyakuNoUnderNendo
hkeiyakuNoUnderRenban municipalNm municipalCd municipalKbnCd selectMunicipal
hItemTokutei hitemRirekiPublishFlg dateStart dateEnd resultWarningFlg
syumokuCdList""".split()


def post(fields):
    """CP932 でエンコードして POST する。セッションは cookie jar で保つ。"""
    body = '&'.join(
        '%s=%s' % (k, urllib.parse.quote(str(v).encode('cp932')))
        for k, v in fields)
    r = subprocess.run(
        ['curl', '-sSL', '-A', UA, '--max-time', '40', '--compressed',
         '-b', str(JAR), '-c', str(JAR),
         '-H', 'Referer: ' + URL,
         '-H', 'Content-Type: application/x-www-form-urlencoded',
         '--data-binary', body, URL],
        capture_output=True, check=True)
    return r.stdout.decode('cp932', 'replace')


def search(keyword='', era='5', y_from='8', y_to='9'):
    """発注予定を検索して一覧HTMLを返す。

    era='5' は令和。y_from/y_to は令和の年。既定は令和8年度いっぱい。
    """
    JAR.unlink(missing_ok=True)
    post([('page', 1), ('act', 1), ('direct', 1)])   # セッション確立
    post([('page', 3), ('act', 3)])                  # 発注予定情報の検索画面

    f = [('page', 4), ('act', 1),
         ('allBureauFlag', '1'),                     # ← これが必須
         ('consgoods', '2'), ('hConsgoods', '2'), ('itemConsgoods', '2'),
         ('Era_KeiyakuNoDate', era), ('Era_KeiyakuNoUnderDate', era),
         ('keiyakuNoUnderKoshu', '00'),
         ('Era_StartDate', era), ('Era_EndDate', era),
         ('StartDateYY', y_from), ('StartDateMM', '4'), ('StartDateDD', '1'),
         ('EndDateYY', y_to), ('EndDateMM', '3'), ('EndDateDD', '31'),
         ('ankenName', keyword), ('hAnkenName', keyword),
         ('bidwayIppan', '1'), ('bidwayKibou', '1'), ('bidwayZuikei', '1'),
         ('hBidwayIppan', '1'), ('hBidwayKibou', '1'), ('hBidwayZuikei', '1'),
         ('totalCnt', '0'), ('elmVolume', '10'), ('gamenId', 'hacchuyotei')]
    f += [(k, '') for k in BLANK]
    post(f)
    return post([('page', 4), ('act', 3)])           # 一覧を表示


def rows(page_html):
    """一覧HTMLから案件名・局・受付期間を拾う。"""
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', page_html, flags=re.S)
    out = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', body, re.S):
        cells = [html.unescape(re.sub(r'\s+', ' ',
                                      re.sub(r'<[^>]+>', ' ', td))).strip()
                 for td in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
        cells = [c for c in cells if c]
        if len(cells) >= 3:
            out.append(cells)
    return out


def next_page(page_html):
    """「次に進む」があるか。ページ送りは SelectSubmit(5,6)。"""
    return 'SelectSubmit(5,6)' in page_html


def fetch_all(keyword='', era='5', y_from='8', y_to='9', max_pages=40):
    """検索してページを最後まで送り、全行を返す。"""
    h = search(keyword, era, y_from, y_to)
    n = total(h)
    out = rows(h)
    seen = 1
    while next_page(h) and seen < max_pages:
        h = post([('page', 5), ('act', 6)])
        got = rows(h)
        if not got:
            break
        out += got
        seen += 1
    return n, out


# 当社（イベント企画・会場設営・装飾）に当たる営業種目。
# 名称は電子調達システムの営業種目欄の表記そのもの。
TARGET_SYUMOKU = ['催事関係業務', '企画立案支援', '広告代理', '映像等制作',
                  '印刷', '運送等請負', '警備・受付', 'その他の業務委託等']


def total(page_html):
    m = re.search(r'総件数[\s　]*([\d,]+)[\s　]*件', page_html)
    return m.group(1) if m else '?'


def main():
    show_all = '--all' in sys.argv
    n, rs = fetch_all()
    body = [c for c in rs if not c[0].startswith('公表日')]
    if show_all:
        hit = body
    else:
        hit = [c for c in body
               if len(c) > 3 and any(t in c[3] for t in TARGET_SYUMOKU)]
    print('総件数 %s件 / 取得 %d件 / 該当 %d件'
          % (n, len(body), len(hit)))
    print('=' * 70)
    for c in hit:
        print('%s  %s' % (c[0], c[3] if len(c) > 3 else ''))
        print('   %s' % c[2].replace('【電子】 ', ''))
        if len(c) > 4:
            print('   履行期間 %s' % c[4])
        print()


if __name__ == '__main__':
    main()
