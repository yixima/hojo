#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""協会からの追加提出依頼（2026-09-07）に応じる書類を作る。

協会の依頼（原文）
  「ご提出いただいた業務実績を証明する書類では、3参加条件（2）と照査することが
   できません。3参加条件（2）と照査できる仕様書等を9/8(火)17時までに電子メールにて
   ご提出（原本は9/9(水)13時までに持参又は書留にて郵送）いただけますでしょうか。」

**「照査できない」＝どの記載が要件のどれに当たるかが読み取れない、ということである。**
仕様書を足すだけでは、同じ判断を協会にもう一度させることになる。
そこで**対照表**を当社で作り、要件を4つに分解して、どの書類のどこが当たるかを示す。

作るもの
  omatsuri_05_taishohyo.docx   業務実績と参加条件との対照表（当社作成の別紙）
  omatsuri_06_soufujo_genpon.docx  原本送付用の送付状（9/9 13時必着）
"""
import argparse
import os
import re
import subprocess
import tempfile

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

OUT = 'docs/omatsuri/submit'
ADDRESS = '〒150-0001　東京都渋谷区神宮前6-18-10　海老名ビル4F'
NAME = '一般社団法人ジャパンプロモーション'
REPRESENTATIVE = '代表理事　生島　儀尊'
PT_MM = 25.4 / 72.0

KENMEI = ('２０２７年国際園芸博覧会　主催者催事「おまつり歳時記プロジェクト（仮）」'
          'にかかる実施計画作成業務委託')
JISSEKI = '令和7年度「東京手仕事」MAISON&OBJET PARIS 2025 出展及びポップアップストア運営'

# 参加条件3(2)アを4つの要素に分解する
YOKEN = [
    ('①　発注者',
     '「国、地方公共団体、公益法人その他これらに準ずる団体が発注した」',
     '公益財団法人東京都中小企業振興公社',
     '同公社は**公益財団法人**であり、要件にいう「公益法人」に該当する。',
     '契約書（鑑）／仕様書の表紙'),
    ('②　規模',
     '「三千人以上の大規模イベントや展示会、文化芸術催事等」',
     'MAISON&OBJET PARIS（フランス・パリ ノール ヴィルパント）',
     '主催者公表によると、2025年9月開催回の来場者は**51,500人**、'
     '出展ブランドは2,125、来場者の出身国は138か国である。**三千人を大きく上回る。**',
     '【要記入】仕様書の該当箇所／主催者公表資料'),
    ('③　計画策定業務',
     '「…にかかる計画策定業務」',
     '出展計画の策定（出展区画の構成、展示計画、出品者の選定支援、広報計画 ほか）',
     '【要記入】仕様書の「業務内容」のうち、**計画の立案・策定**に当たる条項番号と文言',
     '【要記入】仕様書 第◯条／◯頁'),
    ('④　実施運営業務',
     '「および、実施運営業務の経験」',
     'ポップアップストアの運営（現地設営、接客・販売、在庫管理、撤去、報告）',
     '【要記入】仕様書の「業務内容」のうち、**現地での実施・運営**に当たる条項番号と文言',
     '【要記入】仕様書 第◯条／◯頁'),
]

TENPU = [
    '１．仕様書の写し（令和7年度「東京手仕事」MAISON&OBJET PARIS 2025'
    ' 出展及びポップアップストア運営）',
    '２．契約書の写し（9月4日提出済みのものと同一）',
    '３．【要記入】業務完了報告書の写し（来場者数の記載がある場合）',
]


def a4(doc, top=20, bottom=18, left=18, right=18):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.top_margin, sec.bottom_margin = Mm(top), Mm(bottom)
    sec.left_margin, sec.right_margin = Mm(left), Mm(right)
    st = doc.styles['Normal']
    st.font.name = 'ＭＳ 明朝'
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn('w:eastAsia'), 'ＭＳ 明朝')
    st.paragraph_format.line_spacing = 1.15
    st.paragraph_format.space_after = Pt(0)
    return 210 - left - right


def para(doc, text='', align=None, before=0, after=6, pt=None, bold=False):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    if text:
        # **…** を太字として扱う（ＭＳ明朝には太字があるので下線に逃げる必要はない）
        for i, chunk in enumerate(re.split(r'\*\*', text)):
            if not chunk:
                continue
            r = p.add_run(chunk)
            r.bold = bold or (i % 2 == 1)
            if pt:
                r.font.size = Pt(pt)
    return p


def build_taishohyo(args, out):
    doc = docx.Document()
    body_mm = a4(doc)

    para(doc, f'{args.date_y}年{args.date_m}月{args.date_d}日', WD_ALIGN_PARAGRAPH.RIGHT, after=8)
    para(doc, '業務実績と参加条件との対照表', WD_ALIGN_PARAGRAPH.CENTER, pt=14.5, bold=True, after=4)
    para(doc, f'件名：{KENMEI}', WD_ALIGN_PARAGRAPH.CENTER, pt=9.5, after=14)
    para(doc, NAME + '　' + REPRESENTATIVE, WD_ALIGN_PARAGRAPH.RIGHT, pt=10, after=10)

    para(doc, '１．対象とする業務実績', pt=11.5, bold=True, after=5)
    t = doc.add_table(rows=0, cols=2)
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    for k, v in [('件　名', JISSEKI),
                 ('発注者', '公益財団法人東京都中小企業振興公社'),
                 ('契約金額', '40,986,000円（税込）'),
                 ('履行期間', '【要記入】契約書に記載の履行期間'),
                 ('開催地・時期', 'フランス・パリ ノール ヴィルパント／2025年9月')]:
        row = t.add_row().cells
        row[0].width = Mm(26); row[1].width = Mm(body_mm - 26)
        for pp in row[0].paragraphs + row[1].paragraphs:
            pp.paragraph_format.space_after = Pt(0)
        row[0].paragraphs[0].add_run(k).bold = True
        row[1].paragraphs[0].add_run(v)
    para(doc, '', after=8)

    para(doc, '２．提案書作成要領「３ 参加条件(2)ア」との対照', pt=11.5, bold=True, after=3)
    para(doc, '要領の文言を４つの要素に分け、それぞれについて該当する書類と箇所を示します。',
         pt=9.5, after=6)

    t2 = doc.add_table(rows=1, cols=4)
    t2.style = 'Table Grid'
    hdr = t2.rows[0].cells
    widths = [20, 38, 66, 42]
    for c, (w, label) in enumerate(zip(widths, ['要素', '要領の文言', '当社実績における該当内容',
                                                '該当書類・箇所'])):
        hdr[c].width = Mm(w)
        r = hdr[c].paragraphs[0].add_run(label); r.bold = True
        hdr[c].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for label, moji, naiyo, hosoku, shorui in YOKEN:
        cells = t2.add_row().cells
        for c, w in enumerate(widths):
            cells[c].width = Mm(w)
        cells[0].paragraphs[0].add_run(label).bold = True
        cells[1].paragraphs[0].add_run(moji)
        p = cells[2].paragraphs[0]
        p.add_run(naiyo).bold = True
        cells[2].add_paragraph()
        for i, chunk in enumerate(re.split(r'\*\*', hosoku)):
            if chunk:
                rr = cells[2].paragraphs[-1].add_run(chunk); rr.bold = (i % 2 == 1)
        cells[3].paragraphs[0].add_run(shorui)
    for row in t2.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(8.5)
    para(doc, '', after=7)

    para(doc, '３．添付書類', pt=11.5, bold=True, after=4)
    for item in TENPU:
        p = para(doc, item, after=3, pt=10)
        p.paragraph_format.left_indent = Mm(6)
        p.paragraph_format.first_line_indent = Mm(-6)
        p.paragraph_format.space_after = Pt(1)
    para(doc, '（注）②の来場者数は主催者（MAISON&OBJET）の公表値によります。',
         pt=9, before=6, after=0)
    para(doc, '以上', WD_ALIGN_PARAGRAPH.RIGHT, before=2, after=0)
    doc.save(out)
    return out


def build_soufujo(args, out):
    doc = docx.Document()
    body_mm = a4(doc, top=28)
    R, C = WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.CENTER
    para(doc, f'{args.date_y}年{args.date_m}月{args.genpon_d}日', R, after=18)
    para(doc, '公益社団法人２０２７年国際園芸博覧会協会', after=0)
    para(doc, '行催事部　行催事課　御中', after=18)
    para(doc, ADDRESS, R, after=0)
    para(doc, NAME, R, after=0)
    para(doc, REPRESENTATIVE + '　　　　　　印', R, after=0)
    para(doc, '電話　03-5766-2450　E-mail　ikushima@japanpromotion.org', R, after=18)
    para(doc, KENMEI, C, after=0)
    para(doc, '業務実績を証明する書類（追加提出）の送付について', C, after=18)
    para(doc, '　拝啓　時下ますますご清栄のこととお慶び申し上げます。', after=4)
    para(doc, '　このたびは、標記公募型プロポーザルにつきまして、業務実績を証明する書類の'
              '追加提出のご連絡をいただき、ありがとうございました。', after=4)
    para(doc, '　ご指示に従い、下記のとおり原本を送付いたします。'
              'なお、同一の内容を2026年9月8日（火）に電子メールにて送信しております。'
              'ご査収のほどよろしくお願い申し上げます。', after=4)
    para(doc, '敬具', R, after=14)
    para(doc, '記', C, after=12)
    for item in TENPU:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.left_indent = Mm(6)
        p.paragraph_format.first_line_indent = Mm(-6)
        p.paragraph_format.tab_stops.add_tab_stop(Mm(body_mm - 4), WD_TAB_ALIGNMENT.RIGHT)
        p.add_run(f'{item}\t１部')
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.left_indent = Mm(6)
    p.paragraph_format.first_line_indent = Mm(-6)
    p.paragraph_format.tab_stops.add_tab_stop(Mm(body_mm - 4), WD_TAB_ALIGNMENT.RIGHT)
    p.add_run('４．業務実績と参加条件との対照表（当社作成）\t１部')
    para(doc, '', after=8)
    para(doc, '以上', R, after=0)
    doc.save(out)
    return out


def verify(paths, musts):
    env = dict(os.environ); env['HOME'] = tempfile.mkdtemp(prefix='lo-')
    tmp = tempfile.mkdtemp(prefix='verify-')
    subprocess.run(['soffice', '--headless', '--norestore', '--convert-to', 'pdf',
                    '--outdir', tmp] + list(paths), check=True, capture_output=True,
                   env=env, timeout=600)
    import pymupdf
    ng = 0
    for path, must in zip(paths, musts):
        pdf = os.path.join(tmp, os.path.splitext(os.path.basename(path))[0] + '.pdf')
        d = pymupdf.open(pdf)
        problems = []
        w = round(d[0].rect.width * PT_MM, 1); h = round(d[0].rect.height * PT_MM, 1)
        if not (abs(w - 210) < 1 and abs(h - 297) < 1):
            problems.append(f'用紙が A4 ではない（{w}×{h}mm）')
        if d.page_count != 1:
            problems.append(f'{d.page_count} ページある')
        flat = ''.join(''.join(p.get_text().split()) for p in d)
        for m in must:
            if ''.join(m.split()) not in flat:
                problems.append('本文に無い: ' + m)
        if '�' in flat:
            problems.append('文字化け（U+FFFD）がある')
        if not re.fullmatch(r'[A-Za-z0-9._-]+', os.path.basename(path)):
            problems.append('ファイル名が §7-11 に違反')
        print(('OK  ' if not problems else 'NG  ') + path)
        for p in problems:
            print('      - ' + p)
        ng += len(problems)
    print(f'    検査用 PDF: {tmp}')
    return ng


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default='2026-09-08', help='メール提出日')
    ap.add_argument('--genpon-date', default='2026-09-08', help='原本の発送日')
    args = ap.parse_args()
    y, m, d = (int(v) for v in args.date.split('-'))
    args.date_y, args.date_m, args.date_d = y, m, d
    args.genpon_d = int(args.genpon_date.split('-')[2])

    os.makedirs(OUT, exist_ok=True)
    a = build_taishohyo(args, os.path.join(OUT, 'omatsuri_05_taishohyo.docx'))
    b = build_soufujo(args, os.path.join(OUT, 'omatsuri_06_soufujo_genpon.docx'))
    ng = verify([a, b], [
        ['業務実績と参加条件との対照表', '公益財団法人東京都中小企業振興公社',
         '40,986,000円', '51,500人', '計画策定業務', '実施運営業務'],
        ['業務実績を証明する書類（追加提出）の送付について', NAME,
         '対照表', '仕様書の写し'],
    ])
    if ng:
        raise SystemExit(f'{ng} 件の不備がある。発行しない。')
    print('2件とも検査を通過した（A4・1ページ・文字化けなし）。')


if __name__ == '__main__':
    main()
