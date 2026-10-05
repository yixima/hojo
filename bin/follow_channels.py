# -*- coding: utf-8 -*-
"""到達できなかった自治体のトップページから、**サイト自身が張っているリンクを2段たどって**
入札・公募・補助金の一覧ページを見つける。

なぜ要るか（2026-10-05 の実測）
--------------------------------
`bin/retry_unreached.py` は候補パス37本を当てに行き、
**「26自治体に届かない」と報告した。**
ところが同じ26ホストのトップページを HTTP コードで実測すると、
**20ホストが 200 を返した。**神奈川県（4億337万円の相手）も 200 である。

つまり届かなかったのは**ネットワークではなく、こちらのURLの当て推量**だった。
**自分の当て推量の失敗を「相手に届かない」と報告していた。**
これは 9/21 の UTC 刻印、10/5 の 404 を成功と数えた件と同じ型である。

だから当てるのをやめ、**サイトが実際に張っているリンクをたどる。**
`discover_channels.py` は1段しかたどらないが、自治体サイトは
「事業者向け」→「入札・契約」→一覧、と2段先にあることが多い。

**採用するのは案件行が3件以上とれたURLだけ。**取れなかった自治体は名指しで申告する。

    python3 bin/follow_channels.py                  # data/channels_unreached.txt の残りを対象に
    python3 bin/follow_channels.py --all            # 台帳に無い全ホストを対象に
"""
import re, html, json, csv, sys, io, os, time, subprocess, urllib.parse, datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST = ZoneInfo('Asia/Tokyo')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')
HDR = ['-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       '-H', 'Accept-Language: ja,en;q=0.8']

# 1段目にたどる語（「事業者向け」のような入口も含める。ここが狭いと2段目に届かない）
HUB1 = re.compile(r'入札|契約|調達|公募|委託|補助金|助成|事業者|企業|産業|商工|'
                  r'プロポーザル|企画提案|公告|募集|しごと|ビジネス')
# 2段目にたどる語（入口の中で、案件一覧に近いもの）
HUB2 = re.compile(r'入札|契約|調達|公募|委託|補助金|助成|プロポーザル|企画提案|'
                  r'企画競争|公告|事業者.{0,4}募集|業務委託|物品|役務')
CASE = re.compile(r'委託|業務|プロポーザル|企画提案|企画競争|企画競技|入札|公募|請負|'
                  r'補助金|助成金|事業者.{0,4}(募集|選定)|受託|公告')
SKIP = re.compile(r'^(ホーム|トップ|サイトマップ|お問い合わせ|よくある|組織|アクセス|個人情報|'
                  r'リンク|著作権|免責|English|やさしい|文字サイズ|検索|前へ|次へ|このページ)')


def fetch(u, t=20, tries=2):
    """(本文, HTTPステータス)。**ステータスを見る。**長さでは 404 と区別できない。"""
    for i in range(tries):
        try:
            r = subprocess.run(['curl', '-sSL', '-A', UA] + HDR +
                               ['--max-time', str(t), '--compressed',
                                '-w', '\n#H%{http_code}', u],
                               capture_output=True, timeout=t + 10)
            raw = r.stdout.decode('utf-8', 'replace')
            m = re.search(r'\n#H(\d{3})\s*$', raw)
            code = int(m.group(1)) if m else 0
            if m: raw = raw[:m.start()]
            if len(raw) > 500: return raw, code
        except Exception:
            pass
        if i < tries - 1: time.sleep(1.2)
    return '', 0


def anchors(base, s):
    out = []
    for m in re.finditer(r'''<a\s[^>]*href=["']([^"'#]+)["'][^>]*>(.*?)</a>''', s, re.S | re.I):
        t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', m.group(2)))).strip()
        if 2 <= len(t) <= 220:
            # **urljoin を使う。**自前の連結は `//host/...`（プロトコル相対）で壊れる
            out.append((t, urllib.parse.urljoin(base, html.unescape(m.group(1)))))
    return out


def count_cases(base, s):
    hits = [t for t, u in anchors(base, s)
            if len(t) >= 8 and not SKIP.match(t) and CASE.search(t)]
    uniq = list(dict.fromkeys(hits))
    return len(uniq), uniq[:3]


def work(item):
    name, host = item
    trace = []
    top, code = fetch(f'https://{host}/')
    if not top:
        return name, host, f'トップが取得できず（HTTP {code}）', [], trace
    trace.append(f'トップ HTTP {code} / {len(top)}字')

    base = f'https://{host}/'
    seen = {base}
    found = []

    def harvest(url, s):
        n, ex = count_cases(url, s)
        if n >= 3:
            found.append((url, n, ex))
        return n

    harvest(base, top)

    # 1段目
    lv1 = []
    for t, u in anchors(base, top):
        if host not in urllib.parse.urlparse(u).netloc: continue
        if u in seen: continue
        if not HUB1.search(t): continue
        seen.add(u); lv1.append((t, u))
    lv1 = lv1[:26]
    trace.append(f'1段目の候補 {len(lv1)}本')

    lv2 = []
    for t, u in lv1:
        s, c = fetch(u)
        if not s or not (200 <= c < 300): continue
        if harvest(u, s) >= 3: continue        # ここで足りれば深追いしない
        for t2, u2 in anchors(u, s):
            if host not in urllib.parse.urlparse(u2).netloc: continue
            if u2 in seen: continue
            if not HUB2.search(t2): continue
            seen.add(u2); lv2.append((t2, u2))
    lv2 = lv2[:40]
    trace.append(f'2段目の候補 {len(lv2)}本')

    for t, u in lv2:
        if len(found) >= 6: break
        s, c = fetch(u)
        if not s or not (200 <= c < 300): continue
        harvest(u, s)

    found.sort(key=lambda x: -x[1])
    # トップそのものは一覧ではないので、他に取れていれば落とす
    if len(found) > 1:
        found = [f for f in found if f[0].rstrip('/') != base.rstrip('/')] or found
    if not found:
        return name, host, '2段たどったが案件行3件以上のURLが無い', [], trace
    return name, host, 'ok', found[:3], trace


def main():
    now = datetime.datetime.now(JST)
    print(f'基準日時 {now:%Y-%m-%d %H:%M} JST（実時刻）')

    hosts = {}
    hosts.update(json.load(io.open(os.path.join(ROOT, 'workflow/prefs.json'), encoding='utf-8')))
    hosts.update(json.load(io.open(os.path.join(ROOT, 'workflow/cities.json'), encoding='utf-8')))

    if '--all' in sys.argv:
        items = list(hosts.items())
    else:
        # 残りだけ。data/channels_unreached.txt の自治体名を拾う
        p = os.path.join(ROOT, 'data/channels_unreached.txt')
        names = set()
        if os.path.exists(p):
            for ln in io.open(p, encoding='utf-8'):
                ln = ln.strip()
                if not ln or ln.startswith('#'): continue
                # 「名称」単独の行でも「名称（ホスト）」でも拾う。
                # **ここを取りこぼすと対象0件になり、何も調べずに「残り0」と出る。**
                nm = re.split(r'[（(\s,]', ln)[0]
                if nm in hosts: names.add(nm)
        # retry の結果で届いたものは外す
        rp = os.path.join(ROOT, 'data/channels_retry.csv')
        if os.path.exists(rp):
            for r in csv.DictReader(io.open(rp, encoding='utf-8')):
                names.discard(r['自治体'])
        items = [(n, hosts[n]) for n in sorted(names)]
    print(f'対象 {len(items)} 自治体（トップページからリンクを2段たどる）')

    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(work, items))

    ok = [r for r in res if r[2] == 'ok']
    ng = [r for r in res if r[2] != 'ok']

    rows = []
    for name, host, st, found, tr in ok:
        for u, n, exs in found:
            rows.append({'自治体': name, 'ホスト': host, 'URL': u,
                         '案件行の数': n, '見出しの例': ' / '.join(exs)})
    out = os.path.join(ROOT, 'data/channels_followed.csv')
    with io.open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['自治体', 'ホスト', 'URL', '案件行の数', '見出しの例'])
        w.writeheader(); w.writerows(rows)

    print(f'\n**新たに到達できた自治体：{len(ok)}／{len(items)}　→ URL {len(rows)}本**')
    for name, host, st, found, tr in sorted(ok, key=lambda r: -max(f[1] for f in r[3])):
        for u, n, exs in found:
            print(f'   {name:8s} 案件行 {n:3d}  {u}')

    print(f'\n**それでも届かない自治体：{len(ng)}**')
    for name, host, st, _, tr in sorted(ng):
        print(f'   {name}（{host}）… {st}')
        print(f'      経過：{" / ".join(tr)}')

    print(f'\n→ {out}')
    print('**ここで落ちた残りだけを人の手でお願いする。**')


if __name__ == '__main__':
    main()
