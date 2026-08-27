# -*- coding: utf-8 -*-
"""台帳の締切が「関門（参加表明・参加申込）」か「提案書」かを検証し、**報告する**。

   公募型プロポーザルは二段構えで、先に来るのは参加表明・参加申込である。
   提案書の締切を台帳に入れていると、申込を逃した時点で応募資格を失う。

   **このスクリプトは台帳を書き換えない。** 2026-08-28、自動で書き換える版を
   作って実行したところ、公告日や前年度の日付を「参加表明締切」と誤認し、
   正しかった25件を壊した（おまつり歳時記の9/7を、公告日の8/27で上書きした）。
   ページ上の日付から締切か公告日かを機械的に見分けるのは信頼性が足りない。
   **候補を出すところまでが機械の仕事で、確定は一次資料を人が読んで行う。**"""
import csv, re, html, subprocess, urllib.parse, io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from zoneinfo import ZoneInfo

TODAY = datetime.now(ZoneInfo('Asia/Tokyo')).date()
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

# 関門（これを逃すと提案書を出せない）
GATE1 = re.compile(r'参加(意向)?(表明|申出|申込|申請)(書)?[のに]?(受付|提出)?[のを]?(期限|締切)|'
                   r'参加に係る手続き|参加希望[のを]?(申[出込])|意向申出')
# 後段（提案書・企画提案書）
GATE2 = re.compile(r'(企画)?提案書[のを]?(受付|提出)?[のを]?(期限|締切)|提案書受付締切')
# 締切とは関係のない日付
NOT_GATE = re.compile(r'履行期[限間]|契約期間|業務期間|開催[日期]|会期|公告日|掲載日|'
                      r'回答|通知|審査|プレゼン|選定委員会|開札|説明会|質問')

def z2h(s): return s.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

def dates_with_kind(t):
    t = re.sub(r'\s+', ' ', t)
    out = []
    pats = [(r'令和\s*([0-9０-９元]+)\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日', True),
            (r'(20[0-9０-９]{2})\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日', False),
            (r'(20\d{2})[/\-\.](\d{1,2})[/\-\.](\d{1,2})', False)]
    for pat, wareki in pats:
        for m in re.finditer(pat, t):
            g1 = m.group(1)
            y = (2018 + (1 if g1 == '元' else int(z2h(g1)))) if wareki else int(z2h(g1))
            try: d = date(y, int(z2h(m.group(2))), int(z2h(m.group(3))))
            except ValueError: continue
            win = t[max(0, m.start()-90):m.start()+25]
            # 「締切」「期限」「必着」が同じ窓にあることを必須にする。
            # これがないと公告日・開催日・前年度の日付を拾ってしまう
            if not re.search(r'締切|締め切り|期限|必着', win): continue
            if NOT_GATE.search(win) and not (GATE1.search(win) or GATE2.search(win)): continue
            if GATE1.search(win):   out.append(('参加表明', d))
            elif GATE2.search(win): out.append(('提案書', d))
    return out

def get(u, t=22):
    try:
        return subprocess.run(['curl','-sSL','-A',UA,'--max-time',str(t),'--compressed',u],
                              capture_output=True, timeout=t+10).stdout
    except Exception: return b''

def pdftext(b):
    try:
        from pypdf import PdfReader
        return '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(b)).pages[:15])
    except Exception: return ''

def work(r):
    raw = get(r['URL'])
    if not raw: return r, None, None, '取得不可'
    text = pdftext(raw) if raw[:5] == b'%PDF-' else re.sub(r'<[^>]+>', ' ', raw.decode('utf-8','ignore'))
    ds = [(k, d) for k, d in dates_with_kind(text) if TODAY.year - 1 <= d.year <= TODAY.year + 2]
    if not ds and raw[:5] != b'%PDF-':
        # 要領PDFまで辿る
        h = raw.decode('utf-8', 'ignore')
        for p in [urllib.parse.urljoin(r['URL'], m) for m in
                  re.findall(r'href="([^"]+\.pdf[^"]*)"', h, re.I)][:4]:
            ds = [(k, d) for k, d in dates_with_kind(pdftext(get(p, 28)))
                  if TODAY.year - 1 <= d.year <= TODAY.year + 2]
            if ds: break
    if not ds: return r, None, None, '日付なし'
    g1 = sorted([d for k, d in ds if k == '参加表明'])
    g2 = sorted([d for k, d in ds if k == '提案書'])
    gate = g1[0] if g1 else (g2[0] if g2 else None)
    kind = '参加表明' if g1 else '提案書'
    return r, gate, kind, ('一致' if r['締切'] == (gate.isoformat() if gate else '') else 'ずれ')

# 2027年国際園芸博覧会協会は bin/expo2027_schedule.py が構造化された
# スケジュール表を正しく読むので、ここでは対象外にする（誤検出の温床）
rows = [r for r in csv.DictReader(open('data/ledger.csv'))
        if r['格付'] in ('S','A') and re.match(r'\d{4}-\d{2}-\d{2}$', r['締切'] or '')
        and not r['状態'].startswith(('過年度','領域外'))
        and 'expo2027yokohama' not in r['URL']]
print(f'検証対象 {len(rows)}件 / 基準日 {TODAY}\n', flush=True)
with ThreadPoolExecutor(max_workers=10) as ex:
    res = list(ex.map(work, rows))

fix = {}
for r, gate, kind, st in res:
    if st == 'ずれ' and gate:
        old = date.fromisoformat(r['締切'])
        diff = (old - gate).days
        mark = '★' if diff > 0 else ' '   # 台帳のほうが遅い＝関門を逃す危険
        print(f"{mark} 台帳{r['締切']} → 実際{gate}（{kind}）{diff:+d}日  {r['案件名'][:44]}", flush=True)
        if diff > 0: fix[r['URL']] = (gate.isoformat(), kind)
    elif st in ('取得不可', '日付なし'):
        print(f"  {st:8} {r['案件名'][:52]}", flush=True)

print(f'\n**要確認 {len(fix)}件**（★の付いた行）')
print('台帳は書き換えていない。上の★を一次資料で確認し、')
print('本当に関門が早いものだけを手で直すこと。')
print('公告日・開催日・前年度の日付を締切と誤認する例が多い。')
with open('data/gate_audit_20260828.csv','w',newline='') as f:
    w = csv.writer(f); w.writerow(['案件名','台帳の締切','ページ上の最早日','種別','URL'])
    for r, gate, kind, st in res:
        if st == 'ずれ' and gate:
            w.writerow([r['案件名'], r['締切'], gate.isoformat(), kind, r['URL']])
