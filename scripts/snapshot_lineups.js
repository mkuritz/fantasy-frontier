// Pre-lock accountability snapshot: rebuilds the exact Safe/Balanced/Upside lineups the site shows
// (same optimizer code, extracted from app.js) and appends them to data/track/lineups.jsonl.
// Append-only: an existing entry for the same slate+data version is never rewritten; the git commit time proves pre-lock.
const fs=require('fs'),path=require('path'),vm=require('vm');
const R=path.join(__dirname,'..');const kind=process.argv[2]||'mon';
const slate=JSON.parse(fs.readFileSync(path.join(R,'data','slate_'+kind+'.json')));
if(slate.stale){console.log('stale slate; skip');process.exit(0);}
const lock=new Date(slate.start.slice(0,19)+'-04:00');
if(Date.now()>=lock.getTime()&&!process.env.ALLOW_AFTER_LOCK){console.log('locked; no snapshot');process.exit(0);}
const app=fs.readFileSync(path.join(R,'app.js'),'utf8');
const a=app.indexOf('/* ---------- Optimizer'),b=app.indexOf('function recBlock');
const ctx={console};ctx.self=ctx;vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(R,'assets','solver.js'),'utf8'),ctx);

const pre=`var S={rec:{},lock:{},excl:{},kind:${JSON.stringify(kind)},slates:{}};var SL=null;const sl=()=>SL;const isSD=()=>SL.type==='showdown';const lockK=()=>'k';const locks=()=>({});const excls=()=>({});const pool=()=>SL.players.filter(p=>p.sal);const fmt$=n=>'$'+(n/1000).toFixed(1)+'k';`+app.split('\n').find(l=>l.startsWith('const FEES='));
vm.runInContext(pre+app.slice(a,b)+';this.recs=recs;this.why=why;this.optimize=optimize;this.setSL=s=>{SL=s};',ctx);
if(!ctx.solver)throw new Error('solver not loaded');
ctx.setSL(slate);const r=ctx.recs();
// Research-only salary test (not shown as a public pick): median-optimal build capped at $49k, i.e. leaves >= $1k unused.
// Added Oct 16 2026 after a retro test on the first two graded showdowns (data/track/salary_study.json); graded like the others
// so it only goes public if it keeps scoring as well as the full-cap builds.
if(slate.type==='showdown'){const v=ctx.optimize({n:1,exp:100,uniq:1,minsal:46000,script:'any',contest:'cash',fee:50,med:1,stack:0,bring:0,cap:49000},1,[])[0];if(v)r.val=v;}
const out={logged_at:new Date().toISOString(),kind,dg:slate.dg,label:slate.label.trim(),type:slate.type,lock:lock.toISOString(),data_fetched:slate.fetched,game:(slate.games[0]||{}).key,espn_id:(slate.games[0]||{}).id,lineups:{}};
for(const [k,lu] of Object.entries(r)){if(!lu)continue;out.lineups[k]={proj:+lu.proj.toFixed(2),sal:lu.sal,floor:+lu.floor.toFixed(1),ceil:+lu.ceil.toFixed(1),own:Math.round(lu.own),why:ctx.why(lu),
  rows:lu.rows.map(x=>({slot:x.slot,id:x.p.id,name:x.p.name,team:x.p.team,pos:x.p.pos,sal:x.sal,proj:+x.pts.toFixed(2),edges:x.p.edges||[]}))};}
// naive baselines (pre-lock, same rules): chalk = highest own proxy captain + top-own flex under cap; maxsal = spend-up by salary
const P=slate.players.filter(p=>p.sal&&p.elig&&p.proj>0.5);
function greedy(key){const cpt=[...P].filter(p=>p.cid).sort((x,y)=>y[key]-x[key]);for(const c of cpt){let sal=c.csal,rows=[{slot:'CPT',id:c.id,name:c.name,team:c.team,pos:c.pos,sal:c.csal,proj:+(1.5*c.proj).toFixed(2)}];
  for(const p of [...P].sort((x,y)=>y[key]-x[key])){if(rows.length==6)break;if(p.id===c.id||sal+p.sal>50000)continue;sal+=p.sal;rows.push({slot:'FLEX',id:p.id,name:p.name,team:p.team,pos:p.pos,sal:p.sal,proj:p.proj});}
  if(rows.length==6&&new Set(rows.map(x=>x.team)).size>1)return {sal,proj:+rows.reduce((s,x)=>s+x.proj,0).toFixed(2),rows};}return null;}
if(slate.type==='showdown')out.baselines={chalk:greedy('own'),max_salary:greedy('sal')};
const f=path.join(R,'data','track','lineups.jsonl');const prev=fs.existsSync(f)?fs.readFileSync(f,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];
const sig=JSON.stringify(out.lineups);
const last=prev.filter(e=>e.kind===kind&&e.dg===out.dg).pop();
if(last&&JSON.stringify(last.lineups)===sig){console.log('unchanged since',last.logged_at);process.exit(0);}
fs.appendFileSync(f,JSON.stringify(out)+'\n');console.log('logged',kind,out.dg,Object.keys(out.lineups).join(','));
for(const [k,l] of Object.entries(out.lineups))console.log(k,l.proj,l.sal,l.rows.map(x=>x.slot+':'+x.name+'('+x.sal+','+x.proj+')').join(' | '),'\n  ',l.why.join(' / '));
