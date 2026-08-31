# -*- coding: utf-8 -*-
"""東京都の「入札（見積）経過調書」から、過去の落札金額と入札者を取る。

なぜ要るか
----------
東京都の発注予定情報には**予定価格が載っていない**（「非公開」）。
規模がわからないと、応募するかどうかも、いくらで入れるかも判断できない。
**だが開札済みの案件は、入札経過調書に落札金額と全入札者の入札額が載っている。**
**年次で反復する案件なら、前年度の落札額がそのまま今年度の目安になる。**

到達手順（2026-08-31 確立）
--------------------------
`bin/tokyo_procurement.py` と同じセッション機構・同じCP932を使う。

1. 検索画面は **page=3 / act=4**、検索の実行は **page=8 / act=1**
2. **`bidDateChk0`〜`bidDateChk16` の17か月分を全部立てる。**
   `selBidDateList` も `1,1,...` にする。ここが必須条件で、
   立てないと「開札日を選択してください」で弾かれる
3. **`keiyakuNoUnderKoshu='00'` を送る。** 空だと下水道局の契約番号で弾かれる
4. 明細は **page=9 / act=3** に `selectno` `contno` `changeCnt` `bidCnt` `consType`
   を渡す。値は一覧の `SelectSubmitListNoCnt(...)` から取る

**「入札結果一覧」（page=3/act=14）は 2026-08-31 時点でシステムエラーを返す。
使えるのはこちら（入札経過情報）である。**

使い方
------
    python3 bin/tokyo_bid_results.py 連携交流 装飾 設営
"""
import html
import re
import sys

from tokyo_procurement import post, JAR, fetch_all  # noqa: F401  同じセッション機構

BLANK = """consgoods gyosyuCd gyosyuNm constKbnCd selectConst hConsgoods syumokuCd
syumokuNm itemKbnCd selectItem hConstRatingA hConstRatingB hConstRatingC
hConstRatingD hConstRatingE hConstRatingX hConstRatingNon hJvUmu bureauCd
bureauNm divisionCd sectionCd bureauKbnCd selectBureau keiyakuNoNendo
keiyakuNoRenban keiyakuNoUnderNendo keiyakuNoUnderRenban hkeiyakuNoNendo
hkeiyakuNoRenban hkeiyakuNoUnderNendo hkeiyakuNoUnderRenban municipalNm
municipalCd municipalKbnCd selectMunicipal resultWarningFlg
syumokuCdList""".split()


def flat(page_html):
    b = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', page_html, flags=re.S)
    L = [x.strip() for x in
         html.unescape(re.sub(r'<[^>]+>', '\n', b)).split('\n') if x.strip()]
    i = L.index('東京都公式ホームページ') + 1 if '東京都公式ホームページ' in L else 0
    return L[i:]


def search(keyword):
    """件名文字列で入札経過調書を検索する（物品等・過去17か月ぶん）。"""
    JAR.unlink(missing_ok=True)
    post([('page', 1), ('act', 1), ('direct', 1)])
    post([('page', 3), ('act', 4)])
    f = [('page', 8), ('act', 1), ('allBureauFlag', '1'),
         ('constConsgoods', '2'),
         ('Era_KeiyakuNoDate', '5'), ('Era_KeiyakuNoUnderDate', '5'),
         ('keiyakuNoUnderKoshu', '00'),
         ('ankenName', keyword), ('hAnkenName', keyword),
         ('bidwayIppan', '1'), ('bidwayShimei', '1'), ('bidwayKibou', '1'),
         ('bidwayZuikei', '1'), ('bidwayTokumei', '1'),
         ('hBidwayIppan', '1'), ('hBidwayShimei', '1'), ('hBidwayKibou', '1'),
         ('hBidwayZuikei', '1'), ('hBidwayTokumei', '1'),
         ('selBidDateList', ','.join('1' * 17)), ('bidDateCnt', '17'),
         ('totalCnt', '0'), ('elmVolume', '10')]
    f += [('bidDateChk%d' % i, '1') for i in range(17)]
    f += [(k, '') for k in BLANK]
    return post(f)


def details(list_html, limit=6):
    """一覧の各行の明細（落札金額・入札者一覧）を開いて返す。"""
    calls = re.findall(
        r'SelectSubmitListNoCnt\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)',
        list_html)
    out = []
    for pg, ac, sel, cont, chg, bid, ct in calls[:limit]:
        d = post([('page', pg), ('act', ac), ('selectno', sel),
                  ('contno', cont), ('changeCnt', chg), ('bidCnt', bid),
                  ('consType', ct)])
        out.append(flat(d))
    return out


def pick(L, key, n=1):
    if key in L:
        i = L.index(key)
        return ' / '.join(L[i + 1:i + 1 + n])
    return ''


def show(keyword, limit=6):
    h = search(keyword)
    L = flat(h)
    if any('エラー' in x for x in L[:3]):
        print('  [%s] %s' % (keyword, ' / '.join(L[:5])))
        return
    m = re.search(r'総件数[\s　]*([\d,]+)[\s　]*件', h)
    n = m.group(1) if m else '0'
    print('== [%s] 総件数 %s' % (keyword, n))
    if n == '0':
        return
    for D in details(h, limit):
        print('   件名   ', pick(D, '件　名', 2).replace('【電子】 / ', ''))
        print('   契約部署', pick(D, '契約部署'), '／開札', pick(D, '開札日時'))
        print('   営業種目', pick(D, '営業種目'))
        print('   落札者  ', pick(D, '落札者氏名'), '／**落札金額', pick(D, '落札金額'), '**')
        try:
            i = D.index('備考') + 1
            bids = [x for x in D[i:i + 30] if re.match(r'^[\d,]+円$', x)]
            if bids:
                print('   入札額（税抜）', ' / '.join(bids))
        except ValueError:
            pass
        print()


if __name__ == '__main__':
    for w in (sys.argv[1:] or ['連携交流']):
        show(w)
