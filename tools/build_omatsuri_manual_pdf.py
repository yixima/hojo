#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""おまつり歳時記プロポーザル 参加意向申出の「提出マニュアル」PDF を作る。

**読み手は経験の浅い新人である。**これ1冊だけを見て、印刷から郵便局・電話連絡・
社内報告まで完了できることを目標にしている。したがって
「言わなくても分かる」ことも省かない（L1 §2-13 初心者基準）。

出典（すべて一次資料。2026-09-03 に取得・確認）
  docs/omatsuri/02_teiannsyosakusei2_omaturi.pdf（提案書作成要領）
  https://expo2027yokohama.or.jp/contract/detail/20260827-001348.html（協会 案件ページ）

使い方
  python3 tools/build_omatsuri_manual_pdf.py [--date 2026-09-04]
"""
import argparse
import os
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

FONT_DIR = '/usr/share/fonts/opentype/ipafont-gothic'
OUT = 'docs/omatsuri/submit/omatsuri_teishutsu_manual.pdf'

# ── 色（印刷は白黒になる可能性があるので、色だけに意味を持たせない）──
INK = colors.HexColor('#1a1a1a')
RULE = colors.HexColor('#9aa0a6')
BAND = colors.HexColor('#eceff1')
WARN_BG = colors.HexColor('#fdecea')
WARN_LINE = colors.HexColor('#8b2b20')
OK_BG = colors.HexColor('#e8f2ec')
OK_LINE = colors.HexColor('#1f6b45')


def register_fonts():
    pdfmetrics.registerFont(TTFont('JP', os.path.join(FONT_DIR, 'ipagp.ttf')))
    pdfmetrics.registerFont(TTFont('JPMono', os.path.join(FONT_DIR, 'ipag.ttf')))
    # 太字が無いフォントなので、太字の代わりに文字サイズと罫で強弱をつける
    pdfmetrics.registerFontFamily('JP', normal='JP', bold='JP', italic='JP', boldItalic='JP')


def styles():
    base = dict(fontName='JP', textColor=INK, leading=15.5, spaceAfter=4)
    return {
        'title': ParagraphStyle('title', fontName='JP', fontSize=17, leading=24,
                                textColor=INK, alignment=TA_CENTER, spaceAfter=2),
        'subtitle': ParagraphStyle('subtitle', fontName='JP', fontSize=10, leading=15,
                                   textColor=INK, alignment=TA_CENTER, spaceAfter=10),
        'h1': ParagraphStyle('h1', fontName='JP', fontSize=13, leading=19, textColor=INK,
                             spaceBefore=12, spaceAfter=6),
        'h2': ParagraphStyle('h2', fontName='JP', fontSize=11, leading=17, textColor=INK,
                             spaceBefore=8, spaceAfter=3),
        'body': ParagraphStyle('body', fontSize=9.6, **base),
        'small': ParagraphStyle('small', fontName='JP', fontSize=8.4, leading=13,
                                textColor=INK, spaceAfter=3),
        'check': ParagraphStyle('check', fontSize=9.8, fontName='JP', leading=17,
                                textColor=INK, spaceAfter=2, leftIndent=2),
        'mono': ParagraphStyle('mono', fontName='JPMono', fontSize=9, leading=14.5,
                               textColor=INK, spaceAfter=2),
        'cell': ParagraphStyle('cell', fontName='JP', fontSize=9, leading=13.5, textColor=INK),
        'cellhead': ParagraphStyle('cellhead', fontName='JP', fontSize=9, leading=13.5,
                                   textColor=INK),
        # 黒帯の中に置く文字。表側の TEXTCOLOR は段落自身の色に負けるため、
        # 段落スタイルの側で白を指定しないと黒地に黒文字になる（実測で判明）
        'cellwhite': ParagraphStyle('cellwhite', fontName='JP', fontSize=9.5, leading=13.5,
                                    textColor=colors.white, alignment=TA_CENTER),
    }


S = None


def em(text):
    """<b> を下線に置き換える。

    この環境に入っている日本語フォントは IPAGothic の Regular だけで、
    **太字の字形が存在しない。**そのまま <b> を使うと、reportlab は
    同じ字形を返すため、強調したはずの箇所が本文と見分けられなくなる。
    印刷して白黒になっても効く強調として、下線を使う（§2-13 初心者基準：
    どこが重要かが目で分かること）。
    """
    return text.replace('<b>', '<u>').replace('</b>', '</u>')


def P(text, key='body'):
    return Paragraph(em(text), S[key])


def box(flowables, bg, line, width):
    """注意書き・台本を枠で囲む。"""
    t = Table([[flowables]], colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('BOX', (0, 0), (-1, -1), 0.9, line),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def grid(rows, col_widths, head=True):
    data = [[Paragraph(em(c), S['cellhead' if (head and i == 0) else 'cell']) for c in row]
            for i, row in enumerate(rows)]
    t = Table(data, colWidths=col_widths, repeatRows=1 if head else 0)
    style = [
        ('GRID', (0, 0), (-1, -1), 0.5, RULE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    if head:
        style.append(('BACKGROUND', (0, 0), (-1, 0), BAND))
    t.setStyle(TableStyle(style))
    return t


def step_header(n, title, width):
    """手順の見出し。番号を四角で囲んで、目で追えるようにする。"""
    t = Table([[Paragraph(f'手順 {n}', S['cellwhite']),
                Paragraph(em(f'<b>{title}</b>'), S['cellhead'])]],
              colWidths=[22 * mm, width - 22 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), INK),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('BACKGROUND', (1, 0), (1, 0), BAND),
        ('BOX', (0, 0), (-1, -1), 0.8, INK),
        ('INNERGRID', (0, 0), (-1, -1), 0.8, INK),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return t


def build(date_str, out=OUT):
    global S
    register_fonts()
    S = styles()

    y, m, d = (int(v) for v in date_str.split('-'))
    ship = f'{y}年{m}月{d}日'

    LM = RM = 18 * mm
    TM, BM = 16 * mm, 16 * mm
    W = A4[0] - LM - RM

    doc = BaseDocTemplate(out, pagesize=A4, leftMargin=LM, rightMargin=RM,
                          topMargin=TM, bottomMargin=BM,
                          title='おまつり歳時記プロポーザル 参加意向申出 提出マニュアル',
                          author='一般社団法人ジャパンプロモーション')
    frame = Frame(LM, BM, W, A4[1] - TM - BM, id='f', showBoundary=0)

    def decorate(canvas, docu):
        canvas.saveState()
        canvas.setFont('JP', 7.5)
        canvas.setFillColor(colors.HexColor('#5f6368'))
        canvas.drawString(LM, A4[1] - TM + 5 * mm,
                          'おまつり歳時記プロポーザル 参加意向申出 提出マニュアル'
                          '（一般社団法人ジャパンプロモーション）')
        canvas.drawRightString(A4[0] - RM, A4[1] - TM + 5 * mm,
                               '締切 2026年9月7日（月）17時 必着')
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(LM, A4[1] - TM + 3.5 * mm, A4[0] - RM, A4[1] - TM + 3.5 * mm)
        canvas.line(LM, BM - 4 * mm, A4[0] - RM, BM - 4 * mm)
        canvas.drawString(LM, BM - 8 * mm, '作成 2026年9月3日（木）／版 1.0')
        canvas.drawRightString(A4[0] - RM, BM - 8 * mm, f'{docu.page} ページ')
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=decorate)])

    F = []                       # flowables
    A = F.append

    # ───────────────────────── 表紙 ─────────────────────────
    A(P('参加意向申出　提出マニュアル', 'title'))
    A(P('２０２７年国際園芸博覧会　主催者催事「おまつり歳時記プロジェクト（仮）」<br/>'
        'にかかる実施計画作成業務委託　公募型プロポーザル', 'subtitle'))

    A(box([
        P('■ この仕事のゴール', 'h2'),
        P('封筒ひとつを、<b>2026年9月7日（月）17時までに、横浜市中区の協会事務所に'
          '「届いている」状態にする</b>こと。ポストに入れた時刻ではなく、'
          '<b>先方に到着した時刻</b>で判定されます。', 'body'),
        P(f'そのために、<b>{ship}（金）中に郵便局の窓口から書留で発送します。</b>'
          '9月5日（土）・6日（日）を挟むため、この日を過ぎると間に合わない恐れがあります。', 'body'),
        P('<b>1日でも遅れたら受け付けられません。</b>そして参加意向申出を出せなければ、'
          'この案件には一切参加できなくなります（9月29日の提案書も出せません）。', 'body'),
    ], WARN_BG, WARN_LINE, W))
    A(Spacer(1, 6))

    A(box([
        P('■ このマニュアルの使い方', 'h2'),
        P('・<b>上から順に、飛ばさずに行ってください。</b>順番に意味があります。', 'body'),
        P('・□ は、終わったらペンでチェックを入れる欄です。', 'body'),
        P('・<b>判断に迷ったら、自分で決めずに「9. 連絡先」に電話してください。</b>'
          '締切が近いので、迷って止まるほうが危険です。', 'body'),
        P('・このマニュアルに書いていないことを求められたら、それも連絡してください。', 'body'),
    ], OK_BG, OK_LINE, W))
    A(Spacer(1, 8))

    A(P('0. 全体の流れ（所要 約2時間＋郵便局までの移動）', 'h1'))
    A(grid([
        ['', 'やること', '場所', 'かかる時間'],
        ['手順1', '5つのファイルを印刷する', '社内', '10分'],
        ['手順2', '4枚に代表者印を押す', '社内（生島代表理事へ依頼）', '15分'],
        ['手順3', '契約書の写しを用意する', '社内', '20分'],
        ['手順4', '封入前の最終チェックをする', '社内', '10分'],
        ['手順5', '封筒に入れて宛名を書く', '社内', '15分'],
        ['手順6', '郵便局の窓口で書留で出す', '郵便局', '30分'],
        ['手順7', '<b>発送後すぐ協会へ電話する</b>', 'どこでも', '5分'],
        ['手順8', '社内に報告する', 'どこでも', '5分'],
    ], [16 * mm, W - 16 * mm - 42 * mm - 24 * mm, 42 * mm, 24 * mm]))
    A(Spacer(1, 6))
    A(P('※ 郵便局は<b>ゆうゆう窓口ではなく、書留を扱う窓口</b>へ行ってください。'
        'コンビニでは書留を出せません。ポストにも投函できません。', 'small'))

    A(P('1. 最初に覚える言葉（6つだけ）', 'h1'))
    A(grid([
        ['言葉', '意味'],
        ['公募型プロポーザル',
         '発注者が「企画の中身」で相手を選ぶ方式。値段の安さだけで決まる入札とは違う。'],
        ['参加意向申出',
         '「この案件に参加したい」と最初に手を挙げる手続き。<b>これを出さないと、'
          '肝心の提案書を出す資格がもらえない。</b>今回やるのはこれ。'],
        ['様式（ようしき）',
         '発注者が形を決めた用紙のこと。<b>1文字でも書き換えると受け付けられない</b>ことがある。'
         '今回渡されたファイルは、すでに正しい様式で作ってあるので、中身をいじらないこと。'],
        ['必着（ひっちゃく）',
         '<b>その日時までに先方に「届いている」こと。</b>「その日に出せばよい」ではない。'],
        ['書留（かきとめ）',
         '郵便局が引受から配達まで記録し、万一届かなければ賠償する郵便。'
         '<b>今回は要領で書留と指定されている。</b>普通郵便では出せない。'],
        ['守秘義務誓約書',
         '「見せてもらう資料を外に漏らしません」という約束の書面。'
         '<b>これを出さないと、提案書を書くのに必要な資料をもらえない。</b>'],
    ], [34 * mm, W - 34 * mm]))


    # ───────────────────────── 手順1 ─────────────────────────
    A(step_header(1, '5つのファイルを印刷する', W))
    A(Spacer(1, 5))
    A(P('渡されたZIPファイルを展開すると、次の6つが入っています。'
        '<b>名前の先頭の番号が、そのまま扱う順番です。</b>', 'body'))
    A(grid([
        ['ファイル名', '中身', 'どうする'],
        ['00_README.txt', 'この一式の目次', '読むだけ'],
        ['01_teishutsu_manual.pdf', '<b>このマニュアル</b>', '手元用に印刷（<b>同封しない</b>）'],
        ['02_soufujo.docx', '送付状（あいさつと同封物の一覧）', '<b>1枚目</b>として印刷'],
        ['03_sanka_ikou_moushide.docx', '<b>参加意向申出書（第1号様式）</b>',
         '<b>2枚目</b>として印刷'],
        ['04_seiyakusho.docx', '<b>誓約書（参考様式1）</b>', '<b>3枚目</b>として印刷'],
        ['05_himitsu_hoji_seiyakusho.docx', '<b>守秘義務誓約書（参考様式10-1）</b>',
         '<b>4枚目</b>として印刷'],
    ], [56 * mm, W - 56 * mm - 42 * mm, 42 * mm]))
    A(Spacer(1, 5))
    A(P('□ Word で開き、<b>A4・片面・等倍（100%）</b>で印刷した', 'check'))
    A(P('□ 「用紙に合わせて縮小」などの設定が<b>入っていない</b>ことを確認した', 'check'))
    A(P('□ 4枚とも、文字が切れずに全部入っている', 'check'))
    A(P('□ <b>01_teishutsu_manual.pdf（このマニュアル）は同封しない</b>。自分の手元用', 'check'))
    A(Spacer(1, 5))
    A(box([
        P('■ 印刷前に必ず目で見て確かめること', 'h2'),
        P('2枚目の参加意向申出書に、次が入っていますか。空欄があったら'
          '<b>印刷せずに連絡してください。</b>', 'body'),
        P('住所　〒150-0001　東京都渋谷区神宮前6-18-10　海老名ビル4F<br/>'
          '商号又は名称　一般社団法人ジャパンプロモーション<br/>'
          '代表者職氏名　代表理事　生島　儀尊<br/>'
          '≪連絡担当者≫　所属・担当・電話 03-5766-2450・'
          'E-mail ikushima@japanpromotion.org', 'mono'),
        P(f'また、4枚とも<b>日付が「{ship}」</b>になっていますか。'
          '<b>実際に郵便局へ出す日と違う場合は、印刷せずに連絡してください。</b>'
          '日付を直したものを作り直します（数分で終わります）。', 'body'),
    ], WARN_BG, WARN_LINE, W))

    A(Spacer(1, 10))
    # ───────────────────────── 手順2 ─────────────────────────
    A(step_header(2, '4枚すべてに代表者印を押す', W))
    A(Spacer(1, 5))
    A(P('押すのは<b>会社の代表者印（代表理事の印）</b>です。'
        '担当者個人の認印（みとめいん）ではありません。'
        '<b>押印は生島 儀尊 代表理事に依頼してください。</b>', 'body'))
    A(grid([
        ['書類', '押す場所'],
        ['送付状', '右上「代表理事　生島　儀尊」の右にある「印」の位置'],
        ['参加意向申出書（第1号様式）', '「代表者職氏名　代表理事　生島　儀尊」の行の末尾「印」'],
        ['誓約書（参考様式1）', '「代表者職氏名　代表理事　生島　儀尊」の右の丸印マーク'],
        ['守秘義務誓約書（参考様式10-1）', '「代表者職・氏名　代表理事　生島　儀尊」の行の末尾「印」'],
    ], [62 * mm, W - 62 * mm]))
    A(Spacer(1, 5))
    A(P('□ 朱肉（しゅにく）を使った。スタンプ台やシャチハタは使っていない', 'check'))
    A(P('□ 文字が読める向き（上下が正しい）で押した', 'check'))
    A(P('□ かすれ・にじみ・二重押しがない', 'check'))
    A(P('□ 4枚すべてに押した（<b>1枚でも忘れると差し戻される可能性があります</b>）', 'check'))
    A(Spacer(1, 4))
    A(box([
        P('■ 押し損じたら', 'h2'),
        P('<b>修正液・修正テープ・二重線での訂正はしないでください。</b>'
          'その紙は捨てて、手順1に戻ってもう一度印刷し、押し直します。'
          '紙とインクの問題であって、取り返しのつかない失敗ではありません。', 'body'),
    ], OK_BG, OK_LINE, W))


    # ───────────────────────── 手順3 ─────────────────────────
    A(step_header(3, '業務実績を証明する契約書の写しを用意する', W))
    A(Spacer(1, 5))
    A(P('協会は「うちは大きな催事を計画から運営までやった経験があります」という'
        '<b>証拠</b>を求めています。その証拠として、次の契約書のコピーを同封します。', 'body'))
    A(box([
        P('公益財団法人東京都中小企業振興公社<br/>'
          '「令和7年度『東京手仕事』MAISON &amp; OBJET PARIS 2025 '
          '出展及びポップアップストア運営」<br/>'
          '契約金額 40,986,000円（税込）', 'mono'),
    ], BAND, RULE, W))
    A(Spacer(1, 4))
    A(P('この契約書を選んだ理由（聞かれたら答えられるように）', 'h2'))
    A(P('・発注者が<b>公益財団法人</b>＝要領のいう「公益法人」に当たる', 'body'))
    A(P('・来場者<b>3,000人以上</b>の大規模な展示会である', 'body'))
    A(P('・<b>「出展」（計画をつくる仕事）と「運営」（実際に動かす仕事）の両方</b>を含む。'
        '要領は「計画策定業務<b>および</b>実施運営業務」と書いており、'
        '<b>片方だけでは足りません。</b>', 'body'))
    A(Spacer(1, 4))
    A(P('□ 契約書の原本を探し、<b>コピーを1部</b>取った（原本は同封しない。社内保管）', 'check'))
    A(P('□ 契約金額・発注者名・件名・契約日が、コピーで<b>はっきり読める</b>', 'check'))
    A(P('□ 契約書に「運営」の記載が薄い場合は、<b>仕様書のコピーも添えた</b>', 'check'))
    A(P('□ 部数は<b>1部</b>（2部以上は不要）', 'check'))
    A(Spacer(1, 4))
    A(box([
        P('■ 契約書が見つからない・どれか分からないとき', 'h2'),
        P('<b>自分で似た契約書を選ばないでください。</b>要件を満たさない書類を出すと、'
          'それだけで参加資格が認められません。「9. 連絡先」へすぐ相談してください。', 'body'),
    ], WARN_BG, WARN_LINE, W))

    A(Spacer(1, 10))
    # ───────────────────────── 手順4 ─────────────────────────
    A(step_header(4, '封に入れる前の最終チェック', W))
    A(Spacer(1, 5))
    A(P('<b>ここが最後の砦です。封をしてしまうと、もう確認できません。</b>'
        '机の上に5点を並べて、1つずつ声に出して確認してください。', 'body'))
    A(grid([
        ['', '同封するもの', '部数', '押印'],
        ['□', '送付状', '1部', '必要'],
        ['□', '<b>参加意向申出書（第1号様式）</b>', '1部', '必要'],
        ['□', '<b>誓約書（参考様式1）</b>', '1部', '必要'],
        ['□', '<b>業務実績を証明する契約書の写し</b>', '1部', '不要'],
        ['□', '<b>守秘義務誓約書（参考様式10-1）</b>', '1部', '必要'],
    ], [10 * mm, W - 10 * mm - 20 * mm - 18 * mm, 20 * mm, 18 * mm]))
    A(Spacer(1, 5))
    A(P('□ <b>共同企業体届出書（参考様式7）は入れない</b>'
        '（今回は当社1社での応募なので不要です）', 'check'))
    A(P('□ ホチキス留めはしない（クリップも不要。そのまま重ねて入れる）', 'check'))
    A(P('□ 折るなら三つ折りではなく、<b>折らずに角形2号封筒</b>に入れる（手順5）', 'check'))
    A(Spacer(1, 4))
    A(box([
        P('■ なぜ書類が「2種類」に分かれているのか（新人がよく混乱するところ）', 'h2'),
        P('封筒の中身は、実は<b>別々の2つの手続き</b>です。', 'body'),
        P('<b>A．参加意向申出（送付状・参加意向申出書・誓約書・契約書の写し）</b>'
          '……この案件に参加するための手続き。', 'body'),
        P('<b>B．業務説明資料の請求（守秘義務誓約書）</b>'
          '……提案書を書くのに必要な「業務説明資料」を見せてもらうための手続き。', 'body'),
        P('<b>締切がどちらも同じ9月7日17時なので、1つの封筒にまとめて出します。</b>'
          'Bを忘れると、参加はできても中身が分からないまま提案書を書くことになります。', 'body'),
    ], OK_BG, OK_LINE, W))


    # ───────────────────────── 手順5 ─────────────────────────
    A(step_header(5, '封筒に入れて宛名を書く', W))
    A(Spacer(1, 5))
    A(P('<b>角形2号（かくがた2ごう）</b>の封筒を使います。A4の紙を折らずに入れられる大きさです。'
        '（封筒の種類・書き方について要領に指定はありません。'
        '折らずに送るのが商慣行として無難です。）', 'body'))
    A(Spacer(1, 3))
    A(P('封筒のおもて（宛名）', 'h2'))
    A(box([
        P('〒231-0013<br/>'
          '横浜市中区住吉町１丁目13番　松村ビル本館<br/>'
          '公益社団法人２０２７年国際園芸博覧会協会<br/>'
          '　行催事部　行催事課　御中', 'mono'),
    ], BAND, RULE, W))
    A(Spacer(1, 3))
    A(P('封筒のうら（差出人）', 'h2'))
    A(box([
        P('〒150-0001<br/>'
          '東京都渋谷区神宮前6-18-10　海老名ビル4F<br/>'
          '一般社団法人ジャパンプロモーション<br/>'
          'TEL 03-5766-2450', 'mono'),
    ], BAND, RULE, W))
    A(Spacer(1, 4))
    A(P('□ おもてに<b>赤ペンで</b>「参加意向申出書在中」と書いた'
        '（要領の指定ではありませんが、担当部署へ早く回してもらうためです）', 'check'))
    A(P('□ 宛先の郵便番号・住所・団体名を、上の枠と<b>1文字ずつ照合</b>した', 'check'))
    A(P('□ 手順4のチェックが全部済んでから封をした', 'check'))
    A(P('□ のり付けは<b>郵便局に着いてから</b>でもよい（窓口で中身を確認されることがあるため、'
        'ここではまだ封をしない選択もできます）', 'check'))

    A(Spacer(1, 10))
    # ───────────────────────── 手順6 ─────────────────────────
    A(step_header(6, '郵便局の窓口で「書留」で出す', W))
    A(Spacer(1, 5))
    A(P('<b>ポスト投函は不可です。コンビニでも出せません。</b>'
        '郵便局の<b>窓口</b>へ行ってください。', 'body'))
    A(Spacer(1, 3))
    A(P('窓口でそのまま言ってよい言葉', 'h2'))
    A(box([
        P('「<b>書留でお願いします。</b><br/>'
          '　9月7日（月）の17時までに、横浜市中区に<b>必着</b>です。<br/>'
          '　間に合う出し方にしてください。速達が必要ならつけてください。」', 'mono'),
    ], OK_BG, OK_LINE, W))
    A(Spacer(1, 4))
    A(P('□ 窓口で<b>到着予定日を必ず聞き、9月7日（月）17時に間に合うことを確認した</b>', 'check'))
    A(P('□ 間に合わないと言われたら<b>速達を追加した</b>（費用より締切が優先です）', 'check'))
    A(P('□ <b>控え（受領証・追跡番号の書かれた紙）を受け取り、なくさずに持ち帰った</b>', 'check'))
    A(P('□ 控えの<b>写真を撮った</b>（追跡番号が読める状態で）', 'check'))
    A(Spacer(1, 4))
    A(box([
        P('■ 書留の種類について', 'h2'),
        P('要領は「<b>書留郵便とし</b>」としか定めておらず、'
          '<b>一般書留か簡易書留かの指定はありません</b>'
          '（提案書作成要領「４(3) 提出方法」および注意事項。2026-09-03 確認）。'
          'どちらも「書留」ですので要件は満たします。'
          '<b>迷ったら一般書留</b>を選んでください（記録が細かく、補償も手厚いためです）。', 'body'),
        P('日数や料金はその時々で変わります。<b>このマニュアルの数字を信じず、'
          '窓口で必ず確認してください。</b>', 'body'),
    ], BAND, RULE, W))


    # ───────────────────────── 手順7 ─────────────────────────
    A(step_header(7, '発送したら、すぐ協会に電話する（最重要）', W))
    A(Spacer(1, 5))
    A(box([
        P('<b>これは「やったほうがよいこと」ではありません。要領に書かれた義務です。</b>', 'body'),
        P('提案書作成要領の注意事項に、こうあります。', 'body'),
        P('「郵送の場合は書留郵便とし、<b>発送後に必ず提出先まで電話連絡の上</b>、'
          '期限までに到着するように発送してください。」', 'mono'),
        P('<b>電話を忘れると、書類が届いていても受け付けられない恐れがあります。</b>'
          '郵便局を出たら、その場でかけてください。', 'body'),
    ], WARN_BG, WARN_LINE, W))
    A(Spacer(1, 5))
    A(P('かける先', 'h2'))
    A(box([
        P('公益社団法人２０２７年国際園芸博覧会協会　行催事部　行催事課<br/>'
          '<b>045-307-2065</b>　（担当：藤田さま／山中さま／宮下さま）<br/>'
          '受付は平日 9時〜12時、13時〜17時', 'mono'),
    ], BAND, RULE, W))
    A(Spacer(1, 4))
    A(P('電話でそのまま読んでよい台本', 'h2'))
    A(box([
        P('「お世話になっております。<br/>'
          '　<b>一般社団法人ジャパンプロモーション</b>と申します。<br/>'
          '　<b>おまつり歳時記プロジェクト（仮）の実施計画作成業務委託</b>の件で、<br/>'
          '　<b>参加意向申出書</b>と<b>守秘義務誓約書</b>を、<br/>'
          f'　本日{ship}付で<b>書留にて発送いたしました。</b><br/>'
          '　到着予定は〇月〇日と伺っております。<br/>'
          '　ご確認のほど、よろしくお願いいたします。」', 'mono'),
        P('（担当者が不在なら、上の内容を伝言としてお願いし、'
          '<b>受けてくださった方のお名前を控えます。</b>）', 'small'),
    ], OK_BG, OK_LINE, W))
    A(Spacer(1, 4))
    A(P('□ 電話した', 'check'))
    A(P('□ <b>電話した時刻</b>と<b>応対してくださった方のお名前</b>を控えた', 'check'))
    A(P('□ 先方から何か指示があれば、<b>そのまま書き留めた</b>（自分で判断しない）', 'check'))

    A(Spacer(1, 10))
    # ───────────────────────── 手順8 ─────────────────────────
    A(step_header(8, '社内に報告する', W))
    A(Spacer(1, 5))
    A(P('次の5点を、その日のうちに報告してください。', 'body'))
    A(P('□ ① 発送した日時（何月何日の何時）', 'check'))
    A(P('□ ② 書留の<b>追跡番号</b>（控えの写真でも可）', 'check'))
    A(P('□ ③ 郵便局に言われた<b>到着予定日</b>', 'check'))
    A(P('□ ④ 協会へ電話した時刻と、応対者のお名前', 'check'))
    A(P('□ ⑤ 同封したもの5点の内訳（このマニュアル「手順4」の表のとおりでよい）', 'check'))
    A(Spacer(1, 5))
    A(box([
        P('■ この後どうなるか（報告のとき聞かれます）', 'h2'),
        P('<b>2026年9月10日（木）まで</b>に、協会から'
          '「提案資格確認結果通知書」が<b>電子メールで</b>届きます。'
          '宛先は参加意向申出書に書いた <b>ikushima@japanpromotion.org</b> です。', 'body'),
        P('資格が認められれば、あわせて業務説明資料などが送られてきます。'
          'その後の締切は<b>9月17日（木）17時に質問書</b>、'
          '<b>9月29日（火）17時に提案書一式</b>です。', 'body'),
        P('<b>9月10日を過ぎてもメールが来ない場合は、放置せずに'
          '045-307-2065 へ確認してください。</b>', 'body'),
    ], OK_BG, OK_LINE, W))


    # ───────────────────────── 禁止事項 ─────────────────────────
    A(P('8. これだけはやってはいけない', 'h1'))
    A(grid([
        ['やってはいけないこと', 'なぜ'],
        ['<b>メールやFAXで送る</b>',
         '要領で<b>持参または郵送（書留）のみ</b>と定められています。'
         'メールで送っても受け付けられません。'],
        ['<b>普通郵便・ポスト投函・宅配便で送る</b>',
         '「書留郵便とし」と指定されています。'],
        ['<b>様式の文字を書き換える・書き足す</b>',
         '協会が配った様式そのものです。'
         '手書きで書き足したり、文言を変えたりしないでください。'],
        ['<b>空欄のまま出す</b>',
         '記入漏れは差し戻しの理由になります。空欄を見つけたら連絡してください。'],
        ['<b>修正液・修正テープ・二重線で直す</b>',
         '押印のある正式書類です。<b>刷り直してください。</b>'],
        ['<b>発送後の電話連絡を省く</b>',
         '要領に明記された義務です。省くと受け付けられない恐れがあります。'],
        ['<b>期限に間に合わないと分かってから相談する</b>',
         '<b>おかしいと思った時点で、すぐ相談してください。</b>'
         '早ければ持参という手段が残っています。'],
    ], [50 * mm, W - 50 * mm]))

    A(Spacer(1, 8))
    A(P('9. 困ったときのQ&amp;A', 'h1'))
    A(grid([
        ['こんなとき', 'こうする'],
        ['日付が発送日と違う',
         '<b>印刷・押印の前に連絡。</b>日付を直したファイルを作り直します（数分）。'
         '押印後に気づいた場合も連絡してください。刷り直します。'],
        ['代表者印が今日押せない',
         '<b>すぐ連絡。</b>押印が間に合わないなら、'
         '<b>持参（平日9〜12時／13〜17時）</b>という手段が残っています。'
         '9月7日（月）の17時までに横浜へ持って行けば受け付けられます。'],
        ['契約書のコピーが薄い・読めない',
         '読めないコピーは証拠になりません。濃度を上げて取り直してください。'],
        ['郵便局で「7日必着は保証できない」と言われた',
         '<b>速達を追加。</b>それでも不安なら<b>持参に切り替え</b>ます。すぐ連絡してください。'],
        ['封をした後に入れ忘れに気づいた',
         '<b>開けてください。</b>封筒は替えがききますが、書類の不足は取り返せません。'],
        ['協会に電話したがつながらない',
         '受付は平日9〜12時／13〜17時です。時間内にかけ直し、'
         '<b>つながるまで続けてください。</b>つながらないまま終わらせない。'],
        ['先方から知らない書類を求められた',
         '<b>その場で判断しない。</b>言われた内容をそのまま書き留めて、社内に連絡してください。'],
    ], [50 * mm, W - 50 * mm]))

    A(Spacer(1, 8))
    A(P('10. 連絡先', 'h1'))
    A(grid([
        ['どこ', '連絡先', 'いつ使う'],
        ['<b>提出先</b><br/>２０２７年国際園芸博覧会協会<br/>行催事部 行催事課',
         '<b>045-307-2065</b><br/>〒231-0013 横浜市中区住吉町１丁目13番 松村ビル本館<br/>'
         'event@expo2027yokohama.or.jp',
         '発送後の電話連絡（手順7）。<br/>'
         '※メールアドレスは<b>質問書の提出先のみ</b>。書類は送れません。'],
        ['<b>社内</b><br/>一般社団法人ジャパンプロモーション<br/>代表理事 生島 儀尊',
         '<b>03-5766-2450</b><br/>ikushima@japanpromotion.org',
         '押印の依頼、判断に迷ったとき、'
         '<b>このマニュアルに書いていないことが起きたとき</b>'],
    ], [46 * mm, 58 * mm, W - 46 * mm - 58 * mm]))

    A(Spacer(1, 8))
    A(box([
        P('■ 出典（この手順の根拠）', 'h2'),
        P('・提案書作成要領「２ 業務の内容」「４ 参加に係る手続き」'
          '（協会配布 02_teiannsyosakusei2_omaturi.pdf）', 'small'),
        P('・協会 案件ページ　https://expo2027yokohama.or.jp/contract/detail/'
          '20260827-001348.html<br/>'
          '　（2026年9月3日に再取得し、公告時から変更が無いことを確認）', 'small'),
        P('・封筒の種類、朱書き、書留の種別、速達の要否は<b>要領に定めがありません。</b>'
          'このマニュアルでの指定は、確実に届けるための社内判断です。', 'small'),
    ], BAND, RULE, W))

    doc.build(F)
    return out


def verify(path):
    """作った PDF を開き直し、文字が正しく入っているかを機械で確かめる（§2 関門1）。"""
    import pymupdf
    import unicodedata
    d = pymupdf.open(path)
    raw = '\n'.join(p.get_text() for p in d)
    # 抽出時は行送り・全角空白の扱いが元と違う。空白を全部落としてから突き合わせる
    text = ''.join(ch for ch in raw if not ch.isspace() and ch != '\u3000')
    must = [
        '参加意向申出提出マニュアル', '2026年9月7日（月）17時',
        '045-307-2065', '〒231-0013', '横浜市中区住吉町', '書留',
        '一般社団法人ジャパンプロモーション', '生島儀尊',
        'ikushima@japanpromotion.org', '〒150-0001',
        '守秘義務誓約書', '参考様式10-1', '第1号様式', '角形2号',
        '40,986,000円', '9月10日（木）', '9月29日（火）17時',
        '発送後に必ず提出先まで電話連絡', 'MAISON&OBJETPARIS2025',
    ]
    missing = [m for m in must if m.replace(' ', '') not in text]
    # 文字化け（豆腐）の検出。□ はチェック欄として意図的に使っているので除く
    bad = sorted({c for c in text if c == '\ufffd' or 0xE000 <= ord(c) <= 0xF8FF})
    if text.count('□') < 30:
        bad.append('□が少なすぎる（チェック欄が出ていない可能性）')
    # 非日本語の混入検出（キリル文字などを誤って書いていないか）
    cyr = sorted({c for c in text if 0x0400 <= ord(c) <= 0x04FF})
    return d.page_count, missing, bad, cyr, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default='2026-09-04', help='発送日（様式の日付と一致させる）')
    args = ap.parse_args()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out = build(args.date)
    pages, missing, bad, cyr, _ = verify(out)
    print(f'{out}  {pages} ページ  {os.path.getsize(out):,} バイト')
    ng = 0
    if missing:
        print('  NG 本文に入っていない項目:', missing); ng += 1
    if bad:
        print('  NG 文字化けの疑い:', bad); ng += 1
    if cyr:
        print('  NG 日本語以外の文字が混入:', cyr); ng += 1
    base = os.path.basename(out)
    if not re.fullmatch(r'[A-Za-z0-9._-]+', base):
        print('  NG ファイル名が §7-11 に違反:', base); ng += 1
    if ng:
        raise SystemExit('不備があるため発行しない。')
    print('  OK 検査をすべて通過した。')


if __name__ == '__main__':
    main()
