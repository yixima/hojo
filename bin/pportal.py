# -*- coding: utf-8 -*-
"""調達ポータル（p-portal）の調達情報検索。
   curl では「不正な操作が行われました」で弾かれる。セッションと画面遷移を
   厳密に検証しているため、実ブラウザ（Chromium）で操作する。"""
import sys, os, csv, re, time
from playwright.sync_api import sync_playwright

TOP  = 'https://www.p-portal.go.jp/pps-web-biz/UAA01/OAA0101'
EXE  = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
KEYWORDS = ['展示会', 'ブース', '装飾', '出展', '博覧会', '見本市', 'パビリオン',
            '海外展開', '販路開拓', 'プロモーション', '伝統的工芸品', '物産',
            '会場設営', 'イベント', '情報発信', 'インバウンド']

def harvest(page, kw):
    page.goto(TOP, wait_until='domcontentloaded', timeout=60000)
    page.fill('input[name="searchConditionBean.articleNm"]', kw)
    # 入札公告・資料提出招請・意見招請を全て対象にする
    for name, val in [('procurementClaBidNotice', '01'), ('procurementClaBidNotice', '02'),
                      ('requestSubmissionMaterials', '03'), ('requestComment', '04')]:
        sel = f'input[name="searchConditionBean.procurementClaBean.{name}"][value="{val}"]'
        try:
            if page.locator(sel).count(): page.check(sel, timeout=3000)
        except Exception: pass
    page.click('input[name="OAA0102"], button[name="OAA0102"]')
    page.wait_for_load_state('domcontentloaded', timeout=60000)
    time.sleep(1.5)
    rows, seen = [], set()
    while True:
        for tr in page.locator('table tr').all():
            cells = [c.strip() for c in tr.inner_text().split('\t') if c.strip()]
            if len(cells) < 3: continue
            line = ' / '.join(cells)
            if len(line) < 20 or line in seen: continue
            seen.add(line)
            link = tr.locator('a').first
            href = link.get_attribute('href') if link.count() else ''
            rows.append((kw, line[:400], href or TOP))
        nxt = page.locator('a:has-text("次へ"), input[value="次へ"]').first
        if not nxt.count(): break
        try:
            nxt.click(timeout=5000); page.wait_for_load_state('domcontentloaded', timeout=40000); time.sleep(1)
        except Exception: break
    return rows

def main():
    out = []
    with sync_playwright() as pw:
        # 送信はエージェントプロキシ経由。Chromium は環境変数を自動では読まない
        # Playwright の headless=True（headless_shell）はこの環境のプロキシと
        # TLSハンドシェイクできない。--headless=new を引数で渡すと通る。
        proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        args = ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage',
                '--disable-gpu', '--ignore-certificate-errors']
        if proxy: args.append(f'--proxy-server={proxy}')
        br = pw.chromium.launch(executable_path=EXE, headless=False, args=args)
        ctx = br.new_context(locale='ja-JP', ignore_https_errors=True,
                             user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                                        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36')
        page = ctx.new_page()
        for kw in KEYWORDS:
            try:
                r = harvest(page, kw)
            except Exception as e:
                print(f'{kw}: エラー {type(e).__name__}', flush=True); r = []
            print(f'{kw}: {len(r)}件', flush=True)
            out += r
        br.close()
    seen, uq = set(), []
    for r in out:
        k = r[1][:100]
        if k in seen: continue
        seen.add(k); uq.append(r)
    with open('data/pportal_20260827.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['検索語', '案件', 'URL']); w.writerows(uq)
    print(f'合計 {len(uq)}件（重複除去後）')

if __name__ == '__main__':
    main()
