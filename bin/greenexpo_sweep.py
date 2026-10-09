# -*- coding: utf-8 -*-
"""GREEN×EXPO 2027（2027年国際園芸博覧会・横浜）の各県出展業務を全県で探す。
   会期2027年3〜9月。各県が前年度中に個別発注するため、毎月これを回す。"""
import re, html, json, time, subprocess, csv, urllib.parse, datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
# 表記ゆれが多い：「2027年国際園芸博覧会」「GREEN×EXPO 2027」「花博」「園芸博」
EXPO = re.compile(r'国際園芸博覧会|GREEN\s*[×xX]\s*EXPO|ｸﾞﾘｰﾝ|園芸博|花博|横浜花博')
# 発注案件であること（出展者募集・来場案内は除く）
CASE = re.compile(r'委託|業務|プロポーザル|企画提案|企画競争|企画競技|入札|公募|請負|事業者[のをに]?(募集|選定)')
SKIP = re.compile(r'入場券|チケット|来場|ボランティア|出展者募集|参加者募集|開催概要|とは')
HUB  = re.compile(r'入札|公募|調達|プロポーザル|契約|委託|募集|事業者|企画競争|企画提案|お知らせ|新着')

def fetch(u, t=22, tries=3):
    """本文だけを返す（従来の呼び出し互換）。"""
    return fetch2(u, t, tries)[0]


def fetch2(u, t=22, tries=3):
    """(本文, HTTPステータス) を返す。

    **ステータスを見ないと 404 ページを「取得できた」と数えてしまう。**
    2026-10-05、経路の生死を数える仕組みを入れたところ
    「通らなかった県は2県」と出たが、HTTPコードを別に実測すると29県だった。
    自治体の404ページは数十KBのHTMLで、本文の長さでは本物と区別できない。
    **都合のよい数を返す検査は、検査が無いのと同じである。**
    """
    for _i in range(tries):
        try:
            r = subprocess.run(['curl', '-sSL', '-A', UA, '--max-time', str(t),
                                '--compressed', '-w', '\n#HTTP%{http_code}', u],
                               capture_output=True, timeout=t + 8)
            raw = r.stdout.decode('utf-8', 'replace')
            code = 0
            m = re.search(r'\n#HTTP(\d{3})\s*$', raw)
            if m:
                code = int(m.group(1)); raw = raw[:m.start()]
            if len(raw) > 500: return raw, code
        except Exception: pass
        if _i < tries - 1: time.sleep(2 ** _i)
    return '', 0

def anchors(base, s):
    out = []
    for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', s, re.S | re.I):
        t = html.unescape(re.sub(r'<[^>]+>', '', m.group(2)))
        t = re.sub(r'\s+', ' ', t).strip()
        if 4 <= len(t) <= 220: out.append((t, urllib.parse.urljoin(base, m.group(1))))
    return out

def work(item):
    pref, host = item
    hits, seen = [], set()
    # **経路が使えたかを数える。**
    # 2026-10-05 判明：この掃引は「0件」を「案件が無かった」として報告してきたが、
    # **47県中29県でサイト内検索の経路が1つも通っていなかった。**
    # 神奈川県 GREEN×EXPO 2027賓客等接遇業務委託（上限4億337万円・等級要件なし）を、
    # 参加意思表明 9/24 15時が閉じた11日後にようやく検出した。
    # **経路が死んでいる県の「0件」は「探せていない」という意味である。**
    # 鳴らない検出器は、検出器が無いのと同じ（2026-09-21 の UTC の件と同じ型）。
    reach = {'search': 0, 'top': 0}
    # 各県のサイト内検索を叩く。パスは県ごとに違うので複数試す。
    queries = ['国際園芸博覧会', 'GREEN%C3%97EXPO']
    urls = []
    for q in queries:
        urls += [f'https://{host}/site/search.html?q={q}',
                 f'https://{host}/search.html?q={q}',
                 f'https://{host}/cgi-bin/search.cgi?q={q}']
    for u in urls:
        s, code = fetch2(u)
        if not s: continue
        # **2xx でなければ「探せた」とは数えない。**404 の本文でも長さはあるため。
        if 200 <= code < 300: reach['search'] += 1
        else: continue
        for t, link in anchors(u, s):
            if not EXPO.search(t): continue
            if SKIP.search(t) or not CASE.search(t): continue
            k = t
            if k in seen: continue
            seen.add(k); hits.append((pref, t, link))
    # トップから入札・公募ハブへ1段だけ降りる
    top = fetch(f'https://{host}/')
    if top:
        reach['top'] = 1
        for t, link in anchors(f'https://{host}/', top):
            if not HUB.search(t) or host not in link: continue
            hs = fetch(link, 18, 1)
            if not hs: continue
            for t2, l2 in anchors(link, hs):
                if not EXPO.search(t2): continue
                if SKIP.search(t2) or not CASE.search(t2): continue
                k = t2
                if k in seen: continue
                seen.add(k); hits.append((pref, t2, l2))
    return pref, hits, reach

PREFS = json.load(open('workflow/prefs.json'))
with ThreadPoolExecutor(max_workers=12) as ex:
    res = list(ex.map(work, PREFS.items()))

rows = []
blind = []          # 検索経路が1つも通らなかった県
for pref, hits, reach in res:
    if hits: print(f'{pref}: {len(hits)}件', flush=True)
    for h in hits: print('   ', h[1][:76], flush=True)
    rows += hits
    if reach['search'] == 0: blind.append(pref)

# 出力ファイル名は JST の当日。**固定名にすると、いつ採ったものか分からなくなる。**
stamp = datetime.datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y%m%d')
out = f'data/greenexpo_{stamp}.csv'
with open(out, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['都道府県', '案件名', 'URL']); w.writerows(rows)

print(f'\n該当 {len(rows)}件 / {sum(1 for _, h, _ in res if h)}県　→ {out}')
print(f'\n**検索経路が1つも通らなかった県：{len(blind)}／{len(res)}**')
if blind:
    print('   ' + '、'.join(blind))
    print('   **この県の「0件」は「案件が無かった」ではなく「探せていない」という意味である。**')
    print('   トップページに載っている期間しか拾えないため、公告から締切まで短い案件は落ちる。')
    print('   2026-10-05、神奈川県の4億337万円の案件を、参加意思表明が閉じた11日後に検出した。')
