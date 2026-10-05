# -*- coding: utf-8 -*-
"""自治体の「入札・公募・補助金」の一覧ページを自分で見つけ、**実際に案件行が取れたURLだけ**を返す。

なぜ要るか
----------
2026-10-05、47都道府県のサイト内検索を実測したところ、
URLのパターンを3→9種に増やして2xxを返す県は24→28に増えたが、
**そこから得られた案件見出しは0件だった。**
検索結果がJavaScriptで描画されるため curl では読めない。
つまり「検索経路は通っているように見えて、何も返していない」。

その結果、神奈川県 GREEN×EXPO 2027 賓客等接遇業務委託（上限4億337万円・等級要件なし）を
**参加意思表明が閉じた11日後**に検出した。

だから検索に頼るのをやめ、**一覧ページのURLを台帳として持つ**。
ただし手で並べると必ず間抜けが出るので、ここで自動的に見つける。

**この道具は「取れたURL」しか返さない。**候補を叩いて案件行を数え、
0件のURLは採用しない。採用できなかった自治体は**名指しで申告する**。
鳴らない検出器は、検出器が無いのと同じである（2026-09-21・2026-10-05 の教訓）。

    python3 bin/discover_channels.py            # 発見して data/channels_found.csv に書く
    python3 bin/discover_channels.py --limit 10 # 先頭10自治体だけ（動作確認用）
"""
import re, html, json, csv, sys, time, subprocess, urllib.parse, datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0 Safari/537.36')

# ハブの候補を見分ける語（トップページのリンク文字列に対して）
HUB = re.compile(r'入札|契約|調達|公募|委託|補助金|助成|事業者.{0,4}募集|プロポーザル|企画提案|公告')
# 「案件の行」を見分ける語。**これが1件も無いURLは採用しない**
CASE = re.compile(r'委託|業務|プロポーザル|企画提案|企画競争|企画競技|入札|公募|請負|'
                  r'補助金|助成金|事業者.{0,4}(募集|選定)|受託|公告')
# 案件ではないもの
SKIP = re.compile(r'^(ホーム|トップ|サイトマップ|お問い合わせ|よくある|組織|アクセス|個人情報|'
                  r'リンク|著作権|免責|English|やさしい|文字サイズ|検索)')


def fetch(u, t=18, tries=2):
    """(本文, HTTPステータス)。**ステータスを見る。**404の本文は数十KBあり長さでは判らない。"""
    for i in range(tries):
        try:
            r = subprocess.run(['curl', '-sSL', '-A', UA, '--max-time', str(t),
                                '--compressed', '-k', '-w', '\n#H%{http_code}', u],
                               capture_output=True, timeout=t + 10)
            raw = r.stdout.decode('utf-8', 'replace')
            m = re.search(r'\n#H(\d{3})\s*$', raw)
            code = int(m.group(1)) if m else 0
            if m: raw = raw[:m.start()]
            if len(raw) > 500: return raw, code
        except Exception:
            pass
        if i < tries - 1: time.sleep(1.5)
    return '', 0


def anchors(base, s):
    out = []
    for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', s, re.S | re.I):
        t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', m.group(2)))).strip()
        if 3 <= len(t) <= 220:
            out.append((t, urllib.parse.urljoin(base, m.group(1))))
    return out


def count_cases(base, s):
    """そのページに「案件の行」が何件あるか。見出しの例も返す。"""
    hits = []
    for t, u in anchors(base, s):
        if len(t) < 8 or SKIP.match(t): continue
        if CASE.search(t): hits.append(t)
    # 同じ文字列の重複を除く
    uniq = list(dict.fromkeys(hits))
    return len(uniq), uniq[:3]


def work(item):
    """1自治体。トップ→ハブ候補→案件行が取れたURLを返す。"""
    name, host = item
    top, code = fetch(f'https://{host}/')
    if not top:
        return name, host, 'トップが取得できず', []
    cands = []
    for t, u in anchors(f'https://{host}/', top):
        if host not in u: continue
        if not HUB.search(t): continue
        cands.append((t, u))
    # 重複URLを除き、上限20
    seen, cl = set(), []
    for t, u in cands:
        if u in seen: continue
        seen.add(u); cl.append((t, u))
    cl = cl[:20]

    found = []
    for t, u in cl:
        s, c = fetch(u)
        if not s or not (200 <= c < 300): continue
        n, ex = count_cases(u, s)
        if n >= 3:                       # **3件以上とれたURLだけ採用**
            found.append((t, u, n, ex))
    found.sort(key=lambda x: -x[2])
    if not found:
        return name, host, f'ハブ候補{len(cl)}件を叩いたが案件行3件以上のURLが無い', []
    return name, host, 'ok', found[:3]   # 自治体ごとに上位3本まで


def main():
    lim = None
    if '--limit' in sys.argv:
        lim = int(sys.argv[sys.argv.index('--limit') + 1])

    hosts = {}
    hosts.update(json.load(open('workflow/prefs.json')))        # 47都道府県
    hosts.update(json.load(open('workflow/cities.json')))       # 主要市
    items = list(hosts.items())
    if lim: items = items[:lim]
    print(f'対象 {len(items)} 自治体')

    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(work, items))

    ok = [r for r in res if r[2] == 'ok']
    ng = [r for r in res if r[2] != 'ok']
    rows = []
    for name, host, st, found in ok:
        for t, u, n, ex_ in found:
            rows.append([name, host, t[:60], u, n, ' / '.join(e[:40] for e in ex_)])

    stamp = datetime.datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M')
    with open('data/channels_found.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['自治体', 'ホスト', 'ハブの名前', 'URL', '案件行の数', '見出しの例'])
        w.writerows(rows)

    print(f'\n基準日時 {stamp}')
    print(f'**案件行が取れた自治体：{len(ok)}／{len(items)}　→ URL {len(rows)}本**')
    print(f'**取れなかった自治体：{len(ng)}**')
    for name, host, st, _ in ng:
        print(f'   {name}（{host}）… {st}')
    print('\n**取れなかった自治体は、ここでは永久に見つからない。**'
          '手でURLを調べて data/channels.csv に入れること。')
    print('→ data/channels_found.csv')


if __name__ == '__main__':
    main()
