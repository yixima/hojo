#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""おまつり歳時記 参加意向申出の送付状（郵送用）を作る。

送付状は協会の指定様式ではない（要領に定めがない）。日本の商慣行として、
郵送時に同封書類の内訳を示すために添える。持参する場合は不要。
"""
import argparse
import os

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

OUT = 'docs/omatsuri/submit/omatsuri_00_soufujo.docx'
ADDRESS = '〒150-0001　東京都渋谷区神宮前6-18-10　海老名ビル4F'
NAME = '一般社団法人ジャパンプロモーション'
REPRESENTATIVE = '代表理事　生島　儀尊'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default='2026-09-04')
    ap.add_argument('--tanto-shozoku', default='')
    ap.add_argument('--tanto-name', default='')
    ap.add_argument('--tanto-tel', default='')
    ap.add_argument('--tanto-mail', default='')
    a = ap.parse_args()
    y, m, d = (int(v) for v in a.date.split('-'))

    doc = docx.Document()
    st = doc.styles['Normal']
    st.font.name = 'MS Mincho'
    st.font.size = Pt(11)
    st.element.rPr.rFonts.set(docx.oxml.ns.qn('w:eastAsia'), 'ＭＳ 明朝')

    def p(text='', align=None, space_after=6):
        par = doc.add_paragraph(text)
        if align is not None:
            par.alignment = align
        par.paragraph_format.space_after = Pt(space_after)
        return par

    R, C = WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.CENTER
    p(f'{y}年{m}月{d}日', R)
    p()
    p('公益社団法人２０２７年国際園芸博覧会協会')
    p('行催事部　行催事課　御中')
    p()
    p(ADDRESS, R)
    p(NAME, R)
    p(REPRESENTATIVE + '　　　　印', R)
    # 差出人が代表者本人のときは「担当」行を重ねない（同じ名前が2行続くのを避ける）
    if a.tanto_name and a.tanto_name.replace('　', '') != REPRESENTATIVE.replace('　', ''):
        p(f'担当　{a.tanto_shozoku}　{a.tanto_name}'.strip(), R)
    if a.tanto_tel or a.tanto_mail:
        p(f'電話　{a.tanto_tel}　E-mail　{a.tanto_mail}'.strip(), R)
    p()
    p('２０２７年国際園芸博覧会 主催者催事「おまつり歳時記プロジェクト（仮）」に', C)
    p('かかる実施計画作成業務委託　参加意向申出書等の送付について', C)
    p()
    p('　拝啓　時下ますますご清栄のこととお慶び申し上げます。')
    p('　このたび、標記公募型プロポーザルにつきまして、下記のとおり参加意向申出書等を'
      '送付いたします。ご査収のほどよろしくお願い申し上げます。')
    p('　なお、業務説明資料の提供につきましても、参考様式10－1を同封いたしましたので、'
      '併せてご高配を賜りますようお願い申し上げます。')
    p('敬具', R)
    p()
    p('記', C)
    p()
    p('１．参加意向申出書（第１号様式）　　　　　　　　　　　　　　　　　　１部')
    p('２．誓約書（参考様式１）　　　　　　　　　　　　　　　　　　　　　　１部')
    p('３．業務実績を証明する書類（契約書の写し）　　　　　　　　　　　　　１部')
    p('４．業務説明資料提供申込書 兼 守秘義務誓約書（参考様式１０－１）　　１部')
    p()
    p('以上', R)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)

    # 目視検証（§7-7）
    chk = docx.Document(OUT)
    text = '\n'.join(q.text for q in chk.paragraphs)
    for must in [NAME, '参加意向申出書（第１号様式）', '参考様式１０－１', f'{y}年{m}月{d}日']:
        assert must in text, f'差し込めていない: {must}'
    print('OK  ' + OUT)


if __name__ == '__main__':
    main()
