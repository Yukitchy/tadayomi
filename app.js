// 全案共通：data.json読込・締切セクション振り分け・絞り込み（ストア/出版社Web × 無料巻数）
// 各案は window.T = {card, pick, section?} で見た目だけ差し替える
const SECTIONS=[
  {id:"today",name:"今日で終了",sub:"今日まで",min:0,max:0},
  {id:"soon",name:"もうすぐ終了",sub:"あと1〜3日",min:1,max:3},
  {id:"week",name:"1週間以内",sub:"あと4〜7日",min:4,max:7},
  {id:"later",name:"まだ間に合う",sub:"8日以上",min:8,max:Infinity}
];
const STORES=[["","すべて"],["Kindle"],["BOOK☆WALKER"],["ebookjapan"],["コミックシーモア","シーモア"],["ピッコマ"],["LINEマンガ"],["少年ジャンプ＋","ジャンプ＋"],["@publisher","出版社Web"]];
const VOLS=[["all","全巻無料"],["5","5巻以上無料"],["3","3巻以上無料"]];
const DAY=864e5;
// ?today=YYYY-MM-DD で基準日を差し替え可（検証用）。既定は日本時間の今日
const todayStr=new URLSearchParams(location.search).get("today")||new Date(Date.now()+9*36e5).toISOString().slice(0,10);
const today=Date.parse(todayStr);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const md=end=>{const[,m,d]=end.split("-");return `${+m}/${+d}`};
const badge=it=>`<span class="badge${it.category==="publisher"?" pub":""}">${esc(it.store)}</span>`;
// freeEpisodes があれば話単位の無料（例：傑作エピソード54話分）
const volChip=it=>it.freeEpisodes?`<span class="vol">${it.freeEpisodes}話分無料</span>`:it.allFree?`<span class="vol all">全${it.totalVolumes}巻無料</span>`:`<span class="vol">${it.freeVolumes}/${it.totalVolumes}巻無料</span>`;
const leftText=it=>(it.days===0?"今日まで":"あと"+it.days+"日")+`（${md(it.endDate)}）`;
const leftChip=it=>`<span class="left${it.days<=3?" hot":""}">${leftText(it)}</span>`;
const doneChip=it=>it.completed?'<span class="done">完結</span>':"";
const tags=it=>it.tags.map(t=>`<span class="tag">${esc(t)}</span>`).join(" ");

let items=[],state={store:"",vol:""};
const $=id=>document.getElementById(id);
function match(it){
  const s=state.store;
  if(s==="@publisher"?it.category!=="publisher":s&&it.store!==s)return false;
  if(state.vol==="all")return it.allFree;
  if(state.vol)return it.freeVolumes>=+state.vol;
  return true;
}
function render(){
  const list=items.filter(match),p=list.filter(i=>i.allFree);
  $("pick").hidden=!p.length;
  $("pickList").innerHTML=p.map(T.pick).join("");
  $("sections").innerHTML=SECTIONS.map(sec=>{
    const xs=list.filter(i=>i.days>=sec.min&&i.days<=sec.max);
    if(!xs.length)return "";
    return T.section?T.section(sec,xs):`<section id="${sec.id}"><h2>${sec.name}<small>${sec.sub}・${xs.length}作品</small></h2><ul class="list">${xs.map(T.card).join("")}</ul></section>`;
  }).join("");
  $("empty").style.display=list.length?"none":"block";
}
function chips(rowId,key,defs,toggle){
  const row=$(rowId);
  row.innerHTML=defs.map(([v,l])=>`<button class="chip" data-${key}="${v}" aria-pressed="${!toggle&&v===""}">${l||v}</button>`).join("");
  row.addEventListener("click",e=>{
    const b=e.target.closest(".chip");if(!b)return;
    const v=b.dataset[key];
    state[key]=toggle&&state[key]===v?"":v;
    for(const c of row.children)c.setAttribute("aria-pressed",c.dataset[key]===state[key]&&(state[key]!==""||!toggle));
    render();
  });
}
// 実リンクのある項目だけカード全体をリンクにする（サンプルの url:"#" は今までどおり）
const card0=T.card;
T.card=it=>it.url&&it.url!=="#"?card0(it).replace('<li class="card">',`<li class="card linked"><a class="cardlink" href="${esc(it.url)}" target="_blank" rel="noopener" aria-label="${esc(it.title)}を読む"></a>`):card0(it);
chips("storeRow","store",STORES,false);
chips("volRow","vol",VOLS,true);
fetch("data.json").then(r=>r.json()).then(d=>{
  items=d.items.map(i=>({...i,days:Math.round((Date.parse(i.endDate)-today)/DAY)})).filter(i=>i.days>=0)
    .sort((a,b)=>a.days-b.days||a.title.localeCompare(b.title,"ja"));
  $("count").textContent=items.length;
  render();
});
