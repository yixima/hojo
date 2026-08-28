# 分母の全数取得：キーワードで絞らず、全組織の公募・入札・委託案件を全件収集する
import re,html,subprocess,json,sys,csv,urllib.parse
from concurrent.futures import ThreadPoolExecutor
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
HUB=re.compile(r'入札|公募|調達|プロポーザル|契約|委託|募集|事業者|企画競争|企画提案')
ARCH=re.compile(r'過年度|過去|終了|結果|一覧|年度|バックナンバー|アーカイブ|令和\d|平成\d|20\d\d')
# 案件名らしさ：手続き語を含むもの全て（トピック絞り込みは一切しない）
CASE=re.compile(r'委託|業務|公募|入札|プロポーザル|企画競争|企画提案|企画競技|募集|請負|調達|選定')
NOISE=re.compile(r'^(ホーム|トップ|一覧|次へ|前へ|もっと見る|詳細|PDF|Word|Excel|こちら|サイトマップ|お問い合わせ|プライバシー|English|ページの先頭)')
# 取得は bin/fetchlib.py に集約した。3回リトライする。
# 岡山県のように断続的に0バイトを返す巡回先を1回で諦めないため。
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetchlib import fetch as _fetch

def fetch(u, t=18):
    return _fetch(u, timeout=t, tries=3)
def anchors(base,s):
    out=[]
    for m in re.finditer(r'<a\s[^>]*href="([^"#]+)"[^>]*>(.*?)</a>',s,re.S|re.I):
        t=html.unescape(re.sub(r'<[^>]+>','',m.group(2))); t=re.sub(r'\s+',' ',t).strip()
        if 6<=len(t)<=220: out.append((t,urllib.parse.urljoin(base,m.group(1))))
    return out
def work(item):
    label,host=item
    rows=[]
    top=fetch(f"https://{host}/",24)
    if not top: return label,'fail',rows
    A=anchors(f"https://{host}/",top)
    hubs=list(dict.fromkeys([u for t,u in A if HUB.search(t) and host in u]))[:8]
    visited=set(hubs)
    lvl2=[]
    for h in hubs:
        hs=fetch(h)
        if not hs: continue
        for t,u in anchors(h,hs):
            if NOISE.search(t): continue
            if CASE.search(t):
                rows.append((label,t,u,'L1'))
            elif (HUB.search(t) or ARCH.search(t)) and host in u and u not in visited and len(t)<40:
                lvl2.append(u)
    for h in list(dict.fromkeys(lvl2))[:14]:
        if h in visited: continue
        visited.add(h)
        hs=fetch(h,16)
        if not hs: continue
        for t,u in anchors(h,hs):
            if NOISE.search(t): continue
            if CASE.search(t): rows.append((label,t,u,'L2'))
    # 重複除去
    seen=set(); uq=[]
    for r in rows:
        k=r[1][:60]
        if k in seen: continue
        seen.add(k); uq.append(r)
    return label,'ok',uq
T={}
for k,v in json.load(open('prefs.json')).items(): T[f"県|{k}"]=v
for k,v in json.load(open('centers_hosts.json')).items(): T[k.replace(':','|')]=v
for k,v in json.load(open('cities_verified.json')).items(): T[f"市|{k}"]=v
NAT={'伝産協会':'kyokai.kougeihin.jp','JETRO':'www.jetro.go.jp','中小機構':'www.smrj.go.jp',
 '国際交流基金':'www.jpf.go.jp','CLAIR':'www.clair.or.jp','JNTO':'www.jnto.go.jp','VIPO':'www.vipo.or.jp',
 'TCVB':'www.tcvb.or.jp','文化庁':'www.bunka.go.jp','東京都中小企業振興公社':'www.tokyo-kosha.or.jp',
 'アーツカウンシル東京':'www.artscouncil-tokyo.jp','日本商工会議所':'www.jcci.or.jp',
 '東京商工会議所':'www.tokyo-cci.or.jp','全国商工会連合会':'www.shokokai.or.jp','日本デザイン振興会':'www.jdp.or.jp'}
for k,v in NAT.items(): T[f"国|{k}"]=v
print(f"対象組織: {len(T)}",file=sys.stderr,flush=True)
allrows=[]; stat={'ok':0,'fail':0}
with ThreadPoolExecutor(max_workers=14) as ex:
    for label,st,rows in ex.map(work,list(T.items())):
        stat[st]=stat.get(st,0)+1
        allrows+=rows
        print(f"{label}: {st} {len(rows)}",file=sys.stderr,flush=True)
with open('denominator.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['組織','案件名','URL','階層'])
    w.writerows(allrows)
print(f"\n完了 ok={stat['ok']} fail={stat.get('fail',0)} 総件数={len(allrows)}",file=sys.stderr)
