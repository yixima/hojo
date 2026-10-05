# -*- coding: utf-8 -*-
"""到達できなかった自治体に、**候補パスを総当たりで**当てて一覧ページを探す。

2026-10-05、自動発見で28自治体に届かなかった。
生島様にブラウザで調べていただく前に、**機械でできるところまで詰める。**
人にお願いするのは、ここで落ちた残りだけにする。

    python3 bin/retry_unreached.py
"""
import re, html, json, csv, io, os, time, subprocess, datetime, urllib.parse
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0 Safari/537.36')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASE = re.compile(r'委託|業務|プロポーザル|企画提案|企画競争|企画競技|入札|公募|請負|'
                  r'補助金|助成金|事業者.{0,4}(募集|選定)|受託|公告')
SKIP = re.compile(r'^(ホーム|トップ|サイトマップ|お問い合わせ|よくある|組織|アクセス|個人情報|'
                  r'リンク|著作権|免責|English|やさしい|文字サイズ|検索)')

# 自治体CMSでよくある一覧ページのパス。**当たったものだけ採る。**
PATHS = [
 '/nyusatsu/index.html','/nyusatsu/','/kensei/nyusatsu/index.html','/kensei/nyusatsu/',
 '/shisei/nyusatsu/index.html','/shisei/nyusatsu/','/business/nyusatsu/index.html',
 '/jigyousha/nyusatsu/index.html','/jigyosha/nyusatsu/index.html',
 '/soshiki/nyusatsu/index.html','/nyusatsu_keiyaku/index.html','/nyuusatsu/index.html',
 '/kurashi/nyusatsu/index.html','/sangyo/nyusatsu/index.html',
 '/bid/','/bid/index.html','/chotatsu/index.html','/chotatsu/',
 '/koubo/index.html','/kobo/index.html','/proposal/index.html','/propo/index.html',
 '/nyusatsu/koubo/index.html','/kensei/nyuusatsu/index.html',
 '/site/nyusatsu/','/life/nyusatsu/','/kense/chotatsu/index.html',
 '/kense/nyusatsu/index.html','/joho/nyusatsu/index.html',
 '/nyusatsu/itaku/index.html','/nyusatsu/gyomu/index.html',
 '/hojokin/index.html','/josei/index.html','/shien/hojokin/index.html',
 '/sangyo/shokogyo/index.html','/business/index.html','/jigyousha/index.html',
]


def fetch(u, t=16):
    try:
        r = subprocess.run(['curl', '-sSL', '-A', UA, '--max-time', str(t),
                            '--compressed', '-k', '-w', '\n#H%{http_code}', u],
                           capture_output=True, timeout=t + 9)
        raw = r.stdout.decode('utf-8', 'replace')
        m = re.search(r'\n#H(\d{3})\s*$', raw)
        code = int(m.group(1)) if m else 0
        if m: raw = raw[:m.start()]
        return (raw if len(raw) > 500 else ''), code
    except Exception:
        return '', 0


def count_cases(base, s):
    hits = []
    for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', s, re.S | re.I):
        t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', m.group(2)))).strip()
        if len(t) < 8 or SKIP.match(t): continue
        if CASE.search(t): hits.append(t)
    u = list(dict.fromkeys(hits))
    return len(u), u[:3]


def work(item):
    name, host = item
    found = []
    for p in PATHS:
        u = f'https://{host}{p}'
        s, c = fetch(u)
        if not s or not (200 <= c < 300): continue
        n, ex = count_cases(u, s)
        if n >= 3: found.append((u, n, ex))
    found.sort(key=lambda x: -x[1])
    return name, host, found[:2]


def main():
    names = [l.strip() for l in io.open(os.path.join(ROOT, 'data/channels_unreached.txt'),
                                        encoding='utf-8')
             if l.strip() and not l.startswith('#')]
    allh = {}
    allh.update(json.load(open(os.path.join(ROOT, 'workflow/prefs.json'))))
    allh.update(json.load(open(os.path.join(ROOT, 'workflow/cities.json'))))
    items = [(n, allh[n]) for n in names if n in allh]
    now = datetime.datetime.now(ZoneInfo('Asia/Tokyo'))
    print(f'基準日時 {now:%Y-%m-%d %H:%M} JST（実時刻）')
    print(f'対象 {len(items)}自治体 × 候補パス {len(PATHS)}本 = {len(items)*len(PATHS)} 回の試行')

    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(work, items))

    ok = [r for r in res if r[2]]
    ng = [r for r in res if not r[2]]
    rows = []
    for name, host, found in ok:
        for u, n, exs in found:
            rows.append([name, host, u, n, ' / '.join(e[:40] for e in exs)])
    out = os.path.join(ROOT, 'data/channels_retry.csv')
    with io.open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['自治体', 'ホスト', 'URL', '案件行の数', '見出しの例'])
        w.writerows(rows)

    print(f'\n**新たに到達できた自治体：{len(ok)}／{len(items)}　→ URL {len(rows)}本**')
    for name, host, found in ok:
        for u, n, exs in found:
            print(f'   {name:8s} 案件行{n:4d}  {u}')
    print(f'\n**それでも届かない自治体：{len(ng)}**')
    for name, host, _ in ng:
        print(f'   {name}（{host}）')
    print('\n**この残りだけを人の手でお願いする。**'
          'ブラウザで入札・公募の一覧を開き、そのURLを控えるだけでよい。')
    print(f'→ {out}')


if __name__ == '__main__':
    main()
