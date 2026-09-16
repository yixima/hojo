#!/usr/bin/env python3
"""レジストリの調達ページを巡回し、案件候補を機械的に抽出する。

    python3 workflow/sweep.py                      # 確認済みの全組織
    python3 workflow/sweep.py --tier tier_a
    python3 workflow/sweep.py --limit 40
    python3 workflow/sweep.py --min-score 3        # 関連度の下限

出力: data/sweep/sweep_YYYYMMDD.csv

■ 役割の分離
このスクリプトは**判断しない**。広く拾って点数を付けるだけ。
足切り・応募形態・格付・金額の判断は eligibility.md に従って人（とClaude）が行い、
その結果が data/cases/cases_YYYYMMDD.csv になる。

機械の仕事（再現性が要る）と判断の仕事（文脈が要る）を混ぜない。
混ぜると「なぜ拾わなかったのか」が追えなくなる。

■ 拾い方
調達ページのリンクから、案件らしいラベルを持つものを集める。
「案件らしさ」は次で判定する：
  - 公募・入札・委託・プロポーザル・企画競争 などの語を含む
  - 年度・日付を含む（一覧のナビゲーションリンクを弾くため）

拾ったものに**関連度スコア**を付ける。御社の事業ドメイン語との一致数。
スコア0でも捨てずに残す（--min-score 0 で全部見られる）。
**捨てた記録が残らないと、漏れたときに原因が追えない。**
"""
from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
REG = Path("data/registry/orgs.csv")
OUTDIR = Path("data/sweep")

# 案件らしいラベルか
CASE_WORD = re.compile(
    r"公募|入札|委託|プロポーザル|企画競争|企画提案|募集|調達|見積|公告|選定|補助金")
# 一覧・ナビゲーションを弾く
NOT_CASE = re.compile(
    r"^(一覧|過去の|年度別|カテゴリ|次へ|前へ|もっと|検索|トップ|ホーム|"
    r"入札情報$|公募情報$|調達情報$|contact|sitemap)")
# 日付・年度を含むか（案件は必ず時期を持つ）
HAS_DATE = re.compile(r"令和\s*\d+|平成\s*\d+|20\d\d年|R\d|\d+月\d+日|\d{4}[-/]\d{1,2}")

# 御社の事業ドメイン。一致するほど関連度が高い
DOMAIN_WORDS = [
    # 主戦場（重み2）
    ("伝統工芸", 2), ("伝統的工芸", 2), ("工芸", 2), ("海外展開", 2),
    ("海外展示会", 2), ("ジャパンパビリオン", 2), ("パビリオン", 2),
    ("海外販路", 2), ("越境EC", 2), ("インバウンド", 2),
    # 隣接（重み1）
    ("海外", 1), ("国際", 1), ("輸出", 1), ("販路", 1), ("展示会", 1),
    ("商談会", 1), ("見本市", 1), ("出展", 1), ("プロモーション", 1),
    ("観光", 1), ("文化", 1), ("県産品", 1), ("地域産品", 1), ("物産", 1),
    ("ブランド", 1), ("シティプロモーション", 1), ("デザイン", 1),
    ("バイヤー", 1), ("テストマーケティング", 1), ("催事", 1), ("運営", 1),
]
# これが主題なら関連度を下げる（御社の事業ではない）
OFF_DOMAIN = re.compile(
    r"清掃|警備|給食|電気設備|空調|エアコン|舗装|除雪|樹木|草刈|"
    r"車両|燃料|印刷製本のみ|健康診断|派遣職員|システム開発|保守|"
    r"廃棄物|下水|上水|道路|橋梁|耐震|解体|測量|地質")


def fetch(url: str, timeout: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def score(label: str) -> tuple[int, str]:
    """関連度スコアと、一致した語を返す。"""
    if OFF_DOMAIN.search(label):
        return -1, "対象外語"
    pts, hits = 0, []
    for w, weight in DOMAIN_WORDS:
        if w in label:
            pts += weight
            hits.append(w)
    return pts, "/".join(hits)


def extract_table_cases(page: str, base: str) -> list[dict]:
    """表のセルに案件名が書かれ、リンクになっていない調達ページに対応する。

    東京都中小企業振興公社の契約情報がこの形。件名がテキストのまま表に並び、
    実際の応募はビジネスチャンス・ナビ側で行うためリンクが無い。
    リンクだけを見ていると**0件と誤検出する**。実際にそれで見落とした。
    """
    out, seen = [], set()
    for tr in re.finditer(r"(?is)<tr[^>]*>(.*?)</tr>", page):
        cells = [re.sub(r"\s+", " ",
                        html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr.group(1))]
        cells = [c for c in cells if c]
        if not cells:
            continue
        # 一番長いセルを件名とみなす
        label = max(cells, key=len)
        if len(label) < 12 or NOT_CASE.match(label) or not CASE_WORD.search(label):
            continue
        if label in seen:
            continue
        seen.add(label)
        pts, hits = score(label)
        # 同じ行に日付があれば拾って案件名に添える
        when = " ".join(c for c in cells if HAS_DATE.search(c) and c != label)[:60]
        out.append({"案件名": (label + (f"（{when}）" if when else ""))[:160],
                    "URL": base, "関連度": pts, "一致語": hits})
    return out


def extract_cases(page: str, base: str) -> list[dict]:
    page = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    seen, out = set(), []
    for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page):
        label = re.sub(r"\s+", " ",
                       html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))).strip()
        if len(label) < 10 or NOT_CASE.match(label):
            continue
        if not CASE_WORD.search(label):
            continue
        # 案件は時期を持つ。持たないものは一覧やナビの可能性が高い
        if not HAS_DATE.search(label) and len(label) < 24:
            continue
        url = urllib.parse.urljoin(base, m.group(1))
        if not url.startswith("http") or url in seen:
            continue
        seen.add(url)
        pts, hits = score(label)
        out.append({"案件名": label[:160], "URL": url,
                    "関連度": pts, "一致語": hits})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-score", type=int, default=1)
    args = ap.parse_args()

    rows = [r for r in csv.DictReader(REG.open(encoding="utf-8-sig"))
            if r.get("procurement_url") and r.get("status") == "確認済み"]
    if args.tier:
        rows = [r for r in rows if r.get("tier") == args.tier]
    if args.limit:
        rows = rows[: args.limit]

    today = date.today()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTDIR / f"sweep_{today:%Y%m%d}.csv"

    found, failed = [], []
    print(f"巡回対象 {len(rows)} 組織\n", flush=True)
    for i, r in enumerate(rows, 1):
        st, page = fetch(r["procurement_url"])
        if st != 200 or not page:
            failed.append((r["org"], r["procurement_url"], f"HTTP {st}"))
            print(f"-- [{i}/{len(rows)}] {r['org'][:24]:26} 取得失敗 HTTP {st}", flush=True)
            continue
        cases = extract_cases(page, r["procurement_url"])
        # リンクで拾えないページ（件名が表のテキスト）を補う
        cases += [c for c in extract_table_cases(page, r["procurement_url"])
                  if c["案件名"] not in {x["案件名"] for x in cases}]
        keep = [c for c in cases if c["関連度"] >= args.min_score]
        for c in keep:
            c.update({"発注機関": r["org"], "ドメイン": r["domain"],
                      "都道府県": r["pref"], "分類": r["category"],
                      "tier": r["tier"], "検出日": today.isoformat(),
                      "調達ページ": r["procurement_url"]})
        found += keep
        mark = "OK " if keep else "-- "
        print(f"{mark}[{i}/{len(rows)}] {r['org'][:24]:26} "
              f"候補{len(cases):3}件 → 関連{len(keep):2}件", flush=True)

    fields = ["検出日", "発注機関", "都道府県", "分類", "tier", "関連度",
              "一致語", "案件名", "URL", "調達ページ", "ドメイン"]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in sorted(found, key=lambda x: -x["関連度"]):
            w.writerow({k: c.get(k, "") for k in fields})

    print(f"\n{out_path}: {len(found)} 件")
    if failed:
        print(f"\n取得できなかった調達ページ {len(failed)} 件（要調査）:")
        for org, url, why in failed[:20]:
            print(f"  {org[:26]:28} {why:10} {url[:58]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
