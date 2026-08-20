#!/usr/bin/env python3
"""再現率の検査。「本来必ず拾えるべき案件」を今のワークフローが拾えるかを数える。

    python3 workflow/check_recall.py

■ なぜ要るのか
巡回の網羅性は「たぶん漏れていない」では担保できない。**漏れは定義上、見えない。**
そこで逆から測る。既知の正解（御社の過去の受注案件、生島様がご存じの案件、
過去に拾えた案件）を置き、**その発注元が今のレジストリに載っているか**を毎回検査する。

載っていなければ、その案件は二度と拾えない。つまりそれは
「レジストリに足りない母集団」を指し示している。**漏れを仕組みの欠陥に翻訳する装置。**

data/registry/known_positives.csv に正解を置く。
生島様が「これが漏れている」と指摘された案件は、必ずここに追加すること。
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

REG = Path("data/registry/orgs.csv")
KP = Path("data/registry/known_positives.csv")


def domain_matches(target: str, known: set[str]) -> str:
    """発注元ドメインがレジストリのどれかに一致するか（サブドメイン差を吸収）。"""
    t = target.lower().strip()
    if not t:
        return ""
    for d in known:
        d = d.lower()
        if t == d or t.endswith("." + d) or d.endswith("." + t):
            return d
    return ""


def main() -> int:
    if not KP.exists():
        print(f"{KP} がありません")
        return 1
    reg = {r["domain"]: r for r in csv.DictReader(REG.open(encoding="utf-8-sig"))}
    kps = list(csv.DictReader(KP.open(encoding="utf-8")))

    covered, gaps = [], []
    for k in kps:
        hit = domain_matches(k["発注機関ドメイン"], set(reg))
        if hit:
            r = reg[hit]
            reachable = r.get("status") == "確認済み"
            covered.append((k, r, reachable))
        else:
            gaps.append(k)

    print(f"既知の正解 {len(kps)} 件\n")
    print("── レジストリに発注元があるもの ──")
    for k, r, ok in covered:
        mark = "OK  " if ok else "経路×"
        print(f"  {mark} {k['id']} {k['発注機関'][:24]:26} "
              f"tier={r.get('tier','-'):7} status={r.get('status','-')}")

    if gaps:
        print("\n── 発注元がレジストリに無い（＝二度と拾えない） ──")
        for k in gaps:
            print(f"  MISS {k['id']} {k['発注機関'][:26]:28} {k['発注機関ドメイン']}")
            if k.get("備考"):
                print(f"       {k['備考']}")

    n = len(kps)
    in_reg = len(covered)
    reachable = sum(1 for _, _, ok in covered if ok)
    print(f"\n再現率")
    print(f"  発注元がレジストリにある : {in_reg}/{n}  ({in_reg * 100 // n}%)")
    print(f"  調達経路まで判明している : {reachable}/{n}  ({reachable * 100 // n}%)")
    if gaps:
        print(f"\n{len(gaps)} 件の欠けは、レジストリに足りない母集団を指している。")
        print("harvest_orgs.py に名簿を追加するか、data/registry/manual_orgs.csv に手動で足すこと。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
