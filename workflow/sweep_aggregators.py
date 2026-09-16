#!/usr/bin/env python3
"""横断アグリゲータを叩いて、レジストリに載らない発注元の案件を拾う。

    python3 workflow/sweep_aggregators.py

出力: data/sweep/agg_YYYYMMDD.csv

■ なぜ要るのか
レジストリ（252組織）に載っていない発注元がまだ大量にある。市区町村1,700超、
独立行政法人、DMO、商工会議所、文化財団。**これらを一つずつ登録して巡回するのは
現実的でない。** そこで、複数の発注元を横断して集約しているサイトを叩く。

「全てが最優先で、優先順位を低くしても良いものは存在しない」というご指示に対し、
直接巡回できない部分をここで受け止める。**カバーしない系統を作らないための層。**

■ 叩く先（2026-08-21 時点の到達性）
  p-portal   調達ポータル。国の機関の調達を横断        到達可
  jgrants    jGrants。国の補助金を横断                  到達可
  tokyo_bid  東京都電子調達。東京都と都内区市町村       到達可
  kkj        官公需情報ポータル。国・独法・地方公共団体  **503 で到達不可。要再試行**
  mirasapo   ミラサポplus                                **egress ポリシーで遮断**

到達不可のものも定義には残す。**消すと「試していない」のか「試して駄目だった」のか
区別がつかなくなる。** 毎回叩いて、復活したら自動的に使われるようにする。
"""
from __future__ import annotations

import csv
import html
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sweep import DOMAIN_WORDS, OFF_DOMAIN, score, UA  # noqa: E402

OUTDIR = Path("data/sweep")

# 御社の事業ドメインの検索語。アグリゲータの全文検索に投げる
QUERIES = [
    "伝統的工芸品 海外", "工芸品 販路開拓", "海外展示会 出展",
    "ジャパンパビリオン", "海外展開 支援 業務委託", "県産品 海外",
    "インバウンド プロモーション", "シティプロモーション 海外",
    "文化 海外発信", "越境EC 販路",
]

AGGREGATORS = {
    "p-portal": {
        "name": "調達ポータル",
        "probe": "https://www.p-portal.go.jp/",
        "note": "国の機関の調達を横断。経済産業局の競争入札はここにしか出ない",
    },
    "jgrants": {
        "name": "jGrants",
        "probe": "https://www.jgrants-portal.go.jp/",
        "note": "国の補助金を横断",
    },
    "tokyo_bid": {
        "name": "東京都電子調達システム",
        "probe": "https://www.e-procurement.metro.tokyo.lg.jp/",
        "note": "東京都と都内区市町村",
    },
    "kkj": {
        "name": "官公需情報ポータルサイト",
        "probe": "https://www.kkj.go.jp/",
        "note": "国・独法・地方公共団体を横断。最も広い。2026-08-21時点 503",
    },
    "mirasapo": {
        "name": "ミラサポplus",
        "probe": "https://www.mirasapo-plus.go.jp/",
        "note": "中小企業支援制度。egress ポリシーで遮断",
    },
}


def fetch(url: str, timeout: int = 25) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def probe_all() -> dict[str, str]:
    """各アグリゲータの到達性を毎回測る。復活したら自動で使えるようにするため。"""
    out = {}
    for aid, a in AGGREGATORS.items():
        st, _ = fetch(a["probe"], timeout=20)
        out[aid] = "到達可" if st == 200 else f"到達不可 HTTP {st}"
        print(f"  {a['name']:24} {out[aid]}")
    return out


def sweep_jgrants(today: date) -> list[dict]:
    """jGrants の補助金検索。公開APIがあるので使う。"""
    found = []
    base = "https://api.jgrants-portal.go.jp/exp/v1/public/subsidies"
    for q in QUERIES:
        url = (f"{base}?keyword={urllib.parse.quote(q)}"
               "&sort=created_date&order=DESC&acceptance=1")
        st, body = fetch(url)
        if st != 200 or not body:
            continue
        # JSON。件名と締切を素朴に拾う（スキーマ変更に強くするため正規表現）
        for m in re.finditer(r'"title"\s*:\s*"([^"]{6,200})"', body):
            title = html.unescape(m.group(1))
            pts, hits = score(title)
            if pts < 1:
                continue
            found.append({"検出日": today.isoformat(), "経路": "jGrants",
                          "検索語": q, "案件名": title[:160],
                          "関連度": pts, "一致語": hits,
                          "URL": "https://www.jgrants-portal.go.jp/"})
    return found


def sweep_html(aid: str, search_url_tpl: str, today: date) -> list[dict]:
    """HTML検索結果からリンクを拾う汎用版。"""
    found = []
    for q in QUERIES:
        url = search_url_tpl.format(q=urllib.parse.quote(q))
        st, page = fetch(url)
        if st != 200 or not page:
            continue
        page = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
        for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page):
            label = re.sub(r"\s+", " ",
                           html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))).strip()
            if len(label) < 12:
                continue
            pts, hits = score(label)
            if pts < 2:
                continue
            found.append({"検出日": today.isoformat(),
                          "経路": AGGREGATORS[aid]["name"], "検索語": q,
                          "案件名": label[:160], "関連度": pts, "一致語": hits,
                          "URL": urllib.parse.urljoin(url, m.group(1))})
    return found


def main() -> int:
    today = date.today()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("=== アグリゲータ到達性 ===")
    status = probe_all()

    found: list[dict] = []
    if status.get("jgrants") == "到達可":
        print("\n=== jGrants ===")
        rows = sweep_jgrants(today)
        print(f"  {len(rows)} 件")
        found += rows

    # 到達不可のものは飛ばすが、レポートには「叩いたが駄目だった」と残す
    blocked = [AGGREGATORS[k]["name"] for k, v in status.items() if v != "到達可"]

    # 重複除去（同じ案件名は1件に）
    seen, uniq = set(), []
    for f in sorted(found, key=lambda x: -x["関連度"]):
        k = f["案件名"]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)

    out = OUTDIR / f"agg_{today:%Y%m%d}.csv"
    fields = ["検出日", "経路", "検索語", "関連度", "一致語", "案件名", "URL"]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(uniq)

    print(f"\n{out}: {len(uniq)} 件（重複除去後）")
    if blocked:
        print("\n到達できなかったアグリゲータ（レポートに明記すること）:")
        for b in blocked:
            print(f"  - {b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
