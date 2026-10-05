# -*- coding: utf-8 -*-
"""jGrants の募集中の補助金を**キーワードの束で網羅的に**取り、締切つきで出す。

なぜ要るか
----------
2026-10-05 まで、jGrants はチャネル掃引のなかで見出しだけを見ていた。
**締切を見ていなかったため、補助金が「今月の関門」に1件も載らなかった。**

jGrants の公開APIは**キーワードが必須**（2文字以上）で、キーワード無しの全件取得はできない。
そこで**広い語の束を母集団の定義とし、その和集合を取る。**
語を増やせば母集団が増える。**ここに無い語で呼ばれる制度は、永久に見つからない。**
だからこの一覧は `KEYWORDS` として明示し、画面にも出す。

    python3 bin/jgrants_sweep.py              # 募集中の全件を締切順に
    python3 bin/jgrants_sweep.py --days 60    # 60日以内に締切が来るものだけ
    python3 bin/jgrants_sweep.py --ours       # 当社の領域に当たるものだけ
"""
import json, sys, csv, subprocess, urllib.parse, datetime, re
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor

API = 'https://api.jgrants-portal.go.jp/exp/v1/public/subsidies'
UA = 'Mozilla/5.0'

# **母集団の定義。**広い語から始め、当社の領域の語を足している。
# 語を増やすと母集団が増える。**ここに無い語で呼ばれる制度は見つからない。**
KEYWORDS = [
    # 広い語（これだけで200件超が返る）
    '補助金', '助成金', '事業', '支援', '委託', '公募',
    # 当社の領域
    '展示会', '出展', '販路開拓', '海外展開', '観光', 'インバウンド',
    'イベント', '催事', 'プロモーション', '情報発信', 'ブランド',
    '工芸', '伝統', '文化', '芸術', 'デザイン', '映像', '広報',
    '物産', '商談会', 'フェア', '越境EC', '輸出', '地域資源',
]

# 当社の領域に当たるか（見出しで粗く判定。**落とすのではなく印を付けるだけ**）
OURS = re.compile(r'展示会|出展|販路|海外展開|観光|インバウンド|イベント|催事|'
                  r'プロモーション|情報発信|ブランド|工芸|伝統|文化|芸術|デザイン|'
                  r'映像|広報|物産|商談|フェア|越境|輸出|地域資源|誘客|交流')


def get(u, t=45, tries=2):
    for _ in range(tries):
        try:
            b = subprocess.run(['curl', '-sSL', '-A', UA, '--max-time', str(t),
                                '--compressed', '-k', u],
                               capture_output=True, timeout=t + 12).stdout.decode('utf-8', 'replace')
            if len(b) > 50: return b
        except Exception:
            pass
    return ''


def fetch_kw(kw):
    u = (f'{API}?keyword={urllib.parse.quote(kw)}'
         f'&sort=acceptance_end_datetime&order=ASC&acceptance=1')
    s = get(u)
    try:
        d = json.loads(s)
    except Exception:
        return kw, None            # **取得できなかった。0件と区別する**
    return kw, (d.get('result') or [])


def main():
    days = None
    if '--days' in sys.argv: days = int(sys.argv[sys.argv.index('--days') + 1])
    ours_only = '--ours' in sys.argv

    now = datetime.datetime.now(ZoneInfo('Asia/Tokyo'))
    today = now.date()
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(fetch_kw, KEYWORDS))

    dead = [kw for kw, r in res if r is None]
    uni = {}
    for kw, r in res:
        if not r: continue
        for x in r:
            i = x.get('id')
            if i and i not in uni: uni[i] = x

    rows = []
    for x in uni.values():
        end = (x.get('acceptance_end_datetime') or '')[:10]
        title = (x.get('title') or '').replace('\n', ' ')
        org = x.get('name') or ''
        try:
            d = datetime.date.fromisoformat(end)
            left = (d - today).days
        except Exception:
            d, left = None, None
        rows.append({'締切': end, '残り': left, '制度名': title, '所管': org,
                     '当社領域': '○' if OURS.search(title) else '',
                     'ID': x.get('id', ''),
                     'URL': f"https://www.jgrants-portal.go.jp/subsidy/{x.get('id','')}"})
    rows.sort(key=lambda r: (r['締切'] or '9999'))

    sel = [r for r in rows if r['残り'] is not None and r['残り'] >= 0]
    if days is not None: sel = [r for r in sel if r['残り'] <= days]
    if ours_only: sel = [r for r in sel if r['当社領域']]

    stamp = now.strftime('%Y-%m-%d %H:%M')
    out = f'data/jgrants_{now.strftime("%Y%m%d")}.csv'
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['締切', '残り', '当社領域', '制度名', '所管', 'ID', 'URL'])
        w.writeheader(); w.writerows(rows)

    print(f'基準日時 {stamp} JST（実時刻）')
    print(f'キーワード {len(KEYWORDS)}語の和集合 → **募集中 {len(rows)}件**'
          f'（うち当社の領域 {sum(1 for r in rows if r["当社領域"])}件）')
    if dead:
        print(f'**取得できなかったキーワード：{len(dead)}語 → {"、".join(dead)}**')
        print('  **これは「0件」ではなく「取れていない」。母集団が欠けている。**')
    print(f'\n■ 表示対象 {len(sel)}件'
          + (f'（締切まで{days}日以内）' if days is not None else '')
          + ('（当社の領域のみ）' if ours_only else ''))
    for r in sel:
        mark = '★' if r['当社領域'] else ' '
        print(f'  {mark} 残り{r["残り"]:>4}日  {r["締切"]}  {r["制度名"][:62]}')
        print(f'        {r["所管"][:40]}  {r["URL"]}')
    print(f'\n→ {out}')
    print('\n**この一覧は KEYWORDS で定義した母集団しか見ない。**'
          'ここに無い語で呼ばれる制度は永久に見つからない。語を足すこと。')


if __name__ == '__main__':
    main()
