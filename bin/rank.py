# -*- coding: utf-8 -*-
"""分母8,958件を『契約案件性』ゲート付きで再判定する。
   これまでのランキングは案件でないもの（JETRO js-links等）をSに混入させていた。"""
import csv, re, sys
from collections import Counter, defaultdict

SRC = 'data/denominator_20260827.csv'
OUT = 'data/denominator_ranked_20260827.csv'

# ---- 1) 契約案件性ゲート：発注案件・公募案件でなければ土俵に上げない -------
CONTRACT = re.compile(
    r'委託|業務|プロポーザル|企画競争|企画提案|企画競技|公募型|指名競争|一般競争|'
    r'入札|請負|調達|受託|運営者|事業者[のをに]?(募集|選定|公募)|'
    r'業務の?(委託|公募)|パートナー(募集|選定)|支援事業者|補助金|助成金|交付金')

# ---- 2) 明確なノイズ：案件でない / 応募主体が違う ------------------------
NOISE = re.compile(
    r'js-links|リンク集|サービス提供者|'
    r'セミナー|講座|研修(受講)?|説明会(の(開催|案内))?|勉強会|ウェビナー|'
    r'受講者募集|参加者募集|来場者|出展者募集|出展募集|出展者を?募集|'
    r'商談会[へに]の?参加|バイヤー招へい|'
    r'アンケート|パブリックコメント|意見公募|職員(採用|募集)|会計年度任用|'
    r'指定管理者|工事|修繕|清掃|警備|印刷製本|車両|燃料|electricity|電気の?(需給|供給)')

# ---- 3) 業種ドメイン ------------------------------------------------------
DOMAIN = {
 '展示会・出展': re.compile(r'展示会|見本市|博覧会|出展|ブース|パビリオン|EXPO|エキスポ|フェア|商談会|物産展'),
 '海外展開'    : re.compile(r'海外|国際|輸出|越境|インバウンド|外国|グローバル|ジャパン・?パビリオン|販路開拓'),
 '工芸・地域産品': re.compile(r'工芸|伝統|地場産業|特産|物産|地域産品|県産|市産|食品|農林水産物|ブランド'),
 'プロモーション': re.compile(r'プロモーション|PR|広報|情報発信|発信|シティセールス|魅力(発信|向上)|広告|認知度'),
 '観光・誘客'  : re.compile(r'観光|誘客|旅行|ツーリズム|来訪|周遊|MICE'),
 '文化・芸術'  : re.compile(r'文化|芸術|アート|音楽|舞台|映像|クリエイティ|デザイン'),
 'イベント運営': re.compile(r'イベント|催事|フェスティバル|式典|大会(の)?(運営|企画)|会場(運営|設営|装飾)'),
}

# ---- 4) 適合度：当社の中核能力との距離 ------------------------------------
KAISOTSU = re.compile(r'装飾|設営|施工|会場構成|ブース|什器|空間演出|デザイン設計')
KAIGAI   = DOMAIN['海外展開']
TENJI    = DOMAIN['展示会・出展']
KOGEI    = DOMAIN['工芸・地域産品']
PROMO    = DOMAIN['プロモーション']
EVENT    = DOMAIN['イベント運営']

def grade(name):
    """S=中核実績と直結 / A=隣接・十分応札可能 / B=関連はあるが遠い"""
    kaigai, tenji, kogei, promo, event, kaso = (bool(r.search(name)) for r in
        (KAIGAI, TENJI, KOGEI, PROMO, EVENT, KAISOTSU))
    # S: 海外×展示会 / 装飾設営そのもの / 工芸×海外
    if kaso and (tenji or event):            return 'S', '会場装飾・設営の直接発注'
    if kaigai and tenji:                     return 'S', '海外展示会・出展支援（東京手仕事M&Oと同型）'
    if kaigai and kogei:                     return 'S', '工芸・地域産品の海外展開'
    # A: 単独ドメインでも中核に隣接
    if tenji and (kogei or promo):           return 'A', '国内展示会・物産展の企画運営'
    if kaigai and promo:                     return 'A', '海外向けプロモーション'
    if event and (kogei or promo or kaigai): return 'A', 'イベント企画運営'
    if tenji or kaso:                        return 'A', '展示・出展関連'
    # B
    if kaigai or kogei or promo or event:    return 'B', '周辺領域'
    return None, ''

# ---- 5) 案件名の正規化：HTML断片・状態バッジ・重複を落とす ----------------
TAG   = re.compile(r'<[^>]*>?|&[a-z]+;')
BADGE = re.compile(r'(終了|募集終了|公募終了|受付終了|選定結果の?公表|結果[のを]?公表)\s*$')
DECO  = re.compile(r'^\s*[【\[](お知らせ|公募|募集|質問(書)?の?回答(掲載)?|ご?質問に対する回答|'
                   r'【?質問への回答を掲載しました|受託候補者を決定しました|公募終了|募集終了|'
                   r'令和\d+年\d+月\d+日掲載|企画提案公募)[】\]]\s*')
ATTACH = re.compile(r'\[(PDF|Word|Excel)ファイル[^\]]*\]|^(入札公告|入札説明書|業務仕様書|募集要項|仕様書案)（')

def clean(n):
    n = TAG.sub('', n).strip()
    for _ in range(3):
        n2 = DECO.sub('', n); n2 = BADGE.sub('', n2).strip()
        if n2 == n: break
        n = n2
    return n.strip('　 、,')

def dedup_key(org, n):
    # 年度・回次・全半角の揺れを吸収して同一案件をまとめる
    k = re.sub(r'[0-9０-９]+', '#', n)
    k = re.sub(r'令和#+年度?|平成#+年度?|第#+回', '', k)
    return (org, re.sub(r'[\s　「」『』（）()【】・－ー-]', '', k))

rows = list(csv.DictReader(open(SRC)))
out, stat, seen = [], Counter(), {}
for r in rows:
    if 'js-links' in r['URL']:  stat['除外:リンク集'] += 1; continue
    n = clean(r['案件名'])
    if not n or len(n) < 6:     stat['除外:無題'] += 1; continue
    if ATTACH.search(n):        stat['除外:添付資料'] += 1; continue
    if NOISE.search(n):        stat['除外:ノイズ'] += 1; continue
    if not CONTRACT.search(n): stat['除外:案件性なし'] += 1; continue
    g, why = grade(n)
    if not g:                  stat['除外:領域外'] += 1; continue
    key = dedup_key(r['組織'], n)
    if key in seen:
        stat['除外:重複'] += 1
        seen[key]['重複数'] = str(int(seen[key]['重複数']) + 1)
        continue
    doms = '/'.join(k for k, v in DOMAIN.items() if v.search(n))
    stat[g] += 1
    rec = {'適合度': g, '根拠': why, '組織': r['組織'], '分類': doms,
           '案件名': n, 'URL': r['URL'], '階層': r['階層'], '重複数': '1'}
    seen[key] = rec
    out.append(rec)

order = {'S': 0, 'A': 1, 'B': 2}
out.sort(key=lambda x: (order[x['適合度']], x['組織']))
with open(OUT, 'w', newline='') as f:
    w = csv.DictWriter(f, ['適合度', '根拠', '組織', '分類', '案件名', 'URL', '階層', '重複数'])
    w.writeheader(); w.writerows(out)

print('分母', len(rows), '→ 判定後', len(out))
for k, v in stat.most_common(): print(f'  {k}: {v}')
print('S組織:', Counter(r['組織'] for r in out if r['適合度']=='S').most_common(15))
