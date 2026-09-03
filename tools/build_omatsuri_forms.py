#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""おまつり歳時記プロポーザル 参加意向申出（9/7 17時必着）の提出用ファイルを作る。

原本 docs/omatsuri/04_yousikimatome_omaturi.docx から、必要な様式だけを
**書式そのまま**切り出し、当社情報を差し込む。様式の文言は一切書き換えない。

出力（docs/omatsuri/submit/）
  omatsuri_01_sanka_ikou_moushide.docx  第1号様式  参加意向申出書
  omatsuri_02_seiyakusho.docx           参考様式1  誓約書
  omatsuri_03_himitsu_hoji_seiyakusho.docx 参考様式10-1 業務説明資料提供申込書 兼 守秘義務誓約書

使い方
  python3 tools/build_omatsuri_forms.py                     # 既定＝2026年9月4日・連絡担当者は空欄
  python3 tools/build_omatsuri_forms.py --date 2026-09-07 \
      --tanto-shozoku 制作局 --tanto-name "山田 太郎" \
      --tanto-tel 03-0000-0000 --tanto-mail taro@example.jp
"""
import argparse
import copy
import os
import re

import docx
from docx.text.paragraph import Paragraph

SRC = 'docs/omatsuri/04_yousikimatome_omaturi.docx'
OUT = 'docs/omatsuri/submit'

# profile/company-profile.yaml より（status: confirmed の値のみ使う）
ADDRESS = '東京都渋谷区神宮前6-18-10 海老名ビル4F'
NAME = '一般社団法人ジャパンプロモーション'
REPRESENTATIVE = '代表理事　生島　儀尊'

# 原本の本文要素の添字（tools/build_omatsuri_forms.py --dump で確認できる）
RANGES = {
    'form1': (0, 37),      # 第1号様式（37 は改ページのみの段落なので含めない）
    'seiyaku': (179, 203),  # 参考様式1
    'himitsu': (378, 408),  # 参考様式10-1
}


def body_items(doc):
    return list(doc.element.body.iterchildren())


def keep_range(doc, start, end):
    """本文のうち [start, end) 以外の段落・表を削除する。sectPr は残す。"""
    items = body_items(doc)
    for i, el in enumerate(items):
        if el.tag.endswith('}sectPr'):
            continue
        if not (start <= i < end):
            el.getparent().remove(el)


def set_para_text(doc, items, idx, text):
    """段落を1つの run にまとめて書き換える（書式は先頭 run を継承）。"""
    p = Paragraph(items[idx], doc)
    if not p.runs:
        raise RuntimeError(f'段落 {idx} に run がない')
    p.runs[0].text = text
    for r in p.runs[1:]:
        r.text = ''


def append_to_run(doc, items, idx, run_i, text):
    """指定 run の末尾に文字を足す（後続のフィールド＝印などを壊さない）。"""
    p = Paragraph(items[idx], doc)
    p.runs[run_i].text = p.runs[run_i].text + text


def wareki_free_date(iso):
    y, m, d = iso.split('-')
    return f'{int(y)}年{int(m)}月{int(d)}日'


def build_form1(args):
    doc = docx.Document(SRC)
    items = body_items(doc)
    s, e = RANGES['form1']
    assert Paragraph(items[s], doc).text.strip() == '（第１号様式）', '原本の構成が変わっている'

    set_para_text(doc, items, 1, '　' + wareki_free_date(args.date))
    append_to_run(doc, items, 7, -1, ADDRESS)                 # 住所
    append_to_run(doc, items, 8, -1, NAME)                    # 商号又は名称
    # 代表者職氏名（単一 run。末尾の「印」の手前に入れる）
    p9 = Paragraph(items[9], doc)
    p9.runs[0].text = f'代表者職氏名　{REPRESENTATIVE}　　　　　　印'
    # ≪連絡担当者≫ ── 未確定の項目は空欄のままにする（推測で埋めない）
    for idx, val in ((32, args.tanto_shozoku), (33, args.tanto_name),
                     (34, args.tanto_tel), (35, args.tanto_mail)):
        if val:
            append_to_run(doc, items, idx, -1, val)

    keep_range(doc, s, e)
    out = os.path.join(OUT, 'omatsuri_01_sanka_ikou_moushide.docx')
    doc.save(out)
    return out


def build_seiyaku(args):
    doc = docx.Document(SRC)
    items = body_items(doc)
    s, e = RANGES['seiyaku']
    assert Paragraph(items[s], doc).text.strip() == '（参考様式１）', '原本の構成が変わっている'

    set_para_text(doc, items, 194, '　　' + wareki_free_date(args.date))
    append_to_run(doc, items, 197, -1, '　' + ADDRESS)         # 所在地
    append_to_run(doc, items, 198, -1, '　' + NAME)            # 商号又は名称
    # 代表者職氏名（runs[3] が「代表者職氏名」＋全角空白。後続の run に「○印」フィールドがあるので置き換えない）
    Paragraph(items[199], doc).runs[3].text = f'　代表者職氏名　{REPRESENTATIVE}　　　　'

    keep_range(doc, s, e)
    out = os.path.join(OUT, 'omatsuri_02_seiyakusho.docx')
    doc.save(out)
    return out


def build_himitsu(args):
    doc = docx.Document(SRC)
    items = body_items(doc)
    s, e = RANGES['himitsu']
    assert Paragraph(items[s], doc).text.strip() == '（参考様式１０-１）', '原本の構成が変わっている'

    set_para_text(doc, items, 401, '　　　　　　' + wareki_free_date(args.date))
    append_to_run(doc, items, 403, -1, '　' + ADDRESS)         # 所在地
    append_to_run(doc, items, 404, -1, '　' + NAME)            # 商号又は名称
    # 代表者職・氏名（runs = [\t, '代表者職・氏', '名', 空白, 空白, '印']）
    p405 = Paragraph(items[405], doc)
    p405.runs[2].text = '名　' + REPRESENTATIVE
    p405.runs[3].text = '　　　　　　'

    keep_range(doc, s, e)
    out = os.path.join(OUT, 'omatsuri_03_himitsu_hoji_seiyakusho.docx')
    doc.save(out)
    return out


def verify(path, must_have):
    """作った docx を開き直して、差し込んだ文字が実際に入っているか目視検証する（§7-7）。"""
    d = docx.Document(path)
    text = '\n'.join(p.text for p in d.paragraphs)
    missing = [m for m in must_have if m not in text]
    return text, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default='2026-09-04', help='様式に書く日付（YYYY-MM-DD）＝発送日または持参日')
    ap.add_argument('--tanto-shozoku', default='')
    ap.add_argument('--tanto-name', default='')
    ap.add_argument('--tanto-tel', default='')
    ap.add_argument('--tanto-mail', default='')
    ap.add_argument('--dump', action='store_true', help='原本の本文要素を添字つきで表示する')
    args = ap.parse_args()

    if args.dump:
        d = docx.Document(SRC)
        for i, el in enumerate(body_items(d)):
            tag = el.tag.split('}')[1]
            t = Paragraph(el, d).text.strip()[:60] if tag == 'p' else ''
            print(i, tag, repr(t))
        return

    os.makedirs(OUT, exist_ok=True)
    results = [
        (build_form1(args), ['参 加 意 向 申 出 書', ADDRESS, NAME, '生島　儀尊',
                             wareki_free_date(args.date)]),
        (build_seiyaku(args), ['誓　　約　　書', ADDRESS, NAME, '生島　儀尊',
                               wareki_free_date(args.date)]),
        (build_himitsu(args), ['業務説明資料提供申込書', ADDRESS, NAME, '生島　儀尊',
                               wareki_free_date(args.date)]),
    ]
    ng = 0
    for path, must in results:
        text, missing = verify(path, must)
        # 他の様式が混ざっていないか（切り出しの取りこぼし検査）
        strays = sorted(set(re.findall(r'（第[０-９一二三四五六七八九十]+号様式）|（参考様式[０-９一二三四五六七八九十]+(?:-[０-９一二三四五六七八九十]+)?）', text)))
        ok = not missing and len(strays) == 1
        print(('OK  ' if ok else 'NG  ') + path)
        print('    様式:', ','.join(strays))
        if missing:
            print('    差し込めていない項目:', missing)
            ng += 1
        if len(strays) != 1:
            print('    他の様式が混ざっている:', strays)
            ng += 1
        # ファイル名検査（§7-11）
        base = os.path.basename(path)
        if not re.fullmatch(r'[A-Za-z0-9._-]+', base):
            print('    ファイル名が §7-11 に違反:', base)
            ng += 1
    if ng:
        raise SystemExit(f'{ng} 件の不備がある。発行しない。')
    print('\n3件すべて検査を通過した。')


if __name__ == '__main__':
    main()
