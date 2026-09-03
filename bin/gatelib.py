# -*- coding: utf-8 -*-
"""公募ページの本文から「どの関門が、いつ閉まるか」を取り出す。

なぜ独立させたか
----------------
2026-09-04、**この処理の窓の向きが逆だったために、福島県の案件で
本当の関門（参加申込 9/1 正午）を捨て、その3日後の企画提案書の締切（9/4 正午）を
「参加申込」と誤ってラベル付けした。**台帳もその誤りのまま作られ、
検査スクリプトは「一致」と報告した。**誤りが誤りと一致していた。**

原因は単純である。**日本語のスケジュール表は「日付 → ラベル」の順に書かれる。**

    令和8年9月 1日（火）正午まで  参加申込書の提出期限
    令和8年9月 4日（金）正午まで  企画提案書の提出期限

ところが旧実装は日付の**後方90字・前方25字**を見ていた。
前方25字では「参加申込書の提出」までしか届かず「期限」が入らないので 9/1 は捨てられ、
9/4 の後方窓には**前の行の**「参加申込書の提出期限」が入るので 9/4 が参加申込になった。
**表を平文に潰したうえで距離で対応づけると、ラベルは1行ずつずれる。**

**根本原因は「距離で対応づけたこと」ではなく、「行構造を壊したこと」である。**
表の1行は「1つの日付と1つのラベル」という組であり、その組を作っているのは
行の境界であって、文字数の近さではない。旧実装は `<[^>]+>` を空白に置換して
行の境界を消したうえで、消えた境界を距離で推定し直そうとしていた。

したがってここでは、**まず行を復元する**（`html_to_lines`）。
1行に日付が1つなら、その行のラベルがその日付のラベルである。曖昧さは無い。
1行に日付が複数あるとき（前置き型が1行に並ぶ、期間の「AからBまで」）に限り、
行の中だけで前後を見て、**その行でどちら向きの方が多く解けるか**で向きを決める。

そして **ラベルが読めなかった日付を黙って捨てない。** kind='不明' として必ず返す。
捨てると「不一致の証拠が無い」が「一致」に化ける（フェイルセーフの向きが逆になる）。
"""
import datetime
import re

# 関門。**これを逃すと後段に進めない**
GATE1 = re.compile(r'参加(意向)?(表明|申出|申込|申請|希望)|意向申出|参加に係る手続|'
                   r'参加表明書|申込書[のを]?(提出)?')
# 後段
GATE2 = re.compile(r'(企画)?提案書|企画書|見積書|入札書|応募書類|申請書')
# 締切ではない日付
NOT_GATE = re.compile(r'履行期[限間]|契約期間|業務期間|開催[日期]|会期|公告|掲載|公表|'
                      r'回答|通知|審査|プレゼン|選定|開札|説明会|質問|結果|締結|開始')
# 期限であることを示す語
LIMIT = re.compile(r'締切|締め切り|期限|必着|まで|迄')

Z2H = str.maketrans('０１２３４５６７８９', '0123456789')

DATE_PATS = [
    (re.compile(r'令和\s*([0-9０-９]+|元)\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日'), 'wareki'),
    (re.compile(r'(20[0-9０-９]{2})\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日'), 'seireki'),
    (re.compile(r'(20\d{2})[/\-.](\d{1,2})[/\-.](\d{1,2})'), 'seireki'),
]

TIME_PATS = [
    (re.compile(r'正午'), lambda m: datetime.time(12, 0)),
    (re.compile(r'(\d{1,2})\s*[:：]\s*(\d{2})'), lambda m: datetime.time(int(m[1]), int(m[2]))),
    (re.compile(r'午前\s*([0-9０-９]{1,2})\s*時(?:\s*([0-9０-９]{1,2})\s*分)?'),
     lambda m: datetime.time(int(m[1].translate(Z2H)) % 12,
                             int((m[2] or '0').translate(Z2H)))),
    (re.compile(r'午後\s*([0-9０-９]{1,2})\s*時(?:\s*([0-9０-９]{1,2})\s*分)?'),
     lambda m: datetime.time(int(m[1].translate(Z2H)) % 12 + 12,
                             int((m[2] or '0').translate(Z2H)))),
    (re.compile(r'([0-9０-９]{1,2})\s*時(?:\s*([0-9０-９]{1,2})\s*分)?'),
     lambda m: datetime.time(int(m[1].translate(Z2H)),
                             int((m[2] or '0').translate(Z2H)))),
]


BLOCK = re.compile(r'</(tr|p|div|li|h[1-6]|dt|dd|table|caption)>|<br\s*/?>|</t[dh]>\s*</tr>',
                   re.I)


def html_to_lines(raw):
    """HTMLを**行の集まり**に変える。

    **`<[^>]+>` を空白に置換してはならない。**表の行境界が消え、
    どのラベルがどの日付のものかが判別できなくなる（2026-09-04 の事故）。
    """
    b = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', raw, flags=re.S | re.I)
    b = BLOCK.sub('\n', b)
    b = re.sub(r'</t[dh]>', ' \t ', b, flags=re.I)   # セル境界は行内の区切りに留める
    b = re.sub(r'<[^>]+>', ' ', b)
    return b


def normalize(text):
    """実体参照と横方向の空白だけを潰す。**改行は残す。行が意味を持つ。**"""
    t = text.replace('&nbsp;', ' ').replace('\u3000', ' ')
    t = re.sub(r'&[a-z]+;', ' ', t)
    t = re.sub(r'[ \t\r]+', ' ', t)
    return re.sub(r'\n\s*\n+', '\n', t)


def find_dates(t):
    """本文中の日付を、重複を除いて出現順に返す。"""
    seen, out = set(), []
    for pat, era in DATE_PATS:
        for m in pat.finditer(t):
            g1 = m.group(1)
            try:
                y = (2018 + (1 if g1 == '元' else int(g1.translate(Z2H)))) if era == 'wareki' \
                    else int(g1.translate(Z2H))
                d = datetime.date(y, int(m.group(2).translate(Z2H)),
                                  int(m.group(3).translate(Z2H)))
            except ValueError:
                continue
            if m.start() in seen:
                continue
            seen.add(m.start())
            out.append((m.start(), m.end(), d))
    out.sort()
    keep = []
    for s, e, d in out:
        if keep and s < keep[-1][1]:
            continue
        keep.append((s, e, d))
    return keep


def _classify(seg):
    """1つの区間から関門の種別を読む。**期限を示す語が無ければ締切ではない。**"""
    if not seg or not LIMIT.search(seg):
        return None
    g1, g2, ng = GATE1.search(seg), GATE2.search(seg), NOT_GATE.search(seg)
    if ng and not (g1 or g2):
        return None
    if g1 and (not g2 or g1.start() < g2.start()):
        # **「参加申込」と「開催」が同じ行にあるときは、関門ではない方を優先して捨てる**
        return None if (ng and ng.start() < g1.start()) else '参加申込'
    if g2:
        return None if (ng and ng.start() < g2.start()) else '提案書'
    if ng:
        return None
    return '期限'


def _time_in(seg):
    for pat, fn in TIME_PATS:
        m = pat.search(seg)
        if m:
            try:
                return fn(m)
            except ValueError:
                continue
    return None


def _line_gates(line, fwd, back):
    """1行を [(種別, 日付, 時刻, 抜粋)] にする。**行が1レコードである。**"""
    ds = find_dates(line)
    if not ds:
        return []
    if len(ds) == 1:
        s, e, d = ds[0]
        return [(_classify(line) or '不明', d, _time_in(line), line.strip()[:70])]

    # 1行に日付が複数ある。行の中だけで前後を切り、**どちら向きが多く解けるか**で決める
    segs = []
    for i, (s, e, d) in enumerate(ds):
        nxt = ds[i + 1][0] if i + 1 < len(ds) else len(line)
        prv = ds[i - 1][1] if i else 0
        segs.append((d, line[e:min(nxt, e + fwd)], line[max(prv, s - back):s], line[s:e]))
    f = [_classify(a) for _, a, _, _ in segs]
    b = [_classify(c) for _, _, c, _ in segs]
    use_fwd = sum(x is not None for x in f) >= sum(x is not None for x in b)
    out = []
    for i, (d, a, c, raw) in enumerate(segs):
        kind = (f[i] if use_fwd else b[i]) or '不明'
        out.append((kind, d, _time_in(a) or _time_in(c), (raw + ' ' + (a if use_fwd else c)).strip()[:70]))
    return out


def extract_gates(text, fwd=140, back=60):
    """[(種別, 日付, 時刻 or None, 抜粋), ...] を返す。

    **種別が読めなかった日付も '不明' として返す。捨てない。**
    捨てると「不一致の証拠が無い」が「一致」に化ける（フェイルセーフの向きが逆になる）。
    """
    out = []
    for line in normalize(text).split('\n'):
        out += _line_gates(line, fwd, back)
    return out


def earliest_gate(gates, today=None):
    """**関門（参加申込）を最優先で返す。**無ければ提案書、それも無ければ期限。

    戻り値 (種別, 日付, 時刻)。判定できないときは (None, None, None)。
    """
    if today:
        gates = [g for g in gates if g[1] >= today]
    for kind in ('参加申込', '提案書', '期限'):
        c = sorted([g for g in gates if g[0] == kind], key=lambda g: g[1])
        if c:
            return c[0][0], c[0][1], c[0][2]
    return None, None, None
