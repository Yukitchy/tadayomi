#!/usr/bin/python3
# タダヨミ 実データ収集（stdlibのみ・/usr/bin/python3 3.9で動く書き方）
# 各媒体の公式ページから「期間限定の無料」を拾い ../data.json を更新。ログは logs/YYYY-MM-DD.json
# 安全装置: 媒体が失敗したら前回のその媒体分（未終了）を引き継ぐ／総数が MIN_ITEMS 未満なら data.json を書かない
import json, re, unicodedata, sys, html, os, datetime, urllib.request, concurrent.futures as cf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data.json")
HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
JST = datetime.timezone(datetime.timedelta(hours=9))
NOW = datetime.datetime.now(JST)
TODAY = NOW.date()
MIN_ITEMS = 10
MAX_DETAIL = 40  # 1媒体あたりの詳細ページ取得上限（礼儀として）

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.geturl(), r.read().decode("utf-8", "ignore")

def meta(t, prop):
    m = re.search(r'(?:property|name)="%s" content="([^"]*)"' % re.escape(prop), t)
    return html.unescape(m.group(1)).strip() if m else ""

def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

def md_to_date(md):
    """'11/26' → 今日以降で最も近い日付（年またぎ対応）"""
    m, d = map(int, md.split("/"))
    y = TODAY.year
    dt = datetime.date(y, m, d)
    if dt < TODAY - datetime.timedelta(days=180):
        dt = datetime.date(y + 1, m, d)
    return dt

# ---------- ebookjapan: /free/ の埋め込みJSON（__NUXT_DATA__）の話単位キャンペーン
def unflat(arr):
    memo = {}
    def h(i):
        if not isinstance(i, int) or isinstance(i, bool) or i < 0 or i >= len(arr):
            return None
        if i in memo:
            return memo[i]
        v = arr[i]
        if isinstance(v, dict):
            o = {}; memo[i] = o
            for k, x in v.items(): o[k] = h(x)
            return o
        if isinstance(v, list):
            if v and isinstance(v[0], str) and v[0] in ("Reactive", "ShallowReactive", "Ref", "ShallowRef", "EmptyRef", "EmptyShallowRef", "Set", "Map", "Date"):
                r = h(v[1]) if len(v) > 1 else None; memo[i] = r; return r
            o = []; memo[i] = o; o.extend(h(x) for x in v); return o
        return v
    return h(0)

def walk(o, pred, out):
    if isinstance(o, dict):
        if pred(o): out.append(o)
        for v in o.values(): walk(v, pred, out)
    elif isinstance(o, list):
        for v in o: walk(v, pred, out)
    return out

def ebookjapan():
    _, t = get("https://ebookjapan.yahoo.co.jp/free/")
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
    if not m: raise RuntimeError("__NUXT_DATA__ が見つからない（ページ構造変更）")
    sys.setrecursionlimit(100000)
    stories = walk(unflat(json.loads(m.group(1))), lambda o: o.get("serialStoryId") and o.get("campaigns"), [])
    cands = {}
    for s in stories:
        for c in s["campaigns"] or []:
            try:
                st = datetime.datetime.fromisoformat(c["campaignStartDatetime"]); en = datetime.datetime.fromisoformat(c["campaignEndDatetime"])
            except Exception:
                continue
            n = re.search(r"(\d+)話無料", c.get("campaignText") or "")
            if not (n and st <= NOW <= en): continue
            sid = s["serialStoryId"]
            if sid not in cands or int(n.group(1)) > cands[sid]["freeEpisodes"]:
                cands[sid] = dict(sid=sid, freeEpisodes=int(n.group(1)), endDate=en.date().isoformat(),
                                  completed=bool(s.get("isComplete")), genre=((s.get("unificationMiddleGenre") or {}).get("name") or ""))
    def detail(c):
        url = "https://ebookjapan.yahoo.co.jp/stories/%s/" % c["sid"]
        final, t = get(url)  # 実在確認を兼ねる（作品ページへリダイレクトされる）
        title = re.search(r"<title>(.*?)</title>", t, re.S)
        parts = [p.strip() for p in html.unescape(title.group(1)).split(" - ")] if title else []
        if len(parts) < 2 or "/books/" not in final: return None
        name = re.sub(r"^【[^】]*】|\s*[\(（][^\)）]*[\)）]\s*$", "", parts[0]).strip()
        name = re.sub(r"\s*[\(（][^\)）]*[\)）]\s*$", "", name).strip()
        return dict(title=name, author=parts[1], category="store", store="ebookjapan", freeVolumes=0, totalVolumes=None,
                    freeEpisodes=c["freeEpisodes"], allFree=False, completed=c["completed"], endDate=c["endDate"],
                    catch=meta(t, "og:description")[:60], tags=[c["genre"]] if c["genre"] else [], cover=meta(t, "og:image"), url=url)
    return run_details(detail, list(cands.values())[:MAX_DETAIL])

# ---------- ピッコマ: トップの「N巻無料」作品 → 作品ページの「N巻分無料！MM/DD(曜)23:59まで」
def piccoma():
    _, t = get("https://piccoma.com/web/")
    ids = list(dict.fromkeys(re.findall(r'href="/web/product/(\d+)\?etype=volume"[^>]*data-gtm-label="(?:\d+|全)巻無料"', t)))
    if not ids: raise RuntimeError("トップに巻無料の作品が見つからない（ページ構造変更）")
    def detail(pid):
        url = "https://piccoma.com/web/product/%s" % pid
        _, p = get(url)
        x = text(re.sub(r"<script.*?</script>|<style.*?</style>", "", p, flags=re.S))
        m = re.search(r"(全巻|\d+巻分)無料！\s*(\d{1,2}/\d{1,2})\(.\)\s*23:59まで", x)
        if not m: return None  # 期限の書かれていない無料は載せない
        ttl = meta(p, "og:title").split("｜")
        title = re.sub(r"\s*(【[^】]*】|（分冊版）|\(分冊版\))\s*", "", ttl[0]).strip(); author = ttl[-1].strip() if len(ttl) >= 3 else ""
        allfree = m.group(1) == "全巻"
        vols = re.search(r"全(\d+)巻", x)
        return dict(title=title, author=author, category="store", store="ピッコマ",
                    freeVolumes=int(vols.group(1)) if allfree and vols else (0 if allfree else int(m.group(1)[:-2])),
                    totalVolumes=int(vols.group(1)) if vols else None, allFree=allfree,
                    completed="完結" in re.findall(r'<ul class="PCM-productStatus">(.*?)</ul>', p, re.S)[0] if '<ul class="PCM-productStatus">' in p else False,
                    endDate=md_to_date(m.group(2)).isoformat(), catch=meta(p, "og:description")[:60], tags=[],
                    cover=cover(p), url=url)
    def cover(p):  # og:image は共有用の汎用画像なので、作品ページの表紙サムネを使う
        m = re.search(r'class="PCM-productThum_img" src="([^"]+)"', p)
        return ("https:" + m.group(1) if m.group(1).startswith("//") else m.group(1)) if m else ""
    return run_details(detail, ids[:MAX_DETAIL])

# ---------- マガポケ（講談社）: トップの各作品カードの告知文「N巻分無料！MM/DDまで」
def magapoke():
    base = "https://pocket.shonenmagazine.com"
    _, t = get(base + "/")
    out = {}
    for href, blk in re.findall(r'<a href="(/title/\d+)[^"]*"[^>]*>(.*?)</a>', t, re.S):
        ttl = re.search(r'__ttl">(.*?)</h3>', blk, re.S); cm = re.search(r'__cm">(.*?)</p>', blk, re.S)
        if not (ttl and cm): continue
        cm = text(cm.group(1)); title = text(ttl.group(1)).replace("　", " ")
        m = re.search(r"(全巻|(\d+)巻分)(?:＆[^！]*)?無料！\s*(\d{1,2}/\d{1,2})まで", cm)
        if not m or title in out: continue
        img = re.search(r'<img[^>]*src="([^"]+)"[^>]*alt=', blk)
        intro = re.search(r'__intro">(.*?)</p>', blk, re.S)
        out[title] = dict(title=title, author="", category="publisher", store="マガポケ",
                          freeVolumes=int(m.group(2)) if m.group(2) else 0, totalVolumes=None, allFree=m.group(1) == "全巻",
                          completed=False, endDate=md_to_date(m.group(3)).isoformat(), catch=text(intro.group(1)) if intro else "",
                          tags=[], cover=img.group(1) if img else "", url=base + href)
        if "＆" in m.group(0): out[title]["freeLabel"] = re.sub(r"！\s*\d{1,2}/\d{1,2}まで$", "", m.group(0))
    def detail(it):  # 作品ページで実在確認＋作者名
        _, p = get(it["url"])
        a = re.search(r'comic-name"[^>]*>(.*?)</h3>', p, re.S)
        if a: it["author"] = text(a.group(1))
        return it
    return run_details(detail, list(out.values())[:MAX_DETAIL])

def run_details(fn, xs):
    with cf.ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda x: _safe(fn, x), xs))
    return [r for r in res if r]

def _safe(fn, x):
    try: return fn(x)
    except Exception: return None

SOURCES = {"ebookjapan": ebookjapan, "ピッコマ": piccoma, "マガポケ": magapoke}
# 自動収集していない媒体（理由は初回調査 2026-11-20 時点。結果ファイルにも同じ内容）
NOT_COVERED = {
    "Kindle": "amazon.co.jp は自動取得に対しロボット確認ページ（1.4KB）を返す。公式APIはアソシエイト審査が前提",
    "BOOK☆WALKER": "/free/ に作品は並ぶが終了日がHTMLに無い。キャンペーン一覧URLは404",
    "コミックシーモア": "/freecontents/ のHTMLに終了日が無い（作品ごとの期限は取得できず）",
    "LINEマンガ": "ページ本体がJavaScriptで描画され、HTMLにキャンペーン期限が無い",
    "少年ジャンプ＋": "トップ・作品ページに無料期間の構造化された記載が無い。完結記念などは manual.json で手動追加",
    "ヤンマガWeb": "トップに巻無料の告知はあるが終了日の記載が無い",
    "サンデーうぇぶり": "トップに期間限定無料の告知が無い（取得時点）",
    "ヤンチャンWeb": "ynjn.jp / yanchan.jp が接続を返さない（取得時点）",
}

def valid(it):
    try:
        e = datetime.date.fromisoformat(it["endDate"])
    except Exception:
        return False
    return bool(it.get("title")) and it.get("url", "").startswith("https://") and e >= TODAY and \
        (it.get("allFree") or it.get("freeVolumes") or it.get("freeEpisodes") or it.get("freeLabel"))

def score(i):  # 同じ作品が複数媒体にある時は 全巻無料 > 無料巻数 > 終了が遅い方
    return (bool(i.get("allFree")), i.get("freeVolumes") or 0, i["endDate"])

def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[\s　・：:！!？?〜~（）()【】]", "", s).lower()

def main():
    prev = json.load(open(DATA, encoding="utf-8"))
    prev_real = [i for i in prev.get("items", []) if i.get("url", "#") != "#"]
    log = {"run": NOW.isoformat(timespec="seconds"), "sources": {}, "not_covered": NOT_COVERED}
    items = []
    for name, fn in SOURCES.items():
        try:
            got = [i for i in fn() if valid(i)]
            if not got: raise RuntimeError("0件（構造変更の可能性）")
            log["sources"][name] = {"ok": True, "count": len(got)}
        except Exception as e:
            got = [i for i in prev_real if i.get("store") == name and valid(i)]
            log["sources"][name] = {"ok": False, "count": 0, "error": "%s: %s" % (type(e).__name__, e), "kept_from_previous": len(got)}
        for i in got: i["source"] = name
        items += got
    manual = [i for i in json.load(open(os.path.join(HERE, "manual.json"), encoding="utf-8")) if valid(i)]
    log["sources"]["manual"] = {"ok": True, "count": len(manual)}
    # dedupe: タイトル正規化で1件に（手動を優先、次に全巻無料・無料量の多い方）
    best = {}
    for i in manual + items:
        k = norm(i["title"])
        # 片方が省略形（先頭一致・8文字以上）でも同一作品とみなす
        dup = next((b for b in best if b == k or (min(len(b), len(k)) >= 8 and (b.startswith(k) or k.startswith(b)))), None)
        if dup is None: best[k] = i
        elif best[dup].get("source") != "manual" and score(i) > score(best[dup]): best[dup] = i
    items = sorted(best.values(), key=lambda i: (i["endDate"], not i["allFree"], i["title"]))
    for n, i in enumerate(items, 1): i["id"] = n
    log["total"] = len(items); log["allFree"] = sum(1 for i in items if i["allFree"])
    ok = len(items) >= MIN_ITEMS
    log["written"] = ok
    os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
    json.dump(log, open(os.path.join(HERE, "logs", TODAY.isoformat() + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(log, ensure_ascii=False))
    if not ok:
        print("件数不足のため data.json は前回のまま", file=sys.stderr); return 2
    auto = sorted({i["store"] for i in items if i.get("source") != "manual"})
    man = sorted({i["store"] for i in items if i.get("source") == "manual"} - set(auto))
    data = {"updated": TODAY.isoformat(), "sample": False, "sources": auto, "manual": man, "items": items}
    tmp = DATA + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.load(open(tmp, encoding="utf-8"))
    os.replace(tmp, DATA)
    return 0

if __name__ == "__main__":
    sys.exit(main())
