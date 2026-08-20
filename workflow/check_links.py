#!/usr/bin/env python3
"""案件リストの一次情報URLが「クリックして案件に辿り着けるか」を検証する。

    python3 workflow/check_links.py data/cases/cases_20260819.csv

**HTTP 200 だけでは不十分。** 2026-08-20 に実際にやらかした失敗：
ビジネスチャンス・ナビの案件詳細 URL を一次情報URLに入れたが、あのページは
POST 専用で、GET（＝リンクのクリック）では 200 を返しながら中身が空の殻だけ返る。
200 を見て「リンクは生きている」と判断したのが誤りだった。

そこでこのスクリプトは次を確認する：
  1. GET で 200 が返るか
  2. 本文が十分な長さを持つか（空の殻を弾く）
  3. 案件名の主要語が本文に含まれるか（違うページに飛んでいないか）

3 が落ちても一覧ページ（予測案件の監視先など）なら正常なので、
警告に留めて人が判断する。1 と 2 が落ちたら FAIL。
"""
import csv
import re
import sys
import html
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
MIN_BODY = 400          # これ未満は「空の殻」とみなす


def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read().decode("utf-8", "replace")
        return r.status, raw


def visible_text(page: str) -> str:
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)))


def keywords(name: str) -> list[str]:
    """案件名から、ページ側にも出るはずの語を拾う。"""
    name = re.sub(r"[（(].*?[）)]", "", name)
    cand = re.findall(r"[ぁ-んァ-ヴー一-龥A-Za-z0-9&]{4,}", name)
    return sorted(cand, key=len, reverse=True)[:3]


def main(path: Path) -> int:
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    fails, warns = [], []
    for r in rows:
        url = r["一次情報URL"].strip()
        no, name = r["No."], r["案件名"]
        if not url:
            fails.append(f"No.{no} 一次情報URLが空")
            continue
        try:
            status, page = fetch(url)
        except Exception as e:
            fails.append(f"No.{no} 取得失敗 {type(e).__name__} {url}")
            continue
        text = visible_text(page)
        if status != 200:
            fails.append(f"No.{no} HTTP {status} {url}")
        elif len(text) < MIN_BODY:
            fails.append(f"No.{no} 本文が {len(text)} 文字しかない"
                         f"（POST専用ページの可能性）{url}")
        else:
            hit = any(k in text for k in keywords(name))
            mark = "OK  " if hit else "WARN"
            if not hit:
                warns.append(f"No.{no} 案件名が本文に出てこない（一覧ページなら正常）{url}")
            print(f"{mark} No.{no:>2} len={len(text):>6} {url}")

    print()
    for w in warns:
        print("WARN " + w)
    for f in fails:
        print("FAIL " + f)
    print(f"\n{len(rows)}件中 FAIL {len(fails)} / WARN {len(warns)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
