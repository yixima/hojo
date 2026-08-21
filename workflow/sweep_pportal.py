#!/usr/bin/env python3
"""調達ポータル（GEPS）を全文検索し、国の機関の案件を拾う。

    python3 workflow/sweep_pportal.py                # 公開中の案件
    python3 workflow/sweep_pportal.py --awards       # 落札公示も拾う（[5]金額用）
    python3 workflow/sweep_pportal.py --keyword 海外展開

出力: data/sweep/pportal_YYYYMMDD.csv

■ なぜ要るのか
**経済産業局の競争入札は、局のサイトに出ないことがある。** 山形県庁の件と並んで
ご指摘のあった九州経済産業局の案件がまさにそれで、公告が GEPS（政府電子調達）に
しか載らない。局サイトを巡回していても永久に見つからない。
国の機関（省庁・地方支分部局・一部の独法）の調達は、ここが唯一の横断口。

■ 仕組み（実測 2026-08-21）
調達ポータルの検索は Spring の CSRF 付き POST。GET では叩けない。
  1. GET  /pps-web-biz/UAA01/OAA0100?OAA0115   … 検索フォーム。Cookie と _csrf を得る
  2. POST /pps-web-biz/UAA01/OAA0100           … 同じ Cookie セッションで検索条件を送る
  3. 結果は /pps-web-biz/UAA01/OAA0106 に 302 され、そこに一覧が入る

**類義語区分は 01（含まない）を使う。** 02（含む）にすると「工芸」が「作物」に
展開され、財務省の自家用電気工作物保安管理業務が引っかかった。
再現率を上げたつもりが、実際には無関係な案件でリストが埋まって精度が壊れる。
広く取りたいときは類義語ではなく**検索語を増やす**こと。

■ リンクについて
一覧の「公示本文」は javascript:doSubmitParams(...) で、POST でしか開けない。
ビジネスチャンス・ナビと同じ罠で、**そのURLを案件リストに載せても案件ページに
飛べない。** 代わりに同じ行にある GEPS の入札ページ
  https://www.nyusatsu.geps.go.jp/OMP/Accepter/index.jsp?PRM=<調達案件番号>
は GET で開ける実URLなので、これを一次情報URLとして採用する。
調達案件番号も必ず記録する（番号があれば検索窓から必ず辿り着けるため）。
"""
from __future__ import annotations

import argparse
import csv
import html
import http.cookiejar
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sweep import score, UA  # noqa: E402

OUTDIR = Path("data/sweep")
BASE = "https://www.p-portal.go.jp"
FORM = f"{BASE}/pps-web-biz/UAA01/OAA0100?OAA0115"
POST = f"{BASE}/pps-web-biz/UAA01/OAA0100"
PAGE = f"{BASE}/pps-web-biz/UAA01/OAA0106?page={{n}}&size=50"   # 1ページ50件が上限
GEPS = "https://www.nyusatsu.geps.go.jp/OMP/Accepter/index.jsp?PRM={no}"

# 調達案件名称の部分一致で叩く語。類義語展開は使わないので、語のほうを厚くする。
# 実測ヒット数（2026-08-21・公開中）を添えておく。0件の語も**消さない**。
# 消すと「試していない」のか「試して0件だった」のか後から区別できなくなる。
KEYWORDS = [
    "海外展開",     # 14
    "海外",         # 39
    "出展",         # 9
    "プロモーション",  # 7
    "観光",         # 8
    "文化",         # 7
    "情報発信",     # 7
    "誘客",         # 3
    "伝統",         # 2
    "ジャパン",     # 2
    "展示会",       # 1
    "商談会",       # 1
    "インバウンド",   # 1
    "工芸",         # 0
    "販路",         # 0
    "販路開拓",     # 0
    "物産",         # 0
    "越境",         # 0
    "見本市",
    "国際",
    "ブランド",
    "産品",
]

ROW_KEY = 'id="tri_WAA0101FM01/procurementResultListBean/procurementItemNo"'


def strip(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def field(seg: str, name: str) -> str:
    m = re.search(
        r'id="tri_WAA0101FM01/procurementResultListBean/%s"\s*>(.*?)</td>' % name,
        seg, re.S)
    return strip(m.group(1)) if m else ""


class Portal:
    """1セッションを保持する。CSRF トークンは Cookie と対で意味を持つ。"""

    def __init__(self) -> None:
        cj = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cj))
        self.op.addheaders = [("User-Agent", UA), ("Accept-Language", "ja,en;q=0.8")]
        self.csrf = ""

    def open_form(self) -> bool:
        try:
            page = self.op.open(FORM, timeout=45).read().decode("utf-8", "replace")
        except Exception as e:
            print(f"  検索フォームに到達できません: {type(e).__name__}")
            return False
        m = re.search(r'name="_csrf"[^>]*value="([^"]+)"', page)
        if not m:
            print("  _csrf を取得できません（画面構成が変わった可能性）")
            return False
        self.csrf = m.group(1)
        return True

    def search(self, keyword: str, awards: bool = False) -> tuple[int, str]:
        """(件数, 結果HTML) を返す。件数 -1 は失敗。"""
        d = {
            "_csrf": self.csrf,
            "searchConditionBean.caseDivision": "0",
            "searchConditionBean.synonymClassification": "01",   # 類義語含まない
            "searchConditionBean.articleNm": keyword,
            "OAA0102": "検索",
        }
        if awards:
            # 落札者等の公示。[5]金額の裏取りに使う
            d["searchConditionBean.procurementClaBean.successfulBidNotice"] = "08"
        body = urllib.parse.urlencode(d, encoding="utf-8").encode()
        req = urllib.request.Request(
            POST, data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": FORM})
        try:
            page = self.op.open(req, timeout=90).read().decode("utf-8", "replace")
        except Exception as e:
            return -1, f"{type(e).__name__}"
        if "合致する調達案件情報がありません" in page:
            return 0, page
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
        m = re.search(r"検索結果\s*(\d+)\s*件見つかりました", t)
        if not m:
            # 入力エラーで検索フォームに差し戻されたケースを見逃さない
            err = re.search(r"([^ ]{4,40}(?:入力してください|選択してください))", t)
            print(f"  ! 検索が成立しませんでした: {err.group(1) if err else '原因不明'}")
            return -1, page
        return int(m.group(1)), page

    def page(self, n: int) -> str:
        """検索後、同じセッションで n ページ目を取る。size は50が上限（200を指定しても50）。

        **ページ送りを実装しないと静かに取りこぼす。** 「国際」は103件あるのに
        1ページ目の50件しか取れず、しかも件数表示は103のままなので
        気づかずに「拾えている」と誤認する。件数と取得件数を必ず突き合わせること。
        """
        try:
            req = urllib.request.Request(PAGE.format(n=n), headers={"Referer": POST})
            return self.op.open(req, timeout=90).read().decode("utf-8", "replace")
        except Exception:
            return ""


def parse_rows(page: str, keyword: str, today: date) -> list[dict]:
    out = []
    parts = page.split(ROW_KEY)[1:]
    for seg in parts:
        # split で key を落とすと "> 0000…" のように > が残る。剥がしてから判定する
        no = strip(seg.split("</td>", 1)[0]).lstrip(">").strip()
        name = field(seg, "articleNm")
        if not name:
            continue
        # **調達案件番号が「‐」の案件がある。** 2027年国際園芸博覧会の政府出展など、
        # 御社の主戦場そのものがこの形だった。数字でないからと弾くと、
        # 一番拾いたい案件だけが静かに消える。番号の有無で捨ててはいけない。
        if not re.fullmatch(r"\d{10,}", no):
            no = ""
        organ = field(seg, "procurementOrgan")
        addr = field(seg, "receiptAddress")
        pts, hits = score(name)
        # 公開開始日は「令和07年10月16日公開開始」の形で本文に混ざる
        dm = re.search(r"(令和\s*\d+年\s*\d+月\s*\d+日)公開開始", strip(seg[:6000]))
        out.append({
            "検出日": today.isoformat(), "経路": "調達ポータル",
            "検索語": keyword, "調達案件番号": no, "案件名": name[:200],
            "発注機関": organ, "所在地": addr,
            "公開開始日": dm.group(1) if dm else "",
            "関連度": pts, "一致語": hits,
            # 番号があれば GEPS の実URL（GETで開ける）。無ければ検索フォームへ送り、
            # 「直リンクが存在しない」ことを列で明示する。**開けないURLを載せない。**
            "URL": GEPS.format(no=no) if no else FORM,
            "リンク種別": "直リンク" if no else "要検索（調達案件番号なし）",
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", action="append", help="この語だけ検索する")
    ap.add_argument("--awards", action="store_true", help="落札公示も対象にする")
    ap.add_argument("--min-score", type=int, default=0,
                    help="関連度の下限。既定0（捨てた記録を残すため全部書く）")
    args = ap.parse_args()

    today = date.today()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    words = args.keyword or KEYWORDS

    p = Portal()
    if not p.open_form():
        print("調達ポータルに到達できません。到達不可としてレポートに明記すること。")
        return 1

    found: list[dict] = []
    zero: list[str] = []
    failed: list[str] = []
    for i, kw in enumerate(words, 1):
        n, page = p.search(kw, awards=args.awards)
        if n < 0:
            failed.append(kw)
            print(f"-- [{i}/{len(words)}] {kw:10} 検索失敗")
            # セッションが切れた可能性。張り直して次へ
            p = Portal()
            p.open_form()
            continue
        rows = parse_rows(page, kw, today) if n else []
        # 2ページ目以降。件数に追いつくまで送る（上限20ページ=1000件で打ち切り）
        pno = 1
        while len(rows) < n and pno < 20:
            extra = p.page(pno)
            if not extra:
                break
            got = parse_rows(extra, kw, today)
            if not got:
                break
            # 番号なしの案件は空文字がキーになるため、番号だけで重複判定すると
            # 2ページ目以降の番号なし案件が丸ごと消える。機関＋案件名で見る。
            def key(r):
                return r["調達案件番号"] or (r["発注機関"] + "|" + r["案件名"])
            known = {key(r) for r in rows}
            new = [r for r in got if key(r) not in known]
            if not new:
                break
            rows += new
            pno += 1
            time.sleep(0.6)
        if len(rows) < n:
            print(f"   ! {kw}: {n} 件中 {len(rows)} 件しか取得できていない（要調査）")
        keep = [r for r in rows if r["関連度"] >= args.min_score]
        found += keep
        if n == 0:
            zero.append(kw)
        print(f"{'OK ' if keep else '-- '}[{i}/{len(words)}] {kw:10} "
              f"{n:4} 件 → 取得 {len(rows):3} 件 / 関連 {len(keep):3} 件", flush=True)
        time.sleep(1.0)     # 相手は国のシステム。連打しない

    # 同一案件が複数の検索語で出る。調達案件番号で寄せる
    merged: dict[str, dict] = {}
    for r in sorted(found, key=lambda x: -x["関連度"]):
        k = r["調達案件番号"] or (r["発注機関"] + "|" + r["案件名"])
        if k in merged:
            merged[k]["検索語"] += "/" + r["検索語"]
        else:
            merged[k] = r

    out = OUTDIR / f"pportal_{today:%Y%m%d}.csv"
    fields = ["検出日", "経路", "検索語", "関連度", "一致語", "調達案件番号",
              "案件名", "発注機関", "所在地", "公開開始日", "URL", "リンク種別"]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(merged.values(), key=lambda x: -x["関連度"]):
            w.writerow({k: r.get(k, "") for k in fields})

    print(f"\n{out}: {len(merged)} 件（重複除去後）")
    if zero:
        print(f"0件だった語（記録として残す）: {' '.join(zero)}")
    if failed:
        print(f"検索が失敗した語（要再試行）: {' '.join(failed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
