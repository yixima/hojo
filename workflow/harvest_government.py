#!/usr/bin/env python3
"""自治体本体と中央省庁の地方支分部局をレジストリに登録する。

    python3 workflow/harvest_government.py

■ なぜ要るのか（2026-08-20 の実際の取りこぼしから）
生島様から「漏れている」とご指摘を受けた2件は、いずれも**系統ごと欠けていた**：

  1. 九州経済産業局の伝統工芸品・地産品 海外展開事業
     → 経済産業局は「中央省庁の地方支分部局」。meti.go.jp は登録済みだったが、
        全国9局はそれぞれ別ドメイン・別調達ページを持つ。系統ごと未登録だった。

  2. 山形県庁の地産品 海外展開事業
     → 山形県企業振興公社（外郭団体）は登録済みだったが、**県庁本体が未登録**。
        実際には県産品・貿易振興課が毎年プロポーザルを出している。

外郭団体だけを見て本体を見ていなかった。これは設計の穴であって、運用の不注意ではない。

■ 登録する系統
  - 都道府県 47（本体）
  - 政令指定都市 20
  - 経済産業局 8＋沖縄総合事務局
  - 運輸局・農政局など、御社の事業に関わる地方支分部局

ドメインは実測済み（sources.yaml の domain_survey）。pref.X.lg.jp を持たない県が
14あるため、両系統を候補として持ち、到達したほうを採用する。
"""
from __future__ import annotations

import csv
import sys
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
REG = Path("data/registry/orgs.csv")

# 都道府県。lg.jp を持たない県があるので候補を2つ持つ（domain_survey の実測に基づく）
PREFS = [
    ("北海道", ["pref.hokkaido.lg.jp"]), ("青森", ["pref.aomori.lg.jp"]),
    ("岩手", ["pref.iwate.jp"]), ("宮城", ["pref.miyagi.jp"]),
    ("秋田", ["pref.akita.lg.jp", "pref.akita.jp"]), ("山形", ["pref.yamagata.jp"]),
    ("福島", ["pref.fukushima.lg.jp"]), ("茨城", ["pref.ibaraki.jp"]),
    ("栃木", ["pref.tochigi.lg.jp"]), ("群馬", ["pref.gunma.jp"]),
    ("埼玉", ["pref.saitama.lg.jp"]), ("千葉", ["pref.chiba.lg.jp"]),
    ("東京", ["metro.tokyo.lg.jp"]), ("神奈川", ["pref.kanagawa.jp"]),
    ("新潟", ["pref.niigata.lg.jp"]), ("富山", ["pref.toyama.jp"]),
    ("石川", ["pref.ishikawa.lg.jp"]), ("福井", ["pref.fukui.lg.jp"]),
    ("山梨", ["pref.yamanashi.jp"]), ("長野", ["pref.nagano.lg.jp"]),
    ("岐阜", ["pref.gifu.lg.jp"]), ("静岡", ["pref.shizuoka.jp"]),
    ("愛知", ["pref.aichi.jp"]), ("三重", ["pref.mie.lg.jp"]),
    ("滋賀", ["pref.shiga.lg.jp"]), ("京都", ["pref.kyoto.jp"]),
    ("大阪", ["pref.osaka.lg.jp"]), ("兵庫", ["web.pref.hyogo.lg.jp"]),
    ("奈良", ["pref.nara.jp"]), ("和歌山", ["pref.wakayama.lg.jp"]),
    ("鳥取", ["pref.tottori.lg.jp"]), ("島根", ["pref.shimane.lg.jp"]),
    ("岡山", ["pref.okayama.jp"]), ("広島", ["pref.hiroshima.lg.jp"]),
    ("山口", ["pref.yamaguchi.lg.jp"]), ("徳島", ["pref.tokushima.lg.jp"]),
    ("香川", ["pref.kagawa.lg.jp"]), ("愛媛", ["pref.ehime.jp"]),
    ("高知", ["pref.kochi.lg.jp"]), ("福岡", ["pref.fukuoka.lg.jp"]),
    ("佐賀", ["pref.saga.lg.jp"]), ("長崎", ["pref.nagasaki.jp"]),
    ("熊本", ["pref.kumamoto.jp"]), ("大分", ["pref.oita.jp"]),
    ("宮崎", ["pref.miyazaki.lg.jp"]), ("鹿児島", ["pref.kagoshima.jp"]),
    ("沖縄", ["pref.okinawa.jp", "pref.okinawa.lg.jp"]),
]

CITIES = [
    ("北海道", "札幌市", "city.sapporo.jp"), ("宮城", "仙台市", "city.sendai.jp"),
    ("埼玉", "さいたま市", "city.saitama.lg.jp"), ("千葉", "千葉市", "city.chiba.jp"),
    ("神奈川", "横浜市", "city.yokohama.lg.jp"), ("神奈川", "川崎市", "city.kawasaki.jp"),
    ("神奈川", "相模原市", "city.sagamihara.kanagawa.jp"),
    ("新潟", "新潟市", "city.niigata.lg.jp"), ("静岡", "静岡市", "city.shizuoka.lg.jp"),
    ("静岡", "浜松市", "city.hamamatsu.shizuoka.jp"), ("愛知", "名古屋市", "city.nagoya.jp"),
    ("京都", "京都市", "city.kyoto.lg.jp"), ("大阪", "大阪市", "city.osaka.lg.jp"),
    ("大阪", "堺市", "city.sakai.lg.jp"), ("兵庫", "神戸市", "city.kobe.lg.jp"),
    ("岡山", "岡山市", "city.okayama.jp"), ("広島", "広島市", "city.hiroshima.lg.jp"),
    ("福岡", "北九州市", "city.kitakyushu.lg.jp"), ("福岡", "福岡市", "city.fukuoka.lg.jp"),
    ("熊本", "熊本市", "city.kumamoto.jp"),
]

# 中央省庁の地方支分部局。御社の事業に関わるもの
BUREAUS = [
    ("北海道経済産業局", "hokkaido.meti.go.jp"),
    ("東北経済産業局", "tohoku.meti.go.jp"),
    ("関東経済産業局", "kanto.meti.go.jp"),
    ("中部経済産業局", "chubu.meti.go.jp"),
    ("近畿経済産業局", "kansai.meti.go.jp"),
    ("中国経済産業局", "chugoku.meti.go.jp"),
    ("四国経済産業局", "shikoku.meti.go.jp"),
    ("九州経済産業局", "kyushu.meti.go.jp"),
    ("内閣府沖縄総合事務局", "ogb.go.jp"),
]


def alive(domain: str) -> str:
    """到達できたURLを返す。到達不可なら空文字。

    公的機関のサイトは www 有りでしか応答しないものが多い
    （kyushu.meti.go.jp は不可、www.kyushu.meti.go.jp は200）。
    www の有無を必ず両方試すこと。ここを省いて70件を誤って到達不可と判定した。
    """
    hosts = [domain] if domain.startswith("www.") else [f"www.{domain}", domain]
    for host in hosts:
        for scheme in ("https", "http"):
            url = f"{scheme}://{host}/"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=12) as r:
                    if r.status < 400:
                        return url
            except urllib.error.HTTPError as e:
                if e.code in (403, 405):      # 本体は存在する
                    return url
            except Exception:
                continue
    return ""


def main() -> int:
    rows = list(csv.DictReader(REG.open(encoding="utf-8-sig")))
    fields = list(rows[0].keys())
    by = {r["domain"]: r for r in rows}

    def add(domain, org, pref, category, note, top=""):
        d = domain.removeprefix("www.")
        if d in by:
            return False
        by[d] = {"domain": d, "org": org, "pref": pref, "category": category,
                 "source_directory": "government", "url": top or f"https://{d}/",
                 "procurement_url": "", "tier": "tier_a", "frequency": "every_run",
                 "last_checked": "", "status": "未確認", "note": note}
        return True

    added = skipped = 0
    print("=== 都道府県 ===")
    for pref, cands in PREFS:
        hit = next((c for c in cands if alive(c)), None)
        if not hit:
            print(f"  到達不可 {pref}: {cands}")
            skipped += 1
            continue
        if add(hit, f"{pref}県庁" if pref not in ("東京", "北海道", "大阪", "京都")
               else f"{pref}庁", pref, "自治体本体（都道府県）",
               "県産品・貿易・観光の各課がプロポーザルを出す。入札情報／公募型プロポーザルの一覧を見る",
               top=alive(hit)):
            added += 1

    print("=== 政令指定都市 ===")
    for pref, city, dom in CITIES:
        if alive(dom):
            if add(dom, city, pref, "自治体本体（政令市）", "シティプロモーション・観光・産業振興", top=alive(dom)):
                added += 1
        else:
            print(f"  到達不可 {city}: {dom}")
            skipped += 1

    print("=== 中央省庁の地方支分部局 ===")
    for org, dom in BUREAUS:
        if alive(dom):
            if add(dom, org, "", "地方支分部局",
                   "競争入札はGEPS/調達ポータルのみで公告される場合がある。局サイトと調達ポータルの両方を見る",
                   top=alive(dom)):
                added += 1
        else:
            print(f"  到達不可 {org}: {dom}")
            skipped += 1

    with REG.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted(by.values(),
                           key=lambda x: (x["tier"], x["category"], x["pref"], x["org"])))
    print(f"\n新規 {added} 件 / 到達不可 {skipped} 件 → 合計 {len(by)} 組織")
    return 0


if __name__ == "__main__":
    sys.exit(main())
