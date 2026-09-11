#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""おまつり歳時記プロポーザル 質問書（参考様式2）の素案を作る。

提出期限 2026年9月17日（木）17時／**提出はメール（word形式）・送信後に電話連絡**。
提出できるのは提案資格が認められた者のみ（9/10までに通知）。

**これは素案である。**業務説明資料（9/10前後に開示）を読むと、ここに挙げた疑義の
いくつかは解消し、逆に新しい疑義が出る。**資料を読んでから確定させること。**

質問を選ぶときの制約（提案書作成要領 5）
  「質問内容及び回答については、質問者のノウハウ等に係り、質問者の権利、競争上の
   地位その他正当な利害を害するおそれのあるものと協会が認めたものを除き、
   提案資格を満たす者であることを確認した全者に通知します。」
  → **質問は競合他社にも開示される。**こちらの提案の方向が読める質問は書かない。
    ここに並べたのは、どの応募者も等しく知りたい形式・範囲・積算の確認に限っている。

生成の仕組みと検査は tools/build_omatsuri_forms.py と同じ（セクション設定の引き継ぎ、
折り返しの自動回避、LibreOffice で描画してページ数・用紙・同一行を実測）。
"""
import argparse
import copy
import os
import sys
import tempfile

import docx
from docx.oxml.ns import qn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_omatsuri_forms import (ADDRESS, NAME, REPRESENTATIVE, SRC, OUT, TWIP_MM,
                                  append_value, body_items, governing_sectpr, jp_date,
                                  keep_range, para, render_pdf, inspect, set_indent,
                                  text_area_mm)

RANGE = (204, 227)          # 参考様式2（227 は参考様式3の見出し）
OUTFILE = os.path.join(OUT, 'omatsuri_04_shitsumonsho.docx')

QUESTIONS = [
    ('参加条件３(2)イ及び提案書評価基準の②にいう「国際博覧会」の範囲について、'
     '博覧会国際事務局（ＢＩＥ）が認定する博覧会に限られるか、'
     '国際的な文化見本市・フェスティバル等を含むか、ご教示ください。'),
    ('参加条件３(2)アの「三千人以上」について、催事の会期全体の延べ来場者数と'
     '単日の来場者数のいずれで判断されるか、ご教示ください。'),
    ('提案書作成要領６(3)イの「管理技術者は、参加企業に所属していること」について、'
     '雇用契約による者に限られるか、常時業務に従事する委任・準委任契約の者を含むか、'
     'ご教示ください。'),
    ('提案書作成要領６(3)カにより見積書から除外する「令和田楽」の創作にかかる計画、'
     '並びにトゥンクトゥンクねぶた１台及び協賛ねぶた１台の製作費の計画について、'
     '除外の範囲は当該計画の策定に要する費用に限られるか、'
     '関連する調整及び進行管理に要する費用を含むか、ご教示ください。'),
    ('提案内容（参考様式６）の「片面10頁以内」について、表紙及び目次を頁数に含むか、'
     'またＡ３判１枚を用いた場合は何頁として数えるか、ご教示ください。'),
    ('参考様式５に添付する「契約書及び仕様書等の写し」について、契約書の全頁の写しが'
     '必要か、業務内容及び契約金額が確認できる部分の抜粋で足りるか、ご教示ください。'),
    ('実施要領に記載の、２０２７年１月以降の実施運営業務にかかる単独随意契約の予定に'
     'ついて、「協賛金等による財源が確保される場合」とあるところ、財源が確保されな'
     'かった場合の本プロジェクトの取扱いをご教示ください。'),
]


# 【判明したこと・2026-09-04】
# 参考様式2 の「質問事項」の枠は、5本の線と4つの小さなテキストボックスでできた
# 浮動図形で、`wp:wrapTopAndBottom`（上下で本文を押しのける）が指定されている。
# **枠の中に文字を入れる手段が様式に用意されていない。**本文に書くと必ず枠の外へ落ちる。
# 折り返しを「背面」に変える方法も試したが、LibreOffice では高さの押しのけが残った。
#
# → **原本の図形には一切手を触れず、日本の実務どおり「別紙のとおり」＋別紙とする。**
#   様式2 は1ページ、別紙が2ページ目。**2ページになるのが正しい形である。**

def add_bessi(doc, items, anchor_idx, size_pt):
    """様式2 の末尾に改ページを入れ、別紙として質問事項を並べる。"""
    anchor = items[anchor_idx]
    prev = anchor

    def blank_para(ind_left=0, hanging=0, after=60, pt=None, text=None, brk=False):
        p = copy.deepcopy(anchor)
        for child in list(p):
            if child.tag != qn('w:pPr'):
                p.remove(child)
        pPr = p.find(qn('w:pPr'))
        if pPr is None:
            pPr = p.makeelement(qn('w:pPr'), {})
            p.insert(0, pPr)
        for tag in ('w:ind', 'w:spacing', 'w:jc'):
            old = pPr.find(qn(tag))
            if old is not None:
                pPr.remove(old)
        ind = pPr.makeelement(qn('w:ind'), {})
        ind.set(qn('w:left'), str(ind_left)); ind.set(qn('w:leftChars'), '0')
        ind.set(qn('w:hanging'), str(hanging)); ind.set(qn('w:firstLineChars'), '0')
        pPr.append(ind)
        sp = pPr.makeelement(qn('w:spacing'), {})
        sp.set(qn('w:after'), str(after)); sp.set(qn('w:line'), '260')
        sp.set(qn('w:lineRule'), 'auto')
        pPr.append(sp)
        r = p.makeelement(qn('w:r'), {})
        rPr = r.makeelement(qn('w:rPr'), {})
        if pt:
            for tag in ('w:sz', 'w:szCs'):
                e = rPr.makeelement(qn(tag), {}); e.set(qn('w:val'), str(int(pt * 2)))
                rPr.append(e)
        r.append(rPr)
        if brk:
            b = r.makeelement(qn('w:br'), {}); b.set(qn('w:type'), 'page'); r.append(b)
        if text is not None:
            t = r.makeelement(qn('w:t'), {})
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            t.text = text
            r.append(t)
        p.append(r)
        return p

    added = []
    head = blank_para(text='別紙　質問事項', pt=size_pt + 2.5, after=140)
    # 空の改ページ段落を挟むと白紙が1枚増える（実測）。見出し自体を改ページ開始にする
    hPr = head.find(qn('w:pPr'))
    hPr.insert(0, hPr.makeelement(qn('w:pageBreakBefore'), {}))
    added.append(head)
    added.append(blank_para(
        text='件名：２０２７年国際園芸博覧会 主催者催事「おまつり歳時記プロジェクト（仮）」'
             'にかかる実施計画作成業務委託', pt=size_pt, after=180))
    for i, q in enumerate(QUESTIONS, 1):
        added.append(blank_para(ind_left=460, hanging=460, after=110,
                                pt=size_pt, text=f'{i}　{q}'))
    added.append(blank_para(text='以上', pt=size_pt, after=0))

    for p in added:
        prev.addnext(p)
        prev = p
    return len(added)


def build(args, out, size_pt=10.5, ind=1400, margin=4.0):
    doc = docx.Document(SRC)
    items = body_items(doc)
    s, e = RANGE
    assert para(doc, items, s).text.strip() == '（参考様式２）', '原本の構成が変わっている'
    sect = governing_sectpr(items, s)
    width = text_area_mm(sect)

    para(doc, items, 205).runs[0].text = jp_date(args.date)

    for idx in (210, 211, 212):
        set_indent(items, idx, ind)
    avail = width - ind * TWIP_MM
    append_value(doc, items, 210, -1, '　' + ADDRESS, avail, margin)
    append_value(doc, items, 211, -1, '　' + NAME, avail, margin)
    append_value(doc, items, 212, -1, '　' + REPRESENTATIVE, avail, margin)

    # ≪回答の送付先≫
    for idx, val in ((220, args.tanto_shozoku), (221, args.tanto_name),
                     (222, args.tanto_tel), (223, args.tanto_mail)):
        if val:
            append_value(doc, items, idx, -1, val, width - 3200 * TWIP_MM, margin)

    # 枠の中には書けないので、本文には「別紙のとおり」とだけ書く
    para(doc, items, 218).text  # 触れずに確認
    p218 = para(doc, items, 218)
    r = p218._element.makeelement(qn('w:r'), {})
    t = r.makeelement(qn('w:t'), {})
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = '　別紙のとおり'
    r.append(t); p218._element.append(r)

    added = add_bessi(doc, items, 226, size_pt)
    e += added                      # 段落を足したぶん範囲の終わりがずれる
    keep_range(doc, s, e, sect)
    doc.save(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default='2026-09-17', help='質問書に書く日付＝提出日')
    ap.add_argument('--tanto-shozoku', default='一般社団法人ジャパンプロモーション')
    ap.add_argument('--tanto-name', default='代表理事　生島　儀尊')
    ap.add_argument('--tanto-tel', default='03-5766-2450')
    ap.add_argument('--tanto-mail', default='ikushima@japanpromotion.org')
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    groups = [
        ('質問書',), ('住所', '〒150-0001', '海老名ビル4F'),
        ('商号又は名称', NAME), ('代表者職氏名', '生島', '儀尊'),
        ('E-mail', 'ikushima@japanpromotion.org'),
        ('別紙', '質問事項'),
    ]
    tmp = tempfile.mkdtemp(prefix='verify-')
    for step in range(10):
        size = 10.5 - step * 0.25
        build(args, OUTFILE, size_pt=size, ind=max(900, 1400 - 100 * step))
        pdf = render_pdf([OUTFILE], tmp)[0]
        problems, lines = inspect(pdf, groups)
        # **この様式は2ページで正しい**（1ページ目＝様式2、2ページ目＝別紙）
        problems = [p for p in problems if not p.startswith('2 ページある')]
        import pymupdf
        d = pymupdf.open(pdf)
        if d.page_count != 2:
            problems.append(f'{d.page_count} ページある（様式2＋別紙＝2ページのはず）')
        flat = ''.join(''.join(l.split()) for l in lines)
        if '別紙のとおり' not in flat:
            problems.append('本文に「別紙のとおり」が無い')
        if '別紙質問事項' not in flat:
            problems.append('別紙の見出しが無い')
        for i in range(1, len(QUESTIONS) + 1):
            head = ''.join(QUESTIONS[i - 1][:12].split())
            if head not in flat:
                problems.append(f'質問{i}が入っていない')
        if not problems:
            print(f'OK  {OUTFILE}   （質問{len(QUESTIONS)}件・{size}pt・'
                  f'様式2＋別紙の2ページ・{step + 1} 回目で適合）')
            print(f'    検査用 PDF: {pdf}')
            return
    print(f'NG  {OUTFILE}')
    for p in problems:
        print('      - ' + p)
    raise SystemExit('不備があるため発行しない。')


if __name__ == '__main__':
    main()
