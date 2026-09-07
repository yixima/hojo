#!/usr/bin/env python3
"""Markdown の報告書を Artifact 用 HTML に変換する。
使い方: python3 tools/md2artifact.py <入力.md> <出力.html> [<題名>]
題名を省略すると先頭の見出しを使う。<!doctype>/<html>/<body> は付けない（Artifact 側が包む）。"""
import sys, re, html as H, markdown

src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding='utf-8').read()
m = re.search(r'^#\s+(.+)$', text, re.M)
title = sys.argv[3] if len(sys.argv) > 3 else (m.group(1).strip() if m else src)
body = markdown.markdown(text, extensions=['tables', 'fenced_code', 'sane_lists'])
# 表を横スクロール容器で包む
body = body.replace('<table>', '<div class="tw"><table>').replace('</table>', '</table></div>')
# 判定語に印を付ける（表セル内のみ）
for word, cls in (('要修正','bad'),('要注意','warn'),('要更新','warn'),('要訂正','bad'),('要追記','warn'),('適合','ok'),('条件付きで成立','warn')):
    body = re.sub(r'<td>\*\*%s\*\*</td>|<td><strong>%s</strong></td>' % (word, word),
                  '<td><span class="tag %s">%s</span></td>' % (cls, word), body)
css = """
<title>{TITLE}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;700&family=Noto+Sans+JP:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{--bg:#F6F7F5;--paper:#FFFFFF;--ink:#1C2A2E;--muted:#5F6E71;--rule:#D5DCDA;--accent:#0E6B71;--accent-soft:#E2F0F0;
 --ok:#2F7A3E;--ok-bg:#E4F2E6;--warn:#9A5A0F;--warn-bg:#F7EBD6;--bad:#A3312B;--bad-bg:#F7E1DF;--quote:#F1F4F2;--code:#EEF1F0}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#111819;--paper:#182022;--ink:#E4EAE8;--muted:#9AABAE;--rule:#2E3A3D;--accent:#63C3C8;--accent-soft:#16383B;
 --ok:#8ED39A;--ok-bg:#1E3A26;--warn:#F0B86B;--warn-bg:#3E2E15;--bad:#F09A94;--bad-bg:#43211F;--quote:#1E282A;--code:#20292B}}
:root[data-theme="dark"]{--bg:#111819;--paper:#182022;--ink:#E4EAE8;--muted:#9AABAE;--rule:#2E3A3D;--accent:#63C3C8;--accent-soft:#16383B;
 --ok:#8ED39A;--ok-bg:#1E3A26;--warn:#F0B86B;--warn-bg:#3E2E15;--bad:#F09A94;--bad-bg:#43211F;--quote:#1E282A;--code:#20292B}
body{background:var(--bg);color:var(--ink);font-family:"Noto Sans JP",system-ui,-apple-system,"Hiragino Sans",sans-serif;font-size:15px;line-height:1.85;margin:0}
.wrap{max-width:52rem;margin:0 auto;padding:2.5rem 1.5rem 5rem}
.sheet{background:var(--paper);border:1px solid var(--rule);padding:2.5rem clamp(1.25rem,4vw,3rem)}
h1{font-family:"Shippori Mincho","Hiragino Mincho ProN",serif;font-weight:700;font-size:1.65rem;line-height:1.45;margin:0 0 1.25rem;text-wrap:balance;letter-spacing:.01em}
h2{font-family:"Shippori Mincho","Hiragino Mincho ProN",serif;font-weight:700;font-size:1.25rem;margin:2.75rem 0 .9rem;padding-top:1.1rem;border-top:2px solid var(--accent);text-wrap:balance}
h3{font-size:1.02rem;font-weight:700;margin:1.8rem 0 .6rem;color:var(--accent)}
p{margin:.6rem 0}
ul,ol{padding-left:1.4rem;margin:.5rem 0}
li{margin:.25rem 0}
hr{border:0;border-top:1px solid var(--rule);margin:2rem 0}
blockquote{margin:1.2rem 0;padding:1rem 1.25rem;background:var(--quote);border-left:3px solid var(--accent);color:var(--ink)}
blockquote p{margin:.45rem 0}
code{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:.86em;background:var(--code);padding:.1em .35em;border-radius:3px}
pre{background:var(--code);padding:.9rem 1rem;overflow-x:auto;border-radius:4px;font-size:.84rem;line-height:1.6}
pre code{background:none;padding:0}
.tw{overflow-x:auto;margin:1rem 0;border:1px solid var(--rule)}
table{border-collapse:collapse;width:100%;font-size:.9rem;line-height:1.6;font-variant-numeric:tabular-nums}
th,td{padding:.5rem .7rem;border-bottom:1px solid var(--rule);vertical-align:top;text-align:left}
th{background:var(--accent-soft);font-weight:700;white-space:nowrap}
tr:last-child td{border-bottom:0}
.tag{display:inline-block;padding:.05em .55em;border-radius:999px;font-size:.82rem;font-weight:700;white-space:nowrap}
.tag.ok{color:var(--ok);background:var(--ok-bg)}.tag.warn{color:var(--warn);background:var(--warn-bg)}.tag.bad{color:var(--bad);background:var(--bad-bg)}
a{color:var(--accent);word-break:break-all}
strong{font-weight:700}
.meta{color:var(--muted);font-size:.85rem;letter-spacing:.04em;text-transform:none;margin-bottom:1.5rem;border-bottom:1px solid var(--rule);padding-bottom:1rem}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
</style>
""".replace("{TITLE}", H.escape(title))
meta = '<div class="meta">yixima/hojo · %s</div>' % H.escape(src)
open(dst, 'w', encoding='utf-8').write(css + '<div class="wrap"><div class="sheet">' + meta + body + '</div></div>\n')
print('wrote', dst, len(open(dst,encoding="utf-8").read()), 'chars; title =', title)
