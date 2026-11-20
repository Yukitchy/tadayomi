# v1〜v5.html を生成（head・共通部品は共通、見た目は案ごと）。python3 build.py
BASE="https://yukitchy.github.io/tadayomi/"
HEAD='''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>タダヨミ {v}｜いま無料で読める漫画を、終了が近い順に</title>
<meta name="description" content="電子書店と出版社Webの無料漫画を、全巻無料と終了が近い順でまとめる試作版（{v}：{feat}）。">
<meta property="og:type" content="website">
<meta property="og:title" content="タダヨミ {v}｜いま無料の漫画を、終了が近い順に">
<meta property="og:description" content="電子書店と出版社Webの無料キャンペーンを横断。全巻無料をいちばん上に。">
<meta property="og:url" content="{base}{v}.html">
<meta property="og:image" content="{base}og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon.png" type="image/png">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">
<link rel="stylesheet" href="common.css">
<style>{css}</style>
</head>
<body class="{v}">
'''
NOTE='<span class="note">試作版：掲載データはサンプルです</span>'
FILTERS='<div class="filters"><div class="row" id="storeRow" aria-label="ストアで絞り込む"></div><div class="row vol" id="volRow" aria-label="無料巻数で絞り込む"></div></div>'
TAIL='''<main id="sections"></main>
<p id="empty">この条件で無料の作品はいまありません。</p>
{foot}
<script>{js}</script>
<script src="app.js"></script>
</body>
</html>
'''
FOOT='<footer>タダヨミ 試作版 {v} ／ 掲載データはサンプルです。無料期間・巻数は各ストアでご確認ください。表紙画像：AniList ／ <a href="./">5案の見比べに戻る</a></footer>'

V={}
# ---------- v1 縦リスト（模倣元に忠実・基準案）
V["v1"]=dict(feat="模倣元に忠実な縦リスト型（基準案）",css='''
.wrap{max-width:720px;margin:0 auto;padding:0 16px}
header{display:flex;align-items:center;gap:14px;padding:14px 0 12px;border-bottom:1px solid var(--line)}
header img{height:64px;width:auto}
.lead{font-size:13px;color:var(--sub)}.lead strong{color:var(--teal-d);font-size:16px}
header .note{margin-top:6px}
h2{font-size:18px;font-weight:800;display:flex;align-items:baseline;gap:8px}
h2 small{font-size:12px;font-weight:600;color:var(--sub)}
section{padding:22px 0 6px}
#pick{background:var(--yel-l);margin:0 -16px;padding:18px 16px 16px;border-bottom:1px solid #f1e3ad}
.strip{display:flex;gap:12px;overflow-x:auto;padding-top:12px;scroll-snap-type:x mandatory}
.pk{flex:0 0 120px;scroll-snap-align:start;text-decoration:none}
.pk img{width:120px;height:170px;object-fit:cover;border-radius:4px;background:var(--line)}
.pk .t{font-size:13px;font-weight:700;margin:6px 0 4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.pk .chips{margin-top:3px}
.filters{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);padding:10px 16px;margin:0 -16px}
.row+.row{margin-top:8px}
.list{list-style:none;margin-top:8px}
.card{display:flex;gap:12px;padding:12px 0;border-top:1px solid var(--line)}
.card:first-child{border-top:0}
.card img{flex:0 0 76px;width:76px;height:108px;object-fit:cover;border-radius:4px;background:var(--line)}
.card .b{min-width:0;flex:1}
.card .t{font-size:15px;font-weight:800;line-height:1.35;overflow-wrap:anywhere;margin-top:4px}
.card .a{font-size:12px;color:var(--sub)}.card .c{font-size:13px;margin-top:4px}
.card .chips:nth-of-type(2){margin-top:6px}.card .tags{margin-top:4px}
footer{margin-top:28px;padding:20px 0 40px;border-top:1px solid var(--line);font-size:12px;color:var(--sub)}
''',top='''<div class="wrap">
<header><img src="assets/logo.png" alt="タダヨミ" width="74" height="64"><div><p class="lead"><span class="nb">無料終了が近い順に毎日更新。</span><span class="nb">いま<strong id="count">–</strong>作品が無料</span></p>{note}</div></header>
<section id="pick"><h2>全巻無料ピックアップ<small>最後まで読める</small></h2><div class="strip" id="pickList"></div></section>
{filters}''',end='</div>',js='''window.T={
card:it=>`<li class="card"><img src="${esc(it.cover)}" alt="" loading="lazy" width="76" height="108"><div class="b"><div class="chips">${badge(it)}${doneChip(it)}</div><p class="t">${esc(it.title)}</p><p class="a">${esc(it.author)}</p><p class="c">${esc(it.catch)}</p><div class="chips">${volChip(it)}${leftChip(it)}</div><div class="tags">${tags(it)}</div></div></li>`,
pick:it=>`<a class="pk" href="${esc(it.url)}"><img src="${esc(it.cover)}" alt="" loading="lazy" width="120" height="170"><p class="t">${esc(it.title)}</p><div class="chips">${volChip(it)}</div><div class="chips">${leftChip(it)}</div></a>`};''')

# ---------- v2 表紙大きめグリッド
V["v2"]=dict(feat="表紙大きめのカードグリッド型",css='''
.wrap{max-width:960px;margin:0 auto;padding:0 12px}
header{text-align:center;padding:18px 0 14px}
header img{height:96px;width:auto;margin:0 auto}
.lead{font-size:13px;color:var(--sub);margin:6px 0}.lead strong{color:var(--teal-d);font-size:16px}
h2{font-size:19px;font-weight:800;display:flex;align-items:center;gap:8px}
h2::before{content:"";width:6px;height:20px;border-radius:3px;background:var(--teal);flex:none}
h2 small{font-size:12px;font-weight:600;color:var(--sub)}
section{padding:24px 0 4px}
#pick{background:var(--teal);color:#fff;margin:0 -12px;padding:20px 12px;border-radius:0}
#pick h2::before{background:var(--yel)}#pick h2 small{color:#d4f0f1}
.strip{display:flex;gap:12px;overflow-x:auto;padding-top:14px;scroll-snap-type:x mandatory}
.pk{flex:0 0 150px;scroll-snap-align:start;text-decoration:none;background:#fff;color:var(--ink);border-radius:10px;overflow:hidden}
.pk img{width:150px;height:212px;object-fit:cover;background:var(--line)}
.pk .t{font-size:13px;font-weight:800;padding:8px 8px 4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.pk .chips{padding:0 8px 10px}
.filters{position:sticky;top:0;z-index:5;background:#fff;padding:12px 12px 10px;margin:0 -12px;box-shadow:0 1px 0 var(--line)}
.row+.row{margin-top:8px}
.list{list-style:none;display:grid;grid-template-columns:repeat(auto-fill,minmax(136px,1fr));gap:16px 10px;margin-top:12px}
.card{min-width:0}
.card img{width:100%;aspect-ratio:5/7;height:auto;object-fit:cover;border-radius:8px;background:var(--line)}
.card .t{font-size:14px;font-weight:800;line-height:1.35;margin:8px 0 4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card .chips+.chips{margin-top:4px}
.cv{position:relative}.cv .badge{position:absolute;left:6px;top:6px;max-width:calc(100% - 12px);overflow:hidden;text-overflow:ellipsis;box-shadow:0 0 0 2px #fff}
footer{margin-top:32px;padding:20px 0 40px;border-top:1px solid var(--line);font-size:12px;color:var(--sub)}
''',top='''<div class="wrap">
<header><img src="assets/logo.png" alt="タダヨミ" width="111" height="96"><p class="lead"><span class="nb">無料終了が近い順。</span><span class="nb">いま<strong id="count">–</strong>作品が無料</span></p>{note}</header>
<section id="pick"><h2>全巻無料ピックアップ<small>最後まで読める</small></h2><div class="strip" id="pickList"></div></section>
{filters}''',end='</div>',js='''window.T={
card:it=>`<li class="card"><div class="cv"><img src="${esc(it.cover)}" alt="" loading="lazy" width="140" height="196">${badge(it)}</div><p class="t">${esc(it.title)}</p><div class="chips">${volChip(it)}${doneChip(it)}</div><div class="chips">${leftChip(it)}</div></li>`,
pick:it=>`<a class="pk" href="${esc(it.url)}"><img src="${esc(it.cover)}" alt="" loading="lazy" width="150" height="212"><p class="t">${esc(it.title)}</p><div class="chips">${volChip(it)}${leftChip(it)}</div></a>`};''')

# ---------- v3 コンパクト（情報密度・薄いヘッダー）
V["v3"]=dict(feat="情報密度を上げたコンパクト型（薄いヘッダー）",css='''
.wrap{max-width:760px;margin:0 auto}
header{display:flex;align-items:center;gap:8px;height:48px;padding:0 10px;border-bottom:2px solid var(--teal)}
header img{height:36px;width:auto}
.lead{font-size:12px;color:var(--sub);flex:1;min-width:0;white-space:nowrap}.lead strong{color:var(--teal-d);font-size:14px}
header .note{font-size:10px;padding:0 5px;white-space:nowrap}
h2{font-size:14px;font-weight:800;display:flex;align-items:baseline;gap:6px;background:var(--teal-l);color:var(--teal-d);padding:5px 10px}
h2 small{font-size:11px;font-weight:600;color:var(--sub)}
#pick h2{background:var(--yel);color:var(--ink)}#pick h2 small{color:var(--ink)}
.strip{display:flex;gap:8px;overflow-x:auto;padding:8px 10px}
.pk{flex:0 0 84px;text-decoration:none}
.pk img{width:84px;height:118px;object-fit:cover;border-radius:3px;background:var(--line)}
.pk .t{font-size:11px;font-weight:700;margin-top:3px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.pk .vol{font-size:10px;padding:0 4px}
.filters{position:sticky;top:0;z-index:5;background:#fff;padding:6px 10px;border-bottom:1px solid var(--line)}
.row+.row{margin-top:5px}
.chip{font-size:12px;padding:2px 9px}
.badge,.vol,.left,.done{font-size:11px;padding:0 4px}
.list{list-style:none}
.card{display:flex;gap:8px;padding:6px 10px;border-bottom:1px solid var(--line);align-items:center}
.card img{flex:0 0 40px;width:40px;height:56px;object-fit:cover;border-radius:2px;background:var(--line)}
.card .b{min-width:0;flex:1}
.card .t{font-size:13px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card .chips{gap:3px;margin-top:2px}
.card .a{font-size:11px;color:var(--sub);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
footer{padding:14px 10px 30px;font-size:11px;color:var(--sub)}
#empty{font-size:13px}
''',top='''<div class="wrap">
<header><img src="assets/mark.png" alt="タダヨミ" width="67" height="36"><p class="lead">いま<strong id="count">–</strong>作品が無料</p>{note}</header>
<section id="pick"><h2>全巻無料<small>最後まで読める</small></h2><div class="strip" id="pickList"></div></section>
{filters}''',end='</div>',js='''window.T={
card:it=>`<li class="card"><img src="${esc(it.cover)}" alt="" loading="lazy" width="40" height="56"><div class="b"><p class="t">${esc(it.title)}</p><p class="a">${esc(it.author)}${it.completed?"　完結":""}</p><div class="chips">${badge(it)}${volChip(it)}${leftChip(it)}</div></div></li>`,
pick:it=>`<a class="pk" href="${esc(it.url)}"><img src="${esc(it.cover)}" alt="" loading="lazy" width="84" height="118"><p class="t">${esc(it.title)}</p>${volChip(it)}</a>`};''')

# ---------- v4 雑誌・特集風（全巻無料が主役）
V["v4"]=dict(feat="全巻無料を主役にした雑誌・特集風",css='''
.wrap{max-width:880px;margin:0 auto;padding:0 16px}
.mast{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 0;border-bottom:3px double var(--ink)}
.mast img{height:52px;width:auto}
.mast .lead{font-size:12px;color:var(--sub);text-align:right}.mast strong{color:var(--teal-d);font-size:15px}
.mincho{font-family:"Hiragino Mincho ProN","Yu Mincho","Noto Serif JP",serif}
#pick{background:var(--teal);color:#fff;margin:0 -16px;padding:22px 16px 26px}
.kicker{font-size:12px;font-weight:700;letter-spacing:.2em;color:var(--yel)}
#pick h2{font-size:min(30px,8.4vw);font-weight:700;line-height:1.3;margin:4px 0 2px}
.dek{font-size:13px;color:#d4f0f1;margin-bottom:16px}
.strip{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:14px}
.pk{text-decoration:none;color:#fff;min-width:0}
.pk img{width:100%;aspect-ratio:5/7;height:auto;object-fit:cover;background:#0b7f87;box-shadow:0 6px 16px rgba(0,0,0,.18)}
.pk .t{font-size:14px;font-weight:700;margin:8px 0 4px;line-height:1.35}
.pk .c{font-size:12px;color:#d4f0f1;margin-bottom:6px}
.pk:first-child{grid-column:1/-1;display:grid;grid-template-columns:42% 1fr;gap:14px;align-items:end}
.pk:first-child .t{font-size:20px}
.pk:first-child .c{font-size:13px}
.pk .left{color:#fff;border-color:rgba(255,255,255,.5)}
.filters{position:sticky;top:0;z-index:5;background:#fff;padding:10px 16px;margin:0 -16px;border-bottom:1px solid var(--ink)}
.row+.row{margin-top:8px}
section{padding:26px 0 4px}
.sh{display:flex;align-items:baseline;gap:10px;border-bottom:1px solid var(--ink);padding-bottom:6px}
.sh .no{font-size:28px;font-weight:700;color:var(--teal);line-height:1}
.sh h2{font-size:20px;font-weight:700}
.sh small{font-size:12px;color:var(--sub);white-space:nowrap}
.list{list-style:none;display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:0 24px}
.card{display:flex;gap:12px;padding:14px 0;border-bottom:1px solid var(--line);min-width:0}
.card img{flex:0 0 72px;width:72px;height:102px;object-fit:cover;background:var(--line)}
.card .b{min-width:0}
.card .t{font-size:16px;font-weight:700;line-height:1.35}
.card .c{font-size:13px;color:var(--sub);margin:4px 0 6px}
.card .c::before{content:"“"}.card .c::after{content:"”"}
footer{margin-top:28px;padding:20px 0 40px;border-top:3px double var(--ink);font-size:12px;color:var(--sub)}
''',top='''<div class="wrap">
<header class="mast"><img src="assets/logo.png" alt="タダヨミ" width="60" height="52"><div class="lead">いま<strong id="count">–</strong>作品が無料<br>{note}</div></header>
<section id="pick"><p class="kicker">特集</p><h2 class="mincho">全巻、最後まで無料。</h2><p class="dek">完結まで一気に読める作品だけを集めました</p><div class="strip" id="pickList"></div></section>
{filters}''',end='</div>',js='''window.T={
section:(sec,xs)=>`<section id="${sec.id}"><div class="sh"><span class="no mincho">0${SECTIONS.indexOf(sec)+1}</span><h2 class="mincho">${sec.name}</h2><small>${sec.sub}・${xs.length}作品</small></div><ul class="list">${xs.map(T.card).join("")}</ul></section>`,
card:it=>`<li class="card"><img src="${esc(it.cover)}" alt="" loading="lazy" width="72" height="102"><div class="b"><p class="t mincho">${esc(it.title)}</p><p class="c">${esc(it.catch)}</p><div class="chips">${badge(it)}${volChip(it)}${leftChip(it)}</div></div></li>`,
pick:it=>`<a class="pk" href="${esc(it.url)}"><img src="${esc(it.cover)}" alt="" loading="lazy" width="130" height="182"><div><p class="t mincho">${esc(it.title)}</p><p class="c">${esc(it.catch)}</p><div class="chips">${volChip(it)}${leftChip(it)}</div></div></a>`};''')

# ---------- v5 ミニマル（余白広め・タイポ大きめ）
V["v5"]=dict(feat="余白広め・タイポ大きめのミニマル型",css='''
.wrap{max-width:640px;margin:0 auto;padding:0 24px}
header{padding:40px 0 28px}
header img{height:44px;width:auto}
.hl{font-size:30px;font-weight:800;line-height:1.3;letter-spacing:-.01em;margin:24px 0 10px}
.hl em{font-style:normal;color:var(--teal)}
.lead{font-size:14px;color:var(--sub);margin-bottom:12px}.lead strong{color:var(--ink)}
h2{font-size:24px;font-weight:800;display:flex;align-items:baseline;gap:10px}
h2 small{font-size:13px;font-weight:500;color:var(--sub)}
section{padding:56px 0 0}
#pick{padding-top:24px}
#pick h2{box-shadow:inset 0 -10px 0 var(--yel);display:inline-flex}
.strip{display:flex;gap:20px;overflow-x:auto;padding-top:24px}
.pk{flex:0 0 132px;text-decoration:none}
.pk img{width:132px;height:186px;object-fit:cover;background:var(--line)}
.pk .t{font-size:14px;font-weight:700;margin:12px 0 6px;line-height:1.4}
.filters{position:sticky;top:0;z-index:5;background:#fff;padding:14px 24px;margin:48px -24px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.row{gap:2px}.row+.row{margin-top:6px}
.chip{border:0;background:none;padding:4px 10px;color:var(--sub);border-radius:4px}
.chip[aria-pressed=true]{background:var(--teal-l);color:var(--teal-d)}
.row.vol .chip[aria-pressed=true]{background:var(--yel-l);color:var(--ink)}
.list{list-style:none;margin-top:16px}
.card{display:flex;gap:20px;padding:24px 0;border-top:1px solid var(--line)}
.card img{flex:0 0 64px;width:64px;height:90px;object-fit:cover;background:var(--line)}
.card .b{min-width:0}
.card .t{font-size:18px;font-weight:800;line-height:1.4;overflow-wrap:anywhere}
.card .meta{font-size:13px;color:var(--sub);margin-top:6px}
.card .meta b{color:var(--teal-d);font-weight:700}
footer{margin-top:72px;padding:24px 0 56px;font-size:12px;color:var(--sub)}
''',top='''<div class="wrap">
<header><img src="assets/logo.png" alt="タダヨミ" width="51" height="44"><p class="hl"><span class="nb">いま無料の漫画を、</span><span class="nb"><em>終了が近い順</em>に。</span></p><p class="lead">いま<strong id="count">–</strong>作品が無料</p>{note}</header>
<section id="pick"><h2>全巻無料</h2><div class="strip" id="pickList"></div></section>
{filters}''',end='</div>',js='''window.T={
card:it=>`<li class="card"><img src="${esc(it.cover)}" alt="" loading="lazy" width="64" height="90"><div class="b"><p class="t">${esc(it.title)}</p><p class="meta"><b>${leftText(it)}</b>　${esc(it.store)}${it.category==="publisher"?"（出版社）":""}　${it.allFree?"全"+it.totalVolumes+"巻無料":it.freeVolumes+"/"+it.totalVolumes+"巻無料"}${it.completed?"　完結":""}</p></div></li>`,
pick:it=>`<a class="pk" href="${esc(it.url)}"><img src="${esc(it.cover)}" alt="" loading="lazy" width="132" height="186"><p class="t">${esc(it.title)}</p><div class="chips">${volChip(it)}</div></a>`};''')

if __name__=="__main__":
  for v,d in V.items():
    html=HEAD.format(v=v,feat=d["feat"],base=BASE,css=d["css"])+d["top"].format(note=NOTE,filters=FILTERS)+"\n"+TAIL.format(foot=FOOT.format(v=v),js=d["js"]).replace("</main>","</main>",1)
    # end タグは main/empty/footer の後に閉じる
    html=html.replace("</footer>","</footer>\n"+d["end"],1)
    open(f"{v}.html","w").write(html)
  print("ok",list(V))
