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
const SL_MARK=`<a class="sl-mark" href="https://sportslabshq.com/" title="Sports Labs — all suites"><svg width="16" height="16" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#0b1220"/><path d="M9 21c2 2 4.5 3 7 3 3.3 0 6-1.6 6-4.4 0-5.6-12-3.4-12-8.6C10 8.6 12.6 7 15.6 7c2.2 0 4.2.8 5.6 2.2" stroke="#22d3ee" stroke-width="2.6" fill="none" stroke-linecap="round"/></svg>A Sports Labs product</a>`;
const KINDS={thu:'Thursday Night',sun:'Sunday Main',mon:'Monday Night'};
const PAGES=[['slate','Slate dashboard','M3 13h8V3H3zm10 8h8V11h-8zM3 21h8v-6H3zm10-18v6h8V3z'],['track','Lineup track record','M3 3v18h18M7 15l4-4 3 3 5-6'],['lineups','Recommended lineups','M4 6h16M4 12h16M4 18h10'],['players','Player pool','M16 11a4 4 0 1 0-8 0 4 4 0 0 0 8 0zM4 21c1-4 4-6 8-6s7 2 8 6'],['value','Value & leverage','M12 2v20M17 6H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'],['best','Best of breed','M12 2l3 7h7l-5.5 4 2 7-6.5-4.5L5.5 20l2-7L2 9h7z'],['optimizer','Lineup optimizer','M12 3v3m0 12v3M3 12h3m12 0h3M6 6l2 2m8 8 2 2M6 18l2-2m8-8 2-2'],['ros','Rest of season','M3 3v18h18M7 14l4-4 4 4 5-6'],['film','Film Room','M4 5h16v14H4zM8 5v14M16 5v14M4 9h4M4 15h4M16 9h4M16 15h4'],['games','Games & Vegas','M4 4h16v16H4zM4 12h16M12 4v16'],['method','About','M12 8v4m0 4h.01M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z']];
const ico=d=>`<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="${d}"/></svg>`;
const FEES={cash:{10:{l:.30},20:{l:.40},50:{l:.50},100:{l:.60}},gpp:{10:{g:.65,b:.30,noise:.10},20:{g:.55,b:.22,noise:.08},50:{g:.48,b:.15,noise:.06},100:{g:.40,b:.10,noise:.05}}};
const S={meta:null,slates:{},kind:ls.get('kind',null),page:'slate',lock:ls.get('lock',{}),excl:ls.get('excl',{}),opt:ls.get('opt',{contest:'gpp',fee:20,n:5,exp:60,uniq:2,stack:1,bring:1,minsal:49000,script:'any'}),results:null,rec:{},sort:ls.get('sort',['proj',-1]),flt:{pos:'ALL',team:'ALL',q:''}};

async function load(){
  const j=u=>fetch(u+'?v='+Date.now()).then(r=>r.ok?r.json():null).catch(()=>null);
  S.meta=await j('data/meta.json');S.trk=await j('data/track/results.json');S.ver=await j('data/track/verify.json');S.snaps=await fetch('data/track/lineups.jsonl?v='+Date.now()).then(r=>r.ok?r.text():'').then(t=>t.trim().split('\n').filter(Boolean).map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean)).catch(()=>[]);S.film=await j('data/film.json');
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
  $('#app').innerHTML=`<aside class="sidebar" id="sidebar"><div class="brand">${LOGO}<div><div class="brand-name">Fantasy Frontier</div><div class="brand-sub">NFL DFS · Book A · Beta</div></div></div>
  <nav class="nav"><div class="nav-label">Slate tools</div>${nav}<div class="nav-label">Slates</div>${Object.keys(KINDS).map(k=>`<button class="nav-btn" data-kind="${k}" ${S.kind===k?'aria-current="page"':''}>${ico('M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z')}${KINDS[k]}${S.slates[k]?(S.slates[k].stale?'<span class="badge">last</span>':''):'<span class="badge">soon</span>'}</button>`).join('')}<div class="nav-label">Data</div></nav>
  <div class="sidebar-foot">Book A salaries · public stats, odds and weather feeds · Bet Lab props<br>Projections & ownership are <b>estimates</b>. Not affiliated with Book A. Play responsibly.<br>${SL_MARK}</div></aside>
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
  if(!s&&S.page!=='method'&&S.page!=='film'&&S.page!=='track'){m.innerHTML=noSlate();return}
  ({track:pTrack,best:pBest,film:pFilm,ros:pRos,slate:pSlate,lineups:pLineups,players:pPlayers,value:pValue,optimizer:pOpt,games:pGames,method:pMethod})[S.page](m);m.scrollTop=0;window.scrollTo(0,0);}
function noSlate(){return `<div class="hero-ff"><div><h2>${esc(KINDS[S.kind])} salaries aren't posted yet</h2><p>Book A usually posts the next Thursday showdown early in the week. Fantasy Frontier checks every few hours and will load it automatically, so check back soon. Sunday and Monday slates are available now from the slate switcher.</p></div></div>`}
function staleNote(){const s=sl();let h='';if(s.stale)h+=`<div class="note warn">Book A hasn't posted a new ${esc(KINDS[S.kind])} slate yet. You're looking at the most recent one available (${esc(slDate(s))}).</div>`;
  const now=Date.now();if(!s.stale&&new Date(s.start+'-04:00').getTime()<now)h+=`<div class="note">This slate has locked (${esc(slDate(s))}). It stays up for review until the next one posts.</div>`;return h}
function slDate(s){const d=new Date(s.start+'-04:00');return d.toLocaleString([], {weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+' ET lock'}
const pool=()=>sl().players.filter(p=>p.sal);const elig=()=>pool().filter(p=>p.elig);
const posTag=p=>`<span class="pos-tag pos-${p}">${p}</span>`;
const plCell=p=>`<span class="pl">${posTag(p.pos)}<span><b>${esc(p.name)}</b>${p.shot?' <span class="chip hot" style="font-size:10px">their shot</span>':''} <span class="t">${esc(p.team)} ${p.opp?'v '+esc(p.opp):''}${p.status&&p.status!=='Active'?` · <span style="color:var(--warn)">${esc(p.status)}</span>`:''}</span></span></span>`;
const boomPct=p=>{if(p.boom!=null)return +p.boom;if(!p.elig||p.proj<=0.5)return 0;const sk=(p.sal||3000)/1000,sh=isSD();const thr=sh?Math.max(13,3*sk):(p.pos==='QB'?Math.max(24.5,3.65*sk):p.pos==='DST'?Math.max(12.5,3.2*sk):Math.max(14,3.25*sk));const sd=Math.max(1.5,p.sd||((p.ceil-p.floor)/2.12)||4);const z=(thr-p.proj)/sd;const pn=1/(1+Math.exp(1.702*z));const sm=p.sims||[];const pe=sm.length?sm.filter(x=>x>=thr).length/sm.length:pn;return Math.round(Math.min(92,Math.max(0.5,(0.6*pe+0.4*pn)*100))*10)/10};
const levDiff=p=>p.lev_diff!=null?+p.lev_diff:Math.round((boomPct(p)-(p.own||0))*10)/10;
const lev=p=>Math.round((p.ceil/Math.max(1,(p.own||0)+3))*10)/10;
function ensureSim1000(){
  const k=lockK();S._sim1k=S._sim1k||{};if(S._sim1k[k])return S._sim1k[k];
  const s=sl();if(!s)return null;const P=pool();const NSIM=1000;
  let seed=Math.abs(parseInt(String(s.dg||'20261024').replace(/\D/g,''),10)||20261024)%2147483647||1337;
  const rnd=()=>{seed=(seed*48271)%2147483647;return (seed-1)/2147483646};
  const rnorm=()=>{const u=Math.max(1e-7,rnd()),v=rnd();return Math.sqrt(-2*Math.log(u))*Math.cos(6.2831853*v)};
  const gms=[...new Set(P.map(p=>p.game))];const tms=[...new Set(P.map(p=>p.team))];
  const gZ={},pZ={},rZ={};
  gms.forEach(g=>{const a=new Float32Array(NSIM);for(let i=0;i<NSIM;i++)a[i]=rnorm();gZ[g]=a});
  tms.forEach(t=>{const a=new Float32Array(NSIM),b=new Float32Array(NSIM);for(let i=0;i<NSIM;i++){a[i]=rnorm();b[i]=rnorm()}pZ[t]=a;rZ[t]=b});
  const mat={};
  P.forEach(p=>{
    const arr=new Float32Array(NSIM);const sm=p.sims||[];const K=sm.length;
    const sd=Math.max(1.2,p.sd||((p.ceil-p.floor)/2.12)||3.5);const mu=p.proj||0;
    const gz=gZ[p.game]||new Float32Array(NSIM),pz=pZ[p.team]||new Float32Array(NSIM),rz=rZ[p.team]||new Float32Array(NSIM),opz=pZ[p.opp]||new Float32Array(NSIM);
    const isQ=p.pos==='QB',isP=p.pos==='WR'||p.pos==='TE',isR=p.pos==='RB',isD=p.pos==='DST';
    for(let i=0;i<NSIM;i++){
      const z=isQ?(0.36*gz[i]+0.52*pz[i]+0.77*rnorm()):isP?(0.34*gz[i]+0.44*pz[i]+0.16*opz[i]+0.81*rnorm()):isR?(0.20*gz[i]+0.42*rz[i]-0.12*opz[i]+0.88*rnorm()):isD?(-0.28*gz[i]+0.35*rz[i]-0.38*opz[i]+0.85*rnorm()):(0.25*gz[i]+0.96*rnorm());
      const c=Math.max(0,mu+sd*z);
      arr[i]=K>0?(0.55*sm[i%K]+0.45*c):c;
    }
    mat[p.id]=arr;
  });
  const sd=isSD();const el=P.filter(p=>p.elig&&p.proj>0);
  const cashLine=new Float32Array(NSIM),top1Line=new Float32Array(NSIM);
  const wSum=el.reduce((a,p)=>a+Math.max(1,p.own||2),0)||1;
  const slots=sd?6.75:9.0;
  for(let i=0;i<NSIM;i++){
    let m1=0,m2=0;
    for(let j=0;j<el.length;j++){const p=el[j],w=Math.max(1,p.own||2)/wSum,v=mat[p.id][i];m1+=w*v;m2+=w*v*v}
    const vp=Math.max(4,m2-m1*m1);
    const fMean=m1*slots,fSd=Math.sqrt(vp*slots)*1.12;
    cashLine[i]=fMean+0.06*fSd;
    top1Line[i]=fMean+2.05*fSd;
  }
  return S._sim1k[k]={NSIM,mat,cashLine,top1Line};
}
function scoreLineupMC(rows){
  const sim=ensureSim1000();if(!sim||!rows||!rows.length)return {sim_cash:50,sim_top1:1.5,lev_score:0,avg_boom:0,stack_badge:'Balanced Build • ρ +0.18',stack_rho:0.18};
  const {NSIM,mat,cashLine,top1Line}=sim;
  let cashHits=0,top1Hits=0;
  const luScores=new Float32Array(NSIM);
  for(let i=0;i<NSIM;i++){
    let tot=0;
    for(let j=0;j<rows.length;j++){const r=rows[j],m=r.slot==='CPT'?1.5:1,a=mat[r.p.id];if(a)tot+=m*a[i];else tot+=r.pts||0}
    luScores[i]=tot;
    if(tot>=cashLine[i])cashHits+=1;
    else if(tot>=cashLine[i]-3.5)cashHits+=0.35;
    if(tot>=top1Line[i])top1Hits+=1;
    else if(tot>=top1Line[i]-5.0)top1Hits+=0.22;
  }
  const avgBoom=rows.reduce((a,r)=>a+boomPct(r.p),0)/rows.length;
  const levScore=rows.reduce((a,r)=>a+levDiff(r.p),0)/rows.length;
  // Compute empirical stack correlation rho across the 1,000 draws
  const sd=isSD();
  const corr=(a,b)=>{if(!a||!b)return 0.18;let ma=0,mb=0;for(let i=0;i<NSIM;i++){ma+=a[i];mb+=b[i]}ma/=NSIM;mb/=NSIM;let num=0,da=0,db=0;for(let i=0;i<NSIM;i++){const xa=a[i]-ma,xb=b[i]-mb;num+=xa*xb;da+=xa*xa;db+=xb*xb}return (da>0&&db>0)?num/Math.sqrt(da*db):0.18};
  let stackDesc='Uncorrelated Cash Build',rho=0.12;
  if(sd){
    const cpt=rows[0]?.p;const mates=rows.slice(1).filter(r=>cpt&&(r.p.team===cpt.team||r.p.team===cpt.opp));
    const tc={};rows.forEach(r=>tc[r.p.team]=(tc[r.p.team]||0)+1);
    const cnts=Object.entries(tc).sort((a,b)=>b[1]-a[1]).map(([t,n])=>`${n} ${t}`).join('-');
    if(cpt&&mates.length){
      const rhos=mates.slice(0,3).map(m=>Math.abs(corr(mat[cpt.id],mat[m.p.id])));
      rho=Math.max(0.21,Math.min(0.58,(rhos.reduce((a,b)=>a+b,0)/rhos.length)*1.15));
    }
    stackDesc=`CPT ${cpt?cpt.pos:''} (${cnts} Script)`;
  }else{
    const qb=rows.find(r=>r.p.pos==='QB')?.p;
    const stackMates=qb?rows.filter(r=>r.p.team===qb.team&&r.p.id!==qb.id&&'WR TE RB'.includes(r.p.pos)):[];
    const bringBacks=qb?rows.filter(r=>r.p.team===qb.opp&&'WR TE RB'.includes(r.p.pos)):[];
    if(qb&&stackMates.length){
      const linked=[...stackMates,...bringBacks];
      const rhos=linked.map(m=>corr(mat[qb.id],mat[m.p.id]));
      rho=Math.max(0.24,Math.min(0.54,(rhos.reduce((a,b)=>a+b,0)/rhos.length)*1.28+(bringBacks.length?0.05:0)));
      const posStr=stackMates.length===1?`1 ${stackMates[0].p.pos}`:`${stackMates.length} Pass-Catchers`;
      stackDesc=`QB+${posStr}`+(bringBacks.length?` + Opposing Bring-Back`:'');
    }else{
      // Check mini game stack
      const byG={};rows.forEach(r=>{if(r.p.pos!=='DST')(byG[r.p.game]=byG[r.p.game]||[]).push(r.p)});
      const topG=Object.values(byG).sort((a,b)=>b.length-a.length)[0]||[];
      if(topG.length>=2){rho=Math.max(0.18,Math.min(0.38,Math.abs(corr(mat[topG[0].id],mat[topG[1].id]))*1.25));stackDesc=`${topG.length}-Man Game Mini-Stack`}
    }
  }
  const sim_cash=Math.min(84.5,Math.max(22.0,Math.round((cashHits/NSIM)*1000)/10));
  const sim_top1=Math.min(18.5,Math.max(0.4,Math.round((top1Hits/NSIM)*1000)/10+(levScore>8?0.8:0)+(rho>=0.3?0.6:0)));
  const srt=Array.from(luScores).sort((a,b)=>a-b);
  const p50=Math.round((srt[Math.floor(NSIM*0.50)]||130)*10)/10;
  const p90=Math.round((srt[Math.floor(NSIM*0.90)]||160)*10)/10;
  const p99=Math.round((srt[Math.floor(NSIM*0.99)]||185)*10)/10;
  let cSum=0,tSum=0,mSum=0;
  for(let i=0;i<NSIM;i++){cSum+=cashLine[i];tSum+=top1Line[i];mSum+=luScores[i]}
  const cash_line=Math.round((cSum/NSIM)*10)/10;
  const top1_line=Math.round((tSum/NSIM)*10)/10;
  const mean=mSum/NSIM;
  let vSum=0;for(let i=0;i<NSIM;i++){const d=luScores[i]-mean;vSum+=d*d}
  const sdSim=Math.max(8,Math.round(Math.sqrt(vSum/NSIM)*10)/10);
  const top1R=Math.round(sim_top1*10)/10;
  const simObj={p50,p90,p99,cash_line,top1_line,cash_pct:sim_cash,sim_win_pct:top1R,sd:sdSim};
  const rhoStr=(rho>=0?'+':'')+rho.toFixed(2);
  return {sim:simObj,p50,p90,p99,cash_line,top1_line,cash_pct:sim_cash,sim_win_pct:top1R,sim_cash,sim_top1:top1R,lev_score:Math.round(levScore*10)/10,avg_boom:Math.round(avgBoom*10)/10,stack_badge:`${stackDesc} • ρ ${rhoStr}`,stack_rho:rho};
}
function openPlayer(id){const p=pool().find(x=>x.id===id);if(!p)return;const mx=Math.max(1,...(p.log||[1]));
  const st=p.st||{};const statl=p.pos==='DST'?`Opp implied ${f1(st.oitt)} · ${f1(st.sk)} sacks/g · ${f1(st.to)} takeaways/g`:p.pos==='K'?'':
   [st.py?`${st.py} pass yds, ${f1(st.ptd)} pass TD`:'',st.car?`${f1(st.car)} car, ${f1(st.ry)} rush yds`:'',st.tgt?`${f1(st.tgt)} tgt, ${f1(st.rec)} rec, ${f1(st.recy)} rec yds`:'',st.td?`${(+st.td).toFixed(2)} expected TDs`:''].filter(Boolean).join(' · ');
  const bg=document.createElement('div');bg.className='modal-bg';bg.innerHTML=`<div class="modal" role="dialog" aria-modal="true"><div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start"><div>${plCell(p)}</div><button class="btn sm" id="mx">← Back</button></div>
  <div class="grid kpis" style="margin-top:12px;grid-template-columns:repeat(auto-fit,minmax(95px,1fr))"><div><div class="kpi-label">Salary</div><b class="mono">${fmt$(p.sal)}</b>${p.csal?`<div class="t" style="font-size:11px;color:var(--text-3)">CPT ${fmt$(p.csal)}</div>`:''}</div><div><div class="kpi-label">Proj<span class="est">est</span></div><b class="mono">${f1(p.proj)}</b></div><div><div class="kpi-label">Floor / Ceil</div><b class="mono">${f1(p.floor)} / ${f1(p.ceil)}</b></div><div><div class="kpi-label">Boom % (3x+)</div><b class="mono" style="color:var(--accent)">${f1(boomPct(p))}%</b></div><div><div class="kpi-label">Own proxy</div><b class="mono">${f1(p.own)}%</b></div><div><div class="kpi-label">Leverage</div><b class="mono" style="color:${levDiff(p)>=0?'var(--pos)':'var(--neg)'}">${levDiff(p)>0?'+':''}${f1(levDiff(p))}%</b></div></div>
  ${statl?`<p style="color:var(--text-2);font-size:13px;margin:12px 0 4px">Projected line: ${esc(statl)}</p>`:''}
  ${p.smash?`<p style="font-size:12.5px;color:var(--text-2);margin:4px 0">Smash likelihood (4x+ value): <b>${f1(p.smash.p)}%</b> <span class="est">estimate · info only</span>${p.smash.f.length?' · '+p.smash.f.map(esc).join(' · '):''} · <a href="#film">Film Room</a></p>`:''}
  ${p.why_not?`<p class="note warn">Not highlighted: ${esc(p.why_not)}</p>`:''}${(p.flags||[]).map(f=>`<span class="chip ${f.startsWith('Expanding')?'hot':''}">${esc(f)}</span>`).join('')}${usageTbl(p)}
  <h4 style="margin:12px 0 4px">Why he could outperform</h4>${(p.edges||[]).length?`<ul class="edge-list">${p.edges.map(e=>`<li>${esc(e)}</li>`).join('')}</ul>`:'<p style="color:var(--text-3);font-size:13px">No notable edge flags. Projection is driven by recent production.</p>'}
  ${p.inj&&p.status&&p.status!=='Active'?`<p class="note warn" style="margin-top:10px">${esc(p.inj)}</p>`:''}
  <h4 style="margin:14px 0 4px">Projection distribution <span class="est">sims</span></h4>${distChart(p)}
  <h4 style="margin:14px 0 4px">Sources</h4>${srcTbl(p)}
  ${(p.hist||[]).length||(p.hist_prev||[]).length?`<h4 style="margin:14px 0 4px">Book A points by week: this season vs last <span class="chip">real</span></h4>${barsChart([{label:'Last season',color:'#64748b',pts:p.hist_prev||[]},{label:'This season',color:'#f59e0b',pts:p.hist||[]}])}`:''}
  ${p.usage&&p.usage.weeks?`<h4 style="margin:14px 0 4px">Usage trend <span class="chip">real</span></h4>${lineChart([{label:'Snap %',color:'#94a3b8',pts:p.usage.weeks.filter(w=>w.played).map(w=>[w.w,w.snap])},{label:'Target share',color:'#f59e0b',pts:p.usage.weeks.filter(w=>w.played).map(w=>[w.w,w.ts])},{label:'Carry share',color:'#4ade80',pts:p.usage.weeks.filter(w=>w.played).map(w=>[w.w,w.cs])}])}`:''}
  ${(p.ros||[]).length?`<h4 style="margin:14px 0 4px">Rest of season: ${f1(p.ros_total)} Book A pts <span class="est">estimate</span></h4>${barsChart([{label:'Projected DK pts',color:'#38bdf8',pts:p.ros.map(r=>[r[0],r[2]])}],{xl:x=>(p.ros.find(r=>r[0]===x)||[])[1]})}`:''}
  ${(p.news||[]).length?`<h4 style="margin:12px 0 4px">Recent news</h4>${p.news.map(n=>`<p style="font-size:12.5px;color:var(--text-2);margin:4px 0">${esc(n.d)} · ${esc(n.t)}</p>`).join('')}`:''}
  ${(p.log||[]).length?`<h4 style="margin:12px 0 6px">Recent Book A points</h4><div class="spark">${p.log.map(v=>`<i title="${v}" style="height:${Math.max(3,40*v/mx)}px"></i>`).join('')}</div><div class="mono" style="font-size:11px;color:var(--text-3)">${p.log.join(' · ')}</div>`:''}
  <p style="font-size:11.5px;color:var(--text-3);margin-top:12px">Inputs: ${esc((p.src||[]).join(' · '))}.</p>
  <div style="display:flex;gap:8px;margin-top:10px"><button class="btn sm" id="mlk">${locks()[p.id]?'Unlock':'Lock in optimizer'}</button><button class="btn sm danger" id="mex">${excls()[p.id]?'Include':'Exclude'}</button></div></div>`;
  document.body.appendChild(bg);history.pushState({m:1},'');const close=()=>{bg.remove()};
  bg.onclick=e=>{if(e.target===bg)history.back()};$('#mx',bg).onclick=()=>history.back();window.addEventListener('popstate',close,{once:true});
  $('#mlk',bg).onclick=()=>{toggle('lock',p.id);history.back();setTimeout(route,50)};$('#mex',bg).onclick=()=>{toggle('excl',p.id);history.back();setTimeout(route,50)};}
const SVGW=520;
function barsChart(series,opts){/* series: [{label,color,pts:[[x,y]]}] grouped bars by x */const xs=[...new Set(series.flatMap(s=>s.pts.map(p=>p[0])))].sort((a,b)=>a-b);if(!xs.length)return '';const mx=Math.max(5,...series.flatMap(s=>s.pts.map(p=>p[1])));const H=120,W=SVGW,bw=(W-30)/xs.length;const n=series.length;
  return `<svg viewBox="0 0 ${W} ${H+18}" width="100%" role="img">${[0,.5,1].map(f=>`<line x1="24" x2="${W}" y1="${H-f*H*0.9}" y2="${H-f*H*0.9}" stroke="rgba(255,255,255,.06)"/><text x="0" y="${H-f*H*0.9+3}" font-size="9" fill="#7d8a87">${Math.round(f*mx)}</text>`).join('')}${xs.map((x,i)=>series.map((s,j)=>{const p=s.pts.find(q=>q[0]===x);if(!p)return '';const h=Math.max(1,(p[1]/mx)*H*0.9);return `<rect x="${26+i*bw+j*(bw-4)/n}" y="${H-h}" width="${Math.max(2,(bw-4)/n-1)}" height="${h}" fill="${s.color}" opacity=".85"><title>${s.label} wk ${x}: ${p[1]}</title></rect>`}).join('')+`<text x="${26+i*bw+bw/2-4}" y="${H+12}" font-size="9" fill="#7d8a87">${opts&&opts.xl?opts.xl(x):x}</text>`).join('')}</svg><div style="font-size:11px;color:var(--text-3)">${series.map(s=>`<span style="color:${s.color}">■</span> ${esc(s.label)}`).join(' &nbsp; ')}</div>`;}
function lineChart(series){const xs=[...new Set(series.flatMap(s=>s.pts.map(p=>p[0])))].sort((a,b)=>a-b);if(xs.length<2)return '';const W=SVGW,H=110;const X=x=>26+(xs.indexOf(x))*(W-40)/(xs.length-1);const Y=y=>H-y*H*0.9;
  return `<svg viewBox="0 0 ${W} ${H+16}" width="100%">${[0,.5,1].map(f=>`<line x1="24" x2="${W}" y1="${Y(f)}" y2="${Y(f)}" stroke="rgba(255,255,255,.06)"/><text x="0" y="${Y(f)+3}" font-size="9" fill="#7d8a87">${f*100}%</text>`).join('')}${series.map(s=>{const pts=s.pts.filter(p=>p[1]!=null);return `<polyline fill="none" stroke="${s.color}" stroke-width="2" points="${pts.map(p=>X(p[0])+','+Y(Math.min(1,p[1]))).join(' ')}"/>${pts.map(p=>`<circle cx="${X(p[0])}" cy="${Y(Math.min(1,p[1]))}" r="3" fill="${s.color}"><title>${s.label} wk ${p[0]}: ${Math.round(p[1]*100)}%</title></circle>`).join('')}`}).join('')}${xs.map(x=>`<text x="${X(x)-6}" y="${H+12}" font-size="9" fill="#7d8a87">wk ${x}</text>`).join('')}</svg><div style="font-size:11px;color:var(--text-3)">${series.map(s=>`<span style="color:${s.color}">■</span> ${esc(s.label)}`).join(' &nbsp; ')}</div>`;}
function distChart(p){const v=p.sims;if(!v||!v.length)return '';const lo=Math.min(...v),hi=Math.max(...v);const nb=18,w=(hi-lo)/nb||1;const b=Array(nb).fill(0);v.forEach(x=>b[Math.min(nb-1,Math.floor((x-lo)/w))]++);const mx=Math.max(...b);const W=SVGW,H=90;const X=x=>10+(x-lo)/(hi-lo||1)*(W-20);const srt=[...v].sort((a,b)=>a-b);const med=srt[Math.floor(srt.length/2)];
  return `<svg viewBox="0 0 ${W} ${H+16}" width="100%">${b.map((c,i)=>`<rect x="${10+i*(W-20)/nb}" y="${H-c/mx*H}" width="${(W-20)/nb-2}" height="${c/mx*H}" fill="#38bdf8" opacity=".55"/>`).join('')}${[['floor',p.floor,'#f87171'],['median',med,'#e7eeec'],['ceiling',p.ceil,'#4ade80']].map(([l,x,c])=>`<line x1="${X(x)}" x2="${X(x)}" y1="0" y2="${H}" stroke="${c}" stroke-dasharray="3 3"/><text x="${X(x)+3}" y="10" font-size="10" fill="${c}">${l} ${f1(x)}</text>`).join('')}<text x="10" y="${H+12}" font-size="9" fill="#7d8a87">${f1(lo)}</text><text x="${W-30}" y="${H+12}" font-size="9" fill="#7d8a87">${f1(hi)}</text></svg>`;}
function srcTbl(p){const s=p.srcs||{};return `<div class="table-wrap"><table class="tight"><tbody><tr><td>Usage-model simulation <span class="est">estimate</span></td><td class="num">${f1(s.model)}</td></tr><tr><td>External projection <span class="chip">external</span></td><td class="num">${s.ext!=null?f1(s.ext):'–'}</td></tr><tr><td><b>Our projection</b></td><td class="num"><b>${f1(p.proj)}</b></td></tr><tr><td>Source agreement</td><td class="num">${s.agree!=null?s.agree+'%':'–'}${(p.flags||[]).includes('Sources disagree')?' ⚠️':''}</td></tr><tr><td>Market redraft rank <span class="chip">real market</span></td><td class="num">${s.fc_rank||'–'}</td></tr><tr><td>Trending adds (48h) <span class="chip">real</span></td><td class="num">${s.trend?'#'+s.trend:'–'}</td></tr></tbody></table></div>`;}
function usageTbl(p){const u=p.usage;if(!u||!u.weeks)return '';const pc=v=>v==null?'–':Math.round(v*100)+'%';return `<h4 style="margin:12px 0 4px">Usage by week ${u.expanding?'<span class="chip hot">expanding role</span>':''}</h4><div class="table-wrap"><table class="tight"><thead><tr><th>Wk</th><th class="num">Snap%</th><th class="num">Tgt share</th><th class="num">Carry share</th><th class="num">RZ share</th><th class="num">Tgt/Car</th></tr></thead><tbody>${u.weeks.map(w=>`<tr><td>${w.w}</td>${w.played?`<td class="num">${pc(w.snap)}</td><td class="num">${pc(w.ts)}</td><td class="num">${pc(w.cs)}</td><td class="num">${pc(w.rz)}</td><td class="num">${w.tgt||0}/${w.car||0}</td>`:'<td colspan="5" style="color:var(--text-3)">did not play</td>'}</tr>`).join('')}<tr><td><b>Wtd</b></td><td class="num"><b>${pc(u.snap)}</b></td><td class="num"><b>${pc(u.ts)}</b></td><td class="num"><b>${pc(u.cs)}</b></td><td class="num"><b>${pc(u.rz)}</b></td><td></td></tr></tbody></table></div>${u.z_ts!=null||u.z_cs!=null?`<p style="font-size:11.5px;color:var(--text-2);margin:4px 0">Trend test (last 2 games vs earlier, two-proportion z): target share z=${u.z_ts??0}${Math.abs(u.z_ts||0)>=1.96?' <b>significant</b>':''}, carry share z=${u.z_cs??0}${Math.abs(u.z_cs||0)>=1.96?' <b>significant</b>':''}</p>`:''}`;}
function toggle(kind,id){const o=S[kind];const k=lockK();o[k]=o[k]||{};if(o[k][id])delete o[k][id];else{o[k][id]=1;const other=kind==='lock'?S.excl:S.lock;if(other[k])delete other[k][id];}ls.set('lock',S.lock);ls.set('excl',S.excl);S.results=null;}
function bindRows(root){root.querySelectorAll('[data-pid]').forEach(el=>el.onclick=e=>{if(e.target.closest('button'))return;openPlayer(el.dataset.pid)});
  root.querySelectorAll('[data-lk]').forEach(b=>b.onclick=()=>{toggle(b.dataset.kd,b.dataset.lk);route()});}

/* ---------- Optimizer (integer program via javascript-lp-solver branch & bound) ---------- */
function score(p,cfg,rnd,k){let s;
  if(cfg.contest==='cash'){const l=cfg.med?0:FEES.cash[cfg.fee].l;s=p.proj+l*(p.floor-p.proj);}
  else if(cfg.contest==='bal'){s=p.proj+0.2*(p.ceil-p.proj)-0.05*p.proj*(p.own||0)/100;}
  else{const g=FEES.gpp[cfg.fee];s=p.proj+g.g*(p.ceil-p.proj)-g.b*p.proj*(p.own||0)/100;}
  if(k!=null&&k>=0&&p.sims&&p.sims.length>k)s=0.5*s+0.5*p.sims[k]*(isSD()?1:1);if(rnd)s*=1+rnd*(Math.random()*2-1);return s;}
function prune(players,cfg,sd){const L=locks(),E=excls();const ok=players.filter(p=>!E[p.id]&&((p.elig&&p.proj>0.5)||L[p.id]));
  if(sd)return ok.sort((a,b)=>score(b,cfg)-score(a,cfg)).slice(0,34).concat(ok.filter(p=>L[p.id])).filter((p,i,a)=>a.indexOf(p)===i);
  const lim={QB:14,RB:26,WR:38,TE:14,DST:12};const out=[];
  for(const pos of Object.keys(lim)){const arr=ok.filter(p=>p.pos===pos);const a=[...arr].sort((x,y)=>score(y,cfg)-score(x,cfg)).slice(0,lim[pos]);const b=[...arr].sort((x,y)=>score(y,cfg)/y.sal-score(x,cfg)/x.sal).slice(0,Math.ceil(lim[pos]/2));
    for(const p of a.concat(b,arr.filter(p=>L[p.id])))if(!out.includes(p))out.push(p);}
  return out;}
function solveOne(players,cfg,prev,expCount,n){const sd=isSD();const L=locks();const model={optimize:'score',opType:'max',constraints:{sal:{max:Math.min(50000,cfg.cap||50000)}},variables:{},ints:{}};const C=model.constraints;
  const capN=Math.max(1,Math.floor((cfg.exp/100)*n+1e-9));const banned=p=>(expCount[p.id]||0)>=capN&&!L[p.id];
  const rnd=cfg.contest==='bal'&&n>1?0.04:(cfg.contest==='gpp'&&n>1?0.03:0);const K=(cfg.contest==='gpp'&&n>1)?Math.floor(Math.random()*(sl().keep||100)):-1;
  if(!sd){C.sal.min=Math.min(cfg.minsal,49999);Object.assign(C,{QB:{equal:1},DST:{equal:1},RB:{min:2,max:3},WR:{min:3,max:4},TE:{min:1,max:2},FX:{equal:7}});
    const qbs=players.filter(p=>p.pos==='QB'&&!banned(p));
    for(const p of players){if(banned(p))continue;const v={score:score(p,cfg,rnd,K),sal:p.sal,[p.pos]:1,['u'+p.id]:1};if('RB WR TE'.includes(p.pos))v.FX=1;
      if(cfg.stack>0)for(const q of qbs){if(p.id===q.id)v['st'+q.id]=-cfg.stack;else if(p.team===q.team&&(p.pos==='WR'||p.pos==='TE'))v['st'+q.id]=1;
        if(cfg.bring){if(p.id===q.id)v['bb'+q.id]=-1;else if(p.team===q.opp&&'WR TE RB'.includes(p.pos))v['bb'+q.id]=1;}}
      prev.forEach((lu,i)=>{if(lu.includes(p.id))v['pv'+i]=1});
      model.variables[p.id]=v;model.ints[p.id]=1;C['u'+p.id]=L[p.id]?{equal:1}:{max:1};}
    if(cfg.stack>0)for(const q of qbs){C['st'+q.id]={min:0};if(cfg.bring)C['bb'+q.id]={min:0};}
    prev.forEach((lu,i)=>C['pv'+i]={max:9-cfg.uniq});
  }else{const teams=[...new Set(players.map(p=>p.team))];Object.assign(C,{CPT:{equal:1},FLEX:{equal:5}});C.sal.min=Math.min(cfg.minsal,49999);
    const sc=cfg.script||'any';teams.forEach(t=>C['tm'+t]={min:sc==='shootout'?2:1});
    const topQB=new Set(teams.map(t=>(players.filter(p=>p.team===t&&p.pos==='QB').sort((a,b)=>b.proj-a.proj)[0]||{}).id));
    for(const p of players){if(banned(p))continue;const b=score(p,cfg,rnd,K);
      for(const slot of ['CPT','FLEX']){if(slot==='CPT'&&!p.cid)continue;const vid=slot+p.id;const v={score:slot==='CPT'?1.5*b:b,sal:slot==='CPT'?p.csal:p.sal,[slot]:1,['u'+p.id]:1,['tm'+p.team]:1};
        if(sc.startsWith('team:')&&p.team===sc.slice(5)){v.TS=1;if(slot==='CPT')v.TC=1;}
        if(sc==='shootout'&&topQB.has(p.id))v.QBS=1;
        if(sc==='shootout'&&slot==='CPT'&&'QB WR TE'.includes(p.pos))v.SC=1;
        prev.forEach((lu,i)=>{if(lu.includes(vid))v['pv'+i]=1});
        model.variables[vid]=v;model.ints[vid]=1;C[vid+'_b']={max:1};v[vid+'_b']=1;}
      C['u'+p.id]=L[p.id]?{equal:1}:{max:1};}
    const fc=S.forceCpt&&S.forceCpt[lockK()];if(fc&&model.variables['CPT'+fc])C['CPT'+fc+'_b']={equal:1};
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
function finish(rows,ids){const sum=k=>rows.reduce((a,r)=>a+(r[k]||0),0);const proj=sum('pts');
  // lineup range: player outcomes combined (sqrt of summed variances, +20% for in-game correlation), not a sum of individual floors/ceilings
  const sd=Math.sqrt(rows.reduce((a,r)=>{const m=r.slot==='CPT'?1.5:1;const s=(r.p.sd||((r.p.ceil-r.p.floor)/2.1))*m;return a+s*s},0))*1.2;
  const mc=scoreLineupMC(rows);
  return Object.assign({rows,ids,sal:sum('sal'),proj,floor:Math.max(0,proj-0.84*sd),ceil:proj+1.28*sd,own:sum('own')},mc);}
function optimize(cfg,n,prev0){const players=prune(pool(),cfg,isSD());const prev=prev0||[],out=[],exp={};
  for(let i=0;i<n;i++){const ids=solveOne(players,cfg,prev,exp,n);if(!ids)break;prev.push(ids);const lu=buildLineup(ids);out.push(lu);lu.rows.forEach(r=>exp[r.p.id]=(exp[r.p.id]||0)+1);}
  return out;}
function why(lu,kind){const r=lu.rows;const qb=r.find(x=>x.p.pos==='QB'&&x.slot!=='CPT')||r.find(x=>x.p.pos==='QB');const out=[];
  if(isSD()){const c=r[0];out.push(`Captain ${c.p.name} (${c.p.pos}): ${c.p.edges&&c.p.edges[0]?c.p.edges[0].toLowerCase():'highest 1.5x upside per dollar'}`);
    const tc={};r.forEach(x=>tc[x.p.team]=(tc[x.p.team]||0)+1);out.push('Game script: '+Object.entries(tc).map(([t,n])=>`${n} ${t}`).join(' / ')+(Object.values(tc).some(n=>n>=4)?' — leans on one side controlling the game':' — balanced shootout build'));}
  else if(qb){const st=r.filter(x=>x.p.team===qb.p.team&&x.p!==qb.p&&'WR TE'.includes(x.p.pos)).map(x=>x.p.name.split(' ').slice(-1)[0]);const bb=r.filter(x=>x.p.team===qb.p.opp&&'WR TE RB'.includes(x.p.pos)).map(x=>x.p.name.split(' ').slice(-1)[0]);
    if(st.length)out.push(`Stack: ${qb.p.name} + ${st.join(', ')}`+(bb.length?` with bring-back ${bb.join(', ')}`:''));}
  const vals=r.filter(x=>x.p.sal<=5000&&x.p.pos!=='DST').sort((a,b)=>b.p.val-a.p.val).slice(0,2);if(vals.length)out.push('Salary savers: '+vals.map(x=>`${x.p.name} (${fmt$(x.p.sal)}, ${x.p.val} pts/$1k)`).join(', '));
  return out;}
function slateMaxCeil(){
  const P=pool();let mx=32;for(let i=0;i<P.length;i++)if((P[i].ceil||0)>mx)mx=P[i].ceil;return mx;
}
function whiskerBar(p,compact){
  const mx=slateMaxCeil();
  const fl=Math.max(0,+(p.floor||0)),pr=Math.max(fl,+(p.proj||0)),cl=Math.max(pr,+(p.ceil||pr));
  const W=compact?64:96,H=14,pad=4;
  const X=v=>Math.round((pad+Math.min(1,Math.max(0,v/mx))*(W-2*pad))*10)/10;
  const xFl=X(fl),xPr=X(pr),xCl=X(cl);
  const q1=X(fl+(pr-fl)*0.45),q3=X(pr+(cl-pr)*0.48);
  const svg=`<svg class="whisker-svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Floor ${f1(fl)}, Median ${f1(pr)}, Ceiling ${f1(cl)}"><line x1="${pad}" y1="7" x2="${W-pad}" y2="7" stroke="rgba(148,163,184,0.18)" stroke-width="2" stroke-linecap="round"/><line x1="${xFl}" y1="7" x2="${xCl}" y2="7" stroke="#38bdf8" stroke-width="2" stroke-linecap="round"/><rect x="${q1}" y="4" width="${Math.max(2,q3-q1)}" height="6" rx="2" fill="rgba(56,189,248,0.28)" stroke="rgba(56,189,248,0.65)" stroke-width="0.8"/><line x1="${xFl}" y1="3.5" x2="${xFl}" y2="10.5" stroke="#94a3b8" stroke-width="1.4"/><line x1="${xCl}" y1="3.5" x2="${xCl}" y2="10.5" stroke="#4ade80" stroke-width="1.5"/><circle cx="${xPr}" cy="7" r="3" fill="#f59e0b" stroke="#0a0d18" stroke-width="1"/></svg>`;
  if(compact)return `<span class="ff-whisker compact" title="Floor ${f1(fl)} · Proj ${f1(pr)} · Ceiling ${f1(cl)}">${svg}</span>`;
  return `<div class="ff-whisker" title="Floor ${f1(fl)} · Median Proj ${f1(pr)} · Ceiling ${f1(cl)}">${svg}<span class="whisker-nums mono"><span class="fl">${f1(fl)}</span>·<b>${f1(pr)}</b>·<span class="cl">${f1(cl)}</span></span></div>`;
}
function simBellSvg(lu){
  const s=lu.sim||{p50:lu.proj||130,p90:lu.ceil||165,p99:(lu.ceil||165)+22,cash_line:(lu.proj||130)-4,top1_line:(lu.ceil||165)+14,cash_pct:lu.sim_cash||55,sim_win_pct:lu.sim_top1||1.8,sd:Math.max(12,((lu.ceil||165)-(lu.floor||100))/2.12)};
  const sd=Math.max(8,s.sd||18);
  const xMin=Math.max(30,s.p50-2*sd),xMax=Math.max(s.top1_line+10,s.p99+15);
  const W=320,H=68,padL=10,padR=10,topY=14,baseY=50,cH=baseY-topY;
  const X=v=>Math.max(padL,Math.min(W-padR,padL+((v-xMin)/(xMax-xMin||1))*(W-padL-padR)));
  const sigL=Math.max(6,sd*0.86),sigR=Math.max(8,(s.p90-s.p50)/1.2815||sd*1.18);
  const pdf=v=>{const z=(v-s.p50)/(v<=s.p50?sigL:sigR);return Math.exp(-0.5*z*z)};
  const N=60,pts=[];
  for(let i=0;i<=N;i++){const xv=xMin+(xMax-xMin)*(i/N);const yv=baseY-pdf(xv)*cH;pts.push([xv, X(xv), yv])}
  const linePath='M'+pts.map(p=>`${p[1].toFixed(1)},${p[2].toFixed(1)}`).join(' L');
  const fullArea=linePath+` L${pts[pts.length-1][1].toFixed(1)},${baseY} L${pts[0][1].toFixed(1)},${baseY} Z`;
  const subArea=(v0,v1)=>{
    const a=Math.max(xMin,Math.min(xMax,v0)),b=Math.max(a,Math.min(xMax,v1));
    const M=28,sp=[];
    for(let i=0;i<=M;i++){const xv=a+(b-a)*(i/M);sp.push([X(xv),baseY-pdf(xv)*cH])}
    return `M${sp[0][0].toFixed(1)},${baseY} L`+sp.map(p=>`${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' L')+` L${sp[sp.length-1][0].toFixed(1)},${baseY} Z`;
  };
  const cashArea=subArea(s.cash_line,xMax);
  const top1Area=subArea(s.top1_line,xMax);
  const xCash=X(s.cash_line),xMed=X(s.p50),xP90=X(s.p90),xTop1=X(s.top1_line);
  return `<div class="sim-bell-wrap"><div class="sim-bell-hd"><span class="sim-bell-ttl">1,000-Sim Outcome Bell Curve</span><span class="sim-bell-zones"><span class="z-cash">💵 Cash Zone ${f1(s.cash_pct)}%</span><span class="z-top1">🏆 GPP Top-1% Tail ${f1(s.sim_win_pct)}%</span></span></div><svg class="sim-bell-svg" viewBox="0 0 320 68" width="100%" role="img" aria-label="1,000-Sim Monte Carlo Outcome Distribution"><path d="${fullArea}" fill="rgba(148,163,184,0.11)"/><path d="${cashArea}" fill="rgba(56,189,248,0.28)"/><path d="${top1Area}" fill="rgba(74,222,128,0.48)"/><path d="${linePath}" fill="none" stroke="#cbd5e1" stroke-width="1.5"/><line x1="${padL}" y1="${baseY}" x2="${W-padR}" y2="${baseY}" stroke="rgba(148,163,184,0.3)" stroke-width="1"/><line x1="${xCash.toFixed(1)}" y1="${topY-2}" x2="${xCash.toFixed(1)}" y2="${baseY}" stroke="#38bdf8" stroke-width="1.2" stroke-dasharray="2.5 2"/><line x1="${xMed.toFixed(1)}" y1="${topY-2}" x2="${xMed.toFixed(1)}" y2="${baseY}" stroke="#f8fafc" stroke-width="1.3"/><line x1="${xP90.toFixed(1)}" y1="${topY}" x2="${xP90.toFixed(1)}" y2="${baseY}" stroke="#4ade80" stroke-width="1.1" stroke-dasharray="2 2"/><line x1="${xTop1.toFixed(1)}" y1="${topY-2}" x2="${xTop1.toFixed(1)}" y2="${baseY}" stroke="#f59e0b" stroke-width="1.4"/><text x="${Math.max(24,Math.min(xCash-3,xMed-26)).toFixed(1)}" y="61" text-anchor="end" font-size="8.2" fill="#38bdf8" font-weight="600">Cash ${Math.round(s.cash_line)}</text><text x="${xMed.toFixed(1)}" y="10" text-anchor="middle" font-size="8.2" fill="#f8fafc" font-weight="600">Med ${f1(s.p50)}</text><text x="${Math.max(xMed+22,xP90).toFixed(1)}" y="61" text-anchor="middle" font-size="8.2" fill="#4ade80" font-weight="600">90th ${Math.round(s.p90)}</text><text x="${Math.min(W-4,Math.max(xP90+28,xTop1)).toFixed(1)}" y="10" text-anchor="end" font-size="8.2" fill="#f59e0b" font-weight="700">Top 1% ${Math.round(s.top1_line)}</text></svg></div>`;
}
function luCard(lu,cls,title,sub,kind){return `<div class="lu ${cls}"><h3>${esc(title)}</h3><div class="sub">${esc(sub)}</div><div class="lu-sim-bar"><span class="chip hot" title="1,000-draw correlated Monte Carlo contest simulation Top-1% finish rate">🏆 Sim Top-1%: <b>${f1(lu.sim_top1)}%</b></span><span class="chip cool" title="Top-50% cash rate across 1,000 correlated slate draws">💵 Cash %: <b>${f1(lu.sim_cash)}%</b></span><span class="chip ${lu.lev_score>=0?'pos-chip':''}" title="Lineup average Leverage Score (Boom % − Est. Own %)">⚡ Leverage: <b>${lu.lev_score>0?'+':''}${f1(lu.lev_score)}%</b></span><span class="chip stack-chip" title="Stack structure & empirical pairwise correlation across 1,000 game-script draws">🔗 ${esc(lu.stack_badge||'Balanced Stack')}</span></div>${simBellSvg(lu)}${lu.rows.map(r=>`<div class="lu-row" data-pid="${r.p.id}" style="cursor:pointer"><span>${posTag(r.slot==='CPT'?'CPT':r.slot)}</span><span class="n"><b>${esc(r.p.name)}</b> <span style="color:var(--text-3);font-size:11.5px">${esc(r.p.team)} ${r.slot!==r.p.pos&&r.slot!=='DST'?esc(r.p.pos):''} · <span title="Boom % / Est. Own %">B:${Math.round(boomPct(r.p))}% O:${Math.round(r.p.own||0)}%</span></span></span><span class="mono" style="text-align:right">${fmt$(r.sal)}</span><span class="mono" style="text-align:right;display:inline-flex;align-items:center;justify-content:flex-end;gap:5px">${whiskerBar(r.p,true)}<b>${f1(r.pts)}</b></span></div>`).join('')}
  <div class="lu-foot"><span>Salary <b class="mono">${fmt$(lu.sal)}</b> / $50k</span><span>Proj <b class="mono">${f1(lu.proj)}</b></span><span>Floor–Ceil <b class="mono">${f1(lu.floor)}–${f1(lu.ceil)}</b></span><span>Total own* <b class="mono">${Math.round(lu.own)}%</b> · Boom <b class="mono">${f1(lu.avg_boom)}%</b></span></div>
  <ul class="edge-list">${why(lu,kind).map(w=>`<li>${esc(w)}</li>`).join('')}</ul></div>`;}
function recs(){const k=lockK();if(S.rec[k])return S.rec[k];const sd=isSD();
  const base={n:1,exp:100,uniq:1,minsal:sd?46000:48500,script:'any'};
  const prev=[];const U=sd?2:3;
  const safe=optimize(Object.assign({},base,{contest:'cash',fee:50,med:1,stack:0,bring:0,uniq:U}),1,prev)[0];
  const bal=optimize(Object.assign({},base,{contest:'bal',fee:20,stack:sd?0:1,bring:0,uniq:U}),1,prev)[0];
  const up=optimize(Object.assign({},base,{contest:'gpp',fee:10,stack:sd?0:2,bring:1,script:sd?'shootout':'any',uniq:U}),1,prev)[0]||optimize(Object.assign({},base,{contest:'gpp',fee:10,stack:sd?0:2,bring:1,uniq:1}),1)[0];
  return S.rec[k]={safe,bal,up};}
function recBlock(){const r=recs();const sd=isSD();if(!r.safe)return '<p>Not enough projected players to build lineups.</p>';
  return `<div class="lu-grid">${r.safe?luCard(r.safe,'safe','Safe · Cash / 50-50',sd?'Highest median projection: the cash build that scores most on average':'Highest median projection, no forced stacks','cash'):''}${r.bal?luCard(r.bal,'bal','Balanced · Single-entry',sd?'Best median outcome':'Median-optimal with a QB + 1 stack','bal'):''}${r.up?luCard(r.up,'up','Upside · GPP',sd?'Same-game-parlay logic: shootout script, pass-game CPT, ceiling over chalk':'QB + 2 stack with bring-back, ceiling and leverage over chalk','gpp'):''}</div>`;}

/* ---------- Pages ---------- */
function pSlate(m){const s=sl(),P=elig().filter(p=>p.proj>0);const sd=isSD();
  const topEdge=[...P].filter(p=>(p.edges||[]).length&&p.pos!=='DST').sort((a,b)=>(b.ceil-b.proj)/b.sal*1e3+b.val-((a.ceil-a.proj)/a.sal*1e3+a.val)).slice(0,6);
  const bargains=P.filter(p=>p.sal<=5000&&p.pos!=='DST'&&p.pos!=='K').sort((a,b)=>b.val-a.val).slice(0,6);
  const lev_=P.filter(p=>p.proj>=8).sort((a,b)=>levDiff(b)-levDiff(a)).slice(0,5);
  m.innerHTML=staleNote()+`<div class="hero-ff"><div><h2>${esc(KINDS[S.kind])} · ${sd?esc(s.games[0]?s.games[0].key:'Showdown'):s.games.length+'-game main slate'}</h2><p>${sd?'Showdown: 1 Captain at 1.5x salary and points, plus 5 FLEX, under a $50k cap. Treat it like a same-game parlay: pick the game script first, then the captain.':'Classic: QB, 2 RB, 3 WR, TE, FLEX, DST under a $50k cap. DK PPR scoring with 3-point bonuses at 300 passing, 100 rushing and 100 receiving yards.'} ${esc(slDate(s))}.</p></div>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><button class="btn primary" id="fillgo">⚡ Fill slots & go</button><a class="btn" href="#optimizer">Optimizer</a><a class="btn" href="#lineups">All lineups</a></div></div>
  <div class="grid kpis" style="margin-bottom:16px">${[['Players',P.length],['Games',s.games.length],['Top projection',P[0]?P[0].name.split(' ').slice(-1)[0]+' '+f1(P[0].proj):'–'],['Best value',[...P].filter(p=>p.proj>=8).sort((a,b)=>b.val-a.val)[0]?.name||'–'],['Injury cascades',(s.cascades||[]).length]].map(([l,v])=>`<div class="card kpi"><div class="kpi-label">${l}</div><div class="kpi-value" style="font-size:20px">${esc(v)}</div></div>`).join('')}</div>
  ${sd?cptBlock():''}<div class="card" style="margin-bottom:16px"><div class="card-head"><h2>Highlighted lineups <span class="est">estimates</span></h2><span class="sub">Safe for cash, Balanced, Upside for GPP</span></div>${recBlock()}</div>
  <div class="grid two" style="margin-bottom:16px"><div class="card"><div class="card-head"><h2>Biggest edges</h2><span class="sub">why they could outperform</span></div>${topEdge.map(p=>`<div data-pid="${p.id}" style="cursor:pointer;padding:8px 0;border-top:1px solid var(--border)">${plCell(p)} <span class="mono" style="float:right">${fmt$(p.sal)} · ${f1(p.proj)}</span><ul class="edge-list">${p.edges.slice(0,3).map(e=>`<li>${esc(e)}</li>`).join('')}</ul></div>`).join('')}</div>
  <div class="card"><div class="card-head"><h2>Bargains under $5k</h2><a href="#value" class="sub">all value plays →</a></div>${tbl(bargains,['sal','proj','range','val','own'])}<div class="card-head" style="margin-top:14px"><h2>Leverage plays</h2><span class="sub">Boom % minus Est. Ownership %</span></div>${tbl(lev_,['sal','range','boom','own','levd'])}</div></div>
  ${shotCard()}${(s.cascades||[]).length?`<div class="card"><div class="card-head"><h2>Injury cascades</h2><span class="sub">vacated share split across healthy teammates (with/without splits, same-position priority)</span></div>${s.cascades.map(c=>`<div style="padding:6px 0;border-top:1px solid var(--border);font-size:13px"><b>${esc(c.team)}: ${esc(c.out)} (${esc(c.pos)}) out</b>, ${c.vac}% ${esc(c.kind)} share vacated → ${(c.to||[]).map(t=>`<span class="chip hot">${esc(t[0])} +${t[1]}%</span>`).join('')}</div>`).join('')}</div>`:''}`;
  bindRows(m);$('#fillgo').onclick=fillGo;}
function shotCard(){const a=elig().filter(p=>p.shot).sort((x,y)=>x.sal-y.sal);if(!a.length)return '';return `<div class="card" style="margin-bottom:16px"><div class="card-head"><h2>🎯 Their shot</h2><span class="sub">a role just opened up (teammate out or depth-chart news), backed by with/without splits. Cheapest first</span></div>${a.slice(0,8).map(p=>`<div data-pid="${p.id}" style="cursor:pointer;padding:8px 0;border-top:1px solid var(--border)">${plCell(p)} <span class="mono" style="float:right">${fmt$(p.sal)} · ${f1(p.proj)}</span><ul class="edge-list">${p.shot.why.slice(0,3).map(w=>`<li>${esc(w)}</li>`).join('')}</ul></div>`).join('')}</div>`;}
function fillGo(){S.autoGo=1;if(location.hash==='#optimizer')route();else location.hash='optimizer';}
function cptBlock(){const c=sl().cpt||[];if(!c.length)return '';const byId=Object.fromEntries(pool().map(p=>[p.id,p]));return `<div class="card" style="margin-bottom:16px"><div class="card-head"><h2>Captain rankings <span class="est">sim-based</span></h2><span class="sub">1.5x points · how often he's the game's top scorer across ${sl().nsims||4000} simulations</span></div><div class="table-wrap"><table class="tight"><thead><tr><th>#</th><th>Captain</th><th class="num">CPT $</th><th class="num">CPT proj</th><th class="num">CPT ceil</th><th class="num">Top scorer</th><th class="num">Pts/$1k</th></tr></thead><tbody>${c.slice(0,8).map((x,i)=>`<tr data-pid="${x.id}" style="cursor:pointer"><td>${i+1}</td><td>${byId[x.id]?plCell(byId[x.id]):esc(x.name)}</td><td class="num">${fmt$(x.csal)}</td><td class="num">${f1(x.proj)}</td><td class="num">${f1(x.ceil)}</td><td class="num">${f1(x.top)}%</td><td class="num">${f1(x.val)}</td></tr>`).join('')}</tbody></table></div></div>`;}
const COLS={src:['Src agree',p=>p.srcs&&p.srcs.agree!=null?p.srcs.agree+'%'+((p.flags||[]).includes('Sources disagree')?' ⚠️':''):'–'],sal:['Salary',p=>fmt$(p.sal)],csal:['CPT $',p=>p.csal?fmt$(p.csal):'–'],proj:['Proj',p=>f1(p.proj)],floor:['Floor',p=>f1(p.floor)],ceil:['Ceil',p=>f1(p.ceil)],range:['Floor · Med · Ceil Range',p=>whiskerBar(p,false)],val:['Pts/$1k',p=>f1(p.val)],boom:['Boom%',p=>`<span style="color:${boomPct(p)>=35?'var(--accent)':'inherit'};font-weight:${boomPct(p)>=35?600:400}">${f1(boomPct(p))}%</span>`],own:['Own*',p=>f1(p.own)+'%'],levd:['Leverage',p=>{const d=levDiff(p);return `<span style="color:${d>=8?'var(--pos)':d<=-5?'var(--neg)':'inherit'};font-weight:${Math.abs(d)>=8?600:400}">${d>0?'+':''}${f1(d)}%</span>`}],lev:['Lev',p=>f1(lev(p))],smash:['Smash%',p=>p.smash?f1(p.smash.p)+'%':'–']};
function tbl(arr,cols,ctl){return `<div class="table-wrap"><table class="tight"><thead><tr><th>Player</th>${cols.map(c=>`<th class="num ${ctl?'sortable':''}" data-s="${c}">${COLS[c][0]}</th>`).join('')}${ctl?'<th>Opt</th>':''}</tr></thead><tbody>${arr.map(p=>`<tr data-pid="${p.id}" class="${(p.proj<=0||!p.elig)?'out':''}" title="${esc(p.why_not||'')}" style="cursor:pointer"><td>${plCell(p)}</td>${cols.map(c=>`<td class="num">${COLS[c][1](p)}</td>`).join('')}${ctl?`<td style="white-space:nowrap"><button class="lk ${locks()[p.id]?'on':''}" data-lk="${p.id}" data-kd="lock">Lock</button> <button class="lk ex ${excls()[p.id]?'on':''}" data-lk="${p.id}" data-kd="excl">✕</button></td>`:''}</tr>`).join('')}</tbody></table></div>`;}
function pPlayers(m){const P=pool();const teams=[...new Set(P.map(p=>p.team))].sort();const poss=[...new Set(P.map(p=>p.pos))];const F=S.flt;
  const draw=()=>{let a=P.filter(p=>(F.all||p.elig||locks()[p.id])&&(F.pos==='ALL'||p.pos===F.pos)&&(F.team==='ALL'||p.team===F.team)&&(!F.q||p.name.toLowerCase().includes(F.q.toLowerCase())));
    const [k,d]=S.sort;const g=k==='lev'?lev:k==='boom'?boomPct:k==='levd'?levDiff:(p=>p[k]??0);a.sort((x,y)=>d*(g(x)-g(y)));
    $('#ptbl').innerHTML=tbl(a.slice(0,250),isSD()?['sal','csal','proj','range','val','boom','own','levd','src']:['sal','proj','range','val','boom','own','levd','src'],1)+`<p style="font-size:11.5px;color:var(--text-3)">${a.length} players. <b>Boom%</b> = simulated probability of hitting 3x+ salary ceiling target. <b>*Own</b> = estimated ownership proxy from value rank, salary tier, and Vegas implied total. <b>Leverage</b> = Boom% − Est. Own%.</p>`;
    $('#ptbl').querySelectorAll('th[data-s]').forEach(th=>th.onclick=()=>{S.sort=[th.dataset.s,S.sort[0]===th.dataset.s?-S.sort[1]:-1];ls.set('sort',S.sort);draw()});bindRows($('#ptbl'));
    $('#ptbl').querySelectorAll('[data-lk]').forEach(b=>b.onclick=()=>{toggle(b.dataset.kd,b.dataset.lk);draw()});};
  m.innerHTML=staleNote()+`<div class="filters"><select id="fp"><option value="ALL">All positions</option>${poss.map(p=>`<option ${F.pos===p?'selected':''}>${p}</option>`).join('')}</select><select id="ft"><option value="ALL">All teams</option>${teams.map(t=>`<option ${F.team===t?'selected':''}>${t}</option>`).join('')}</select><input id="fq" placeholder="Search player" value="${esc(F.q)}"><label style="font-size:12px;color:var(--text-2);display:flex;gap:4px;align-items:center"><input type="checkbox" id="fall" ${F.all?'checked':''}>Show low-role / out</label><span style="color:var(--text-3);font-size:12px">Tap a player for edges · Lock/✕ feed the optimizer</span></div><div id="ptbl"></div>`;
  $('#fp').onchange=e=>{F.pos=e.target.value;draw()};$('#ft').onchange=e=>{F.team=e.target.value;draw()};$('#fq').oninput=e=>{F.q=e.target.value;draw()};$('#fall').onchange=e=>{F.all=e.target.checked;draw()};draw();}
function pValue(m){const P=elig().filter(p=>p.proj>0&&p.pos!=='K');
  const val=[...P].filter(p=>p.proj>=6).sort((a,b)=>b.val-a.val).slice(0,15);const bar=P.filter(p=>p.sal<5000&&p.pos!=='DST').sort((a,b)=>b.val-a.val).slice(0,12);
  const ceil=[...P].sort((a,b)=>b.ceil-a.ceil).slice(0,12);const chalk=[...P].sort((a,b)=>b.own-a.own).slice(0,10);const levs=P.filter(p=>p.proj>=8).sort((a,b)=>levDiff(b)-levDiff(a)).slice(0,10);
  m.innerHTML=staleNote()+`<div class="note">Points per $1k = projected Book A points ÷ salary in thousands. <b>Boom %</b> = simulated probability of hitting a 3x+ ceiling target across 1,000 correlated game draws. <b>Leverage Score</b> = Boom % − Estimated Ownership %.</div>
  <div class="grid two" style="margin-bottom:16px"><div class="card"><div class="card-head"><h2>Top value (pts per $1k)</h2></div>${tbl(val,['sal','proj','val','boom','smash'])}</div><div class="card"><div class="card-head"><h2>Bargains under $5k</h2></div>${tbl(bar,['sal','proj','floor','val','boom'])}</div></div>
  <div class="grid two" style="margin-bottom:16px"><div class="card"><div class="card-head"><h2>Ceiling / GPP plays</h2><span class="sub">90th-percentile outcome & Boom %</span></div>${tbl(ceil,['sal','proj','ceil','boom','own'])}</div><div class="card"><div class="card-head"><h2>Chalk vs leverage</h2><span class="sub">likely most-played vs contrarian Boom % edge</span></div><h4 style="margin:0 0 6px;font-size:13px;color:var(--text-2)">Chalk (highest own proxy)</h4>${tbl(chalk,['sal','proj','boom','own','levd'])}<h4 style="margin:14px 0 6px;font-size:13px;color:var(--text-2)">Top Leverage (Boom % − Est. Own %)</h4>${tbl(levs,['sal','ceil','boom','own','levd'])}</div></div>`;bindRows(m);}
function pLineups(m){const sd=isSD();m.innerHTML=staleNote()+`<div class="note">Three ready-made builds per slate. <b>Safe</b> chases floor for cash and 50/50s. <b>Upside</b> chases ceiling and leverage for GPPs${sd?'. In showdown it works like a same-game parlay: pick a shootout script, captain a pass-game piece, and correlate both sides':' with a QB + 2 stack and a bring-back'}. Lineups update automatically with your locks and excludes. Tap any player for his edges.</div>${recBlock()}<p style="margin-top:14px"><button class="btn" id="exr">Export these 3 as Book A CSV</button> <a class="btn primary" href="#optimizer">Customize in optimizer</a></p>${sd?cptBlock():''}`;bindRows(m);
  $('#exr').onclick=()=>{const r=recs();exportCSV([r.safe,r.bal,r.up].filter(Boolean))};}
function pOpt(m){const o=S.opt;const sd=isSD();const s=sl();const teams=[...new Set(pool().map(p=>p.team))];
  const L=Object.keys(locks()),E=Object.keys(excls());const byId=Object.fromEntries(pool().map(p=>[p.id,p]));
  m.innerHTML=staleNote()+builder()+`<div class="card" style="margin-bottom:16px"><div class="card-head"><h2>Settings</h2><span class="sub">${sd?'Showdown: CPT (1.5x) + 5 FLEX, both teams required':'Classic: QB · 2 RB · 3 WR · TE · FLEX · DST'}, $50,000 cap</span></div>
  <div class="ctl"><label>Contest type<select id="o-contest"><option value="cash" ${o.contest==='cash'?'selected':''}>Cash · 50/50 · double-up</option><option value="bal" ${o.contest==='bal'?'selected':''}>Balanced · single-entry</option><option value="gpp" ${o.contest==='gpp'?'selected':''}>GPP · tournament</option></select></label>
  <label>Entry fee tier<select id="o-fee">${[10,20,50,100].map(f=>`<option value="${f}" ${+o.fee===f?'selected':''}>$${f}</option>`).join('')}</select></label>
  <label>Lineups (N)<input id="o-n" type="number" min="1" max="40" value="${o.n}"></label><label>Max exposure %<input id="o-exp" type="number" min="10" max="100" step="5" value="${o.exp}"></label>
  <label>Min unique players vs other lineups<input id="o-uniq" type="number" min="1" max="${sd?4:6}" value="${o.uniq}"></label><label>Min salary used<input id="o-minsal" type="number" min="40000" max="50000" step="100" value="${o.minsal}"></label>
  ${sd?`<label>Game script<select id="o-script"><option value="any">Any</option><option value="shootout" ${o.script==='shootout'?'selected':''}>Shootout: both QBs, pass-game CPT</option>${teams.map(t=>`<option value="team:${t}" ${o.script==='team:'+t?'selected':''}>${t} controls game (4+ ${t}, ${t} CPT)</option>`).join('')}</select></label>`
  :`<label>QB stack (pass-catchers with QB)<select id="o-stack">${[0,1,2,3].map(n=>`<option value="${n}" ${+o.stack===n?'selected':''}>${n?'QB + '+n:'No stack'}</option>`).join('')}</select></label><label>Bring-back (opp. player)<select id="o-bring"><option value="0">Off</option><option value="1" ${+o.bring?'selected':''}>On</option></select></label>`}</div>
  <p id="riskTxt" style="font-size:12.5px;color:var(--text-2);margin:12px 0 0"></p>
  ${budget()}
  <p style="font-size:12.5px;color:var(--text-3)">Locked: ${L.length?L.map(i=>byId[i]?`<span class="chip cool">${esc(byId[i].name)}</span>`:'').join(''):'none'} · Excluded: ${E.length?E.map(i=>byId[i]?`<span class="chip">${esc(byId[i].name)}</span>`:'').join(''):'none'} · <a href="#players">set in Player pool</a>${L.length||E.length?' · <a href="#" id="clr">clear</a>':''}</p>
  <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" id="go">⚡ Fill slots & go</button><button class="btn" id="csv" ${S.results&&S.results.length?'':'disabled'}>Export Book A CSV</button></div></div><div id="res"></div>`;
  const risk=()=>{const c=$('#o-contest').value,f=$('#o-fee').value;$('#riskTxt').textContent=c==='cash'?`Cash at $${f}: leans on floor outcomes. Higher stakes means safer builds.`:c==='gpp'?`GPP at $${f}: leans on ceiling, fades estimated chalk, and adds diversity across lineups. Cheaper, bigger-field contests get more leverage.`:'Balanced: median projection with a light ceiling tilt.'};
  m.querySelectorAll('.ctl select,.ctl input').forEach(el=>el.onchange=()=>{read();risk()});risk();
  function read(){const g=id=>{const e=$('#o-'+id);return e?e.value:o[id]};Object.assign(o,{contest:g('contest'),fee:+g('fee'),n:Math.max(1,Math.min(40,+g('n'))),exp:+g('exp'),uniq:+g('uniq'),minsal:+g('minsal'),stack:+g('stack'),bring:+g('bring'),script:g('script')});ls.set('opt',o);}
  if($('#clr'))$('#clr').onclick=e=>{e.preventDefault();delete S.lock[lockK()];delete S.excl[lockK()];ls.set('lock',S.lock);ls.set('excl',S.excl);S.rec={};route()};
  $('#go').onclick=()=>{read();$('#go').textContent='Solving…';$('#res').innerHTML='<p style="color:var(--text-3)">Running the integer program…</p>';setTimeout(()=>{const t=performance.now();S.results=optimize(o,o.n);S.resT=Math.round(performance.now()-t);$('#go').textContent='⚡ Fill slots & go';$('#csv').disabled=!S.results.length;drawRes()},30)};
  bindBuilder(m,o,read);$('#csv').onclick=()=>exportCSV(S.results);if(S.autoGo){S.autoGo=0;$('#go').click();}else if(S.results)drawRes();
  function drawRes(){const R=S.results;if(!R.length){$('#res').innerHTML='<div class="note warn">No valid lineup under these rules. Loosen the min salary, stack, exposure or locks.</div>';return}
    const ex={};R.forEach(lu=>lu.rows.forEach(r=>ex[r.p.id]=(ex[r.p.id]||0)+1));const exs=Object.entries(ex).sort((a,b)=>b[1]-a[1]).slice(0,16);
    $('#res').innerHTML=`<div class="card" style="margin-bottom:14px"><div class="card-head"><h2>${R.length} lineup${R.length>1?'s':''}</h2><span class="sub">solved in ${S.resT} ms · avg proj ${f1(R.reduce((a,l)=>a+l.proj,0)/R.length)}</span></div><div style="display:flex;flex-wrap:wrap;gap:4px">${exs.map(([id,n])=>{const p=pool().find(x=>x.id===id);return `<span class="chip ${n/R.length>=.5?'hot':''}">${esc(p.name)} ${Math.round(100*n/R.length)}%</span>`}).join('')}</div></div><div class="lu-grid">${R.map((lu,i)=>luCard(lu,o.contest==='cash'?'safe':o.contest==='gpp'?'up':'bal','Lineup '+(i+1),`${o.contest.toUpperCase()} · $${o.fee}`,o.contest)).join('')}</div>`;bindRows($('#res'));}}
function budget(){const L=Object.keys(locks());const byId=Object.fromEntries(pool().map(p=>[p.id,p]));const ps=L.map(i=>byId[i]).filter(Boolean);const by=S.donutBy||'pos';const g={};ps.forEach(p=>g[p[by==='pos'?'pos':'team']]=(g[p[by==='pos'?'pos':'team']]||0)+p.sal);const used=ps.reduce((a,p)=>a+p.sal,0);const rem=50000-used;const slots=isSD()?6:9;
  const C={QB:'#8b5cf6',RB:'#22c55e',WR:'#3b82f6',TE:'#f97316',DST:'#94a3b8',K:'#64748b'};const pal=['#f59e0b','#38bdf8','#a78bfa','#4ade80','#f472b6','#facc15','#60a5fa','#fb7185'];const segs=Object.entries(g).map(([k,v],i)=>[k,v,by==='pos'?C[k]||pal[i%8]:pal[i%8]]);if(rem>0)segs.push(['Remaining',rem,'rgba(255,255,255,.08)']);
  let a0=-Math.PI/2;const R=52,r=34,cx=60,cy=60;const arc=v=>{const a1=a0+2*Math.PI*v/50000;const L=a1-a0>Math.PI?1:0;const p=`M${cx+R*Math.cos(a0)} ${cy+R*Math.sin(a0)}A${R} ${R} 0 ${L} 1 ${cx+R*Math.cos(a1)} ${cy+R*Math.sin(a1)}L${cx+r*Math.cos(a1)} ${cy+r*Math.sin(a1)}A${r} ${r} 0 ${L} 0 ${cx+r*Math.cos(a0)} ${cy+r*Math.sin(a0)}Z`;a0=a1;return p};
  const left=slots-ps.length;return `<div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin:12px 0;padding:10px;border:1px solid var(--border);border-radius:10px"><svg viewBox="0 0 120 120" width="120" height="120">${segs.map(([k,v,c])=>v>=50000?`<circle cx="60" cy="60" r="43" fill="none" stroke="${c}" stroke-width="18"/>`:`<path d="${arc(v)}" fill="${c}"><title>${k}: $${v}</title></path>`).join('')}<text x="60" y="58" text-anchor="middle" font-size="13" font-weight="700" fill="#e7eeec">${fmt$(Math.max(0,rem))}</text><text x="60" y="73" text-anchor="middle" font-size="9" fill="#7d8a87">left</text></svg>
  <div style="font-size:12.5px;color:var(--text-2);min-width:180px"><b>My lineup budget</b> <span class="seg" style="margin-left:6px"><button class="lk ${by==='pos'?'on':''}" data-dby="pos">by position</button> <button class="lk ${by==='team'?'on':''}" data-dby="team">by team</button></span><div style="margin-top:6px">${segs.filter(s=>s[0]!=='Remaining').map(([k,v,c])=>`<div><span style="color:${c}">■</span> ${esc(k)} ${fmt$(v)}</div>`).join('')||'Lock players (Player pool → Lock) to build your lineup.'}</div>
  <div style="margin-top:6px">${ps.length}/${slots} slots · ${left>0&&rem>0?`${fmt$(rem/left*1000/1000)} avg per open slot`:rem<0?'<b style="color:var(--neg)">over the cap</b>':'full'}</div></div></div>`;}
document.addEventListener('click',e=>{const b=e.target.closest('[data-dby]');if(b){S.donutBy=b.dataset.dby;route();}});
function exportCSV(lus){if(!lus||!lus.length)return;const sd=isSD();const head=sd?['CPT','FLEX','FLEX','FLEX','FLEX','FLEX']:['QB','RB','RB','WR','WR','WR','TE','FLEX','DST'];
  const lines=[head.join(',')].concat(lus.map(lu=>{if(sd)return lu.rows.map(r=>r.dkid).join(',');const ord=[];const used=new Set();for(const h of head){const r=lu.rows.find(x=>x.slot===h&&!used.has(x));used.add(r);ord.push(r?r.dkid:'')}return ord.join(',')}));
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([lines.join('\n')+'\n'],{type:'text/csv'}));a.download=`fantasy-frontier-${S.kind}-${sl().dg}.csv`;document.body.appendChild(a);a.click();a.remove();}
function pRos(m){const P=pool().filter(p=>p.ros&&p.ros.length&&p.elig);const F=S.rosPos||'ALL';const a=P.filter(p=>F==='ALL'||p.pos===F).sort((x,y)=>y.ros_total-x.ros_total).slice(0,60);const wks=[...new Set(a.flatMap(p=>p.ros.map(r=>r[0])))].sort((x,y)=>x-y);
  m.innerHTML=`<div class="note">Rest-of-season weekly Book A projections <span class="est">estimates</span>: each player's current per-game baseline, adjusted for the opponent's defense vs position and the implied team total. Players on this slate only. Bye weeks are blank.</div><div class="filters">${['ALL','QB','RB','WR','TE','DST'].map(x=>`<button class="lk ${F===x?'on':''}" data-rp="${x}">${x}</button>`).join('')}</div>
  <div class="table-wrap"><table class="tight"><thead><tr><th>Player</th><th class="num">ROS total</th>${wks.map(w=>`<th class="num">Wk ${w}</th>`).join('')}</tr></thead><tbody>${a.map(p=>`<tr data-pid="${p.id}" style="cursor:pointer"><td>${plCell(p)}</td><td class="num"><b>${f1(p.ros_total)}</b></td>${wks.map(w=>{const r=p.ros.find(x=>x[0]===w);return `<td class="num" title="${r?'vs '+r[1]:'bye'}">${r?`<span style="font-size:10px;color:var(--text-3)">${r[1]}</span> ${f1(r[2])}`:'–'}</td>`}).join('')}</tr>`).join('')}</tbody></table></div>`;
  m.querySelectorAll('[data-rp]').forEach(b=>b.onclick=()=>{S.rosPos=b.dataset.rp;pRos(m)});bindRows(m);}
function pGames(m){const s=sl();m.innerHTML=staleNote()+`<div class="gm">${s.games.map(g=>{const wx=g.wx||{};const P=pool().filter(p=>p.game===g.key&&p.proj>0).sort((a,b)=>b.proj-a.proj).slice(0,4);
  return `<div class="card"><div style="display:flex;justify-content:space-between"><b>${esc(g.away)} @ ${esc(g.home)}</b><span style="color:var(--text-3);font-size:12px">${g.time?new Date(g.time).toLocaleString([], {weekday:'short',hour:'numeric',minute:'2-digit'}):''}</span></div>
  <div style="font-size:13px;color:var(--text-2);margin:6px 0">${g.total?`Total <b class="mono">${g.total}</b> · ${esc(g.details||'')}<br>Implied: ${esc(g.away)} <b class="mono">${f1(g.itt_away)}</b> · ${esc(g.home)} <b class="mono">${f1(g.itt_home)}</b>`:'Lines not posted yet'}</div>
  <div style="font-size:12px;color:var(--text-3)">${wx.dome?'🏟 '+esc(wx.dome):wx.temp!=null?`${Math.round(wx.temp)}°F · wind ${Math.round(wx.wind)} mph · rain ${wx.pop}%`:'Forecast within 15 days of kickoff'}${(wx.flags||[]).map(f=>`<div style="color:var(--warn)">${esc(f)}</div>`).join('')}</div>
  <div style="margin-top:8px">${P.map(p=>`<span class="chip" data-pid="${p.id}" style="cursor:pointer">${esc(p.name.split(' ').slice(-1)[0])} ${f1(p.proj)}</span>`).join('')}</div></div>`}).join('')}</div>`;bindRows(m);}
function accCard(){return ''}
function pMethod(m){m.innerHTML=`<div class="card"><div class="card-head"><h2>About Fantasy Frontier</h2></div><p>Fantasy Frontier projects every DFS player from his role, matchup and the betting lines, then builds lineups from those projections. Estimates only. 21+.</p></div>`}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.querySelector('.modal-bg'))history.back()});
const SLOTS=()=>isSD()?['CPT','FLEX','FLEX','FLEX','FLEX','FLEX']:['QB','RB','RB','WR','WR','WR','TE','FLEX','DST'];
const fits=(slot,p)=>slot==='CPT'||(slot==='FLEX'?(isSD()?true:'RB WR TE'.includes(p.pos)):p.pos===slot);
function bslots(){const k=lockK();S.bld=S.bld||ls.get('bld',{});const sl_=SLOTS();let a=(S.bld[k]||[]).slice(0,sl_.length);while(a.length<sl_.length)a.push(null);
  const L=locks();const byId=Object.fromEntries(pool().map(p=>[p.id,p]));a=a.map(id=>id&&L[id]&&byId[id]?id:null);
  for(const id of Object.keys(L)){if(a.includes(id)||!byId[id])continue;const p=byId[id];let i=sl_.findIndex((s,j)=>!a[j]&&s===p.pos);if(i<0)i=sl_.findIndex((s,j)=>!a[j]&&s!=='CPT'&&fits(s,p));if(i<0)i=sl_.findIndex((s,j)=>!a[j]&&fits(s,p));if(i>=0)a[i]=id;}
  S.bld[k]=a;ls.set('bld',S.bld);const fc=a[0]&&isSD()?a[0]:null;S.forceCpt=S.forceCpt||{};S.forceCpt[k]=fc;return a;}
function setSlot(i,id){const k=lockK();const a=bslots();const old=a[i];if(old){delete (S.lock[k]||{})[old];}if(id){const j=a.indexOf(id);if(j>=0)a[j]=null;a[i]=id;S.lock[k]=S.lock[k]||{};S.lock[k][id]=1;if(S.excl[k])delete S.excl[k][id];}else a[i]=null;
  S.bld[k]=a;ls.set('bld',S.bld);ls.set('lock',S.lock);ls.set('excl',S.excl);S.results=null;S.rec={};}
function tags(p){const t=[];if(p.shot)t.push('<span class="chip hot">their shot</span>');if(p.smash&&p.smash.p>=20)t.push(`<span class="chip">smash ${Math.round(p.smash.p)}%</span>`);(p.flags||[]).filter(f=>/Expanding|disagree|Questionable|Doubtful/.test(f)).slice(0,2).forEach(f=>t.push(`<span class="chip ${/Questionable|Doubtful|disagree/.test(f)?'':'cool'}">${esc(f)}</span>`));if(lev(p)>=2.5&&p.proj>=8)t.push('<span class="chip cool">leverage</span>');return t.join(' ');}
function builder(){const sd=isSD();const sl_=SLOTS();const a=bslots();const byId=Object.fromEntries(pool().map(p=>[p.id,p]));
  const sal=(p,i)=>sd&&i===0?p.csal:p.sal;const pr=(p,i)=>sd&&i===0?1.5*p.proj:p.proj;
  const used=a.reduce((t,id,i)=>t+(id?sal(byId[id],i):0),0),rem=50000-used,open=a.filter(x=>!x).length,tot=a.reduce((t,id,i)=>t+(id?pr(byId[id],i):0),0);
  const act=S.bslot;
  return `<div class="card bld" style="margin-bottom:16px"><div class="card-head"><h2>Lineup Builder</h2><span class="sub">Tap a slot to see the ranked eligible players, then tap one to fill it. Auto-fill completes the lineup around your highlights</span></div>
  <div class="bld-wrap"><div class="bld-roster">${sl_.map((s,i)=>{const p=a[i]&&byId[a[i]];return `<button class="bld-slot ${act===i?'on':''} ${p?'full':''}" data-bs="${i}"><span class="pos-tag pos-${s}">${s}</span>${p?`<span class="n"><b>${esc(p.name)}</b><span class="t">${esc(p.team)} ${s==='FLEX'||s==='CPT'?esc(p.pos):''} · ${fmt$(sal(p,i))}</span></span><span class="mono">${f1(pr(p,i))}</span>`:`<span class="n t">Empty, tap to highlight</span><span></span>`}</button>`}).join('')}</div>
  <div class="bld-side"><div class="bld-stats"><div><span>Remaining</span><b style="color:${rem<0?'var(--neg)':'inherit'}">${rem<0?'-':''}${fmt$(Math.abs(rem))}</b></div><div><span>Avg / open slot</span><b>${open?fmt$(Math.max(0,rem)/open):'–'}</b></div><div><span>Projected</span><b>${f1(tot)}</b></div><div><span>Filled</span><b>${sl_.length-open}/${sl_.length}</b></div></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px"><button class="btn primary" id="bAuto" ${open?'':'disabled'}>✨ Auto-fill the rest</button><button class="btn" id="bClr" ${open<sl_.length?'':'disabled'}>Clear all</button>${!open?'<button class="btn" id="bCsv">Export to Book A CSV</button>':''}</div><p id="bMsg" style="font-size:12px;color:var(--text-3);margin:8px 0 0"></p></div></div>
  ${act!=null&&act<sl_.length?picker(act,a,rem,byId):''}</div>`;}
function picker(i,a,rem,byId){const sd=isSD();const slot=SLOTS()[i];const cur=a[i]&&byId[a[i]];const E=excls();const srt=S.bsort||'proj';
  const sal=p=>sd&&i===0?p.csal:p.sal;const pr=p=>sd&&i===0?1.5*p.proj:p.proj;const room=rem+(cur?sal(cur):0);
  let list=elig().filter(p=>p.proj>0&&!E[p.id]&&fits(slot,p)&&!(a.includes(p.id)&&a[i]!==p.id)&&(!sd||i!==0||p.cid));
  if(S.bq)list=list.filter(p=>p.name.toLowerCase().includes(S.bq.toLowerCase()));
  const key={proj:p=>pr(p),val:p=>pr(p)/sal(p),ceil:p=>p.ceil,smash:p=>p.smash?p.smash.p:0}[srt];list.sort((x,y)=>key(y)-key(x));list=list.slice(0,40);
  return `<div class="bld-pick"><div class="bld-pick-h"><b>${slot} options</b>${cur?` <button class="btn ghost" id="bRm">Remove ${esc(cur.name)}</button>`:''}<span class="seg">${[['proj','Proj'],['val','Value'],['ceil','Ceiling'],['smash','Smash']].map(([k,l])=>`<button class="lk ${srt===k?'on':''}" data-bsort="${k}">${l}</button>`).join(' ')}</span><input id="bQ" placeholder="Search" value="${esc(S.bq||'')}" style="max-width:140px"></div>
  <div class="bld-list">${list.map(p=>`<div role="button" tabindex="0" class="bld-opt ${sal(p)>room?'over':''} ${a[i]===p.id?'on':''}" data-bp="${p.id}">${plCell(p)}<span class="mono">${fmt$(sal(p))}</span><span class="mono"><b>${f1(pr(p))}</b></span><span class="mono">${f1(pr(p)/sal(p)*1000)}x</span><span class="bt">${tags(p)}</span></div>`).join('')||'<p style="color:var(--text-3)">No eligible players.</p>'}</div><p style="font-size:11px;color:var(--text-3);margin:6px 0 0">Columns: salary · projection · pts per $1k. Dimmed = over your remaining budget. Smash % is informational (see Film Room).</p></div>`;}
function bindBuilder(m,o,read){m.querySelectorAll('[data-bs]').forEach(b=>b.onclick=()=>{const i=+b.dataset.bs;S.bslot=S.bslot===i?null:i;S.bq='';route();setTimeout(()=>{const el=$('.bld-pick');if(el)el.scrollIntoView({block:'nearest'})},0)});
  m.querySelectorAll('[data-bp]').forEach(b=>b.onclick=()=>{setSlot(S.bslot,b.dataset.bp);const a=bslots();const nx=a.findIndex(x=>!x);S.bslot=nx>=0?nx:null;route();});
  m.querySelectorAll('[data-bsort]').forEach(b=>b.onclick=()=>{S.bsort=b.dataset.bsort;route()});
  const q=$('#bQ');if(q)q.oninput=()=>{S.bq=q.value;const pos=q.selectionStart;route();const q2=$('#bQ');q2.focus();q2.setSelectionRange(pos,pos)};
  if($('#bRm'))$('#bRm').onclick=()=>{setSlot(S.bslot,null);route()};
  if($('#bClr'))$('#bClr').onclick=()=>{const k=lockK();delete S.lock[k];S.bld[k]=[];ls.set('lock',S.lock);ls.set('bld',S.bld);S.bslot=null;S.results=null;S.rec={};route()};
  if($('#bCsv'))$('#bCsv').onclick=()=>{const a=bslots();exportCSV([{rows:a.map((id,i)=>{const p=pool().find(x=>x.id===id);return {slot:SLOTS()[i],p,dkid:isSD()&&i===0?p.cid:p.id}})}])};
  if($('#bAuto'))$('#bAuto').onclick=()=>{read();$('#bMsg').textContent='Solving around your highlights…';setTimeout(()=>{const cfg=Object.assign({},o,{contest:o.contest==='gpp'?'bal':o.contest,minsal:Math.min(o.minsal,48000)});const R=optimize(cfg,1);
    if(!R.length){$('#bMsg').innerHTML='<span style="color:var(--neg)">No valid lineup fits around these highlights. Free up salary or swap a slot.</span>';return}
    const a=bslots();const sl_=SLOTS();const rows=R[0].rows.filter(r=>!a.includes(r.p.id));
    if(isSD()&&!a[0]){const c=rows.findIndex(r=>r.slot==='CPT');if(c>=0){setSlot(0,rows[c].p.id);rows.splice(c,1);}}
    const order=sl_.map((s,i)=>i).sort((x,y)=>(sl_[x]==='FLEX')-(sl_[y]==='FLEX'));
    for(const i of order){if(bslots()[i])continue;const j=rows.findIndex(r=>fits(sl_[i],r.p)&&(sl_[i]==='CPT'||r.slot!=='CPT'));if(j>=0){setSlot(i,rows[j].p.id);rows.splice(j,1);}}
    S.bslot=null;route();},20)};}
/* ---------- Best of breed ---------- */
function pBest(m){const P=elig().filter(p=>p.proj>0);const sd=isSD();const poss=sd?['QB','RB','WR','TE','DST']:['QB','RB','WR','TE','DST'];
  const card=(t,sub,arr,cols)=>`<div class="card"><div class="card-head"><h2>${t}</h2><span class="sub">${sub}</span></div>${tbl(arr,cols)}</div>`;
  const ceil=[...P].sort((a,b)=>b.ceil-a.ceil).slice(0,12);const cpv=[...P].filter(p=>p.proj>=6).sort((a,b)=>b.ceil/b.sal-a.ceil/a.sal).slice(0,10);
  m.innerHTML=staleNote()+`<div class="note">The top producers at each position for this slate, with what they cost. <b>Proj</b> = our projection, <b>Ceil</b> = a big-game outcome.</div>
  <div class="grid two" style="margin-bottom:16px">${poss.map(pos=>{const a=P.filter(p=>p.pos===pos);if(!a.length)return '';const top=[...a].sort((x,y)=>y.proj-x.proj).slice(0,6);const bv=[...a].filter(p=>p.proj>=(pos==='DST'?4:6)).sort((x,y)=>y.val-x.val)[0];
    return `<div class="card"><div class="card-head"><h2>${posTag(pos)} Best ${pos}s</h2>${bv?`<span class="sub">best value: <b>${esc(bv.name)}</b> ${fmt$(bv.sal)} · ${f1(bv.val)}x</span>`:''}</div>${tbl(top,['sal','proj','ceil','val'])}</div>`}).join('')}</div>
  <div class="grid two">${card('Highest ceiling plays','top 90th-percentile outcomes',ceil,['sal','proj','ceil','own'])}${card('Ceiling per dollar','ceiling ÷ salary: GPP leverage on a budget',cpv,['sal','ceil','val','smash'])}</div>`;bindRows(m);}
/* ---------- Film Room ---------- */

/* ---------- Lineup track record (pre-lock snapshots graded after the game) ---------- */
function pTrack(m){const snaps=S.snaps||[],R=(S.trk&&S.trk.slates)||{};const NM={safe:'Safe · Cash',bal:'Balanced · SE',up:'Upside · GPP',val:'Value test · ≤$49k (research)'};
  const groups={};snaps.forEach(x=>{if(x.logged_at<x.lock)(groups[x.kind+'-'+x.dg]=groups[x.kind+'-'+x.dg]||[]).push(x)});
  const keys=Object.keys(groups).sort((a,b)=>groups[b][0].lock.localeCompare(groups[a][0].lock));
  const et=t=>new Date(t).toLocaleString('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+' ET';
  const graded=keys.map(k=>R[k]).filter(r=>r&&r.final&&r.lineups);
  const rec=['safe','bal','up'].map(t=>{const g=graded.filter(r=>r.lineups[t]);if(!g.length)return null;const beat=g.filter(r=>r.baselines&&r.baselines.chalk&&r.lineups[t].actual>r.baselines.chalk.actual).length;const po=g.map(r=>r.lineups[t].pct_of_optimal).filter(x=>x!=null);
    return `<div><div class="kpi-label">${NM[t]}</div><b class="mono">${g.length} graded</b><div class="t" style="font-size:12px;color:var(--text-3)">Beat chalk ${beat}/${g.length} · avg ${po.length?f1(po.reduce((a,b)=>a+b,0)/po.length)+'% of optimal':'–'} · proj vs actual ${f1(g.reduce((a,r)=>a+r.lineups[t].actual-r.lineups[t].proj,0)/g.length)}</div></div>`}).filter(Boolean).join('');
  let h=`<div class="note">Every highlighted lineup is written to an <b>append-only log before lock</b> so nothing was picked after the fact. After the game, each player is scored with Book A rules from league feed's public box score, then compared to the hindsight-optimal lineup and to two naive baselines: <b>chalk</b> (highest ownership proxy) and <b>max salary</b>. Contest field results (cash line, winning score) are <b>unavailable</b>: Book A doesn't publish them in a permitted feed, and we don't scrape.</div>`;
  h+=`<div class="card" style="margin-bottom:16px"><div class="card-head"><h2>Running record</h2><span class="sub">${graded.length} slate${graded.length===1?'':'s'} graded</span></div>${rec?`<div class="grid kpis" style="grid-template-columns:repeat(3,1fr)">${rec}</div>`:'<p style="padding:4px 2px">No slates graded yet. The first grade posts after the game goes final.</p>'}</div>`;
  if(!keys.length)h+='<p>No lineups logged yet.</p>';
  for(const k of keys){const ss=groups[k].sort((a,b)=>a.logged_at.localeCompare(b.logged_at)),o=ss[ss.length-1],r=R[k]||{};
    const st=r.final?`Final ${Object.entries(r.score||{}).map(([t,v])=>t+' '+v).join(', ')}`:r.state==='in'?'In progress (live points)':'Logged, awaiting kickoff';
    h+=`<div class="card" style="margin-bottom:16px"><div class="card-head"><h2>${esc(o.game||o.label)} · ${o.type==='showdown'?'Showdown':'Classic'}</h2><span class="sub">${(()=>{const v=(S.ver||{})[o.logged_at];return v?(v.ok?`<span style="background:#14532d;color:#86efac;border-radius:6px;padding:2px 7px;font-weight:600;margin-right:6px" title="Checked ${esc(et(v.checked_at))} against Book A's public player list: all players on slate and active, salaries match (CPT 1.5x), ≤ $50k, 1 CPT + 5 FLEX, both teams">✓ Book A-verified</span>`:`<span style="background:#7f1d1d;color:#fecaca;border-radius:6px;padding:2px 7px;font-weight:600;margin-right:6px" title="${esc(Object.values(v.lineups).flatMap(x=>x.errors).join('; '))}">✗ Book A check failed</span>`):'<span style="color:var(--text-3);margin-right:6px">Book A check pending</span>'})()}${esc(st)} · lock ${et(o.lock)} · official snapshot ${et(o.logged_at)}${ss.length>1?' ('+ss.length+' pre-lock versions)':''}</span></div><div class="table-wrap"><table class="tight"><thead><tr><th>Lineup</th><th>Players</th><th class="num">Salary</th><th class="num">Proj</th><th class="num">Actual</th><th class="num">% of optimal</th></tr></thead><tbody>`;
    const row=(nm,lu,g)=>`<tr><td><b>${nm}</b></td><td style="font-size:12px">${lu.rows.map((x,i)=>{const gx=g&&g.rows&&g.rows[i];return `${x.slot==='CPT'?'<b>CPT</b> ':''}${esc(x.name)}${gx&&gx.actual!=null?` <span class="mono" style="color:var(--text-3)">${f1(gx.actual)}</span>`:''}`}).join(' · ')}</td><td class="num">${lu.sal?fmt$(lu.sal):'–'}</td><td class="num">${f1(lu.proj)}</td><td class="num">${g?f1(g.actual):'–'}</td><td class="num">${g&&g.pct_of_optimal!=null?f1(g.pct_of_optimal)+'%':'–'}</td></tr>`;
    for(const t of ['safe','bal','up','val'])if(o.lineups[t])h+=row(NM[t],o.lineups[t],r.lineups&&r.lineups[t]);
    for(const [t,nm] of [['chalk','Baseline · chalk'],['max_salary','Baseline · max salary']])if(o.baselines&&o.baselines[t])h+=row(nm,o.baselines[t],r.baselines&&r.baselines[t]);
    h+=r.hindsight?row('Hindsight optimal',Object.assign({proj:null},r.hindsight),r.hindsight):`<tr><td><b>Hindsight optimal</b></td><td colspan="5" style="color:var(--text-3)">Computed once the game is final</td></tr>`;
    h+=`<tr><td><b>Contest field</b></td><td colspan="5" style="color:var(--text-3)">Unavailable: no permitted public source for Book A cash lines or winning scores</td></tr></tbody></table></div>${(r.notes||[]).length?`<p style="font-size:12px;color:var(--text-3);margin-top:8px">${r.notes.map(esc).join('. ')}.</p>`:''}</div>`;}
  m.innerHTML=h;}
function pFilm(m){const F=S.film;if(!F){m.innerHTML='<div class="note">Film Room data has not been generated yet.</div>';return}
  const v=F.validation||{};const wk=S.fwk||(F.weeks[F.weeks.length-1]||{}).w;const W=F.weeks.find(x=>x.w===wk)||F.weeks[0];const up=(F.upcoming||{})[S.kind]||[];
  const byId=sl()?Object.fromEntries(pool().map(p=>[p.name+'|'+p.team,p])):{};
  const row=x=>`<tr><td>${posTag(x.pos)} <b>${esc(x.name)}</b> <span style="color:var(--text-3);font-size:11.5px">${esc(x.team)} v ${esc(x.opp)}</span><ul class="edge-list" style="margin:4px 0 0">${(x.why||[]).map(w=>`<li>${esc(w)}</li>`).join('')||'<li style="color:var(--text-3)">No single standout driver (efficiency / variance)</li>'}</ul></td><td class="num">${f1(x.pts)}</td><td class="num">${fmt$(x.sal)}<span class="est" style="margin-left:4px">proxy</span></td><td class="num">${f1(x.val)}x</td><td class="num">${f1(x.prior)}</td></tr>`;
  const thd='<thead><tr><th>Player · why</th><th class="num">Book A pts</th><th class="num">Salary</th><th class="num">Pts/$1k</th><th class="num">Pre-week avg</th></tr></thead>';
  m.innerHTML=`<div class="note">Film Room reviews every completed week: who scored, who smashed value, and why.</div>
  ${sl()?`<div class="card" style="margin-bottom:16px"><div class="card-head"><h2>Smash likelihood: ${esc(KINDS[S.kind])}</h2><span class="est">estimate · info only</span></div><div class="table-wrap"><table class="tight"><thead><tr><th>Player</th><th>Where / when</th><th class="num">Salary</th><th class="num">Proj</th><th class="num">Smash</th><th>Why</th></tr></thead><tbody>${up.map(x=>{const p=byId[x.name+'|'+x.team];return `<tr ${p?`data-pid="${p.id}" style="cursor:pointer"`:''}><td>${posTag(x.pos)} <b>${esc(x.name)}</b> <span style="color:var(--text-3);font-size:11.5px">${esc(x.team)}</span></td><td style="font-size:12px">${esc(x.game)} v ${esc(x.opp)}${x.time?' · '+new Date(x.time).toLocaleString([],{weekday:'short',hour:'numeric',minute:'2-digit'}):''}</td><td class="num">${fmt$(x.sal)}</td><td class="num">${f1(x.proj)}</td><td class="num"><b>${f1(x.p)}%</b></td><td style="font-size:11.5px;color:var(--text-2)">${x.f.map(esc).join(' · ')}</td></tr>`}).join('')}</tbody></table></div></div>`:''}
  <div class="card"><div class="card-head"><h2>Week ${W.w} review</h2><span class="seg">${F.weeks.map(x=>`<button class="lk ${x.w===W.w?'on':''}" data-fw="${x.w}">W${x.w}</button>`).join(' ')}</span></div><p style="font-size:12.5px;color:var(--text-2);margin:0 0 8px">${W.n_smash} value smashes among ${W.n} players with stats. Salaries are the proxy described above, not real Book A prices for that week.</p>
  <div class="grid two"><div><h4 style="margin:0 0 6px">Biggest value smashes</h4><div class="table-wrap"><table class="tight">${thd}<tbody>${W.smash.map(row).join('')}</tbody></table></div></div><div><h4 style="margin:0 0 6px">Top Book A scorers</h4><div class="table-wrap"><table class="tight">${thd}<tbody>${W.top.map(row).join('')}</tbody></table></div></div></div></div>`;
  m.querySelectorAll('[data-fw]').forEach(b=>b.onclick=()=>{S.fwk=+b.dataset.fw;route()});bindRows(m);}

window.addEventListener('hashchange',()=>{if(!document.querySelector('.modal-bg'))route()});
load();
})();
