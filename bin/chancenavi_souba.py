# -*- coding: utf-8 -*-
"""ビジネスチャンス・ナビの「結果公表済み」から**落札額の相場**を作る。

なぜ要るのか
------------
東京都の外郭団体等の案件は、**予定価格をほぼ全部「非公表」にしている。**
公社も都産技研も、仕様書を最後まで読んでも金額が1字も書かれていない。
金額が分からなければ、**出すべきか・いくらで出すかが決められない。**

どこに書いてあるのか（2026-10-16 判明）
--------------------------------------
案件（詳細）の「公表結果」に **`入札経過調書`（様式7）** が付いている。
ここに **落札者氏名・落札金額（税込）・全入札者の入札金額** が載っている。
例＝東京ケアウィーク'26 出展に係る企画運営・装飾業務委託（都産技研）
    落札 株式会社日広通信社 3,382,720円（税込）／入札8者／
    入札額（税抜）3,075,200〜8,250,000円。**最低札が落札している。**

**仕様書に金額が無いことは、金額が分からないことと同じではなかった。**
終わった案件の経過調書に、同型の案件の相場がそのまま書いてある。

使い方
------
    python3 bin/chancenavi_souba.py            # 当社領域（S/A）だけ
    python3 bin/chancenavi_souba.py --all      # 全件（重い）
    python3 bin/chancenavi_souba.py --limit 10

環境変数 `CN_USER` / `CN_PASS` が要る。**リポジトリには絶対に書かない。**
"""
import csv
import datetime
import io
import os
import re
import sys
import time
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'bin'))
import chancenavi as C          # noqa: E402
import rank                      # noqa: E402

JST = ZoneInfo('Asia/Tokyo')
# **経過調書のファイル名は発注者ごとに違う。**都産技研は「入札経過調書」、
# 公社は「入札（見積）経過調書」「経過調書」など。広めに取る。
CHOSHO = re.compile(r'経過調書|開札|落札者?(の)?(決定|公表)|入札結果')
YEN = re.compile(r'([0-9０-９][0-9０-９,，]{2,})\s*円')
# 法人名の冠。**落札者の氏名はこれを必須にして取る**（見出しの残りを拾わないため）
# 3桁区切りのカンマがある数だけを金額として採る（日付・番号を拾わないため）
AMOUNT = r'(?<![0-9,])([0-9]{1,3}(?:,[0-9]{3})+)(?![0-9,])'
CORP = (r'(?:株式会社|有限会社|合同会社|合名会社|合資会社|'
        r'\(株\)|（株）|\(有\)|（有）|\(同\)|（同）|\(財\)|（財）|\(一財\)|（一財）|'
        r'一般社団法人|公益社団法人|一般財団法人|公益財団法人|'
        r'協同組合|企業組合|協業組合|特定非営利活動法人|'
        r'地方独立行政法人|独立行政法人)')


def money(s):
    return int(re.sub(r'[,，]', '', s.translate(str.maketrans('０１２３４５６７８９',
                                                             '0123456789'))))


def read_chosho(path):
    """経過調書から（落札者, 落札金額(税込), 入札額の件数, 入札額の並び, 失敗の理由）。

    **書式は発注者ごとに違う。1つの型だけ見ていると「読めない」で終わる。**
    2026-10-16 に実測した4つの型：
      ・都産技研（様式7）＝「3,382,720円（うち消費税及び地方消費税 307,520円）」
      ・東京都公立大学法人＝「落 札 者 氏 名 株式会社コイヌマ ¥26,235,000」。
        **円ではなく ¥ で、ラベルの文字の間に空白が入る。**
      ・東京都農林水産振興財団＝「落札者名 TSP東日本株式会社 落札金額 5,698,000」。
        **金額に円も ¥ も付かない。法人名の「株式会社」が後ろに付く。**
      ・東京都立病院機構＝「落札金額 \\11,550,000-」。
        **pypdf は ¥ を「\\」として取り出す。**
    **金額は3桁区切りのカンマがある数だけを採る。**日付や番号を金額と間違えないため。
    **読めなかったら空で返す。推測で埋めない。**
    """
    try:
        from pypdf import PdfReader
        t = '\n'.join(p.extract_text() or '' for p in PdfReader(path).pages)
    except Exception as e:
        return ('', 0, 0, [], '調書を開けない（%s）' % type(e).__name__, '')
    return parse_chosho(t)


def parse_chosho(t):
    """調書の**本文（文字列）**から読む。PDFを作らずに回帰テストできるよう分けてある。"""
    t = t.translate(str.maketrans('０１２３４５６７８９，￥', '0123456789,\u00a5'))
    t = t.replace('\\', '\u00a5')          # pypdf は ¥ を「\」として出す
    z = re.sub(r'[ \u3000\t]', '', t)      # 「落 札 者 氏 名」→「落札者氏名」

    def amts(x):
        return [money(m) for m in re.findall(AMOUNT, x)]

    # **消費税額は1つではない。**「うち消費税及び地方消費税額」が行をまたいで
    # 分かれて出る書式がある（東京都農林水産振興財団）。見つかった候補は全部除く。
    taxes = set()
    for pat in (r'うち消費税[^0-9]{0,40}?' + AMOUNT,
                r'地方消費税(?:額)?[^0-9]{0,24}?' + AMOUNT,
                r'消費税(?:額|相当額)[^0-9]{0,16}?' + AMOUNT):
        for m in re.finditer(pat, z):
            taxes.add(money(m.group(1)))
    tax = min(taxes) if taxes else 0
    win, zei = 0, ''
    m = (re.search(AMOUNT + r'円?[-\u00a5]?[（(]?うち消費税', z)
         or re.search(r'落札(?:金額|価格)[^0-9]{0,24}?' + AMOUNT, z)
         or re.search(r'落札者(?:氏)?名?[^0-9]{0,40}?' + AMOUNT, z))
    if m:
        win, zei = money(m.group(1)), '税込'
    if not win:
        # **入札ではなくプロポーザルの「審査委員会 実施報告書」という別の書類がある。**
        # 2026-10-16 実測（東京都福祉保健財団）。落札額ではなく
        # 「６ 見積金額 ３５，４７０，０００円（税抜）」と**税抜**で書かれ、
        # 入札額の並びは無く、代わりに**評価点**が載る。
        # **「調書が読めない」で捨てていたら、プロポーザルの相場は永久に出なかった。**
        # **「決定金額」という書式もある**（一般財団法人GovTech東京の経過調書。
        # 「決定業者 決定金額（税抜） 株式会社第一文眞堂 … 34,580,000円」）。
        # **ラベルの語は発注者ごとに違う。落札・決定・契約・見積・委託を全部見る。**
        # 間に住所が入る（「東京都足立区江北２丁目４番２７号」→ 数字になる）ので
        # **数字で止めず、長さで区切る。**金額は3桁区切りのカンマがある数だけ採るので
        # 住所の番地を金額と間違えることはない。
        m = re.search(r'(?:見積|契約|委託|決定)(?:金額|料|価格)[\s\S]{0,80}?' + AMOUNT, z)
        if m:
            win = money(m.group(1))
            # **改行をまたいで「（税抜）」が来る。**`[^。\n]` で止めると
            # 2026-10-16 のように「区分不明」になる。税区分は金額の意味を変える
            zei = ('税抜' if re.search(r'(?:見積|契約|委託|決定)(?:金額|料|価格)[^。]{0,40}税抜', z)
                   else ('税込' if re.search(r'(?:見積|契約|委託|決定)(?:金額|料|価格)[^。]{0,40}税込', z)
                         else '区分不明'))
    # 落札者＝**法人名の冠か、後ろに付く「株式会社」等で取る。**
    # 2026-10-16、冠を任意にしていたため見出しの残り「者氏名」を落札者として出した。
    # **名前を取り違える道具は、黙っている道具より悪い。**
    # **不調・中止は「読めない」ではない。結果である。**
    # 2026-10-16（東京都立大学）：「落札者氏名 契約不調 契約不調／
    # 予定価格内での応札がなかったため、不調とする。」
    # **これを「読めない」に混ぜると、相場の母数が狂う。**
    if re.search(r'落札者?氏?名?[：:]?(?:契約)?不調|不調とする|'
                 r'応札がなかった|入札者がなかった|取りやめ|入札中止', z):
        bids0 = sorted(set(a for a in amts(z) if a >= 10000))
        return ('', 0, len(bids0), bids0[:12], '**契約不調（落札者なし）。読めないのではない**', '')

    who = ''
    for pat in (r'落札者(?:氏)?名?[：:]?(' + CORP + r'[^\s\n、。\u00a50-9]{1,30})',
                r'落札者(?:氏)?名?[：:]?([^\s\n、。\u00a50-9]{2,30}?' + CORP + r')',
                r'落札(' + CORP + r'[^\s\n、。\u00a50-9]{1,30})',
                # プロポーザルの実施報告書＝「○○の提案が最も優れていると判断された」
                r'(' + CORP + r'[^\s\n、。\u00a50-9]{1,30})の提案が',
                r'([^\s\n、。\u00a50-9]{2,30}?' + CORP + r')の提案が',
                r'決定業者[^0-9]{0,40}?(' + CORP + r'[^\s\n、。\u00a50-9]{1,30})',
                r'決定業者[^0-9]{0,40}?([^\s\n、。\u00a50-9]{2,30}?' + CORP + r')',
                # **様式7は、ラベルを先に全部並べて値を後に出す。**
                # 「落札者氏名」の直後に名前が来ない。入札者の一覧で
                # 「<法人名> 落札」「<法人名> 2,680,000 落札」と並ぶほうが確実である。
                r'(' + CORP + r'[^\s\n、。\u00a50-9]{1,30})'
                r'\s*(?:[\u00a50-9,]+円?\s*)?落札',
                r'([^\s\n、。\u00a50-9]{2,30}?' + CORP + r')'
                r'\s*(?:[\u00a50-9,]+円?\s*)?落札'):
        m = re.search(pat, z)
        if m:
            who = m.group(1).strip()
            # **後ろに続く見出しを名前に含めない。**2026-10-16、
            # 「株式会社ツクルス落札金額」を落札者として出した。
            for cut in ('落札', '金額', '価格', '入札', 'うち', '住所', '様式',
                        '記事', '備考', '（', '(', '第'):
                i = who.find(cut)
                if i > 1:
                    who = who[:i]
            who = who.strip()
            # **冠だけ・短すぎるものは氏名ではない。**2026-10-16、
            # 「株式会社」だけを落札者として出した（住所の数字で切れていた）
            if len(who) < 4 or re.fullmatch(CORP, who):
                who = ''
                continue
            break
    # 入札額の並び＝調書に出る金額のうち、落札金額（税込）と消費税額を除いたもの。
    # **これが入札者の数である。**落札者の入札額もこの中に入る（税抜で書かれる）。
    allamt = sorted(set(a for a in amts(z) if a >= 10000))
    # ── 整合の検査：**落札金額（税込）は、どれかの入札額（税抜）の1.1倍である。**
    # 2026-10-16 実測の事故：(一財)東京都人材支援事業団の調書は
    # 「落札者氏名 落札金額 ¥268,000」と出るが、**268,000円は消費税相当額**で、
    # 本当の落札金額は ¥2,948,000（＝最低札 2,680,000 × 1.1）だった。
    # PDFの文字の並び順がラベルと値を取り違えさせる。
    # **税込金額が最低入札額より小さいことは、ありえない。**そこで気づける。
    # 落札者が最低札とは限らない（総合評価方式）ので、
    # **「最低札×1.1」と決め打ちせず、どれかの入札額の1.1倍を探す。**
    def consistent(v):
        return [b for b in allamt if b != v and int(b * 1.1) == v]
    note = ''
    # **自分自身を除いた他の金額と比べる。**2026-10-16、allamt に落札金額そのものが
    # 入っているため min() が落札金額になり、**検査が一度も鳴らなかった。**
    others = [a for a in allamt if a != win]
    # **プロポーザル（見積金額・税抜）には入札額の並びが無い。**検査は入札だけ
    # **不課税・非課税の案件がある。**2026-10-16（都産技研 Singapore Airshow 2026）：
    # 「落札金額（税込）3,172,237円（不課税）」で、入札額と同額である。
    # 1.1倍の検査をかけると**正しい値を「読めない」と言ってしまう。**
    hikazei = bool(re.search(r'不課税|非課税', z))
    if zei == '税込' and not hikazei and win and others and win < min(others):
        cands = [v for v in allamt if consistent(v)]
        if len(cands) == 1:
            note = ('落札金額を %s円 → %s円 に訂正した'
                    '（調書の「落札金額」の直後に消費税相当額が並んでいた）'
                    % ('{:,}'.format(win), '{:,}'.format(cands[0])))
            win = cands[0]
        else:
            return (who, 0, len(allamt), allamt[:12],
                    '**落札金額（%s円）が最低入札額（%s円）より小さい。'
                    '消費税額を拾った疑いがあり、訂正先を一つに絞れない**'
                    % ('{:,}'.format(win), '{:,}'.format(min(others))), zei)
    if zei == '税込' and not hikazei and win and others and not consistent(win):
        note = (note + '／' if note else '') + \
            '**どの入札額の1.1倍にも一致しない。書式が未知か、辞退・不参が混じっている**'
    bids = [a for a in allamt if a != win and a not in taxes]
    if not win:
        return (who, 0, len(bids), bids[:12], '調書から金額を読めない', zei)
    # **氏名が取れないときは、落札金額のすぐ前に並ぶ法人名を拾う。**
    # 2026-10-16（人材支援事業団）：ラベルと値の並び順が崩れており、
    # 「(株)ブレインワークス ¥2,948,000」として金額の直前に出ていた。
    if not who:
        m = re.search(r'(' + CORP + r'[^\s\n、。\u00a50-9]{0,30})\u00a5?'
                      + re.escape('{:,}'.format(win)), z)
        if m:
            who = m.group(1).strip()
    return (who, win, len(bids), bids[:12], note, zei)


def main():
    now = datetime.datetime.now(JST)
    print('基準日時 %s JST（実時刻）' % now.strftime('%Y-%m-%d %H:%M'))
    if not os.environ.get('CN_USER'):
        print('**CN_USER / CN_PASS が設定されていないため確認できなかった。'
              '黙って飛ばさない。**')
        return 1
    src = os.path.join(ROOT, 'data',
                       'chancenavi_kekka_%s.csv' % now.strftime('%Y%m%d'))
    if not os.path.exists(src):
        print('**%s が無い。先に `python3 bin/chancenavi_anken.py --kekka` '
              'を実行すること。**' % src)
        return 1
    rows = list(csv.DictReader(io.open(src, encoding='utf-8')))
    allf = '--all' in sys.argv
    lim = 0
    if '--limit' in sys.argv:
        lim = int(sys.argv[sys.argv.index('--limit') + 1])
    tgt = []
    for r in rows:
        g, why = ('S', '全件') if allf else rank.grade(r['案件名'])
        if allf or g in ('S', 'A'):
            tgt.append((g, why, r))
    if lim:
        tgt = tgt[:lim]
    print('対象 %d件 / 結果公表済み %d件' % (len(tgt), len(rows)))

    my, tok = C.login()
    if not tok:
        print('**ログインできなかった。**')
        return 1
    who0 = re.search(r'([^\s]+様)', C.plain(my))
    print('ログイン：%s' % (who0.group(1) if who0 else '（氏名を読めず）'))

    out, miss = [], []
    dead = 0
    for g, why, r in tgt:
        pn = r['提案番号']
        # **ナビは1回でも想定外の遷移をすると、そのセッションが即死する**
        # （SBA9001 処理中断／SBA9002 タイムアウト。CLAUDE.md）。
        # 2026-10-16 実測：1件目は読めるが、2件目から全部 SBA9002 になった。
        # cga0201 を見たあとに一覧へ戻る遷移が、そもそも許されていない。
        # **同じセッションで試行錯誤せず、1件ごとに入り直す。**
        # 遅いが、**速くて1件しか読めない道具は、読めない道具である。**
        my, tok = C.login()
        if not tok:
            dead += 1
            miss.append((pn, r['案件名'], '入り直せなかった（%d回目）' % dead))
            if dead >= 3:
                print('**3回続けて入り直せなかった。中断する。**')
                break
            time.sleep(5)
            continue
        time.sleep(1)
        # 一覧（結果公表済み）を開いてから詳細へ入る。**作法の順を飛ばさない。**
        hl = C.screen('cga0101', tok, [('status', '1')])
        ml = re.search(r'id="token"[^>]*value="([^"]*)"', hl)
        if ml:
            tok = ml.group(1)
        time.sleep(1)
        C._curl(C.BASE + '/cga0101/index/showProposalDetailInfo',
                [('token', tok), ('proposalNumber', pn)], C.BASE + '/cga0101', xhr=True)
        time.sleep(1)
        h = C._curl(C.BASE + '/cga0201', [('token', tok), ('proposalNumber', pn)],
                    C.BASE + '/cga0101')
        head = C.plain(h)[:60]
        if '中断' in head or 'タイムアウト' in head or 'エラー' in head:
            miss.append((pn, r['案件名'], '案件（詳細）が開かない（%s）' % head[:24]))
            print('  **× %s %s**' % (pn, head[:30]))
            continue
        m = re.search(r'id="token"[^>]*value="([^"]*)"', h)
        tok2 = m.group(1) if m else tok
        import html as H
        import json
        files = []
        for mm in re.finditer(r'<INPUT id="(\w*[Ff]ile\w*)" type="hidden" value="([^"]*)"', h):
            try:
                files += json.loads(H.unescape(mm.group(2)))
            except Exception:
                pass
        cand = [f for f in files if CHOSHO.search(f['name'])]
        if not cand:
            miss.append((pn, r['案件名'], '経過調書が付いていない（添付%d点）' % len(files)))
            continue
        d = os.path.join('/tmp', 'cn_souba')
        os.makedirs(d, exist_ok=True)
        f = cand[0]
        ext = os.path.splitext(f['name'])[1] or '.pdf'
        p = os.path.join(d, '%s%s' % (pn, ext))
        res = C._curl_bin(C.BASE + '/cga0201/download',
                          [('token', tok2), ('key', str(f['key'])),
                           ('index', str(f['index'])), ('flag', str(f['flag']))],
                          C.BASE + '/cga0201', p)
        sp = res.split()
        size = int(sp[2]) if len(sp) > 2 and sp[2].isdigit() else 0
        if not (sp and sp[0] == '200' and size > 1000):
            miss.append((pn, r['案件名'], '調書を落とせない（HTTP %s %dバイト）'
                         % (sp[0] if sp else '0', size)))
            continue
        who, win, n, bids, err, zei = read_chosho(p)
        if not win:
            miss.append((pn, r['案件名'], err or '調書から落札金額を読めない'))
            continue
        if err:
            # **読めたが、気になることがある。**黙って通さず、その場で出す
            print('    ▲ %s' % err)
        out.append({'提案番号': pn, '格': g, '案件名': r['案件名'],
                    '発注組織': r['発注組織'], '契約方法': r['契約方法'],
                    '受付締切': r['受付締切'], '落札者': who,
                    '落札・見積金額': win, '税区分': zei, '入札額の件数（＝入札者数）': n,
                    '入札額の並び': ' / '.join('%d' % b for b in bids),
                    '調書': f['name'], '注記': err})
        print('  ○ [%s] %s' % (g, r['案件名'][:48]))
        print('       %s  **%s円（%s）**  ほかの金額 %d件'
              % (who or '**（氏名を読めず）**', '{:,}'.format(win), zei or '区分不明', n))
        time.sleep(1)

    dst = os.path.join(ROOT, 'data', 'chancenavi_souba_%s.csv' % now.strftime('%Y%m%d'))
    if out:
        with io.open(dst, 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
            w.writeheader()
            w.writerows(out)
        print('\n→ %s（%d件）' % (dst, len(out)))
        ws = sorted(x['落札・見積金額'] for x in out)
        print('落札金額（税込）の並び：%s' % ' / '.join('{:,}'.format(x) for x in ws))
        print('中央値 **%s円**／最小 %s円／最大 %s円'
              % ('{:,}'.format(ws[len(ws) // 2]), '{:,}'.format(ws[0]),
                 '{:,}'.format(ws[-1])))
    else:
        print('\n**1件も読めなかった。「相場が無い」ではない。読めていない。**')
    if miss:
        print('\n★**読めなかった %d件。黙って飛ばさない。**' % len(miss))
        for pn, name, why in miss:
            print('    %s %s … %s' % (pn, name[:42], why))
    return 0


if __name__ == '__main__':
    sys.exit(main())
