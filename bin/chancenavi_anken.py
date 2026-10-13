# -*- coding: utf-8 -*-
"""ビジネスチャンス・ナビの「東京都の外郭団体等 入札・発注案件」を全件読む。

なぜ要るか
----------
**2026-09-16 から 2026-10-13 まで27日間、ナビの中を一度も見られなかった。**
公社の案件の予定価格と仕様書はナビ上にしかなく、
「ナビにログインする以外に取る道がない」と 10/13 の朝に申し上げていた。
同日、生島様より認証情報を頂いた。

**画面IDは開発者ツール無しで解明できた。**
マイページの onclick に書かれた関数名を、外部JS
（`js/pages/caa0101.js`・`js/pages/cga0101.js`・`js/provider/common.js`）で引くと、
送る値が全部書いてある。**「JavaScript から開くので URL が分からない」は誤りだった。
JS を読んでいなかっただけである。**

経路（2026-10-13 実測）
-----------------------
1. `caa0101` マイページ → `id="token"` を取る
2. `caa0202`（東京都の外郭団体等）… STEP1 検索・申請／STEP2 入札・見積提出／STEP3 結果の確認
3. **`cga0101` に `tocog_flag=0` `status=0`** → 入札参加可能な案件（STEP1）の一覧
   - `status=1` にすると**結果が公表された案件**（STEP3）。落札額はこちら
4. 一覧の送り：`cga0101/index/search` に `limit` `sort` `status` `tocog_flag` `page` ほか
   **`limit=50` にすれば32件は1ページに収まる。**送りを使わずに済む
5. 個別：**`cga0201` に `proposalNumber`** （先に `cga0101/index/showProposalDetailInfo`
   へ同じ値を投げるのが本来の作法。省くと弾かれることがある）

**`tmpTokenKey` は送らない。**本物の post()（common.js）は token だけを足す。

**token は画面ごとに発行される（2026-10-13 実測。ここでいちばん時間を使った）。**
`post()` は `$("#token").val()` を**いま開いている画面から**読む。
マイページの token を一覧の検索に使うと `SBA9001 処理中断` になる。
**「送る値が足りない」と2回疑って外したが、原因は token の持ち回りだった。**
だから画面を開いたら、その HTML から token を取り直す。

    python3 bin/chancenavi_anken.py                 # 受付中の全件
    python3 bin/chancenavi_anken.py --kekka         # 結果が公表された案件（落札額）
    python3 bin/chancenavi_anken.py --detail 1000030449
"""
import io, os, re, sys, csv, html, json, time, datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'bin'))
import chancenavi as C

JST = ZoneInfo('Asia/Tokyo')


def rows_of(h):
    """一覧の HTML から案件を切り出す。1件＝案件名＋業種＋発注組織＋公示日＋契約方法＋受付期間。"""
    t = html.unescape(re.sub(r'<[^>]+>', '\n', re.sub(r'(?is)<(script|style).*?</\1>', ' ', h)))
    lines = [x.strip() for x in t.split('\n') if x.strip()]
    # 提案番号は onclick から順番に拾える（一覧の並びと同じ順）
    nums = re.findall(r"myPageLoginOrOut\(this,\s*'[^']*',\s*'(\d+)'\)", h)
    out, cur, idx = [], None, 0
    for i, ln in enumerate(lines):
        if ln == '案件業種：' and i > 0:
            if cur: out.append(cur)
            cur = {'案件名': lines[i - 1], '提案番号': nums[idx] if idx < len(nums) else '',
                   '案件業種': '', '発注組織': '', '公示日': '', '契約方法': '',
                   '受付開始': '', '受付締切': '', 'ステータス': ''}
            idx += 1
            continue
        if cur is None:
            continue
        if not cur['案件業種'] and i > 0 and lines[i - 1] == '案件業種：':
            cur['案件業種'] = ln
        for k, pat in (('発注組織', '発注組織：'), ('公示日', '公示日：'),
                       ('契約方法', '契約方法：'), ('ステータス', 'ステータス：')):
            if ln.startswith(pat):
                v = ln[len(pat):].strip()
                cur[k] = v or (lines[i + 1].strip() if i + 1 < len(lines) else '')
        if ln.startswith('受付期間：'):
            v = ln[len('受付期間：'):].strip()
            cur['受付開始'] = v or (lines[i + 1].strip() if i + 1 < len(lines) else '')
        if re.match(r'^令和\d+年\d+月\d+日\s*\d+時\d+分$', ln) and cur['受付開始'] and not cur['受付締切']:
            if ln != cur['受付開始']:
                cur['受付締切'] = ln
    if cur: out.append(cur)
    return out


def main():
    now = datetime.datetime.now(JST)
    print('基準日時 %s JST（実時刻）' % now.strftime('%Y-%m-%d %H:%M'))
    if not os.environ.get('CN_USER'):
        print('**CN_USER / CN_PASS が設定されていないため確認できなかった。黙って飛ばさない。**')
        return 1
    my, tok = C.login()
    if not tok:
        print('**ログインできなかった。**')
        return 1
    who = re.search(r'([^\s]+様)', C.plain(my))
    print('ログイン：%s' % (who.group(1) if who else '（氏名を読めず）'))

    if '--detail' in sys.argv:
        pn = sys.argv[sys.argv.index('--detail') + 1]
        # 本来の作法：先に showProposalDetailInfo を叩く
        C._curl(C.BASE + '/cga0101/index/showProposalDetailInfo',
                [('token', tok), ('proposalNumber', pn)], C.BASE + '/cga0101', xhr=True)
        time.sleep(1)
        h = C._curl(C.BASE + '/cga0201', [('token', tok), ('proposalNumber', pn)],
                    C.BASE + '/cga0101')
        p = '/tmp/cn_detail_%s.html' % pn
        io.open(p, 'w', encoding='utf-8').write(h)
        head = C.plain(h)[:90]
        print('cga0201（提案番号 %s）→ %s' % (pn, head))
        print('  保存：%s' % p)
        return 0 if ('タイムアウト' not in head and 'エラー' not in head) else 2

    status = '1' if '--kekka' in sys.argv else '0'
    label = '結果が公表された案件' if status == '1' else '入札参加可能な案件'
    h = C.screen('cga0101', tok, [('status', status)])
    # **開いた画面の token を取り直す。**前の画面の token では弾かれる
    m = re.search(r'id="token"[^>]*value="([^"]*)"', h)
    if m:
        tok = m.group(1)
    if 'タイムアウト' in C.plain(h)[:90]:
        print('**一覧を開けなかった（タイムアウト）。入り直すこと。**')
        return 2
    m = re.search(r'(\d+)件\s*の案件が見つかりました', C.plain(h))
    total = int(m.group(1)) if m else 0
    print('%s：**%d件**' % (label, total))

    # 50件表示にして送りを減らす
    allrows, page = [], 1
    while True:
        if page > 1 or (total > 10 and page == 1 and not allrows):
            # **doPaging が送る値を1つも欠かさずに送る。**
            # 2026-10-13 実測：`sort` に `1` を送って SBA9001「処理中断」になった。
            # 正しい値は `desc`／`asc` である（option の value）。
            # **欠けても、知らない値でも、「想定していない操作」として即死する。**
            d = ([('token', tok), ('limit', '50'), ('sort', 'desc'),
                  ('status', status), ('tocog_flag', '0'),
                  ('keywordRetrievalMethod', '1'), ('page', str(page))]
                 + [(k, '') for k in (
                     'txt_free_word', 'txt_acceptance_date_from', 'txt_acceptance_date_to',
                     'txt_bid_date_from', 'txt_bid_date_to',
                     'acceptedBefore', 'bidding', 'accepting', 'resultPublishing',
                     'examinationApplicationResultInput', 'bidResultInput',
                     'prepareResultPublished', 'freeWordArray', 'contractMethodArray',
                     'proposalExecuteLocationPrefectturesArray', 'proposalBusinessArray',
                     'environmentalConsiderationArray',
                     'responsibilityRightProhibitedMatterArray',
                     'providerOrganizationArray', 'recommendId')])
            h = C._curl(C.BASE + '/cga0101/index/search', d, C.BASE + '/cga0101')
            time.sleep(1)
            m2 = re.search(r'id="token"[^>]*value="([^"]*)"', h)
            if m2:
                tok = m2.group(1)
            if '処理中断' in C.plain(h)[:40]:
                print('  **SBA9001 処理中断。送る値が足りないか、知らない値がある。**')
                print('  **入り直すこと。同じセッションで試行錯誤しない**（CLAUDE.md）')
                break
        rs = rows_of(h)
        if not rs:
            break
        allrows += rs
        if len(allrows) >= total or page >= 12:
            break
        page += 1
    # 重複を落とす（**案件名を切り詰めない**）
    seen, uniq = set(), []
    for r in allrows:
        k = (r['案件名'], r['提案番号'])
        if k in seen: continue
        seen.add(k); uniq.append(r)
    # **数の意味を混ぜない。**画面の「32件」は「入札参加可能な案件」の数で、
    # こちらの検索（状態の絞り込みを空にして送る）は公示前や入札準備中も返す。
    # 2026-10-13、これを「50件（32件中）」と出した。**届いていないように読める。**
    import collections as _c
    st = _c.Counter(r['ステータス'][:24] for r in uniq)
    print('検索で返った案件 %d件（画面の「入札参加可能」は %d件。'
          'こちらは状態を絞らずに送るので公示前なども入る）' % (len(uniq), total))
    for k, v in st.most_common():
        print('    %3d  %s' % (v, k))
    if not uniq:
        print('**0件。これは「無い」ではなく「読めなかった」可能性がある。入り直すこと**')

    out = os.path.join(ROOT, 'data/chancenavi_%s_%s.csv'
                       % ('kekka' if status == '1' else 'open', now.strftime('%Y%m%d')))
    with io.open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['提案番号', '案件名', '案件業種', '発注組織',
                                          '公示日', '契約方法', '受付開始', '受付締切',
                                          'ステータス'])
        w.writeheader(); w.writerows(uniq)
    print('→ %s' % out)

    # 当社領域だけを出す
    import rank
    def judge(n):
        if rank.NOISE.search(n) and not rank.NOISE_UNEI.search(n): return None
        return rank.grade(n)[0]
    sa = [(judge(r['案件名']), r) for r in uniq]
    sa = [(g, r) for g, r in sa if g in ('S', 'A')]
    print('\n■ 当社領域（S または A） %d件' % len(sa))
    for g, r in sa:
        print('  [%s] %s' % (g, r['案件名'][:62]))
        print('       %s ／ %s ／ 締切 %s ／ 提案番号 %s'
              % (r['発注組織'][:28], r['契約方法'][:16], r['受付締切'] or '未取得', r['提案番号']))
    print('\n■ 発注組織の内訳')
    import collections
    for k, v in collections.Counter(r['発注組織'] for r in uniq).most_common():
        print('  %3d  %s' % (v, k[:48]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
