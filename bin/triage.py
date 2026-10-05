# -*- coding: utf-8 -*-
"""掃引で拾った見出しを、**相性（第一）→金額（第二）**で並べ、締切を一次資料から引く。

生島様のご指示（2026-10-05）：
「当社が申請できそうな、相性の良いもの優先。但し金額も第二優先」

**台帳は書き換えない。**候補を出すところまでが機械の仕事（CLAUDE.md）。
出力＝data/triage_YYYYMMDD.csv

    python3 bin/triage.py                 # 当日の掃引ログから
    python3 bin/triage.py --max 200       # 上限
"""
import csv, os, re, sys, io, time, subprocess, datetime, urllib.parse
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'bin'))
from rank import grade
import gatelib

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0 Safari/537.36')
JST = ZoneInfo('Asia/Tokyo')

# 応募できないものは最初から外す
DONE = re.compile(r'入札結果|開札結果|契約結果|落札|最優秀|受託(候補)?者?を?(決定|選定)|'
                  r'選定しました|選定結果|結果[のを]?公表|結果について|終了しました|'
                  r'募集(は)?終了|公募終了|受付終了|中止|質問(書)?[のへ]?回答')

# 金額。千円単位・万円・円 を拾う
MONEY = [
    (re.compile(r'([0-9０-９,，]{2,12})\s*千円'), 1000),
    (re.compile(r'([0-9０-９,，]{1,8})\s*万円'), 10000),
    (re.compile(r'([0-9０-９,，]{5,15})\s*円'), 1),
]
MONEY_CTX = re.compile(r'(上限|予定価格|委託料|概算|業務価格|限度額|予算|見積上限)')


def z(x):
    return x.translate(str.maketrans('０１２３４５６７８９，', '0123456789,')).replace(',', '')


def fetch(u, t=25, tries=2):
    for i in range(tries):
        try:
            r = subprocess.run(['curl', '-sSL', '-A', UA, '--max-time', str(t),
                                '--compressed', '-w', '\n#H%{http_code}', u],
                               capture_output=True, timeout=t + 12)
            raw = r.stdout
            m = re.search(rb'\n#H(\d{3})\s*$', raw)
            code = int(m.group(1)) if m else 0
            if m: raw = raw[:m.start()]
            if len(raw) > 400: return raw, code
        except Exception:
            pass
        if i < tries - 1: time.sleep(1.5)
    return b'', 0


def text_of(raw, url):
    """HTML も PDF も本文テキストにする。"""
    if raw[:4] == b'%PDF':
        try:
            from pypdf import PdfReader
            return '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(raw)).pages)
        except Exception:
            return ''
    s = raw.decode('utf-8', 'replace')
    if '<' not in s[:2000] and 'charset' not in s[:400].lower():
        pass
    s = re.sub(r'(?is)<(script|style).*?</\1>', ' ', s)
    import html as H
    return H.unescape(re.sub(r'<[^>]+>', '\n', s))


def money_of(t):
    """最も大きい「上限・予定価格」らしい金額を円で返す。"""
    best = 0
    flat = re.sub(r'[ 　]+', '', t)
    for pat, mul in MONEY:
        for m in pat.finditer(flat):
            head = flat[max(0, m.start() - 36):m.start()]
            if not MONEY_CTX.search(head): continue
            try:
                v = int(z(m.group(1))) * mul
            except Exception:
                continue
            if 100000 <= v <= 20000000000: best = max(best, v)
    return best


def repair(u):
    """掃引ログのURLを直す。

    2026-10-05 実測：ログには
    `https://www.city.fukushima.fukushima.jp//www.city.fukushima.fukushima.jp/...`
    のようなURLが54本あった。プロトコル相対リンク（`//host/...`）を
    自前で連結したためである（`bin/sweep_channels.py` 側は urljoin に直した）。
    **過去に積んだログは直らないので、読む側でも修復する。**
    """
    if not u: return u
    p = urllib.parse.urlsplit(u)
    path = p.path
    for _ in range(4):
        if not path.startswith('//'): break
        seg = path[2:].split('/', 1)
        if '.' in seg[0] and ' ' not in seg[0]:       # ホスト名が重複している
            path = '/' + (seg[1] if len(seg) > 1 else '')
        else:
            path = path[1:]
    # **同じ経路が2回続くURLを直す。**
    # 2026-10-05 実測：ログの38本が
    # `/kensei/nyuusatsu/compe/sanka/kensei/nyuusatsu/compe/sanka/1099190.html`
    # の形で 404 だった。旧 absolutize が `href.lstrip('./')` と書いており、
    # **`../../../../` の「上へ4つ」をただ削り落としていた**ためである。
    # 直したのは掃引側だが、**既に積んだログは直らないので読む側でも直す。**
    seg = [x for x in path.split('/') if x != '']
    for k in range(len(seg) // 2, 0, -1):
        if seg[:k] == seg[k:2 * k]:
            seg = seg[k:]
            break
    if seg:
        path = '/' + '/'.join(seg)
    return urllib.parse.urlunsplit((p.scheme, p.netloc, path, p.query, ''))


_NORM_DROP = re.compile(r'[\s　・,，.。「」『』“”\'"（）()\[\]【】〔〕\-–—‐─ー~〜/／]+')


def _norm(t):
    t = t.translate(str.maketrans('０１２３４５６７８９（）［］　', '0123456789()[] '))
    return _NORM_DROP.sub('', t)


def _lcs(a, b):
    """最長共通部分文字列の長さ。見出しと a タグの文字列を突き合わせる。"""
    if not a or not b: return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best: best = cur[j]
        prev = cur
    return best


_A = re.compile(r'<a\s[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', re.S | re.I)


def find_detail(base, raw, title):
    """一覧ページから、その見出しの**詳細ページ**のURLを1本返す。

    なぜ要るか（2026-10-05）
    ------------------------
    掃引が拾ったリンクは一覧ページであることが多く、
    **締切と金額は詳細ページにしか書いていない。**
    一覧だけを読んで「締切が取れたのは1件」と出しても判断には使えない。
    だから**1段たどる。**

    **半分以上が一致しないリンクは採らない。**取り違えると、
    別の案件の締切を入れてしまい、それは締切が無いより危ない。
    """
    if raw[:4] == b'%PDF': return ''
    import html as H
    s = raw.decode('utf-8', 'replace')
    nt = _norm(title)
    if len(nt) < 8: return ''
    best, bu = 0, ''
    for m in _A.finditer(s):
        at = _norm(re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', '', m.group(2)))))
        if len(at) < 8: continue
        n = _lcs(nt, at)
        if n > best:
            best, bu = n, urllib.parse.urljoin(base, H.unescape(m.group(1)).strip())
    if best >= max(10, int(len(nt) * 0.5)) and bu and bu.rstrip('/') != base.rstrip('/'):
        return bu
    return ''


def job(row):
    stamp, cid, title, link, state = row
    g, why = grade(title)
    out = {'相性': g or '-', '理由': why, 'チャネル': cid, '案件名': title,
           'URL': link, '締切': '', '締切種別': '', '金額': '', '金額_円': 0,
           '取得': ''}
    if not link:
        out['取得'] = 'リンクなし（ナビ等。手で開く必要あり）'
        return out
    link = repair(link)
    out['URL'] = link
    raw, code = fetch(link)
    if not raw or not (200 <= code < 300):
        out['取得'] = f'取得できず HTTP {code}'
        return out
    t = text_of(raw, link)
    out['取得'] = 'ok'

    def read(txt):
        try:
            gs = gatelib.extract_gates(txt)
        except Exception:
            gs = []
        return gs, money_of(txt)

    gates, v = read(t)

    # **一覧ページには締切も金額も無い。だから1段たどる。**（2026-10-05）
    # 直す前は、締切が取れたのは54件中1件だった。
    if not gates or not v:
        d = find_detail(link, raw, title)
        if d:
            raw2, c2 = fetch(d)
            if raw2 and 200 <= c2 < 300:
                g2, v2 = read(text_of(raw2, d))
                if g2 and not gates: gates = g2
                if v2 and not v: v = v2
                if g2 or v2:
                    out['URL'] = d
                    out['取得'] = 'ok（詳細を1段たどった）'

    if gates:
        gs = sorted(gates, key=lambda x: str(x[1]))   # 最も早い関門
        out['締切種別'], d0 = gs[0][0], gs[0][1]
        out['締切'] = str(d0)
    if v:
        out['金額_円'] = v
        out['金額'] = f'{v:,}円'
    return out


def main():
    mx = 200
    if '--max' in sys.argv: mx = int(sys.argv[sys.argv.index('--max') + 1])
    now = datetime.datetime.now(JST)
    today = now.strftime('%Y-%m-%d')

    rows = []
    with io.open(os.path.join(ROOT, 'data/sweep_log.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if not r['観測日時'].startswith(today): continue
            if r['判定'] != '未登録': continue
            if DONE.search(r['見出し']): continue
            g, _ = grade(r['見出し'])
            if g not in ('S', 'A'): continue
            rows.append((r['観測日時'], r['チャネルID'], r['見出し'], r['リンク'], r['判定']))
    # 同じ見出しの重複を落とす
    seen, uniq = set(), []
    for r in rows:
        k = r[2][:60]
        if k in seen: continue
        seen.add(k); uniq.append(r)
    uniq = uniq[:mx]
    print(f'基準日時 {now:%Y-%m-%d %H:%M} JST（実時刻）')
    print(f'対象 {len(uniq)}件（当日の掃引・台帳に無い・S または A・結果通知を除く）')

    res = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, o in enumerate(ex.map(job, uniq), 1):
            res.append(o)
            if i % 20 == 0: print(f'  …{i}/{len(uniq)} 件を確認', flush=True)

    # **締切が過去のものは外す。**新しく到達した一覧には過年度の案件も並ぶため、
    # 金額で並べると2020〜2025年の終わった案件が上位に来てしまった（2026-10-05 実測）。
    # 締切が取れなかったものは残す（「無い」ではなく「読めていない」ため）。
    td = now.date()
    live, past = [], 0
    for r in res:
        if r['締切']:
            try:
                if datetime.date.fromisoformat(r['締切']) < td:
                    past += 1; continue
            except Exception:
                pass
        live.append(r)
    res = live
    print(f'  締切が過去のものを {past}件 外した（応募できない）')

    # **相性が第一、金額が第二。**（生島様 2026-10-05）
    res.sort(key=lambda r: (0 if r['相性'] == 'S' else 1, -r['金額_円']))

    out = os.path.join(ROOT, f'data/triage_{now:%Y%m%d}.csv')
    with io.open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['相性', '理由', '金額', '金額_円', '締切',
                                          '締切種別', '案件名', 'チャネル', 'URL', '取得'])
        w.writeheader(); w.writerows(res)

    ng = [r for r in res if r['取得'] != 'ok']
    print(f'\n**S {sum(1 for r in res if r["相性"]=="S")}件 ／ '
          f'A {sum(1 for r in res if r["相性"]=="A")}件**')
    print(f'金額が取れた {sum(1 for r in res if r["金額_円"])}件 ／ '
          f'締切が取れた {sum(1 for r in res if r["締切"])}件')
    print(f'**一次資料を取得できなかった {len(ng)}件**（「案件なし」ではない。判定不能）')
    print(f'\n→ {out}')
    print('\n■ 上位20件（相性→金額）')
    for r in res[:20]:
        print(f'  [{r["相性"]}] {r["金額"] or "金額未取得":>16s}  '
              f'{r["締切"] or "締切未取得":>10s} {r["締切種別"]:8s} {r["案件名"][:58]}')
    print('\n**台帳は書き換えていない。**確定は一次資料を読んで手で行う（CLAUDE.md）。')


if __name__ == '__main__':
    main()
