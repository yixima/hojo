#!/usr/bin/env python3
"""調達ポータルの落札実績オープンデータから、過年度の落札金額を引く。

    python3 workflow/awards_pportal.py                 # ドメイン語で全年度を検索
    python3 workflow/awards_pportal.py --match         # 今回の案件に前年実績を突き合わせる
    python3 workflow/awards_pportal.py --keyword 出展
    python3 workflow/awards_pportal.py --refresh       # zip を取り直す

出力:
    data/awards/awards_hits_YYYYMMDD.csv    ドメイン語に当たった落札実績
    data/awards/match_YYYYMMDD.csv          今回拾った案件 × 過年度実績の対応づけ
キャッシュ:
    data/awards/cache/successful_bid_record_info_all_YYYY.zip

■ なぜ要るのか
[5]金額の第1手段は「同じ事業の前年の落札金額」である。ところが各省庁の
落札公示は年度ごとにPDFで散らばっていて、横断して引く手段が無い……と
思っていたが、**調達ポータルが全件のオープンデータCSVを配っている。**
国の機関の落札実績が、案件番号・件名・落札日・落札金額・落札者・法人番号の
6情報で1行ずつ入っている。R6で約3.4万行。これを引けば、
「仕様書から積算」に頼らずに済む案件がかなりある。

■ データの形（実測 2026-08-21）
ヘッダ行が無い8列CSV（UTF-8 BOM付き・zip圧縮）。列は次のとおり。
    0 調達案件番号  1 調達案件名称  2 落札日  3 落札金額(円・小数)
    4 区分コード    5 機関コード    6 落札者名  7 法人番号
**ヘッダが無いので、列の意味は位置でしか分からない。** 将来ずれたら
検算が効かないため、読み込み時に金額列が数値であることを必ず確認する。

■ 限界（正直に書く）
これは**国の機関の GEPS 経由の調達だけ**である。都道府県・市区町村・
外郭団体の落札実績は入っていない。山形県庁や東京都中小企業振興公社の
過去実績はここでは引けず、各団体の入札結果ページを個別に見るしかない。
その分は [5] の第2手段以降（発注元サイトの落札者情報／予算執行報告）で拾う。
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
OUT = Path("data/awards")
CACHE = OUT / "cache"
DL = ("https://api.p-portal.go.jp/pps-web-biz/UAB03/OAB0301"
      "?fileversion=v001&filename=successful_bid_record_info_all_{y}.zip")
YEARS = [2026, 2025, 2024, 2023]

# 御社の事業ドメイン。落札実績を引くときの網
DOMAIN = re.compile(
    r"伝統的?工芸|工芸品|海外展開|海外展示会|海外販路|海外プロモーション|"
    r"ジャパンパビリオン|日本パビリオン|パビリオン|日本ブース|越境EC|"
    r"インバウンド|見本市|商談会|展示会|出展|物産展|県産品|地域産品|"
    r"産品|誘客|訪日|観光プロモーション|シティプロモーション|文化発信")
# 主題が別物のものを落とす
OFF = re.compile(r"清掃|警備|給食|空調|舗装|除雪|車両|燃料|健康診断|"
                 r"廃棄物処理|下水|上水|道路|橋梁|耐震|解体|測量|地質")


def download(y: int, refresh: bool = False) -> Path | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"successful_bid_record_info_all_{y}.zip"
    if p.exists() and not refresh:
        return p
    try:
        req = urllib.request.Request(DL.format(y=y), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except Exception as e:
        print(f"  {y}年度: 取得できません（{type(e).__name__}）")
        return None
    if not data.startswith(b"PK"):
        # HTMLのエラーページが返ることがある。zipでないものを保存しない
        print(f"  {y}年度: zip ではないものが返りました（{len(data)}B）")
        return None
    p.write_bytes(data)
    print(f"  {y}年度: {len(data):,}B 取得")
    return p


def load(p: Path) -> list[list[str]]:
    z = zipfile.ZipFile(p)
    name = z.namelist()[0]
    raw = z.read(name).decode("utf-8-sig", "replace")
    rows = [r for r in csv.reader(io.StringIO(raw)) if len(r) >= 8]
    # 列の意味は位置でしか分からない。金額列が数値であることを毎回確かめる
    ok = sum(1 for r in rows[:200] if re.fullmatch(r"\d+(\.\d+)?", r[3] or ""))
    if ok < 150:
        print(f"  ! {p.name}: 4列目が金額に見えません。列構成が変わった可能性")
    return rows


def yen(s: str) -> int:
    try:
        return int(float(s))
    except Exception:
        return 0


def norm(s: str) -> str:
    """突き合わせ用に件名を正規化する。年度表記・案件番号・記号を落とす。

    「令和７年度 ○○業務」と「令和８年度 ○○業務」を同じ事業として繋ぐのが目的。
    ここを雑にすると、毎年出ている事業なのに前年実績が引けない。
    """
    s = re.sub(r"[0-9０-９]{2}-[0-9０-９]{4}-[0-9０-９]{3,4}", "", s)
    s = re.sub(r"(令和|平成)\s*[0-9０-９元]+\s*年度?", "", s)
    s = re.sub(r"20[0-9]{2}\s*年度?", "", s)
    s = re.sub(r"[（(\[【].*?[)）\]】]", "", s)
    s = re.sub(r"[\s　・,，、。．\.\-−ー―~〜/／]", "", s)
    s = re.sub(r"(に係る|に関する|の請負|業務委託|委託業務|業務|一式)$", "", s)
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", action="append")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--match", action="store_true",
                    help="data/sweep/pportal_*.csv の案件に前年実績を突き合わせる")
    ap.add_argument("--min-yen", type=int, default=0)
    args = ap.parse_args()

    today = date.today()
    OUT.mkdir(parents=True, exist_ok=True)

    print("=== 落札実績オープンデータ ===")
    data: dict[int, list[list[str]]] = {}
    for y in YEARS:
        p = download(y, args.refresh)
        if p:
            data[y] = load(p)
            print(f"    {y}年度 {len(data[y]):,} 行")
    if not data:
        print("1年度も取得できませんでした。到達不可としてレポートに明記すること。")
        return 1

    rx = (re.compile("|".join(re.escape(k) for k in args.keyword))
          if args.keyword else DOMAIN)

    hits = []
    for y, rows in data.items():
        for r in rows:
            if not rx.search(r[1]) or OFF.search(r[1]):
                continue
            v = yen(r[3])
            if v < args.min_yen:
                continue
            hits.append({"年度": f"{y}年度", "落札日": r[2], "落札金額": v,
                         "調達案件番号": r[0], "案件名": r[1],
                         "落札者": r[6], "法人番号": r[7]})
    hits.sort(key=lambda x: (-x["落札金額"],))
    hp = OUT / f"awards_hits_{today:%Y%m%d}.csv"
    with hp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["年度", "落札日", "落札金額",
                                          "調達案件番号", "案件名",
                                          "落札者", "法人番号"])
        w.writeheader()
        w.writerows(hits)
    print(f"\n{hp}: {len(hits)} 件")
    for h in hits[:15]:
        print(f"  {h['落札金額']:>13,}円 {h['落札日']} {h['案件名'][:44]} / {h['落札者'][:18]}")

    if args.match:
        srcs = sorted(Path("data/sweep").glob("pportal_*.csv"))
        if not srcs:
            print("\n突き合わせ対象（data/sweep/pportal_*.csv）がありません")
            return 0
        cur = list(csv.DictReader(srcs[-1].open(encoding="utf-8-sig")))
        # 正規化した件名 -> 過年度の実績
        idx: dict[str, list[dict]] = {}
        for y, rows in data.items():
            for r in rows:
                idx.setdefault(norm(r[1]), []).append(
                    {"年度": y, "落札日": r[2], "落札金額": yen(r[3]),
                     "落札者": r[6], "案件名": r[1]})
        out = []
        for c in cur:
            k = norm(c["案件名"])
            past = idx.get(k, [])
            if not past and len(k) >= 12:
                # 完全一致で引けないときは包含で探す。ただし**長さ比の下限を置く。**
                # 置かないと「東京国際空港航空灯火…実施設計」のような無関係の案件が、
                # 短い別件名を含んでいるだけで前年実績として付いてしまう。
                # 金額欄に嘘が入るのが一番まずいので、ここは辛く判定する。
                for kk, ps in idx.items():
                    if len(kk) < 12:
                        continue
                    if kk in k or k in kk:
                        short, long = sorted((len(kk), len(k)))
                        if short / long >= 0.7:
                            past += ps
            past.sort(key=lambda p: p["落札日"], reverse=True)
            out.append({
                "案件名": c["案件名"], "発注機関": c["発注機関"],
                "関連度": c["関連度"], "調達案件番号": c["調達案件番号"],
                "過年度実績件数": len(past),
                "直近落札日": past[0]["落札日"] if past else "",
                "直近落札金額": past[0]["落札金額"] if past else "",
                "直近落札者": past[0]["落札者"] if past else "",
                "根拠": ("落札実績オープンデータ（同一事業と判定）" if past
                        else "過去実績なし。仕様書からの積算が必要"),
                "URL": c["URL"],
            })
        mp = OUT / f"match_{today:%Y%m%d}.csv"
        with mp.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
            w.writeheader()
            w.writerows(out)
        n = sum(1 for o in out if o["過年度実績件数"])
        print(f"\n{mp}: {len(out)} 件中 {n} 件に過年度実績が付きました")
        for o in sorted(out, key=lambda x: -(x["直近落札金額"] or 0))[:12]:
            if o["直近落札金額"]:
                print(f"  {o['直近落札金額']:>13,}円 ← {o['案件名'][:46]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
