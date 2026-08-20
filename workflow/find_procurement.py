#!/usr/bin/env python3
"""レジストリの各組織について「入札・調達・公募ページ」を自動発見する。

    python3 workflow/find_procurement.py                 # 未発見の組織だけ
    python3 workflow/find_procurement.py --all           # 全件やり直し
    python3 workflow/find_procurement.py --limit 30      # 件数を絞る

data/registry/orgs.csv の procurement_url / status / last_checked を埋める。

■ なぜ要るのか
組織名のリストがあっても、各組織のどこに調達情報があるかを知らなければ巡回できない。
公的機関の調達ページのURLには規則性が無い（/nyusatsu/ /keiyaku/ /chotatsu/ /koubo/
/procurement/ /information/bid/ …）。人手で171組織分を探すのは非現実的なので機械化する。

■ 手順
  1. トップページを取得
  2. リンクのラベルとURLから「調達らしさ」を採点し、最有力を採用
  3. 見つからなければ、よくあるパスを直接叩く
  4. どうしても見つからなければ status=要手動確認 として残す（黙って諦めない）

見つけたページは after で中身も確認し、実際に案件が載っているかを見る。
ナビゲーションだけの空ページを掴まないため。
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

# ラベルの語 -> 得点。強い語ほど高い
LABEL_SCORE = [
    (re.compile(r"入札・?契約情報|調達情報|入札情報|契約情報"), 10),
    (re.compile(r"公募情報|公募一覧|募集情報"), 9),
    (re.compile(r"入札|調達"), 7),
    (re.compile(r"企画競争|プロポーザル|公募型"), 7),
    (re.compile(r"契約"), 4),
    (re.compile(r"公募|募集"), 3),
]
# URLパスの語 -> 得点
PATH_SCORE = [
    (re.compile(r"nyusatsu|nyuusatsu|chotatsu|choutatsu|procurement|bid|tender"), 8),
    (re.compile(r"keiyaku|contract"), 6),
    (re.compile(r"koubo|kobo|boshu|proposal"), 5),
]
# 誤爆しやすい語（職員採用、入居者募集など）
NEGATIVE = re.compile(
    r"採用|求人|職員募集|入居者|会員募集|セミナー|イベント|受講|参加者募集|"
    r"寄付|助成金の(交付|申請)|補助金.{0,4}申請|メルマガ")

COMMON_PATHS = [
    "/nyusatsu/", "/nyusatsu.html", "/chotatsu/", "/chotatsu.html",
    "/keiyaku/", "/keiyaku.html", "/procurement/", "/bid/", "/koubo/",
    "/about/nyusatsu/", "/info/nyusatsu/", "/outline/nyusatsu/",
]


def fetch(url: str, timeout: int = 12) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def visible(page: str) -> str:
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)))


def score_link(label: str, url: str) -> int:
    if NEGATIVE.search(label):
        return 0
    s = 0
    for rx, pts in LABEL_SCORE:
        if rx.search(label):
            s = max(s, pts)
    path = urllib.parse.urlparse(url).path.lower()
    for rx, pts in PATH_SCORE:
        if rx.search(path):
            s += pts
            break
    return s


def looks_like_listing(page: str) -> bool:
    """案件が実際に載っていそうか。ナビだけの空ページを弾く。"""
    t = visible(page)
    if len(t) < 500:
        return False
    signals = len(re.findall(
        r"公告|入札|公募|締切|受付期間|見積|仕様書|企画競争|プロポーザル|令和\d|20\d\d年", t))
    return signals >= 4


def discover(domain: str, top_url: str) -> tuple[str, str]:
    """(procurement_url, status) を返す。"""
    base = top_url if top_url.startswith("http") else f"https://{domain}/"
    status, page = fetch(base)
    if status == 0:
        return "", "到達不可"
    if not page:
        return "", f"HTTP {status}"

    best, best_score = "", 0
    page_nav = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page_nav):
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))).strip()
        if not label:
            continue
        url = urllib.parse.urljoin(base, m.group(1))
        if not url.startswith("http"):
            continue
        sc = score_link(label, url)
        if sc > best_score:
            best, best_score = url, sc

    if best_score >= 7:
        st, pg = fetch(best)
        if st == 200 and looks_like_listing(pg):
            return best, "確認済み"
        if st == 200:
            return best, "要手動確認（中身が薄い）"

    for path in COMMON_PATHS:
        cand = urllib.parse.urljoin(base, path)
        st, pg = fetch(cand, timeout=8)
        if st == 200 and looks_like_listing(pg):
            return cand, "確認済み"

    if best:
        return best, "要手動確認（候補のみ）"
    return "", "要手動確認（未発見）"


def save(rows, fields) -> None:
    with REG.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="発見済みも含め全件やり直す")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--tier", help="この tier だけ処理する（例 tier_a）")
    ap.add_argument("--skip-z", action="store_true", help="tier_z を飛ばす")
    args = ap.parse_args()

    rows = list(csv.DictReader(REG.open(encoding="utf-8-sig")))
    fields = list(rows[0].keys())
    today = date.today().isoformat()

    targets = [r for r in rows
               if args.all or not r.get("procurement_url")]
    if args.tier:
        targets = [r for r in targets if r.get("tier") == args.tier]
    if args.skip_z:
        targets = [r for r in targets if r.get("tier") != "tier_z"]
    if args.limit:
        targets = targets[: args.limit]
    print(f"対象 {len(targets)} / 全 {len(rows)} 組織\n")

    done = 0
    for r in targets:
        url, st = discover(r["domain"], r.get("url") or "")
        r["procurement_url"], r["status"], r["last_checked"] = url, st, today
        done += 1
        mark = "OK " if st == "確認済み" else "-- "
        print(f"{mark}{r['org'][:26]:28} {st:22} {url[:60]}", flush=True)
        if done % 20 == 0:
            save(rows, fields)          # 途中経過を失わない

    save(rows, fields)

    from collections import Counter
    c = Counter(r["status"] for r in rows)
    print(f"\n{done} 件処理。レジストリ全体の状況:")
    for k, v in c.most_common():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
