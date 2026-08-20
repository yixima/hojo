#!/usr/bin/env python3
"""発注元の「全国一覧」を権威ある名簿から取り込み、巡回対象レジストリを作る。

    python3 workflow/harvest_orgs.py            # 全ディレクトリを取り込む
    python3 workflow/harvest_orgs.py --only chusho_shien

出力: data/registry/orgs.csv

■ なぜこれが要るのか
初版のワークフローは巡回先を人手で列挙していた。これは**原理的に漏れる**。
実際、都道府県の産業振興外郭団体は47のうち11しか把握できていなかった。

そこで、行政が公表している**権威ある全国名簿**を起点にする。
名簿に載っているものが母集団であり、そこから漏れたら名簿側の問題として扱える。
「たぶん全部見た」ではなく「この名簿のN件のうちM件を確認済み」と言えるようにする。

■ 取り込む名簿
  chusho_shien : 中小企業庁「都道府県等中小企業支援センター等」（47都道府県＋政令市）
                 → 御社の受注実績先である東京都中小企業振興公社がこの類型
  clair_rliea  : CLAIR「地域国際化協会一覧」（総務省認定の中核的民間国際交流組織）
                 → 自治体の国際交流・海外プロモーションの実施主体
  jnet21       : J-Net21「中小企業支援を行う公的機関一覧」（中小機構運営）
                 → 上記2つに入らない公的支援機関を拾う

いずれも一覧ページの構造が変わりうるので、抽出件数が前回より大きく減ったら
警告を出す（後述の EXPECTED_MIN）。黙って0件になるのが最悪。
"""
from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

OUT = Path("data/registry/orgs.csv")

DIRECTORIES = {
    "chusho_shien": {
        "url": "https://www.chusho.meti.go.jp/soudan/todou_sien.html",
        "category": "都道府県等中小企業支援センター",
        "note": "中小企業支援法に基づく指定法人。47都道府県＋政令市",
        "expected_min": 40,
    },
    "clair_rliea": {
        "url": "https://www.clair.or.jp/j/multiculture/association/rliea_list.html",
        "category": "地域国際化協会",
        "note": "総務省認定の中核的民間国際交流組織",
        "expected_min": 40,
    },
    "jnet21": {
        "url": "https://j-net21.smrj.go.jp/kikan_contact.html",
        "category": "公的中小企業支援機関",
        "note": "中小機構 J-Net21 の公的機関一覧",
        "expected_min": 40,
    },
}

# 一覧ページ自身のナビゲーション等を除外する
SKIP_HOST = re.compile(
    r"(facebook|twitter|x\.com|instagram|youtube|line\.me|google|adobe|"
    r"chusho\.meti\.go\.jp$|clair\.or\.jp$|j-net21\.smrj\.go\.jp$|smrj\.go\.jp$)")
SKIP_TEXT = re.compile(r"^(ホーム|トップ|一覧|詳細|こちら|PDF|Excel|次へ|前へ|印刷|English)")

# 御社の事業と関係が無い支援機関。名簿には載るが巡回対象にしない
IRRELEVANT = re.compile(
    r"ナースセンター|ポリテク|職業能力|技能検定|労働災害|産業保健|退職金|共済|"
    r"信用保証|投資育成|不動産|建設業|テレワーク|働き方改革|年金|健康保険|"
    r"官民人材交流|技能実習|情報処理推進|宇宙航空|特許|工業所有権")
# 主戦場と直結する語
CORE = re.compile(
    r"伝統|工芸|文化|観光|国際交流|貿易|物産|デザイン|クリエイティブ|コンテンツ")
PREF = ("北海道 青森 岩手 宮城 秋田 山形 福島 茨城 栃木 群馬 埼玉 千葉 東京 神奈川 "
        "新潟 富山 石川 福井 山梨 長野 岐阜 静岡 愛知 三重 滋賀 京都 大阪 兵庫 奈良 "
        "和歌山 鳥取 島根 岡山 広島 山口 徳島 香川 愛媛 高知 福岡 佐賀 長崎 熊本 大分 "
        "宮崎 鹿児島 沖縄").split()

# 団体名が漢字表記でない県がある（例:「しまね産業振興財団」）。
# 都道府県が空欄のまま残ると網羅率の計算が狂うので、別名も見る。
PREF_ALIAS = {
    "しまね": "島根", "とっとり": "鳥取", "おおいた": "大分", "ふくおか": "福岡",
    "ひろしま": "広島", "みやざき": "宮崎", "かごしま": "鹿児島", "あおもり": "青森",
    "いわて": "岩手", "みやぎ": "宮城", "あきた": "秋田", "やまがた": "山形",
    "ふくしま": "福島", "いばらき": "茨城", "とちぎ": "栃木", "ぐんま": "群馬",
    "さいたま": "埼玉", "ちば": "千葉", "かながわ": "神奈川", "にいがた": "新潟",
    "とやま": "富山", "いしかわ": "石川", "ふくい": "福井", "やまなし": "山梨",
    "ながの": "長野", "ぎふ": "岐阜", "しずおか": "静岡", "あいち": "愛知",
    "みえ": "三重", "しが": "滋賀", "きょうと": "京都", "おおさか": "大阪",
    "ひょうご": "兵庫", "なら": "奈良", "わかやま": "和歌山", "おかやま": "岡山",
    "やまぐち": "山口", "とくしま": "徳島", "かがわ": "香川", "えひめ": "愛媛",
    "こうち": "高知", "さが": "佐賀", "ながさき": "長崎", "くまもと": "熊本",
    "おきなわ": "沖縄", "ほっかいどう": "北海道",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def clean_name(text: str) -> str:
    """リンクラベルに説明文が続く一覧があるので団体名だけを残す。

    例: 「ひまわり中小企業センター 弁護士への相談が可能。初回は無料で…」
    句点・全角スペース・読点のいずれかで切れれば、その手前が団体名。
    """
    text = re.split(r"[。\n]", text)[0]
    text = re.sub(r"（[^）]{12,}）", "", text)
    parts = re.split(r"[　\t]|  +", text)
    if parts and len(parts[0]) >= 4:
        text = parts[0]
    return text.strip(" 　・:：-—")


def relevance(name: str, category: str) -> str:
    """御社の事業ドメインからの距離で tier を付ける。

    全組織を毎週巡回するのは非現実的なので、優先度を機械的に決める。
    tier_z は巡回しないが、レジストリからは消さない（判断の記録を残すため）。
    """
    if IRRELEVANT.search(name):
        return "tier_z"
    # 都道府県等中小企業支援センターが最優先。御社が実際に受注してきた類型で
    # （東京都中小企業振興公社がこれ）、海外展示会出展事業の運営委託を出す。
    # 「実績のある類型」を、名称の語感より優先する。
    if category == "都道府県等中小企業支援センター":
        return "tier_a"
    if CORE.search(name):
        return "tier_b"      # 伝統工芸・文化・観光・貿易を名に持つ団体
    if category == "地域国際化協会":
        return "tier_c"      # 自治体の国際交流・海外プロモーションの実施主体
    return "tier_d"


def guess_pref(text: str) -> str:
    for p in PREF:
        if p in text:
            return p
    for kana, p in PREF_ALIAS.items():
        if kana in text:
            return p
    return ""


def extract(page: str, base: str) -> list[dict]:
    page = re.sub(r"(?is)<(script|style|nav|footer)[^>]*>.*?</\1>", " ", page)
    seen, out = set(), []
    for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page):
        href, label = m.group(1), m.group(2)
        name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", label))).strip()
        name = clean_name(name)
        if not name or len(name) < 4 or SKIP_TEXT.match(name):
            continue
        url = urllib.parse.urljoin(base, href)
        if not url.startswith("http"):
            continue
        host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
        if not host or SKIP_HOST.search(host):
            continue
        if host in seen:
            continue
        seen.add(host)
        out.append({"org": name[:60], "url": url, "domain": host,
                    "pref": guess_pref(name)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="取り込むディレクトリID")
    args = ap.parse_args()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict] = {}
    if OUT.exists():
        for r in csv.DictReader(OUT.open(encoding="utf-8-sig")):
            existing[r["domain"]] = r

    added = updated = 0
    problems = []
    for did, d in DIRECTORIES.items():
        if args.only and did != args.only:
            continue
        try:
            page = fetch(d["url"])
        except Exception as e:
            problems.append(f"{did}: 取得失敗 {type(e).__name__}")
            continue
        rows = extract(page, d["url"])
        print(f"{did}: {len(rows)} 件抽出")
        if len(rows) < d["expected_min"]:
            problems.append(
                f"{did}: 抽出 {len(rows)} 件は想定下限 {d['expected_min']} を下回る。"
                "一覧ページの構造が変わった可能性。抽出ロジックを見直すこと")
        for r in rows:
            key = r["domain"]
            if key in existing:
                e = existing[key]
                if not e.get("category"):
                    e["category"] = d["category"]; updated += 1
                if not e.get("tier"):
                    e["tier"] = relevance(e.get("org", ""), e.get("category", "")); updated += 1
                continue
            existing[key] = {
                "domain": key, "org": r["org"], "pref": r["pref"],
                "category": d["category"], "source_directory": did,
                "url": r["url"], "procurement_url": "",
                "tier": relevance(r["org"], d["category"]),
                "frequency": "", "last_checked": "", "status": "未確認",
                "note": d["note"],
            }
            added += 1

    fields = ["domain", "org", "pref", "category", "source_directory", "url",
              "procurement_url", "tier", "frequency", "last_checked", "status", "note"]
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(existing.values(), key=lambda x: (x["category"], x["pref"], x["org"])):
            w.writerow({k: r.get(k, "") for k in fields})

    print(f"\n{OUT}: 合計 {len(existing)} 組織（新規 {added} / 補完 {updated}）")
    for p in problems:
        print("WARN " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
