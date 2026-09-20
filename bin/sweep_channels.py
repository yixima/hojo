# -*- coding: utf-8 -*-
"""チャネル台帳の各所を実際に叩き、**台帳に無い案件を報告する。書き換えない。**

なぜ要るか
----------
2026-09-15、**TOKYO LIGHTS 2027（9/1正午締切）と SusHi Tech Tokyo 2027（8/3締切）を
丸ごと見落としていた**ことが判明した。どちらも東京都の旗艦イベントで当社の本業である。

原因は2つ。
  ① ビジネスチャンス・ナビを、**どのスクリプトも一度も叩いていなかった**
     （「登録必須」を「見られない」と誤って断定していた。§3-15 原因の一括断定）
  ② **実行委員会・協議会の発注は、自治体の電子調達システムに載らない。**
     TOKYO LIGHTS は実行委員会、SusHi Tech は局のWebページでの「事業者募集」だった。

つまり見落としは「探し方が下手」ではなく、**探す場所の一覧を持っていなかった**ことによる。
`data/channels.csv` がその一覧＝分母であり、本スクリプトはそこを実際に叩いて
**台帳との差**を出す。差が出ることが正常である。差が「出ない」ことを確認する道具ではない。

    python3 bin/sweep_channels.py            # 全チャネル
    python3 bin/sweep_channels.py chancenavi # IDを指定
"""
import csv
import datetime
import io
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = os.path.join(ROOT, 'data', 'channels.csv')
LEDGER = os.path.join(ROOT, 'data', 'ledger.csv')
LOG = os.path.join(ROOT, 'data', 'sweep_log.csv')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

# 案件らしさ。**「募集」だけでは参加者募集も拾うので、発注側の語を要求する**
LOOKS = re.compile(r'委託|業務|公募|プロポーザル|入札|企画提案|事業者.{0,4}募集|受託|請負')
# 案件ではないもの
# **案件ではないもの。**ここを削るほど拾えるが、読む気が失せると読まれなくなる。
# 読まれない一覧は、無い一覧と同じである。
NOT = re.compile(
    r'採択者|審査結果|選定結果|結果の公表|終了しました|よくある|Q&amp;A|パスワード|ログイン|'
    r'個人情報|サイトマップ|アクセシビリティ|お問い合わせ|プライバシー|'
    r'エリアの|一覧$|一覧です|検索について|検索サービス|リンク集|利用開始|利用団体|'
    r'とは、|を探したい|はこちら|ください$|できます$|しています$|'
    r'を探しています|募集を締め切|受付を終了|'
    # **事務局サイトのお知らせ文。**制度の回次の話であって案件ではない
    r'掲載しました|公開しました|公表しました|更新しました|開始しました|'
    r'締切済|公募を締め切|お待ちください|ご覧いただけます|情報を掲載|'
    r'修正について|意見招請|の各案件について|スケジュール$|採択後に必要|'
    r'へ応募する|まとめサイト|新旧対照表|概要動画|操作手引き|よくあるご質問')


def norm(s):
    """比較用。**空白と実体参照と記号の揺れを消す。**"""
    s = s.replace('&amp;', '&').replace('&nbsp;', ' ')
    s = re.sub(r'[\s　]+', '', s)
    return re.sub(r'[「」『』（）()【】\[\]・,，。．\-―ー~〜]', '', s)


def fetch(url):
    try:
        p = subprocess.run(
            ['curl', '-sSL', '--http1.1', '-A', UA, '--max-time', '35', '--compressed', url],
            capture_output=True, timeout=60)
        return p.stdout.decode('utf-8', 'replace')
    except Exception:
        return ''


def titles(raw):
    """本文から案件名らしき行を拾う。**行構造を壊さない**（gatelib と同じ理由）。

    直前の `href` を一緒に返す。**見出しだけ持ち帰っても、あとで辿れない。**
    """
    b = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', raw, flags=re.S | re.I)
    # リンクは行の頭に印として残してから、タグを落とす
    b = re.sub(r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>',
               lambda m: '\n\x01' + m.group(1) + '\x02', b, flags=re.I)
    b = re.sub(r'</(tr|p|div|li|h[1-6]|dt|dd|td|a)>', '\n', b, flags=re.I)
    b = re.sub(r'<[^>]+>', ' ', b).replace('&nbsp;', ' ')
    out, seen = [], set()
    for ln in b.split('\n'):
        href = ''
        m = re.match(r'\x01([^\x02]*)\x02', ln)
        if m:
            href = m.group(1)
            ln = ln[m.end():]
        ln = ln.replace('\x01', ' ').replace('\x02', ' ')
        ln = ' '.join(ln.split())
        ln = re.sub(r'^【[^】]*】', '', ln).strip()
        if not (10 <= len(ln) <= 110):
            continue
        if not LOOKS.search(ln) or NOT.search(ln):
            continue
        k = norm(ln)
        if k in seen:
            continue
        seen.add(k)
        out.append((ln, href))
    return out


def absolutize(base, href):
    """相対リンクを絶対URLにする。**辿れないリンクは無いのと同じ。**"""
    if not href or href.startswith(('javascript:', '#', 'mailto:')):
        return ''
    if href.startswith('http'):
        return href
    m = re.match(r'(https?://[^/]+)', base)
    root = m.group(1) if m else ''
    if href.startswith('/'):
        return root + href
    return base.rsplit('/', 1)[0] + '/' + href.lstrip('./')


def save_log(rows_):
    """観測を追記する。**上書きしない。**回転表示は、日をまたいで初めて全量になる。"""
    if not rows_:
        return
    new = not os.path.exists(LOG)
    with io.open(LOG, 'a', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['観測日時', 'チャネルID', '見出し', 'リンク', '判定'])
        w.writerows(rows_)


def ledger_keys():
    with io.open(LEDGER, encoding='utf-8') as f:
        return {norm(r['案件名']) for r in csv.DictReader(f)}


def known(k, keys):
    """完全一致だけでなく、**どちらかがどちらかを含む**なら既知とみなす。
    案件名は媒体ごとに前後が削れるため、一致だけでは取りこぼす。"""
    if k in keys:
        return True
    return any((k in x or x in k) for x in keys if len(x) >= 12 and len(k) >= 12)


def main():
    want = [a for a in sys.argv[1:] if not a.startswith('-')]
    with io.open(CH, encoding='utf-8') as f:
        chans = [r for r in csv.DictReader(f)]
    if want:
        chans = [c for c in chans if c['チャネルID'] in want]
    keys = ledger_keys()

    with ThreadPoolExecutor(max_workers=8) as ex:
        pages = list(ex.map(lambda c: fetch(c['URL']), chans))

    # 制度の回次を見に行くだけのチャネルは、**案件として差を取らない。**
    # 事務局サイトのお知らせを毎日165件出せば、読まれなくなる。
    # 読まれない一覧は、無い一覧と同じである（2026-09-16 実測）。
    progs = {}
    ppath = os.path.join(ROOT, 'data', 'programs.csv')
    if os.path.exists(ppath):
        with io.open(ppath, encoding='utf-8') as f:
            progs = {r['制度ID']: r for r in csv.DictReader(f)}

    # **見たものは、その場で保存する。**
    # 2026-09-16、チャンスナビのトップが**回転表示**であることが判明した。
    # 朝8時に見えたねんりんピック2件は、夕方には消えていた。
    # 出力を標準出力に流すだけでは、回転で消えたものは二度と辿れない。
    # **観測日時は JST で刻む。**
    # 2026-09-21 判明：ここが naive な now() だったため、コンテナの UTC が書かれていた。
    # 毎朝 08:0x JST の掃引は「前日 23:0x」として記録され、
    # 「本日はじめて見た見出し」を JST の日付で数えると**常に0件**になっていた。
    # 0件は「新規が無かった」ではなく「その日付の行が存在しない」という意味だった。
    stamp = datetime.datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M')
    log = []

    total_new = 0
    dead = []
    for c, raw in zip(chans, pages):
        if c.get('用途') == '制度更新':
            pr = progs.get(c.get('紐づく制度ID') or '')
            print('\n□ %-18s %s ［制度の更新監視］' % (c['チャネルID'], c['名称']))
            if pr:
                print('   紐づく制度：%s' % pr['制度名'])
                print('   台帳の締切 %s ／ 公募開始 %s ／ 最終確認 %s'
                      % (pr['締切'] or '—', pr['公募開始'] or '—', pr['最終確認日'] or '**未**'))
            print('   **案件としての差は取らない。**回次が変わっていないかを人が見る')
            continue
        ts = titles(raw) if raw else []
        if not raw:
            dead.append(c)
            print('\n■ %-18s %s' % (c['チャネルID'], c['名称']))
            print('   **取得できなかった。「案件なし」ではない。**判定不能として扱う')
            continue
        new = [(t, h) for t, h in ts if not known(norm(t), keys)]
        total_new += len(new)
        log += [(stamp, c['チャネルID'], t, absolutize(c['URL'], h),
                 '未登録' if (t, h) in new else '既知') for t, h in ts]
        print('\n■ %-18s %s' % (c['チャネルID'], c['名称']))
        print('   案件らしき見出し %d件 ／ うち**台帳に無い %d件**' % (len(ts), len(new)))
        for t, h in new[:15]:
            print('     ・%s' % t[:100])
            if h:
                print('       %s' % absolutize(c['URL'], h)[:110])
        if len(new) > 15:
            print('     …ほか %d件' % (len(new) - 15))

    save_log(log)
    print('\n' + '=' * 62)
    print('**台帳に無い見出し 合計 %d件 ／ 取得できなかったチャネル %d件**'
          % (total_new, len(dead)))
    print('観測 %d行を data/sweep_log.csv に追記した（回転表示への備え）' % len(log))
    print('**台帳は書き換えていない。**見出しは案件とは限らない。'
          '一次資料を開き、締切種別と締切確認日を埋めてから台帳へ入れること。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
