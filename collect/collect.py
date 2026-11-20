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
    return run_details(piccoma_detail, ids[:MAX_DETAIL])

def piccoma_detail(pid):
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
                cover=piccoma_cover(p), url=url)
def piccoma_cover(p):  # og:image は共有用の汎用画像なので、作品ページの表紙サムネを使う
    m = re.search(r'class="PCM-productThum_img" src="([^"]+)"', p)
    return ("https:" + m.group(1) if m.group(1).startswith("//") else m.group(1)) if m else ""


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

# ---------- 公式Xの告知（fxtwitter の公開API api.fxtwitter.com/2/profile/<id>/statuses。ログイン不要）
# 公式アカウント本人の投稿だけを見る（リポスト・非公式は除外）。1投稿＝作品1つ（『』が1つ）・無料範囲・期限が全部読み取れるものだけ。
# 告知内のリンク先に実サイトの検証器があればそこで裏取り（basis=site、値も実サイト優先・取れなければ載せない）。
# 検証器の無い媒体（Kindle・シーモア等の直接巡回できない媒体）は公式Xの告知を一次情報として掲載（basis=x、リンクは告知ポスト）。
X_ACCOUNTS = {  # handle: (媒体名, category, 投稿に必須の語)  2026-11-20 fxtwitter でプロフィール確認済み
    "championcross": ("チャンピオンクロス", "publisher", ""), "shonenjump_plus": ("少年ジャンプ＋", "store", ""),
    "magapoke": ("マガポケ", "publisher", ""), "ynjn_jp": ("ヤンジャン＋", "publisher", ""),
    "sundaywebry": ("サンデーうぇぶり", "publisher", ""), "comicdays_team": ("コミックDAYS", "publisher", ""),
    "comic_cmoa": ("コミックシーモア", "store", ""), "BOOK_WALKER": ("BOOK☆WALKER", "store", ""),
    "LINEMANGA": ("LINEマンガ", "store", ""), "AmazonJP": ("Kindle", "store", "Kindle"),
    "ebookjapan": ("ebookjapan", "store", ""), "piccoma_jp": ("ピッコマ", "store", ""),
}
X_DAYS = 5     # 何日前までの投稿を見るか
X_PAGES = 2    # 1アカウントあたり 20件×2ページ
X_FAILED = {}  # handle → エラー（main が前回分を引き継ぐ）

def xposts(handle):
    out, cur = [], ""
    for _ in range(X_PAGES):
        u = "https://api.fxtwitter.com/2/profile/%s/statuses%s" % (handle, "?cursor=" + cur if cur else "")
        try: _, t = get(u)
        except Exception: _, t = get(u)  # 1回だけ再試行（たまにTLSタイムアウトする）
        d = json.loads(t)
        if d.get("code") != 200: raise RuntimeError("fxtwitter code=%s" % d.get("code"))
        out += d.get("results") or []
        cur = (d.get("cursor") or {}).get("bottom")
        if not cur: break
    return out

def x_parse(text_, posted):
    """告知文 → (title, 無料範囲dict, endDate) / 読み取れなければ None"""
    t = unicodedata.normalize("NFKC", text_)
    titles = list(dict.fromkeys(re.sub(r"\s*#\s*", "", s).strip() for s in re.findall(r"『([^』]+)』", t)))
    if len(titles) != 1: return None
    fr = None
    m = re.search(r"全(話|巻|エピソード)\s*(?:完全)?無料", t)
    if m: fr = dict(allFree=m.group(1) == "巻", freeLabel="全%s無料" % ("巻" if m.group(1) == "巻" else "話"))
    m = m or re.search(r"(?<![〜~\-\d])(\d+)\s*(巻|話|エピソード)分?\s*(?:完全)?無料", t)
    if m and not fr:
        n = int(m.group(1)); fr = dict(freeVolumes=n) if m.group(2) == "巻" else dict(freeEpisodes=n)
    if not fr: return None
    m = re.search(r"([^\s※・『』]{1,16}除く)", t)  # 「最終巻除く」「最新巻&以降の話を除く」等は表記に残す
    base = lambda: fr.get("freeLabel") or ("%d話分無料" % fr["freeEpisodes"] if "freeEpisodes" in fr else "%d巻無料" % fr["freeVolumes"])
    if m: fr["freeLabel"] = base() + "（%s）" % m.group(1)
    m = re.search(r"ブラウザ版のみ|アプリ(?:版)?(?:のみ|限定)|待てば", t)  # 条件付きの無料は表記に残す
    if m: fr["freeLabel"] = base() + "（%s）" % m.group(0)
    end = None
    m = re.search(r"(\d{1,2})/(\d{1,2})\s*(?:\(.\))?\s*(\d{1,2}:\d{2})?\s*(?:まで|迄)", t)
    if m:
        end = md_to_date("%s/%s" % (m.group(1), m.group(2)))
        if m.group(3) in ("0:00", "00:00"): end -= datetime.timedelta(days=1)  # 0:00まで＝前日いっぱい
    else:
        m = re.search(r"(?:今から|(\d{1,2})/(\d{1,2})\s*(?:\(.\))?\s*から)\s*(\d+)\s*時間", t)
        if m:
            start = datetime.datetime.combine(md_to_date("%s/%s" % (m.group(1), m.group(2))), datetime.time(), JST) if m.group(1) else posted.replace(minute=0, second=0)  # 告知は毎正時開始の前提
            end = (start + datetime.timedelta(hours=int(m.group(3)), seconds=-1)).date()
    if not end: return None
    return titles[0], fr, end.isoformat()

def verify_championcross(url, it):  # comici の作品ページ「キャンペーンにつき N 話分無料 YYYY/MM/DD HH:MMまで」
    final, p = get(url.split("?")[0].rstrip("/"))  # 末尾/付きは別ページ扱いになる
    x = text(re.sub(r"<script.*?</script>|<style.*?</style>", "", p, flags=re.S))
    m = re.search(r"キャンペーンにつき\s*(\d+)\s*話分無料\s*(\d{4})/(\d{2})/(\d{2})\s*(\d{2}:\d{2})まで", x)
    if not m: return None
    end = datetime.date(int(m.group(2)), int(m.group(3)), int(m.group(4)))
    if m.group(5) == "00:00": end -= datetime.timedelta(days=1)
    vols = re.search(r"全(\d+)冊", x)
    it.update(freeEpisodes=int(m.group(1)), freeVolumes=0, allFree=False, endDate=end.isoformat(), url=final.split("?")[0],
              totalVolumes=int(vols.group(1)) if vols else None, cover=meta(p, "og:image"),
              catch=re.sub(r"^\S+・第\S+\s*", "", meta(p, "og:description"))[:60])
    if "freeLabel" in it and "最終" not in it["freeLabel"]: it.pop("freeLabel")  # 実サイトの話数を優先
    return it

VERIFIERS = [(r"https://championcross\.jp/(?:episodes|series)/\w+[^\s]*", verify_championcross),
             (r"https://piccoma\.com/web/product/(\d+)", lambda u, it: piccoma_detail(re.search(r"product/(\d+)", u).group(1)))]

def xcheck():
    out = []
    for h, (store, cat, need) in X_ACCOUNTS.items():
        try: posts = xposts(h)
        except Exception as e:
            X_FAILED[h] = "%s: %s" % (type(e).__name__, e); continue
        for p in posts:
            if (p.get("author") or {}).get("screen_name", "").lower() != h.lower() or p.get("reposted_by"): continue
            posted = datetime.datetime.fromtimestamp(p["created_timestamp"], JST)
            if posted < NOW - datetime.timedelta(days=X_DAYS) or (need and need not in p["text"]): continue
            r = x_parse(p["text"], posted)
            if not r: continue
            title, fr, end = r
            it = dict(title=title, author="", category=cat, store=store, freeVolumes=0, totalVolumes=None, allFree=False,
                      completed=False, endDate=end, catch="", tags=[], cover="", url=p["url"], basis="x", xPost=p["url"], xAccount=h)
            it.update(fr)
            for pat, fn in VERIFIERS:
                u = re.search(pat, p["text"])
                if u:
                    try: v = fn(u.group(0), dict(it))
                    except Exception: v = None
                    if not v: it = None; break  # 実サイトで確認できる媒体なのに確認できない → 載せない
                    v.update(title=title, basis="site", xPost=p["url"], xAccount=h, store=v.get("store", store)); it = v; break
            if it: out.append(it)
    if len(X_FAILED) == len(X_ACCOUNTS): raise RuntimeError("全アカウント取得失敗: %s" % X_FAILED)
    return out

def run_details(fn, xs):
    with cf.ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda x: _safe(fn, x), xs))
    return [r for r in res if r]

def _safe(fn, x):
    try: return fn(x)
    except Exception: return None

SOURCES = {"ebookjapan": ebookjapan, "ピッコマ": piccoma, "マガポケ": magapoke, "X告知": xcheck}
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
            if not got and name != "X告知": raise RuntimeError("0件（構造変更の可能性）")  # X は告知0件の日もある
            log["sources"][name] = {"ok": True, "count": len(got)}
            if name == "X告知":  # 取得に失敗したアカウントは前回分を引き継ぐ
                kept = [i for i in prev_real if i.get("xAccount") in X_FAILED and valid(i)]
                got += kept; log["sources"][name].update(failed=X_FAILED, kept_from_previous=len(kept),
                                                         items=[(i["store"], i["title"], i["basis"], i["xPost"]) for i in got])
        except Exception as e:
            got = [i for i in prev_real if (i.get("source") or i.get("store")) == name and valid(i)]
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
    auto = sorted({i["store"] for i in items if i.get("source") not in ("manual", "X告知")})
    xs = sorted({i["store"] for i in items if i.get("source") == "X告知"} - set(auto))
    man = sorted({i["store"] for i in items if i.get("source") == "manual"} - set(auto) - set(xs))
    data = {"updated": TODAY.isoformat(), "sample": False, "sources": auto, "xSources": xs, "manual": man, "items": items}
    tmp = DATA + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.load(open(tmp, encoding="utf-8"))
    os.replace(tmp, DATA)
    return 0

def x_test():  # python3 collect.py --test（実際の告知文で x_parse を確認）
    P = datetime.datetime(2026, 11, 20, 0, 0, 2, tzinfo=JST)
    assert x_parse("『ちひろさん』が今から96時間、全話無料です。", P)[2] == "2026-11-23"
    assert x_parse("『ちひろさん』11/20から96時間 全話無料です", P)[2] == "2026-11-23"
    assert x_parse("『Thisコミュニケーション』が 15話分無料‼️\n※12/3まで", P)[1:] == ({"freeEpisodes": 15}, "2026-12-03")
    assert x_parse("12/4 18:00まで 1巻完全無料\n『Villainな奥さま』", P)[1] == {"freeVolumes": 1}
    assert x_parse("『銀河英雄伝説』が今だけ5巻分無料", P) is None          # 期限なし
    assert x_parse("『A』『B』 全巻無料 11/30まで", P) is None              # 作品が2つ
    assert x_parse("『封神演義』11/27までは【第55〜70回】が無料", P) is None  # 範囲が読めない
    assert x_parse("※最終巻除く『ちひろさん』全話完全無料 11/24 0:00まで", P)[1:] == ({"allFree": False, "freeLabel": "全話無料（最終巻除く）"}, "2026-11-23")
    assert x_parse("『早乙女姉妹は漫画のためなら!?』が 全話無料‼️\n※ブラウザ版のみ・12/3まで", P)[1]["freeLabel"] == "全話無料（ブラウザ版のみ）"
    assert x_parse("『あせとせっけん』\n72時間限定【全話無料公開中】です！！\n※最新巻&以降の話を除く\n※期間は11/20（金）〜11/22（日）まで", P)[1:] == ({"allFree": False, "freeLabel": "全話無料（最新巻&以降の話を除く）"}, "2026-11-22")
    assert x_parse("『X』 15話無料 ※最終巻除く 12/3まで", P)[1]["freeLabel"] == "15話分無料（最終巻除く）"
    print("x_test ok")

if __name__ == "__main__":
    if "--test" in sys.argv: x_test(); sys.exit(0)
    sys.exit(main())
