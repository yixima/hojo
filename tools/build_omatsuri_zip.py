#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部下に渡す一式を ZIP にまとめる。

中身は「印刷するもの4点＋手順マニュアル1点＋読み札（README）」。
ファイル名はすべて半角英数（§7-11）。展開したときに印刷順に並ぶよう、
先頭に 00〜03 の番号が入っている。
"""
import hashlib
import os
import re
import zipfile

SUB = 'docs/omatsuri/submit'
OUT = os.path.join(SUB, 'omatsuri_teishutsu_ichiki_20260904.zip')

# (ZIP内の名前, 元ファイル) ── ZIP内の名前は展開時に印刷順で並ぶようにしている
MEMBERS = [
    ('00_README.txt', None),                                   # 生成する
    ('01_teishutsu_manual.pdf', 'omatsuri_teishutsu_manual.pdf'),
    ('02_soufujo.docx', 'omatsuri_00_soufujo.docx'),
    ('03_sanka_ikou_moushide.docx', 'omatsuri_01_sanka_ikou_moushide.docx'),
    ('04_seiyakusho.docx', 'omatsuri_02_seiyakusho.docx'),
    ('05_himitsu_hoji_seiyakusho.docx', 'omatsuri_03_himitsu_hoji_seiyakusho.docx'),
]

README = """おまつり歳時記プロポーザル 参加意向申出 一式
==================================================

締切：2026年9月7日（月）17時 必着
発送：2026年9月4日（金）中に、郵便局の窓口から「書留」で
作成：2026年9月3日（木）／一般社団法人ジャパンプロモーション


■ まず最初に

  01_teishutsu_manual.pdf を開いて、上から順に読んでください。
  印刷から郵便局・電話連絡・社内報告まで、これ1冊で完了できます。
  このテキストは、その目次にあたるものです。

  ファイル名の先頭の番号が、そのまま扱う順番です。


■ 印刷するもの（4点・すべてA4・片面・等倍100%）

  1枚目  02_soufujo.docx                   送付状
  2枚目  03_sanka_ikou_moushide.docx       参加意向申出書（第1号様式）
  3枚目  04_seiyakusho.docx                誓約書（参考様式1）
  4枚目  05_himitsu_hoji_seiyakusho.docx   守秘義務誓約書（参考様式10-1）

  ・4枚とも代表者印（代表理事の印）を押します。押印は生島代表理事へ依頼してください。
  ・様式の文字は書き換えないでください。空欄はありません。
  ・01_teishutsu_manual.pdf は手元用です。封筒には入れません。
    （印刷して持ち歩くと確認しやすくなります）


■ 封筒に入れるもの（5点）

  1. 送付状                                   1部  押印あり
  2. 参加意向申出書（第1号様式）              1部  押印あり
  3. 誓約書（参考様式1）                      1部  押印あり
  4. 業務実績を証明する契約書の写し           1部  押印不要  ← このZIPには入っていません
  5. 守秘義務誓約書（参考様式10-1）           1部  押印あり

  4の契約書は社内で用意します。どの契約書を使うかはマニュアルの「手順3」にあります。
  共同企業体届出書（参考様式7）は、今回は当社1社での応募なので入れません。


■ 送り先

  〒231-0013 横浜市中区住吉町1丁目13番 松村ビル本館
  公益社団法人２０２７年国際園芸博覧会協会 行催事部 行催事課 御中
  電話 045-307-2065

  ※ メール・FAX・普通郵便・ポスト投函・宅配便では出せません。
  ※ 発送したあと、必ず 045-307-2065 へ電話連絡してください（要領で定められた義務です）。


■ 困ったら

  自分で判断せず、一般社団法人ジャパンプロモーション 代表理事 生島 儀尊
  電話 03-5766-2450 / ikushima@japanpromotion.org へ連絡してください。
  締切が近いので、迷って止まるほうが危険です。
"""


def main():
    os.makedirs(SUB, exist_ok=True)
    readme_path = os.path.join(SUB, '00_README.txt')
    open(readme_path, 'w', encoding='utf-8').write(README)

    missing = [src for _, src in MEMBERS if src and not os.path.exists(os.path.join(SUB, src))]
    if missing:
        raise SystemExit(f'元ファイルが無い: {missing}')

    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, src in MEMBERS:
            path = readme_path if src is None else os.path.join(SUB, src)
            z.write(path, arcname=name)

    # ── 検査：中身・件数・名前・壊れていないか（§2 関門1）──
    ng = 0
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None, 'ZIP が壊れている'
        names = z.namelist()
        print(f'{OUT}  {os.path.getsize(OUT):,} バイト  {len(names)} 件')
        for n in names:
            info = z.getinfo(n)
            digest = hashlib.sha256(z.read(n)).hexdigest()[:12]
            mark = 'OK '
            if not re.fullmatch(r'[A-Za-z0-9._-]+', n):     # §7-11
                mark = 'NG '; ng += 1
            print(f'  {mark}{n:<44} {info.file_size:>8,} バイト  sha256:{digest}')
        if len(names) != len(MEMBERS):
            print('  NG 件数が合わない'); ng += 1
        # 展開したときに印刷順で並ぶか
        if sorted(names) != names:
            print('  NG 名前順が印刷順になっていない:', sorted(names)); ng += 1
    if ng:
        raise SystemExit('不備があるため発行しない。')
    print('  検査をすべて通過した。')


if __name__ == '__main__':
    main()
