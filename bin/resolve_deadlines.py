# -*- coding: utf-8 -*-
"""締切未特定の案件を、一覧ページから個別の詳細ページまで辿って確定させる。

   前回の bin/verify_deadlines.py は URL をそのまま取得していたが、
   台帳のURLの多くは一覧ページで、その案件の詳細ページではなかった。
   一覧に案件名が載っているだけで、締切は個別ページにしか書かれていない。
   ここでは案件名と最も一致するリンクを追ってから締切を読む。"""
import csv, re, html, subprocess, urllib.parse, io
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from zoneinfo import ZoneInfo

TODAY = datetime.now(ZoneInfo('Asia/Tokyo')).date()   # CLAUDE.md: 日付は実時刻から
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
TARGET = ('要精査（締切未特定）', '要調査', '新規（締切要確認）',
          '新規（質問回答掲載済・締切要確認）', '要精査（ページ取得不可）')

# 締切を示す語。参加申込の期限が先に来る案件があるので、両方を拾って早いほうを採る
GATE = re.compile(r'参加意向申出|参加表明|参加申[込出]|参加に係る手続き|'
                  r'締切|締め切り|提出期限|申込期限|応募期限|受付期限|申請期限|'
                  r'提出期間|受付期間|必着')
# 締切ではないもの（履行期間・開催日・公告日）を弾く
NOT_GATE = re.compile(r'履行期[限間]|契約期間|業務期間|開催[日期]|会期|公告日|掲載日|'
                      r'回答|通知|審査|プレゼン|選定|開札|説明会')

def z2h(s): return s.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

def dates(t):
    out = []
    for m in re.finditer(r'令和\s*([0-9０-９元]+)\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日', t):
        y = m.group(1); y = 1 if y == '元' else int(z2h(y))
        try: out.append((m.start(), date(2018 + y, int(z2h(m.group(2))), int(z2h(m.group(3))))))
        except ValueError: pass
    for r in (r'(20[0-9０-９]{2})\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日',
              r'(20\d{2})[/\-\.](\d{1,2})[/\-\.](\d{1,2})'):
        for m in re.finditer(r, t):
            try: out.append((m.start(), date(int(z2h(m.group(1))), int(z2h(m.group(2))), int(z2h(m.group(3))))))
            except ValueError: pass
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

def norm(s):
    return re.sub(r'[\s　「」『』（）()【】・－ー\-,、。]', '', s)

def anchors(base, h):
    out = []
    for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', h, re.S | re.I):
        t = html.unescape(re.sub(r'<[^>]+>', '', m.group(2)))
        t = re.sub(r'\s+', ' ', t).strip()
        if t: out.append((t, urllib.parse.urljoin(base, m.group(1))))
    return out

def best_link(name, base, h):
    """案件名と最も重なるリンクを選ぶ。一覧ページから詳細ページへ降りるため"""
    n = norm(name)
    best, score = None, 0
    for t, u in anchors(base, h):
        tn = norm(t)
        if len(tn) < 8: continue
        # 連続一致の長さで測る（部分一致だと別案件を拾う）
        common = 0
        for size in range(min(len(n), len(tn)), 7, -1):
            if any(n[i:i+size] in tn for i in range(len(n)-size+1)):
                common = size; break
        if common > score: best, score = u, common
    return best if score >= 12 else None

def scan(text):
    """締切語の近傍にある日付のうち、最も早い将来日を採る"""
    text = re.sub(r'\s+', ' ', text)
    hits = []
    for pos, d in dates(text):
        win = text[max(0, pos - 80):pos + 30]
        if NOT_GATE.search(win): continue
        if GATE.search(win): hits.append(d)
    fut = sorted(d for d in hits if d >= TODAY)
    if fut: return fut[0], '募集中'
    if hits: return max(hits), '締切超過'
    return None, ''

def work(r):
    raw = get(r['URL'])
    if not raw: return r, None, '取得不可'
    if raw[:5] == b'%PDF-':
        d, st = scan(pdftext(raw))
        return r, d, st or '締切記載なし'
    h = raw.decode('utf-8', 'ignore')
    d, st = scan(re.sub(r'<[^>]+>', ' ', h))
    if d: return r, d, st
    # 一覧ページだった可能性。案件名に最も近いリンクへ降りる
    link = best_link(r['案件名'], r['URL'], h)
    if link and link != r['URL']:
        raw2 = get(link)
        if raw2:
            t2 = pdftext(raw2) if raw2[:5] == b'%PDF-' else re.sub(r'<[^>]+>', ' ', raw2.decode('utf-8','ignore'))
            d, st = scan(t2)
            if d: return r, d, st + '（詳細ページより）'
            # さらに募集要領PDFを見る
            if raw2[:5] != b'%PDF-':
                h2 = raw2.decode('utf-8', 'ignore')
                for p in [urllib.parse.urljoin(link, m) for m in
                          re.findall(r'href="([^"]+\.pdf[^"]*)"', h2, re.I)][:4]:
                    d, st = scan(pdftext(get(p, 28)))
                    if d: return r, d, st + '（要領PDFより）'
    return r, None, '締切記載なし'

rows = [r for r in csv.DictReader(open('data/ledger.csv')) if r['状態'] in TARGET]
print(f'対象 {len(rows)}件 / 基準日 {TODAY}\n', flush=True)
with ThreadPoolExecutor(max_workers=10) as ex:
    res = list(ex.map(work, rows))

fixed = {}
for r, d, st in res:
    mark = '●' if d and st.startswith('募集中') else ' '
    print(f"{mark} {st:22} {d or '—'}  [{r['格付']}] {r['案件名'][:46]}", flush=True)
    if d: fixed[r['URL']] = (d.isoformat(), st)

allrows = list(csv.DictReader(open('data/ledger.csv')))
n = 0
for r in allrows:
    if r['URL'] in fixed and r['状態'] in TARGET:
        d, st = fixed[r['URL']]
        r['締切'] = d
        r['状態'] = '新規（応募可）' if st.startswith('募集中') else '締切超過'
        n += 1
with open('data/ledger.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, list(allrows[0].keys())); w.writeheader(); w.writerows(allrows)
print(f'\n締切を確定 {n}件 / 対象 {len(rows)}件')
