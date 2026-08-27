# -*- coding: utf-8 -*-
"""締切を特定できなかった台帳案件を、リンク先PDFまで辿って再確認する。
   HTML本文に締切が無く、募集要領PDFにしか書かれていない案件が多いため。"""
import csv, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from zoneinfo import ZoneInfo

TODAY = datetime.now(ZoneInfo('Asia/Tokyo')).date()   # CLAUDE.md: 日付は実時刻から
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
NEAR = re.compile(r'(締切|締め切り|提出期限|申込期限|応募期限|受付[期終]|提出期間|'
                  r'参加申[込出]|参加表明|申請期限|必着|まで（必着）|期限)')
PASTYEAR = re.compile(r'20(1\d|2[0-5])|令和[2-6]年|平成\d+年|Ｒ[2-6]\.')

def z2h(s): return s.translate(str.maketrans('０１２３４５６７８９', '0123456789'))

def dates(text):
    out = []
    for m in re.finditer(r'令和\s*([0-9０-９元]+)\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日', text):
        y = m.group(1); y = 1 if y == '元' else int(z2h(y))
        try: out.append((m.start(), date(2018 + y, int(z2h(m.group(2))), int(z2h(m.group(3))))))
        except ValueError: pass
    for r in (r'(20[0-9０-９]{2})\s*年\s*([0-9０-９]+)\s*月\s*([0-9０-９]+)\s*日',
              r'(20\d{2})[/\-\.](\d{1,2})[/\-\.](\d{1,2})'):
        for m in re.finditer(r, text):
            try: out.append((m.start(), date(int(z2h(m.group(1))), int(z2h(m.group(2))), int(z2h(m.group(3))))))
            except ValueError: pass
    return out

def get(u, t=25):
    try:
        return subprocess.run(['curl', '-sSL', '-A', UA, '--max-time', str(t), '--compressed', u],
                              capture_output=True, timeout=t + 10).stdout
    except Exception: return b''

def pdftext(b):
    try:
        import io
        from pypdf import PdfReader
        return '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(b)).pages[:12])
    except Exception: return ''

def scan(text):
    """締切語の近傍にある将来日付のうち最も早いものを採る"""
    text = re.sub(r'\s+', ' ', text)
    hit = []
    for pos, d in dates(text):
        if not (TODAY.year - 1 <= d.year <= TODAY.year + 2): continue
        if NEAR.search(text[max(0, pos - 70):pos + 30]): hit.append(d)
    fut = sorted(d for d in hit if d >= TODAY)
    return (fut[0], '募集中') if fut else ((max(hit), '締切超過') if hit else (None, ''))

def work(r):
    raw = get(r['URL'])
    if not raw: return r, None, '取得不可'
    if raw[:5] == b'%PDF-': text = pdftext(raw)
    else: text = re.sub(r'<[^>]+>', ' ', raw.decode('utf-8', 'ignore'))
    d, st = scan(text)
    if d: return r, d, st
    # HTMLに無ければ、リンクされた募集要領PDFを最大3本まで見る
    if raw[:5] != b'%PDF-':
        import urllib.parse
        html = raw.decode('utf-8', 'ignore')
        pdfs = [urllib.parse.urljoin(r['URL'], m) for m in
                re.findall(r'href="([^"]+\.pdf[^"]*)"', html, re.I)][:3]
        for p in pdfs:
            t = pdftext(get(p, 30))
            if not t: continue
            d, st = scan(t)
            if d: return r, d, st + '（要領PDFより）'
    return r, None, '締切記載なし'

rows = [r for r in csv.DictReader(open('data/ledger.csv'))
        if r['締切'] in ('未確認', '') or r['状態'].startswith('要精査')]
print(f'対象 {len(rows)}件 / 基準日 {TODAY}', flush=True)
with ThreadPoolExecutor(max_workers=10) as ex:
    res = list(ex.map(work, rows))

fixed = {}
for r, d, st in res:
    if d: fixed[r['URL']] = (d.isoformat(), st)
    print(f"  {st:20} {d or '—'}  {r['案件名'][:44]}", flush=True)

allrows = list(csv.DictReader(open('data/ledger.csv')))
n = 0
for r in allrows:
    if r['URL'] in fixed:
        d, st = fixed[r['URL']]
        # 過年度アーカイブの日付を「募集中」と誤認しないよう、案件名で二重に判定する
        if PASTYEAR.search(r['案件名']) and st.startswith('締切超過'):
            r['締切'], r['状態'] = d, '過年度実績（次回公告を待つ）'
        else:
            r['締切'] = d
            r['状態'] = '新規（応募可）' if st.startswith('募集中') else '締切超過'
        n += 1
with open('data/ledger.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, list(allrows[0].keys())); w.writeheader(); w.writerows(allrows)
print(f'締切を特定 {n}件 / 対象 {len(rows)}件')
