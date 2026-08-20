#!/usr/bin/env python3
"""ビジネスチャンス・ナビの公開情報を読む（ログイン不要・閲覧のみ）。

    python3 workflow/fetch_chancenavi.py search 海外展開シンポジウム
    python3 workflow/fetch_chancenavi.py detail 1000029684

東京都中小企業振興公社をはじめ都外郭団体の入札・発注案件は、
**ログインしなくても検索と詳細閲覧ができる**（2026-08-20 確認）。
ログインが要るのは以下だけ：

    - 案件添付資料（仕様書・図面など）の閲覧
    - 質問・希望申請・入札などの送信操作
    - 民間発注案件の企業名・履行場所詳細

したがって「案件の存在・締切・契約方法・受付期間」までは本スクリプトで取れる。
予定価格と仕様書だけは生島様がログインして確認する必要がある。

**このスクリプトは閲覧しかしない。** 送信系のエンドポイントは一切叩かない。

仕組み：サイトは JS で hidden form を組んで POST する素直な作りで、
CSRF トークン(tmpTokenKey)はクライアント側の乱数なので任意の値でよい。
（common.js の createToken() が Date.getTime()+Math.random()+"CLIENT" を返すだけ）
"""
import re
import sys
import html
import time
import urllib.parse
import urllib.request

BASE = "https://www.chancenavi.jp/bcn"
SEARCH = f"{BASE}/uab0201/index"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

# 案件種別 -> 詳細ページ
DETAIL_PAGE = {
    2: "uab0401",   # 東京都の外郭団体等 入札・発注案件  ← 公社案件はここ
    3: "uab0402",   # 民間発注案件（調達案件）
    4: "uab0403",   # 東京都
    5: "uab0404",   # 都内区市町村等
}


def token() -> str:
    return f"{int(time.time() * 1000)}{int(time.time() % 1000)}CLIENT"


def post(url: str, fields: dict, referer: str) -> str:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"User-Agent": UA, "Referer": referer,
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def text_of(page: str) -> list[str]:
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    s = re.sub(r"(?is)</(td|th|tr|div|p|li|dd|dt|h\d)>", "\n", s)
    t = html.unescape(re.sub(r"<[^>]+>", " ", s))
    t = re.sub(r"[ \t　]+", " ", t)
    return [l.strip() for l in t.split("\n") if l.strip()]


def search(word: str):
    page = post(SEARCH, {
        "tmpTokenKey": token(),
        "txt_free_word": word,
        "lst_keyword_retrieval_method": "1",
        "lst_display_num": "50",
        "lst_sort_order": "1",
    }, referer=SEARCH)
    lines = text_of(page)
    i = next((k for k, l in enumerate(lines) if "件の案件が見つかりました" in l), None)
    print(lines[i] if i is not None else "検索結果の見出しを取得できず")
    hits = re.findall(r"goNextPage\((\d+),\s*(\d+)\)", page)
    if not hits:
        print("  該当なし（またはログインが必要な案件のみ）")
    for num, typ in hits:
        print(f"  案件番号 {num} / 種別 {typ} → detail {num} {typ}")
    return hits


def detail(number: str, typ: int = 2):
    pg = DETAIL_PAGE.get(int(typ), "uab0401")
    page = post(f"{BASE}/{pg}/index", {
        "tmpTokenKey": token(), "model": "0",
        "proposalType": str(typ), "proposalNumber": str(number),
    }, referer=SEARCH)
    keep = ("発注者名", "契約管理番号", "件名", "契約方法", "案件業種", "案件概要",
            "履行期間", "履行場所", "案件公示期間", "案件受付期間", "入札資格",
            "希望受付業種", "希望申請要件", "最低制限価格", "発注等級", "受付等級",
            "備考", "添付資料", "状態", "予定価格")
    lines = text_of(page)
    out, grab = [], 0
    for l in lines:
        if any(k in l for k in keep):
            grab = 3
        if grab:
            out.append(l)
            grab -= 1
    print("\n".join(out) if out else "\n".join(lines[:60]))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "search":
        search(" ".join(sys.argv[2:]))
    elif cmd == "detail":
        detail(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 2)
    else:
        sys.exit(__doc__)
