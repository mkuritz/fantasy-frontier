/* Fantasy Frontier — NFL DFS lab (DraftKings). All projections are estimates. localStorage prefix: ffx_ */
(function(){
'use strict';
const LS='ffx_';
const $=(s,r=document)=>r.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ls={get:(k,d)=>{try{const v=localStorage.getItem(LS+k);return v==null?d:JSON.parse(v)}catch(e){return d}},set:(k,v)=>{try{localStorage.setItem(LS+k,JSON.stringify(v))}catch(e){}}};
const fmt$=n=>'$'+(n/1000).toFixed(1)+'k';
const f1=n=>(n==null?'–':(+n).toFixed(1));
const LOGO=`<svg width="34" height="34" viewBox="0 0 34 34" role="img" aria-label="Fantasy Frontier"><rect x="1" y="1" width="32" height="32" rx="8" fill="#161b33"/><path d="M7 25l7.5-14 5 8 3.2-5L27 25z" fill="#f59e0b"/><circle cx="24.5" cy="9.5" r="2.3" fill="#38bdf8"/></svg>`;
const SL_MARK=`<a class="sl-mark" href="https://mkuritz.github.io/sports-labs/" title="Sports Labs — all suites"><svg width="16" height="16" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#0b1220"/><path d="M9 21c2 2 4.5 3 7 3 3.3 0 6-1.6 6-4.4 0-5.6-12-3.4-12-8.6C10 8.6 12.6 7 15.6 7c2.2 0 4.2.8 5.6 2.2" stroke="#22d3ee" stroke-width="2.6" fill="none" stroke-linecap="round"/></svg>A Sports Labs product</a>`;
const KINDS={thu:'Thursday Night',sun:'Sunday Main',mon:'Monday Night'};
const PAGES=[['slate','Slate dashboard','M3 13h8V3H3zm10 8h8V11h-8zM3 21h8v-6H3zm10-18v6h8V3z'],['lineups','Recommended lineups','M4 6h16M4 12h16M4 18h10'],['players','Player pool','M16 11a4 4 0 1 0-8 0 4 4 0 0 0 8 0zM4 21c1-4 4-6 8-6s7 2 8 6'],['value','Value & leverage','M12 2v20M17 6H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'],['optimizer','Lineup optimizer','M12 3v3m0 12v3M3 12h3m12 0h3M6 6l2 2m8 8 2 2M6 18l2-2m8-8 2-2'],['games','Games & Vegas','M4 4h16v16H4zM4 12h16M12 4v16'],['method','How it works','M12 8v4m0 4h.01M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z']];
const ico=d=>`<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="${d}"/></svg>`;
const FEES={cash:{10:{l:.30},20:{l:.40},50:{l:.50},100:{l:.60}},gpp:{10:{g:.65,b:.30,noise:.10},20:{g:.55,b:.22,noise:.08},50:{g:.48,b:.15,noise:.06},100:{g:.40,b:.10,noise:.05}}};
const S={meta:null,slates:{},kind:ls.get('kind',null),page:'slate',lock:ls.get('lock',{}),excl:ls.get('excl',{}),opt:ls.get('opt',{contest:'gpp',fee:20,n:5,exp:60,uniq:2,stack:1,bring:1,minsal:49000,script:'any'}),results:null,rec:{},sort:ls.get('sort',['proj',-1]),flt:{pos:'ALL',team:'ALL',q:''}};

async function load(){
  const j=u=>fetch(u+'?v='+Date.now()).then(r=>r.ok?r.json():null).catch(()=>null);
  S.meta=await j('data/meta.json');
  for(const k of Object.keys(KINDS)){if(S.meta&&S.meta.slates&&(!S.meta.slates[k]||S.meta.slates[k].missing))continue;const d=await j('data/slate_'+k+'.json');if(d)S.slates[k]=d;}
  if(!S.kind||!S.slates[S.kind]){const now=Date.now();const ks=Object.keys(KINDS).filter(k=>S.slates[k]);
    const upcoming=ks.filter(k=>!S.slates[k].stale&&new Date(S.slates[k].start+'-04:00').getTime()>now-4*3600e3).sort((a,b)=>S.slates[a].start.localeCompare(S.slates[b].start));
    S.kind=upcoming[0]||ks[0]||'sun';}
  route();
}
const sl=()=>S.slates[S.kind];
const isSD=()=>sl()&&sl().type==='showdown';
const lockK=()=>S.kind+':'+(sl()?sl().dg:'');
const locks=()=>S.lock[lockK()]||{};const excls=()=>S.excl[lockK()]||{};
function shell(){
  const nav=PAGES.map(([id,l,d])=>`<button class="nav-btn" data-page="${id}" ${S.page===id?'aria-current="page"':''}>${ico(d)}${l}</button>`).join('');
  const segs=Object.keys(KINDS).map(k=>{const s=S.slates[k];const sub=s?(s.type==='showdown'?(s.games[0]?s.games[0].key:''):s.games.length+' games'):'not posted';return `<button data-kind="${k}" aria-pressed="${S.kind===k}">${k==='thu'?'TNF':k==='sun'?'Sunday':'MNF'}<span class="s">${esc(sub)}</span></button>`}).join('');
  const s=sl();const upd=S.meta?new Date(S.meta.updated):null;
  $('#app').innerHTML=`<aside class="sidebar" id="sidebar"><div class="brand">${LOGO}<div><div class="brand-name">Fantasy Frontier</div><div class="brand-sub">NFL DFS · DraftKings · Beta</div></div></div>
  <nav class="nav"><div class="nav-label">Slate tools</div>${nav}<div class="nav-label">Slates</div>${Object.keys(KINDS).map(k=>`<button class="nav-btn" data-kind="${k}" ${S.kind===k?'aria-current="page"':''}>${ico('M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z')}${KINDS[k]}${S.slates[k]?(S.slates[k].stale?'<span class="badge">last</span>':''):'<span class="badge">soon</span>'}</button>`).join('')}</nav>
  <div class="sidebar-foot">DraftKings salaries · nflverse · ESPN odds · Bet Lab props · Open-Meteo<br>Projections & ownership are <b>estimates</b>. Not affiliated with DraftKings. Play responsibly.<br>${SL_MARK}</div></aside>
  <header class="header"><button class="btn ghost menu-btn" id="menuBtn" aria-label="Menu">☰</button><div><h1>${esc((PAGES.find(p=>p[0]===S.page)||[])[1]||'')}</h1><div class="crumb">${esc(KINDS[S.kind])}${s?' · '+(s.type==='showdown'?'Showdown (CPT 1.5x)':'Classic $50k'):''}</div></div>
  <div class="header-actions"><div class="slate-seg" role="group" aria-label="Slate">${segs}</div><span class="badge-upd ${s&&s.stale?'stale':''} hide-m" title="Data updated"><span class="dot"></span>Data updated ${upd?upd.toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'–'}</span></div></header>
  <main class="main" id="main" tabindex="-1"></main>`;
  document.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>{location.hash=b.dataset.page;document.body.classList.remove('sidebar-open')});
  document.querySelectorAll('[data-kind]').forEach(b=>b.onclick=()=>{S.kind=b.dataset.kind;ls.set('kind',S.kind);S.results=null;document.body.classList.remove('sidebar-open');route()});
  $('#menuBtn').onclick=()=>document.body.classList.toggle('sidebar-open');
  $('#scrim').onclick=()=>document.body.classList.remove('sidebar-open');
}
function route(){S.page=(location.hash||'#slate').slice(1).split('/')[0];if(!PAGES.find(p=>p[0]===S.page))S.page='slate';shell();const m=$('#main');
  const s=sl();
  if(!s&&S.page!=='method'){m.innerHTML=noSlate();return}
  ({slate:pSlate,lineups:pLineups,players:pPlayers,value:pValue,optimizer:pOpt,games:pGames,method:pMethod})[S.page](m);m.scrollTop=0;}
function noSlate(){return `<div class="hero-ff"><div><h2>${esc(KINDS[S.kind])} salaries aren't posted yet</h2><p>DraftKings usually posts the next Thursday showdown early in the week. Fantasy Frontier checks every few hours and will load it automatically, so check back soon. Sunday and Monday slates are available now from the slate switcher.</p></div></div>`}
function staleNote(){const s=sl();let h='';if(s.stale)h+=`<div class="note warn">DraftKings hasn't posted a new ${esc(KINDS[S.kind])} slate yet. You're looking at the most recent one available (${esc(slDate(s))}).</div>`;
  const now=Date.now();if(!s.stale&&new Date(s.start+'-04:00').getTime()<now)h+=`<div class="note">This slate has locked (${esc(slDate(s))}). It stays up for review until the next one posts.</div>`;return h}
function slDate(s){const d=new Date(s.start+'-04:00');return d.toLocaleString([], {weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+' ET lock'}
const pool=()=>sl().players.filter(p=>p.sal);
const posTag=p=>`<span class="pos-tag pos-${p}">${p}</span>`;
const plCell=p=>`<span class="pl">${posTag(p.pos)}<span><b>${esc(p.name)}</b> <span class="t">${esc(p.team)} ${p.opp?'v '+esc(p.opp):''}${p.status&&p.status!=='Active'?` · <span style="color:var(--warn)">${esc(p.status)}</span>`:''}</span></span></span>`;
const lev=p=>Math.round((p.ceil/Math.max(1,(p.own||0)+3))*10)/10;
function openPlayer(id){const p=pool().find(x=>x.id===id);if(!p)return;const mx=Math.max(1,...(p.log||[1]));
  const st=p.st||{};const statl=p.pos==='DST'?`Opp implied ${f1(st.oitt)} · ${f1(st.sk)} sacks/g · ${f1(st.to)} takeaways/g`:p.pos==='K'?'':
   [st.py?`${st.py} pass yds, ${f1(st.ptd)} pass TD`:'',st.car?`${f1(st.car)} car, ${f1(st.ry)} rush yds`:'',st.tgt?`${f1(st.tgt)} tgt, ${f1(st.rec)} rec, ${f1(st.recy)} rec yds`:'',st.td?`${(+st.td).toFixed(2)} expected TDs`:''].filter(Boolean).join(' · ');
  const bg=document.createElement('div');bg.className='modal-bg';bg.innerHTML=`<div class="modal" role="dialog" aria-modal="true"><div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start"><div>${plCell(p)}</div><button class="btn sm" id="mx">← Back</button></div>
  <div class="grid kpis" style="margin-top:12px;grid-template-columns:repeat(4,1fr)"><div><div class="kpi-label">Salary</div><b class="mono">${fmt$(p.sal)}</b>${p.csal?`<div class="t" style="font-size:11px;color:var(--text-3)">CPT ${fmt$(p.csal)}</div>`:''}</div><div><div class="kpi-label">Proj<span class="est">est</span></div><b class="mono">${f1(p.proj)}</b></div><div><div class="kpi-label">Floor / Ceil</div><b class="mono">${f1(p.floor)} / ${f1(p.ceil)}</b></div><div><div class="kpi-label">Own proxy</div><b class="mono">${f1(p.own)}%</b></div></div>
  ${statl?`<p style="color:var(--text-2);font-size:13px;margin:12px 0 4px">Projected line: ${esc(statl)}</p>`:''}
  <h4 style="margin:12px 0 4px">Why he could outperform</h4>${(p.edges||[]).length?`<ul class="edge-list">${p.edges.map(e=>`<li>${esc(e)}</li>`).join('')}</ul>`:'<p style="color:var(--text-3);font-size:13px">No notable edge flags. Projection is driven by recent production.</p>'}
  ${p.inj?`<p class="note warn" style="margin-top:10px">${esc(p.inj)}</p>`:''}
  ${(p.log||[]).length?`<h4 style="margin:12px 0 6px">Recent DK points</h4><div class="spark">${p.log.map(v=>`<i title="${v}" style="height:${Math.max(3,40*v/mx)}px"></i>`).join('')}</div><div class="mono" style="font-size:11px;color:var(--text-3)">${p.log.join(' · ')}</div>`:''}
  <p style="font-size:11.5px;color:var(--text-3);margin-top:12px">Inputs: ${esc((p.src||[]).join(' · '))}. Matchup factor ×${p.mf??'–'}, Vegas factor ×${p.vegas??'–'}.</p>
  <div style="display:flex;gap:8px;margin-top:10px"><button class="btn sm" id="mlk">${locks()[p.id]?'Unlock':'Lock in optimizer'}</button><button class="btn sm danger" id="mex">${excls()[p.id]?'Include':'Exclude'}</button></div></div>`;
  document.body.appendChild(bg);history.pushState({m:1},'');const close=()=>{bg.remove()};
  bg.onclick=e=>{if(e.target===bg)history.back()};$('#mx',bg).onclick=()=>history.back();window.addEventListener('popstate',close,{once:true});
  $('#mlk',bg).onclick=()=>{toggle('lock',p.id);history.back();setTimeout(route,50)};$('#mex',bg).onclick=()=>{toggle('excl',p.id);history.back();setTimeout(route,50)};}
function toggle(kind,id){const o=S[kind];const k=lockK();o[k]=o[k]||{};if(o[k][id])delete o[k][id];else{o[k][id]=1;const other=kind==='lock'?S.excl:S.lock;if(other[k])delete other[k][id];}ls.set('lock',S.lock);ls.set('excl',S.excl);S.results=null;}
function bindRows(root){root.querySelectorAll('[data-pid]').forEach(el=>el.onclick=e=>{if(e.target.closest('button'))return;openPlayer(el.dataset.pid)});
  root.querySelectorAll('[data-lk]').forEach(b=>b.onclick=()=>{toggle(b.dataset.kd,b.dataset.lk);route()});}

/* ---------- Optimizer (integer program via javascript-lp-solver branch & bound) ---------- */
function score(p,cfg,rnd){let s;
  if(cfg.contest==='cash'){const l=FEES.cash[cfg.fee].l;s=p.proj+l*(p.floor-p.proj);}
  else if(cfg.contest==='bal'){s=p.proj+0.2*(p.ceil-p.proj)-0.05*p.proj*(p.own||0)/100;}
  else{const g=FEES.gpp[cfg.fee];s=p.proj+g.g*(p.ceil-p.proj)-g.b*p.proj*(p.own||0)/100;}
  if(rnd)s*=1+rnd*(Math.random()*2-1);return s;}
function prune(players,cfg,sd){const L=locks(),E=excls();const ok=players.filter(p=>!E[p.id]&&(p.proj>0.5||L[p.id]));
  if(sd)return ok.sort((a,b)=>score(b,cfg)-score(a,cfg)).slice(0,34).concat(ok.filter(p=>L[p.id])).filter((p,i,a)=>a.indexOf(p)===i);
  const lim={QB:14,RB:26,WR:38,TE:14,DST:12};const out=[];
  for(const pos of Object.keys(lim)){const arr=ok.filter(p=>p.pos===pos);const a=[...arr].sort((x,y)=>score(y,cfg)-score(x,cfg)).slice(0,lim[pos]);const b=[...arr].sort((x,y)=>score(y,cfg)/y.sal-score(x,cfg)/x.sal).slice(0,Math.ceil(lim[pos]/2));
    for(const p of a.concat(b,arr.filter(p=>L[p.id])))if(!out.includes(p))out.push(p);}
  return out;}
function solveOne(players,cfg,prev,expCount,n){const sd=isSD();const L=locks();const model={optimize:'score',opType:'max',constraints:{sal:{max:50000}},variables:{},ints:{}};const C=model.constraints;
  const capN=Math.max(1,Math.floor((cfg.exp/100)*n+1e-9));const banned=p=>(expCount[p.id]||0)>=capN&&!L[p.id];
  const rnd=cfg.contest==='gpp'&&n>1?FEES.gpp[cfg.fee].noise:(cfg.contest==='bal'&&n>1?0.04:0);
  if(!sd){C.sal.min=Math.min(cfg.minsal,49999);Object.assign(C,{QB:{equal:1},DST:{equal:1},RB:{min:2,max:3},WR:{min:3,max:4},TE:{min:1,max:2},FX:{equal:7}});
    const qbs=players.filter(p=>p.pos==='QB'&&!banned(p));
    for(const p of players){if(banned(p))continue;const v={score:score(p,cfg,rnd),sal:p.sal,[p.pos]:1,['u'+p.id]:1};if('RB WR TE'.includes(p.pos))v.FX=1;
      if(cfg.stack>0)for(const q of qbs){if(p.id===q.id)v['st'+q.id]=-cfg.stack;else if(p.team===q.team&&(p.pos==='WR'||p.pos==='TE'))v['st'+q.id]=1;
        if(cfg.bring){if(p.id===q.id)v['bb'+q.id]=-1;else if(p.team===q.opp&&'WR TE RB'.includes(p.pos))v['bb'+q.id]=1;}}
      prev.forEach((lu,i)=>{if(lu.includes(p.id))v['pv'+i]=1});
      model.variables[p.id]=v;model.ints[p.id]=1;C['u'+p.id]=L[p.id]?{equal:1}:{max:1};}
    if(cfg.stack>0)for(const q of qbs){C['st'+q.id]={min:0};if(cfg.bring)C['bb'+q.id]={min:0};}
    prev.forEach((lu,i)=>C['pv'+i]={max:9-cfg.uniq});
  }else{const teams=[...new Set(players.map(p=>p.team))];Object.assign(C,{CPT:{equal:1},FLEX:{equal:5}});C.sal.min=Math.min(cfg.minsal,49999);
    teams.forEach(t=>C['tm'+t]={min:1});
    const sc=cfg.script||'any';
    for(const p of players){if(banned(p))continue;const b=score(p,cfg,rnd);
      for(const slot of ['CPT','FLEX']){if(slot==='CPT'&&!p.cid)continue;const vid=slot+p.id;const v={score:slot==='CPT'?1.5*b:b,sal:slot==='CPT'?p.csal:p.sal,[slot]:1,['u'+p.id]:1,['tm'+p.team]:1};
        if(sc.startsWith('team:')&&p.team===sc.slice(5)){v.TS=1;if(slot==='CPT')v.TC=1;}
        if(sc==='shootout'&&p.pos==='QB')v.QBS=1;
        if(sc==='shootout'&&slot==='CPT'&&'QB WR TE'.includes(p.pos))v.SC=1;
        prev.forEach((lu,i)=>{if(lu.includes(vid))v['pv'+i]=1});
        model.variables[vid]=v;model.ints[vid]=1;C[vid+'_b']={max:1};v[vid+'_b']=1;}
      C['u'+p.id]=L[p.id]?{equal:1}:{max:1};}
    if(sc.startsWith('team:')){C.TS={min:4};C.TC={equal:1};}
    if(sc==='shootout'){C.QBS={min:2};C.SC={equal:1};}
    prev.forEach((lu,i)=>C['pv'+i]={max:6-cfg.uniq});}
  const r=solver.Solve(model);if(!r.feasible)return null;
  const ids=Object.keys(r).filter(k=>model.variables[k]&&r[k]>0.5);return ids;}
function buildLineup(ids){const P=pool();const byId=Object.fromEntries(P.map(p=>[p.id,p]));
  if(isSD()){const rows=ids.map(v=>{const slot=v.startsWith('CPT')?'CPT':'FLEX';const p=byId[v.slice(slot.length)];return {slot,p,sal:slot==='CPT'?p.csal:p.sal,pts:slot==='CPT'?1.5*p.proj:p.proj,fl:slot==='CPT'?1.5*p.floor:p.floor,cl:slot==='CPT'?1.5*p.ceil:p.ceil,own:p.own,dkid:slot==='CPT'?p.cid:p.id}});
    rows.sort((a,b)=>(a.slot==='CPT'?-1:1)-(b.slot==='CPT'?-1:1)||b.sal-a.sal);return finish(rows,ids);}
  const ps=ids.map(i=>byId[i]);const take=(pos,n)=>{const a=ps.filter(p=>p.pos===pos&&!p._u).sort((x,y)=>y.sal-x.sal).slice(0,n);a.forEach(p=>p._u=1);return a};
  const rows=[];take('QB',1).forEach(p=>rows.push({slot:'QB',p}));take('RB',2).forEach(p=>rows.push({slot:'RB',p}));take('WR',3).forEach(p=>rows.push({slot:'WR',p}));take('TE',1).forEach(p=>rows.push({slot:'TE',p}));
  ps.filter(p=>!p._u&&p.pos!=='DST').forEach(p=>{p._u=1;rows.push({slot:'FLEX',p})});take('DST',1).forEach(p=>rows.push({slot:'DST',p}));ps.forEach(p=>delete p._u);
  rows.forEach(r=>Object.assign(r,{sal:r.p.sal,pts:r.p.proj,fl:r.p.floor,cl:r.p.ceil,own:r.p.own,dkid:r.p.id}));return finish(rows,ids);}
function finish(rows,ids){const sum=k=>rows.reduce((a,r)=>a+(r[k]||0),0);return {rows,ids,sal:sum('sal'),proj:sum('pts'),floor:sum('fl'),ceil:sum('cl'),own:sum('own')};}
function optimize(cfg,n){const players=prune(pool(),cfg,isSD());const prev=[],out=[],exp={};
  for(let i=0;i<n;i++){const ids=solveOne(players,cfg,prev,exp,n);if(!ids)break;prev.push(ids);const lu=buildLineup(ids);out.push(lu);lu.rows.forEach(r=>exp[r.p.id]=(exp[r.p.id]||0)+1);}
  return out;}
function why(lu,kind){const r=lu.rows;const qb=r.find(x=>x.p.pos==='QB'&&x.slot!=='CPT')||r.find(x=>x.p.pos==='QB');const out=[];
  if(isSD()){const c=r[0];out.push(`Captain ${c.p.name} (${c.p.pos}): ${c.p.edges&&c.p.edges[0]?c.p.edges[0].toLowerCase():'highest 1.5x upside per dollar'}`);
    const tc={};r.forEach(x=>tc[x.p.team]=(tc[x.p.team]||0)+1);out.push('Game script: '+Object.entries(tc).map(([t,n])=>`${n} ${t}`).join(' / ')+(Object.values(tc).some(n=>n>=4)?' — leans on one side controlling the game':' — balanced shootout build'));}
  else if(qb){const st=r.filter(x=>x.p.team===qb.p.team&&x.p!==qb.p&&'WR TE'.includes(x.p.pos)).map(x=>x.p.name.split(' ').slice(-1)[0]);const bb=r.filter(x=>x.p.team===qb.p.opp&&'WR TE RB'.includes(x.p.pos)).map(x=>x.p.name.split(' ').slice(-1)[0]);
    if(st.length)out.push(`Stack: ${qb.p.name} + ${st.join(', ')}`+(bb.length?` with bring-back ${bb.join(', ')}`:''));}
  const vals=r.filter(x=>x.p.sal<=5000&&x.p.pos!=='DST').sort((a,b)=>b.p.val-a.p.val).slice(0,2);if(vals.length)out.push('Salary savers: '+vals.map(x=>`${x.p.name} (${fmt$(x.p.sal)}, ${x.p.val} pts/$1k)`).join(', '));
  return out;}
function luCard(lu,cls,title,sub,kind){return `<div class="lu ${cls}"><h3>${esc(title)}</h3><div class="sub">${esc(sub)}</div>${lu.rows.map(r=>`<div class="lu-row" data-pid="${r.p.id}" style="cursor:pointer"><span>${posTag(r.slot==='CPT'?'CPT':r.slot)}</span><span class="n"><b>${esc(r.p.name)}</b> <span style="color:var(--text-3);font-size:11.5px">${esc(r.p.team)} ${r.slot!==r.p.pos&&r.slot!=='DST'?esc(r.p.pos):''}</span></span><span class="mono" style="text-align:right">${fmt$(r.sal)}</span><span class="mono" style="text-align:right">${f1(r.pts)}</span></div>`).join('')}
  <div class="lu-foot"><span>Salary <b class="mono">${fmt$(lu.sal)}</b> / $50k</span><span>Proj <b class="mono">${f1(lu.proj)}</b></span><span>Floor–Ceil <b class="mono">${f1(lu.floor)}–${f1(lu.ceil)}</b></span><span>Own proxy <b class="mono">${Math.round(lu.own)}%</b></span></div>
  <ul class="edge-list">${why(lu,kind).map(w=>`<li>${esc(w)}</li>`).join('')}</ul></div>`;}
function recs(){const k=lockK();if(S.rec[k])return S.rec[k];const sd=isSD();
  const base={n:1,exp:100,uniq:1,minsal:sd?46000:48500,script:'any'};
  const safe=optimize(Object.assign({},base,{contest:'cash',fee:50,stack:sd?0:0,bring:0}),1)[0];
  const bal=optimize(Object.assign({},base,{contest:'bal',fee:20,stack:sd?0:1,bring:0}),1)[0];
  const up=optimize(Object.assign({},base,{contest:'gpp',fee:10,stack:sd?0:2,bring:1,script:sd?'shootout':'any'}),1)[0];
  return S.rec[k]={safe,bal,up};}
function recBlock(){const r=recs();const sd=isSD();if(!r.safe)return '<p>Not enough projected players to build lineups.</p>';
  return `<div class="lu-grid">${r.safe?luCard(r.safe,'safe','Safe · Cash / 50-50',sd?'Highest floor, CPT on the steadiest volume':'Built on floor: steady volume, no forced stacks','cash'):''}${r.bal?luCard(r.bal,'bal','Balanced · Single-entry',sd?'Best median outcome':'Median-optimal with a QB + 1 stack','bal'):''}${r.up?luCard(r.up,'up','Upside · GPP',sd?'Same-game-parlay logic: shootout script, pass-game CPT, ceiling over chalk':'QB + 2 stack with bring-back, ceiling and leverage over chalk','gpp'):''}</div>`;}

/* ---------- Pages ---------- */
function pSlate(m){const s=sl(),P=pool().filter(p=>p.proj>0);const sd=isSD();
  const topEdge=[...P].filter(p=>(p.edges||[]).length&&p.pos!=='DST').sort((a,b)=>(b.ceil-b.proj)/b.sal*1e3+b.val-((a.ceil-a.proj)/a.sal*1e3+a.val)).slice(0,6);
  const bargains=P.filter(p=>p.sal<=5000&&p.pos!=='DST'&&p.pos!=='K').sort((a,b)=>b.val-a.val).slice(0,6);
  const lev_=P.filter(p=>p.proj>=8).sort((a,b)=>lev(b)-lev(a)).slice(0,5);
  m.innerHTML=staleNote()+`<div class="hero-ff"><div><h2>${esc(KINDS[S.kind])} · ${sd?esc(s.games[0]?s.games[0].key:'Showdown'):s.games.length+'-game main slate'}</h2><p>${sd?'Showdown: 1 Captain at 1.5x salary and points, plus 5 FLEX, under a $50k cap. Treat it like a same-game parlay: pick the game script first, then the captain.':'Classic: QB, 2 RB, 3 WR, TE, FLEX, DST under a $50k cap. DK PPR scoring with 3-point bonuses at 300 passing, 100 rushing and 100 receiving yards.'} ${esc(slDate(s))}.</p></div>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><a class="btn primary" href="#optimizer">Open optimizer</a><a class="btn" href="#lineups">All lineups</a></div></div>
  <div class="grid kpis" style="margin-bottom:16px">${[['Players',P.length],['Games',s.games.length],['Top projection',P[0]?P[0].name.split(' ').slice(-1)[0]+' '+f1(P[0].proj):'–'],['Best value',[...P].filter(p=>p.proj>=8).sort((a,b)=>b.val-a.val)[0]?.name||'–'],['Injury cascades',(s.cascades||[]).length]].map(([l,v])=>`<div class="card kpi"><div class="kpi-label">${l}</div><div class="kpi-value" style="font-size:20px">${esc(v)}</div></div>`).join('')}</div>
  <div class="card" style="margin-bottom:16px"><div class="card-head"><h2>Recommended lineups <span class="est">estimates</span></h2><span class="sub">Safe for cash, Balanced, Upside for GPP</span></div>${recBlock()}</div>
  <div class="grid two" style="margin-bottom:16px"><div class="card"><div class="card-head"><h2>Biggest edges</h2><span class="sub">why they could outperform</span></div>${topEdge.map(p=>`<div data-pid="${p.id}" style="cursor:pointer;padding:8px 0;border-top:1px solid var(--border)">${plCell(p)} <span class="mono" style="float:right">${fmt$(p.sal)} · ${f1(p.proj)}</span><ul class="edge-list">${p.edges.slice(0,3).map(e=>`<li>${esc(e)}</li>`).join('')}</ul></div>`).join('')}</div>
  <div class="card"><div class="card-head"><h2>Bargains under $5k</h2><a href="#value" class="sub">all value plays →</a></div>${tbl(bargains,['sal','proj','val','own'])}<div class="card-head" style="margin-top:14px"><h2>Leverage plays</h2><span class="sub">high ceiling, low est. ownership</span></div>${tbl(lev_,['sal','ceil','own','lev'])}</div></div>
  ${(s.cascades||[]).length?`<div class="card"><div class="card-head"><h2>Injury cascades</h2><span class="sub">vacated opportunity redistributed to healthy teammates</span></div>${s.cascades.map(c=>`<span class="chip hot">${esc(c.team)}: ${esc(c.out)} out → ${c.vac} ${esc(c.kind)}/g up for grabs</span>`).join('')}</div>`:''}`;
  bindRows(m);}
const COLS={sal:['Salary',p=>fmt$(p.sal)],csal:['CPT $',p=>p.csal?fmt$(p.csal):'–'],proj:['Proj',p=>f1(p.proj)],floor:['Floor',p=>f1(p.floor)],ceil:['Ceil',p=>f1(p.ceil)],val:['Pts/$1k',p=>f1(p.val)],own:['Own*',p=>f1(p.own)+'%'],lev:['Lev',p=>f1(lev(p))]};
function tbl(arr,cols,ctl){return `<div class="table-wrap"><table class="tight"><thead><tr><th>Player</th>${cols.map(c=>`<th class="num ${ctl?'sortable':''}" data-s="${c}">${COLS[c][0]}</th>`).join('')}${ctl?'<th>Opt</th>':''}</tr></thead><tbody>${arr.map(p=>`<tr data-pid="${p.id}" class="${p.proj<=0?'out':''}" style="cursor:pointer"><td>${plCell(p)}</td>${cols.map(c=>`<td class="num">${COLS[c][1](p)}</td>`).join('')}${ctl?`<td style="white-space:nowrap"><button class="lk ${locks()[p.id]?'on':''}" data-lk="${p.id}" data-kd="lock">Lock</button> <button class="lk ex ${excls()[p.id]?'on':''}" data-lk="${p.id}" data-kd="excl">✕</button></td>`:''}</tr>`).join('')}</tbody></table></div>`;}
function pPlayers(m){const P=pool();const teams=[...new Set(P.map(p=>p.team))].sort();const poss=[...new Set(P.map(p=>p.pos))];const F=S.flt;
  const draw=()=>{let a=P.filter(p=>(F.pos==='ALL'||p.pos===F.pos)&&(F.team==='ALL'||p.team===F.team)&&(!F.q||p.name.toLowerCase().includes(F.q.toLowerCase())));
    const [k,d]=S.sort;const g=k==='lev'?lev:(p=>p[k]??0);a.sort((x,y)=>d*(g(x)-g(y)));
    $('#ptbl').innerHTML=tbl(a.slice(0,250),isSD()?['sal','csal','proj','floor','ceil','val','own','lev']:['sal','proj','floor','ceil','val','own','lev'],1)+`<p style="font-size:11.5px;color:var(--text-3)">${a.length} players. *Own = estimated ownership proxy from projected value and salary tier, not real contest ownership. Lev = ceiling ÷ (own proxy + 3).</p>`;
    $('#ptbl').querySelectorAll('th[data-s]').forEach(th=>th.onclick=()=>{S.sort=[th.dataset.s,S.sort[0]===th.dataset.s?-S.sort[1]:-1];ls.set('sort',S.sort);draw()});bindRows($('#ptbl'));
    $('#ptbl').querySelectorAll('[data-lk]').forEach(b=>b.onclick=()=>{toggle(b.dataset.kd,b.dataset.lk);draw()});};
  m.innerHTML=staleNote()+`<div class="filters"><select id="fp"><option value="ALL">All positions</option>${poss.map(p=>`<option ${F.pos===p?'selected':''}>${p}</option>`).join('')}</select><select id="ft"><option value="ALL">All teams</option>${teams.map(t=>`<option ${F.team===t?'selected':''}>${t}</option>`).join('')}</select><input id="fq" placeholder="Search player" value="${esc(F.q)}"><span style="color:var(--text-3);font-size:12px">Tap a player for edges · Lock/✕ feed the optimizer</span></div><div id="ptbl"></div>`;
  $('#fp').onchange=e=>{F.pos=e.target.value;draw()};$('#ft').onchange=e=>{F.team=e.target.value;draw()};$('#fq').oninput=e=>{F.q=e.target.value;draw()};draw();}
function pValue(m){const P=pool().filter(p=>p.proj>0&&p.pos!=='K');
  const val=[...P].filter(p=>p.proj>=6).sort((a,b)=>b.val-a.val).slice(0,15);const bar=P.filter(p=>p.sal<5000&&p.pos!=='DST').sort((a,b)=>b.val-a.val).slice(0,12);
  const ceil=[...P].sort((a,b)=>b.ceil-a.ceil).slice(0,12);const chalk=[...P].sort((a,b)=>b.own-a.own).slice(0,10);const levs=P.filter(p=>p.proj>=8).sort((a,b)=>lev(b)-lev(a)).slice(0,10);
  m.innerHTML=staleNote()+`<div class="note">Points per $1k = projected DK points ÷ salary in thousands. Around 3x is the usual cash target and 4x+ is a smash. Ownership is an <b>estimated proxy</b> built from projected value and salary tier, not real contest data.</div>
  <div class="grid two" style="margin-bottom:16px"><div class="card"><div class="card-head"><h2>Top value (pts per $1k)</h2></div>${tbl(val,['sal','proj','val','own'])}</div><div class="card"><div class="card-head"><h2>Bargains under $5k</h2></div>${tbl(bar,['sal','proj','floor','val'])}</div></div>
  <div class="grid two" style="margin-bottom:16px"><div class="card"><div class="card-head"><h2>Ceiling / GPP plays</h2><span class="sub">90th-percentile outcome</span></div>${tbl(ceil,['sal','proj','ceil','own'])}</div><div class="card"><div class="card-head"><h2>Chalk vs leverage</h2><span class="sub">likely most-played vs contrarian ceiling</span></div><h4 style="margin:0 0 6px;font-size:13px;color:var(--text-2)">Chalk (highest own proxy)</h4>${tbl(chalk,['sal','proj','own'])}<h4 style="margin:14px 0 6px;font-size:13px;color:var(--text-2)">Leverage (ceiling per ownership)</h4>${tbl(levs,['sal','ceil','own','lev'])}</div></div>`;bindRows(m);}
function pLineups(m){const sd=isSD();m.innerHTML=staleNote()+`<div class="note">Three ready-made builds per slate. <b>Safe</b> chases floor for cash and 50/50s. <b>Upside</b> chases ceiling and leverage for GPPs${sd?'. In showdown it works like a same-game parlay: pick a shootout script, captain a pass-game piece, and correlate both sides':' with a QB + 2 stack and a bring-back'}. Lineups update automatically with your locks and excludes. Tap any player for his edges.</div>${recBlock()}<p style="margin-top:14px"><button class="btn" id="exr">Export these 3 as DK CSV</button> <a class="btn primary" href="#optimizer">Customize in optimizer</a></p>`;bindRows(m);
  $('#exr').onclick=()=>{const r=recs();exportCSV([r.safe,r.bal,r.up].filter(Boolean))};}
function pOpt(m){const o=S.opt;const sd=isSD();const s=sl();const teams=[...new Set(pool().map(p=>p.team))];
  const L=Object.keys(locks()),E=Object.keys(excls());const byId=Object.fromEntries(pool().map(p=>[p.id,p]));
  m.innerHTML=staleNote()+`<div class="card" style="margin-bottom:16px"><div class="card-head"><h2>Settings</h2><span class="sub">${sd?'Showdown: CPT (1.5x) + 5 FLEX, both teams required':'Classic: QB · 2 RB · 3 WR · TE · FLEX · DST'}, $50,000 cap</span></div>
  <div class="ctl"><label>Contest type<select id="o-contest"><option value="cash" ${o.contest==='cash'?'selected':''}>Cash · 50/50 · double-up</option><option value="bal" ${o.contest==='bal'?'selected':''}>Balanced · single-entry</option><option value="gpp" ${o.contest==='gpp'?'selected':''}>GPP · tournament</option></select></label>
  <label>Entry fee tier<select id="o-fee">${[10,20,50,100].map(f=>`<option value="${f}" ${+o.fee===f?'selected':''}>$${f}</option>`).join('')}</select></label>
  <label>Lineups (N)<input id="o-n" type="number" min="1" max="40" value="${o.n}"></label><label>Max exposure %<input id="o-exp" type="number" min="10" max="100" step="5" value="${o.exp}"></label>
  <label>Min unique players vs other lineups<input id="o-uniq" type="number" min="1" max="${sd?4:6}" value="${o.uniq}"></label><label>Min salary used<input id="o-minsal" type="number" min="40000" max="50000" step="100" value="${o.minsal}"></label>
  ${sd?`<label>Game script<select id="o-script"><option value="any">Any</option><option value="shootout" ${o.script==='shootout'?'selected':''}>Shootout: both QBs, pass-game CPT</option>${teams.map(t=>`<option value="team:${t}" ${o.script==='team:'+t?'selected':''}>${t} controls game (4+ ${t}, ${t} CPT)</option>`).join('')}</select></label>`
  :`<label>QB stack (pass-catchers with QB)<select id="o-stack">${[0,1,2,3].map(n=>`<option value="${n}" ${+o.stack===n?'selected':''}>${n?'QB + '+n:'No stack'}</option>`).join('')}</select></label><label>Bring-back (opp. player)<select id="o-bring"><option value="0">Off</option><option value="1" ${+o.bring?'selected':''}>On</option></select></label>`}</div>
  <p id="riskTxt" style="font-size:12.5px;color:var(--text-2);margin:12px 0 0"></p>
  <p style="font-size:12.5px;color:var(--text-3)">Locked: ${L.length?L.map(i=>byId[i]?`<span class="chip cool">${esc(byId[i].name)}</span>`:'').join(''):'none'} · Excluded: ${E.length?E.map(i=>byId[i]?`<span class="chip">${esc(byId[i].name)}</span>`:'').join(''):'none'} · <a href="#players">set in Player pool</a>${L.length||E.length?' · <a href="#" id="clr">clear</a>':''}</p>
  <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" id="go">Generate lineups</button><button class="btn" id="csv" ${S.results&&S.results.length?'':'disabled'}>Export DK CSV</button></div></div><div id="res"></div>`;
  const risk=()=>{const c=$('#o-contest').value,f=$('#o-fee').value;$('#riskTxt').textContent=c==='cash'?`Cash at $${f}: weights floor ${Math.round(FEES.cash[f].l*100)}% toward the 20th-percentile outcome. Higher stakes means safer builds.`:c==='gpp'?`GPP at $${f}: pushes ${Math.round(FEES.gpp[f].g*100)}% toward ceiling, fades est. chalk by ${Math.round(FEES.gpp[f].b*100)}%, with ±${Math.round(FEES.gpp[f].noise*100)}% randomness for diverse lineups. Cheaper, bigger-field contests get more leverage.`:'Balanced: median projection with a light ceiling tilt.'};
  m.querySelectorAll('.ctl select,.ctl input').forEach(el=>el.onchange=()=>{read();risk()});risk();
  function read(){const g=id=>{const e=$('#o-'+id);return e?e.value:o[id]};Object.assign(o,{contest:g('contest'),fee:+g('fee'),n:Math.max(1,Math.min(40,+g('n'))),exp:+g('exp'),uniq:+g('uniq'),minsal:+g('minsal'),stack:+g('stack'),bring:+g('bring'),script:g('script')});ls.set('opt',o);}
  if($('#clr'))$('#clr').onclick=e=>{e.preventDefault();delete S.lock[lockK()];delete S.excl[lockK()];ls.set('lock',S.lock);ls.set('excl',S.excl);S.rec={};route()};
  $('#go').onclick=()=>{read();$('#go').textContent='Solving…';$('#res').innerHTML='<p style="color:var(--text-3)">Running the integer program…</p>';setTimeout(()=>{const t=performance.now();S.results=optimize(o,o.n);S.resT=Math.round(performance.now()-t);$('#go').textContent='Generate lineups';$('#csv').disabled=!S.results.length;drawRes()},30)};
  $('#csv').onclick=()=>exportCSV(S.results);if(S.results)drawRes();
  function drawRes(){const R=S.results;if(!R.length){$('#res').innerHTML='<div class="note warn">No valid lineup under these rules. Loosen the min salary, stack, exposure or locks.</div>';return}
    const ex={};R.forEach(lu=>lu.rows.forEach(r=>ex[r.p.id]=(ex[r.p.id]||0)+1));const exs=Object.entries(ex).sort((a,b)=>b[1]-a[1]).slice(0,16);
    $('#res').innerHTML=`<div class="card" style="margin-bottom:14px"><div class="card-head"><h2>${R.length} lineup${R.length>1?'s':''}</h2><span class="sub">solved in ${S.resT} ms · avg proj ${f1(R.reduce((a,l)=>a+l.proj,0)/R.length)}</span></div><div style="display:flex;flex-wrap:wrap;gap:4px">${exs.map(([id,n])=>{const p=pool().find(x=>x.id===id);return `<span class="chip ${n/R.length>=.5?'hot':''}">${esc(p.name)} ${Math.round(100*n/R.length)}%</span>`}).join('')}</div></div><div class="lu-grid">${R.map((lu,i)=>luCard(lu,o.contest==='cash'?'safe':o.contest==='gpp'?'up':'bal','Lineup '+(i+1),`${o.contest.toUpperCase()} · $${o.fee}`,o.contest)).join('')}</div>`;bindRows($('#res'));}}
function exportCSV(lus){if(!lus||!lus.length)return;const sd=isSD();const head=sd?['CPT','FLEX','FLEX','FLEX','FLEX','FLEX']:['QB','RB','RB','WR','WR','WR','TE','FLEX','DST'];
  const lines=[head.join(',')].concat(lus.map(lu=>{if(sd)return lu.rows.map(r=>r.dkid).join(',');const ord=[];const used=new Set();for(const h of head){const r=lu.rows.find(x=>x.slot===h&&!used.has(x));used.add(r);ord.push(r?r.dkid:'')}return ord.join(',')}));
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([lines.join('\n')+'\n'],{type:'text/csv'}));a.download=`fantasy-frontier-${S.kind}-${sl().dg}.csv`;document.body.appendChild(a);a.click();a.remove();}
function pGames(m){const s=sl();m.innerHTML=staleNote()+`<div class="gm">${s.games.map(g=>{const wx=g.wx||{};const P=pool().filter(p=>p.game===g.key&&p.proj>0).sort((a,b)=>b.proj-a.proj).slice(0,4);
  return `<div class="card"><div style="display:flex;justify-content:space-between"><b>${esc(g.away)} @ ${esc(g.home)}</b><span style="color:var(--text-3);font-size:12px">${g.time?new Date(g.time).toLocaleString([], {weekday:'short',hour:'numeric',minute:'2-digit'}):''}</span></div>
  <div style="font-size:13px;color:var(--text-2);margin:6px 0">${g.total?`Total <b class="mono">${g.total}</b> · ${esc(g.details||'')}<br>Implied: ${esc(g.away)} <b class="mono">${f1(g.itt_away)}</b> · ${esc(g.home)} <b class="mono">${f1(g.itt_home)}</b>`:'Lines not posted yet'}</div>
  <div style="font-size:12px;color:var(--text-3)">${wx.dome?'🏟 '+esc(wx.dome):wx.temp!=null?`${Math.round(wx.temp)}°F · wind ${Math.round(wx.wind)} mph · rain ${wx.pop}%`:'Forecast within 15 days of kickoff'}${(wx.flags||[]).map(f=>`<div style="color:var(--warn)">${esc(f)}</div>`).join('')}</div>
  <div style="margin-top:8px">${P.map(p=>`<span class="chip" data-pid="${p.id}" style="cursor:pointer">${esc(p.name.split(' ').slice(-1)[0])} ${f1(p.proj)}</span>`).join('')}</div></div>`}).join('')}</div>`;bindRows(m);}
function pMethod(m){const M=S.meta||{};const sm=M.slates||{};m.innerHTML=`<div class="card" style="margin-bottom:14px"><div class="card-head"><h2>How Fantasy Frontier projects players</h2><span class="est">all projections are estimates</span></div><div style="color:var(--text-2);font-size:13.5px;line-height:1.6">
  <p><b>Real data:</b> DraftKings salaries, positions and Captain/FLEX IDs come from DK's public lobby and salary export. Season game logs come from nflverse (weeks ${esc((M.log_weeks||[]).join(', '))}). Spreads and totals are DraftKings lines via ESPN, along with ESPN injury statuses, Open-Meteo kickoff weather, and Bet Lab's DraftKings player-prop lines and anytime-TD model where posted.</p>
  <p><b>Model (estimated):</b> each player's mean is built stat by stat (pass yds/TDs/INTs, rush yds, receptions, receiving yds and TDs). It starts from recency-weighted game logs and blends in prop lines as implied medians (65/35) when Bet Lab has them. It is then scaled by team implied total (Vegas), defense-vs-position (DK points allowed to that position, shrunk 50% toward league average), weather (wind over 15 mph or likely rain), and injury cascades (an out player's recent targets and carries go to healthy teammates). Bonus odds use a normal approximation. Floor is the 20th percentile and ceiling the 90th, from each player's game-to-game spread blended with a positional prior. DST uses the opponent's implied total mapped onto DK's points-allowed tiers, plus sack and takeaway rates.</p>
  <p><b>Ownership proxy:</b> not real ownership. It's a popularity estimate from value and salary tier, used only for chalk vs leverage.</p>
  <p><b>Scoring:</b> ${esc(M.scoring||'')}. Showdown Captain earns 1.5x points at 1.5x salary.</p>
  <p><b>Optimizer:</b> an exact integer program (branch and bound) solved in your browser. It handles the cap, roster slots, locks and excludes, max exposure, QB stacks, bring-backs, min unique players between lineups, and showdown game scripts. Contest type and entry fee set the risk profile. Cash leans on floor, and GPP leans on ceiling minus estimated chalk with some randomness.</p></div></div>
  <div class="card"><div class="card-head"><h2>Slate status</h2></div>${Object.keys(KINDS).map(k=>`<div style="padding:6px 0;border-top:1px solid var(--border);font-size:13px">${KINDS[k]}: ${sm[k]&&!sm[k].missing?`draft group ${sm[k].dg}, ${sm[k].n} players, ${sm[k].games} game(s)${sm[k].stale?' (most recent available, new slate not posted yet)':''}`:'not posted yet'}</div>`).join('')}<p style="font-size:12px;color:var(--text-3)">Refresh: a dispatcher runs about every 30 minutes and does a full rebuild overnight, when new DK salaries post, and before each lock. NHL DFS is next.</p></div>`;}
window.addEventListener('hashchange',()=>{if(!document.querySelector('.modal-bg'))route()});
load();
})();
