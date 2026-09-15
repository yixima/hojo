#!/usr/bin/env python3
"""東京都電子調達システム（入札情報サービス）の発注予定情報を拾う。

    python3 workflow/sweep_tokyo.py
    python3 workflow/sweep_tokyo.py --min-score 2

出力: data/sweep/tokyo_YYYYMMDD.csv

■ なぜ要るのか
東京都の業務委託は、局ごとのサイトではなく**この1か所に集まる**。
都庁本体・各局・事務所の発注予定が横断で載るため、局を一つずつ巡回するより
取りこぼしが少ない。御社の主戦場である「催事関係業務」「企画立案支援」
「広告代理」がそのまま営業種目として立っている。

■ 仕組み（実測 2026-09-15）
文字コードは **Windows-31J（cp932）**。UTF-8で読むと件名が全部化ける。
POST 先は `/SrvPublish` の1本で、`page` と `act` の組で画面が決まる。
  1. POST page=1 act=1 direct=1   … 入口。セッションを張る
  2. POST page=3 act=3            … 発注予定の検索フォーム（全項目をここから写す）
  3. POST page=4 act=1            … 検索実行
  4. POST page=4 act=3            … 「表示」。ここで初めて一覧が出る

**必須項目は `consgoods` である。** ここが最大の落とし穴だった。
画面上のラジオは `constConsgoods`（工事）／`itemConsgoods`（物品等）だが、
サーバが見ているのは隠しフィールドの `consgoods` のほうで、JavaScript が
そこへ写している。ラジオだけ送ると「検索条件なし（コード6）」で弾かれ続ける。
**画面に見えている項目を送っても通らない。** 隠しフィールドまで写すこと。

■ 件名検索を使わない理由
`ankenName` で「海外」を引くと0件になる。都の発注予定の件名は
「○○に係る業務委託」のように事務的で、事業内容の語が件名に出ないものが多い。
そこで**営業種目（物品等）で全件取り、こちらで関連度を付ける**。
件名検索に頼ると、拾えるはずのものを件名の書き方だけで落とす。
"""
from __future__ import annotations

import argparse
import csv
import html
import http.cookiejar
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sweep import score  # noqa: E402

ROOT = "https://www.e-procurement.metro.tokyo.lg.jp/"
SRV = ROOT + "SrvPublish"
OUTDIR = Path("data/sweep")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")


def text(s: str) -> str:
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)))


def form_fields(page: str) -> dict[str, str]:
    """画面の入力項目をそっくり写す。隠しフィールドを落とさないのが要点。"""
    d: dict[str, str] = {}
    for m in re.finditer(r"(?is)<input[^>]*>", page):
        tag = m.group(0)
        nm = re.search(r'name=["\']?([\w.]+)', tag)
        if not nm:
            continue
        ty = re.search(r'type=["\']?(\w+)', tag)
        vl = re.search(r'value=["\']([^"\']*)["\']', tag)
        kind = (ty.group(1).lower() if ty else "text")
        if kind in ("checkbox", "radio"):
            if "checked" in tag.lower():
                d[nm.group(1)] = vl.group(1) if vl else "1"
            continue
        d[nm.group(1)] = vl.group(1) if vl else ""
    for m in re.finditer(r'(?is)<select[^>]*name=["\']?(\w+)["\']?[^>]*>(.*?)</select>', page):
        sel = re.search(r'(?is)<option[^>]*value=["\']([^"\']*)["\'][^>]*selected', m.group(2))
        opts = re.findall(r'(?is)<option[^>]*value=["\']([^"\']*)["\']', m.group(2))
        d[m.group(1)] = sel.group(1) if sel else (opts[0] if opts else "")
    return d


class Tokyo:
    def __init__(self) -> None:
        cj = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj))
        self.op.addheaders = [("User-Agent", UA)]

    def post(self, d: dict) -> str:
        body = urllib.parse.urlencode(d, encoding="cp932", errors="replace").encode()
        req = urllib.request.Request(
            SRV, data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": SRV})
        # cp932 で読む。UTF-8 で読むと件名が全部化ける
        return self.op.open(req, timeout=90).read().decode("cp932", "replace")

    def open_search(self) -> dict[str, str]:
        self.post({"page": 1, "act": 1, "direct": 1})
        return form_fields(self.post({"page": 3, "act": 3}))


def parse_list(page: str) -> list[dict]:
    """一覧の行を拾う。

    案件行は必ず `SelectSubmitNo(7,3,...)` の詳細リンクを持つ。**件名の語で
    絞ると取りこぼす。** 当初「委託|業務|購入…」を含む行だけ拾ったところ、
    423件のはずが311行しか取れず、しかも画面の総件数は423のままなので
    取りこぼしに気づけなかった。構造（詳細リンクの有無）で判定する。
    """
    out = []
    for tr in re.finditer(r"(?is)<tr[^>]*>(.*?)</tr>", page):
        row = tr.group(1)
        if "SelectSubmitNo" not in row:
            continue
        cells = [re.sub(r"\s+", " ",
                        html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", row)]
        cells = [c for c in cells if c]
        if not cells:
            continue
        name = max(cells, key=len)
        if len(name) < 6:
            continue
        out.append({"案件名": name, "行": " / ".join(cells)[:300]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=int, default=1)
    args = ap.parse_args()

    today = date.today()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    t = Tokyo()
    try:
        base = t.open_search()
    except Exception as e:
        print(f"東京都電子調達に到達できません（{type(e).__name__}）。"
              "到達不可としてレポートに明記すること。")
        return 1
    print(f"検索フォームの項目 {len(base)} 個を取得")

    # **一度に全部取ろうとすると500件で頭打ちになる。** 621件のうち500件しか
    # 一覧に出ず、しかも画面には「総件数621件」と表示され続けるため、
    # 取りこぼしに気づけない。契約方法で3つに割り、どれも上限に届かなくする。
    METHODS = [("一般競争入札", "bidwayIppan", "hBidwayIppan"),
               ("希望制指名競争入札", "bidwayKibou", "hBidwayKibou"),
               ("随意契約", "bidwayZuikei", "hBidwayZuikei")]
    rows: list[dict] = []
    seen: set[str] = set()
    grand = 0
    for label, fld, hfld in METHODS:
        t = Tokyo()
        try:
            base = t.open_search()
        except Exception as e:
            print(f"  {label}: 到達できません（{type(e).__name__}）")
            continue
        d = dict(base)
        d.pop("constConsgoods", None)
        # ここが要。サーバが見るのは consgoods。画面のラジオだけでは通らない
        d.update({"page": 4, "act": 1, "itemConsgoods": "2",
                  "consgoods": "2", "hConsgoods": "2", fld: "1", hfld: "1"})
        res = t.post(d)
        m = re.search(r"該当する検索結果は\s*(\d+)\s*件", re.sub(r"\s+", "", text(res)))
        if m:
            # 200件を超えると確認画面を挟む。「表示」を押して一覧へ
            total = int(m.group(1))
            listing = t.post({"page": 4, "act": 3})
        else:
            # 200件以下はそのまま一覧が返る
            total = 0
            listing = res
        got = parse_list(listing)
        page_n = 1
        while (total == 0 or len(got) < total) and page_n < 30:
            nxt = t.post({"page": 5, "act": 6})
            more = [r for r in parse_list(nxt)
                    if r["案件名"] not in {x["案件名"] for x in got}]
            if not more:
                break
            got += more
            page_n += 1
        grand += total or len(got)
        new_rows = [r for r in got if r["案件名"] not in seen]
        seen.update(r["案件名"] for r in new_rows)
        rows += new_rows
        short = f"（総件数 {total} 件）" if total else ""
        print(f"  {label:10} {len(got):4} 行取得{short} / {page_n} 画面")

    print(f"発注予定（物品等・委託）合計 {len(rows)} 件")
    if not rows:
        print("0件。検索が通っていない可能性があるので画面を確認すること。")
        return 1

    found = []
    for r in rows:
        pts, hits = score(r["案件名"])
        if pts < args.min_score:
            continue
        found.append({"検出日": today.isoformat(), "経路": "東京都電子調達",
                      "関連度": pts, "一致語": hits, "案件名": r["案件名"][:200],
                      "明細": r["行"],
                      "URL": ROOT + "indexPbi.jsp"})
    out = OUTDIR / f"tokyo_{today:%Y%m%d}.csv"
    fields = ["検出日", "経路", "関連度", "一致語", "案件名", "明細", "URL"]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(found, key=lambda x: -x["関連度"]):
            w.writerow(r)
    print(f"\n{out}: {len(found)} 件（関連度{args.min_score}以上）")
    for r in sorted(found, key=lambda x: -x["関連度"])[:15]:
        print(f"  [{r['関連度']}] {r['案件名'][:60]}")
    if grand and len(rows) < grand * 0.95:
        print(f"\n! 一覧が {len(rows)}/{grand} 件しか取れていない。"
              "契約方法よりさらに細かい分割が要る")
    return 0


if __name__ == "__main__":
    sys.exit(main())
