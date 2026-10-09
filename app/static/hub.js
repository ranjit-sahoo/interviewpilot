(()=>{'use strict';
const D=window.HUBDATA,$=id=>document.getElementById(id);let M=null,ME=null,OPT=null;
const VIEWS={'h-dash':'Dashboard','h-camp':'Screening Campaigns','h-screen':'Resume Screener','h-pipe':'Pipeline','h-kit':'Hiring Kit','h-team':'Company & Team','h-skills':'Skill Tests'};
const STYLE=`body[data-view^="h-"] .layout{display:none}#hubRoot{display:none}body[data-view^="h-"] #hubRoot{display:block}
#hubRoot .card{margin:12px 0}#hubRoot h3{margin:0 0 8px;font-size:17px}#hubRoot table{width:100%;border-collapse:collapse;font-size:14px}#hubRoot th,#hubRoot td{padding:8px 6px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
#hubRoot .tw{overflow-x:auto}#hubRoot .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}#hubRoot .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
#hubRoot .stat{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px}#hubRoot .stat b{display:block;font-size:26px}#hubRoot .tag{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;border:1px solid var(--line);margin:2px 4px 2px 0}
#hubRoot .tag.bad{color:var(--bad);border-color:var(--bad)}#hubRoot .tag.ok{color:var(--acc);border-color:var(--acc)}#hubRoot .tag.warn{color:var(--warn);border-color:var(--warn)}
#hubRoot textarea,#hubRoot input[type=text],#hubRoot input[type=number],#hubRoot input[type=tel],#hubRoot input[type=date],#hubRoot input[type=time],#hubRoot input[type=datetime-local],#hubRoot select{width:100%;margin:4px 0 8px}
#hubRoot .cols{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(220px,1fr);gap:10px;overflow-x:auto;padding-bottom:8px}#hubRoot .col{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:8px}
#hubRoot .pc{background:#0d1426;border:1px solid var(--line);border-radius:10px;padding:8px;margin:6px 0;font-size:14px}#hubRoot button.sm{min-height:36px;padding:4px 10px;font-size:13px}
#hubRoot pre{white-space:pre-wrap;background:#0d1426;border:1px solid var(--line);border-radius:12px;padding:12px;font:inherit;font-size:14px}
#hubRoot .pass{font-size:17px;line-height:1.7;background:#0d1426;border-radius:12px;padding:12px;user-select:none}
body.lite *{animation:none!important;transition:none!important}body.lite .hero .strip,body.lite .hero .feat{display:none!important}`;
function h(tag,a,...k){const e=document.createElement(tag);for(const x in(a||{})){if(x==='class')e.className=a[x];else if(x.startsWith('on'))e.addEventListener(x.slice(2),a[x]);else if(x==='value')e.value=a[x];else if(a[x]!==false&&a[x]!=null)e.setAttribute(x,a[x])}
 for(const c of k.flat())if(c!=null&&c!==false)e.append(c.nodeType?c:document.createTextNode(c));return e}
async function api(p,o){const r=await fetch(p,Object.assign({headers:{'Content-Type':'application/json'},credentials:'same-origin'},o||{}));let j={};try{j=await r.json()}catch(e){}
 if(!r.ok){const er=new Error(typeof j.detail==='string'?j.detail:'Please check your entries and try again.');er.status=r.status;throw er}return j}
const get=p=>api(p),send=(p,b,m)=>api(p,{method:m||'POST',body:JSON.stringify(b||{})});
const lbl=(t,el)=>h('div',{},h('label',{},t),el);
function err(el){return m=>{el.textContent=m&&m.message||m||''}}
function dl(name,text,type){const a=h('a',{href:URL.createObjectURL(new Blob([text],{type:type||'text/plain'})),download:name});document.body.append(a);a.click();a.remove()}
function csvCell(v){v=v==null?'':String(v);if(/^[=+\-@]/.test(v))v="'"+v;return '"'+v.replace(/"/g,'""')+'"'}
const toCsv=rows=>'\ufeff'+rows.map(r=>r.map(csvCell).join(',')).join('\r\n');
function printHtml(title,html){const w=window.open('','_blank');if(!w){alert('Please allow pop-ups to print.');return}w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${D.esc(title)}</title><style>body{font:14px/1.5 system-ui,sans-serif;padding:24px;color:#111}table{border-collapse:collapse}td,th{vertical-align:top}</style></head><body>${html}</body></html>`);w.document.close();setTimeout(()=>w.print(),300)}
async function copy(t,btn){try{await navigator.clipboard.writeText(t);if(btn){const o=btn.textContent;btn.textContent='Copied';setTimeout(()=>btn.textContent=o,1200)}}catch(e){prompt('Copy this:',t)}}
const wa=(ph,msg)=>'https://wa.me/'+String(ph||'').replace(/\D/g,'')+'?text='+encodeURIComponent(msg);
const audit=a=>send('/api/hub/audit',{action:a,target:''}).catch(()=>{});
const when=ts=>ts?new Date(ts*1000).toLocaleString():'';
const LINK=t=>location.origin+'/s/'+t;
const root=()=>$('hubRoot');
function head(t,sub){return[h('h2',{style:'margin:6px 0'},t),sub?h('p',{class:'note'},sub):null]}
function need(role){const r=root();r.replaceChildren(h('div',{class:'card'},h('h3',{},role==='recruiter'?'Recruiter account needed':'Candidate account needed'),
 h('p',{},role==='recruiter'?'These tools are for recruiters. Create a free recruiter account (use a different email from any candidate account) or log in as a recruiter.':'These practice tests are for candidates. You are logged in as a recruiter, so they are not available on this account.'),
 role==='recruiter'?h('button',{'data-v':'account'},'Log in / Sign up'):null))}

// ================= recruiter: dashboard
async function vDash(r){const d=await get('/api/hub/dashboard');
 r.append(...head('Dashboard'),h('div',{class:'grid'},[['Campaigns',d.campaigns],['Open',d.open],['Invited',d.invited],['Completed',d.completed],['In progress',d.in_progress],['Completion',d.completion_rate==null?'-':d.completion_rate+'%'],['Avg score',d.avg_score==null?'-':d.avg_score],['Avg time (min)',d.avg_minutes==null?'-':d.avg_minutes]].map(([a,b])=>h('div',{class:'stat'},h('span',{class:'note'},a),h('b',{},String(b))))),
 h('div',{class:'card'},h('h3',{},'Pipeline'),h('div',{class:'row'},Object.entries(d.pipeline||{}).map(([s,n])=>h('span',{class:'tag'},s+': '+n)))),
 h('div',{class:'card'},h('h3',{},'By campaign'),(d.per_campaign&&d.per_campaign.length)?h('div',{class:'tw'},h('table',{},h('tr',{},['Campaign','Invited','Done','Avg'].map(x=>h('th',{},x))),d.per_campaign.map(c=>h('tr',{},h('td',{},c.name),h('td',{},c.total),h('td',{},c.done),h('td',{},c.avg==null?'-':Math.round(c.avg)))))):h('p',{class:'note'},'No campaigns yet. Create one in Screening Campaigns.')))}

// ================= recruiter: campaigns
async function vCamp(r){const [o,l]=await Promise.all([OPT?OPT:get('/api/hub/options'),get('/api/hub/campaigns')]);OPT=o;const view=ME.org_role==='viewer';
 const list=h('div',{});const detail=h('div',{});
 function renderList(cs){list.replaceChildren(...(cs.length?cs.map(c=>h('div',{class:'card'},h('div',{class:'row',style:'justify-content:space-between'},h('div',{},h('b',{},c.name),h('div',{class:'note'},o.pools[c.pool]+' - '+c.modules.map(m=>o.modules[m].split(' ')[0]).join(', '))),h('span',{class:'tag '+(c.status==='open'?'ok':'warn')},c.status)),
  h('div',{class:'note'},`Invited ${c.total} - Completed ${c.done}${c.avg!=null?' - Avg '+c.avg:''} - Expires ${new Date(c.expires*1000).toLocaleDateString()}`),h('button',{class:'sm',onclick:()=>openCamp(c.id)},'Open results and invites'))):[h('p',{class:'note'},'No campaigns yet.')]))}
 renderList(l.campaigns);
 const f={name:h('input',{type:'text',maxlength:80,placeholder:'e.g. Voice process drive, Oct'}),pool:h('select',{},Object.entries(o.pools).map(([k,v])=>h('option',{value:k},v))),n:h('select',{},[3,4,5,6,8,10].map(x=>h('option',{value:x,selected:x===6},x+' questions'))),secs:h('select',{},[45,60,90,120,180].map(x=>h('option',{value:x,selected:x===90},x+' seconds per answer'))),
  exp:h('select',{},[3,7,14,30,60].map(x=>h('option',{value:x,selected:x===14},'Link valid '+x+' days'))),ret:h('select',{},[7,14,30,60,90].map(x=>h('option',{value:x,selected:x===30},'Auto-delete answers after '+x+' days'))),
  lang:h('select',{},[['en','English'],['hinglish','Hinglish'],['hi','Hindi'],['ar','Arabic']].map(([a,b])=>h('option',{value:a},'Candidate screen language: '+b))),open:h('input',{type:'checkbox',checked:'checked'})};
 const mods=Object.entries(o.modules).map(([k,v])=>[k,v,h('input',{type:'checkbox',value:k,checked:['voice','typing'].includes(k)?'checked':null})]);const er=h('div',{class:'err',role:'alert'});
 r.append(...head('Screening Campaigns','Send candidates a link. They answer by voice on their phone (no typing), plus optional tests. Each candidate gets one attempt. Results are a first screen to help you shortlist, not a final decision.'),
  view?h('p',{class:'note'},'You have view-only access.'):h('div',{class:'card'},h('h3',{},'New campaign'),lbl('Name',f.name),lbl('Job type (picks the question set)',f.pool),h('label',{},'Tests included'),mods.map(([k,v,cb])=>h('label',{class:'consent'},cb,h('span',{},v))),
   lbl('Voice questions per candidate (drawn at random from a bigger set)',f.n),lbl('Time per answer',f.secs),lbl('Link expiry',f.exp),lbl('Privacy',f.ret),lbl('Language',f.lang),h('label',{class:'consent'},f.open,h('span',{},'Also create one shared open link (candidate enters name and phone; one attempt per phone number)')),er,
   h('button',{onclick:async ev=>{er.textContent='';const sel=mods.filter(m=>m[2].checked).map(m=>m[0]);if(!f.name.value.trim()){er.textContent='Please enter a campaign name.';return}if(!sel.length){er.textContent='Pick at least one test.';return}
    ev.target.disabled=true;try{const c=await send('/api/hub/campaigns',{name:f.name.value,pool:f.pool.value,modules:sel,n_questions:+f.n.value,secs:+f.secs.value,expires_days:+f.exp.value,retention_days:+f.ret.value,lang:f.lang.value,open_link:f.open.checked});openCamp(c.id,true)}catch(e){er.textContent=e.message}ev.target.disabled=false}},'Create campaign')),
  list,detail);
 async function openCamp(id,fresh){const d=await get('/api/hub/campaigns/'+id);const c=d.campaign;const co=ME.company||'our company';const name=h('textarea',{rows:4,placeholder:'One per line: Name, phone\nAsha Rao, 98765 43210'});const out=h('div',{});const e2=h('div',{class:'err'});
  const mins=Math.max(5,Math.round(((c.modules.includes('voice')?c.n_questions*(c.secs+40):0)+(c.modules.length)*150)/60));let lang='hinglish';
  const lsel=h('select',{onchange:()=>lang=lsel.value},[['hinglish','Hinglish'],['en','English'],['ar','Arabic']].map(([a,b])=>h('option',{value:a},'WhatsApp message: '+b)));
  detail.replaceChildren(h('div',{class:'card'},h('h3',{},c.name),h('div',{class:'note'},'Candidates can only take it once. Voice is converted to text in their browser; no audio is stored.'),
   c.open_link?h('div',{},h('p',{},h('b',{},'Open link: '),LINK('o-'+c.id)),h('div',{class:'row'},h('button',{class:'sm',onclick:ev=>copy(LINK('o-'+c.id),ev.target)},'Copy link'),h('a',{class:'sm',href:wa('',D.fill(D.MSG.invite.hinglish,{name:'',company:co,role:c.role_title,min:mins,link:LINK('o-'+c.id)})).replace('wa.me/','wa.me/'),target:'_blank',rel:'noopener'},'Share on WhatsApp'))):null,
   view?null:h('div',{},h('h3',{style:'margin-top:14px'},'Personal invites (WhatsApp)'),name,lsel,e2,h('button',{class:'sm',onclick:async()=>{e2.textContent='';const cands=name.value.split('\n').map(x=>x.trim()).filter(Boolean).map(x=>{const p=x.split(/[,\t]/);return{name:(p[0]||'').trim(),phone:(p[1]||'').trim()}});if(!cands.length)return;
    try{const res=await send('/api/hub/campaigns/'+id+'/invite',{candidates:cands});out.replaceChildren(h('div',{class:'tw'},h('table',{},res.invites.map(i=>h('tr',{},h('td',{},i.name),h('td',{},i.phone||'(no phone)'),h('td',{},i.phone?h('a',{href:wa(i.phone,D.fill(D.MSG.invite[lang],{name:i.name,company:co,role:c.role_title,min:mins,link:LINK(i.token)})),target:'_blank',rel:'noopener'},'Send on WhatsApp'):h('button',{class:'sm',onclick:ev=>copy(LINK(i.token),ev.target)},'Copy link')))))));openCamp(id)}catch(e){e2.textContent=e.message}}},'Create invite links')),out,
   view?null:h('div',{class:'row',style:'margin-top:10px'},h('button',{class:'ghost sm',onclick:async()=>{await send('/api/hub/campaigns/'+id+'/status',{status:c.status==='open'?'closed':'open'});openCamp(id)}},c.status==='open'?'Close campaign':'Re-open campaign'),
    h('button',{class:'ghost sm',onclick:async()=>{if(confirm('Delete this campaign and all its candidate answers?')){await send('/api/hub/campaigns/'+id,{},'DELETE');detail.replaceChildren();renderList((await get('/api/hub/campaigns')).campaigns)}}},'Delete campaign'))),
   resultsCard(d,id));detail.scrollIntoView({behavior:'smooth'})}
 function resultsCard(d,id){const a=d.attempts,c=d.campaign;
  const csvB=h('button',{class:'sm',onclick:()=>{audit('export_csv');dl('results-'+c.name.replace(/\W+/g,'_')+'.csv',toCsv([['Name','Phone','Status','Score','Signals','Finished']].concat(a.map(x=>[x.name,x.phone,x.status,x.score,x.signals.join('; '),x.finished?when(x.finished):''])))  ,'text/csv')}},'Download CSV');
  const prB=h('button',{class:'sm ghost',onclick:()=>{audit('print_report');printHtml(c.name+' results','<h2>'+D.esc(c.name)+'</h2><p>First-round screening results. Scores are a guide, not a decision.</p><table border=1 cellpadding=6>'+'<tr><th>Rank</th><th>Name</th><th>Phone</th><th>Score</th><th>Signals</th></tr>'+a.filter(x=>x.status==='done').map((x,i)=>`<tr><td>${i+1}</td><td>${D.esc(x.name)}</td><td>${D.esc(x.phone)}</td><td>${x.score}</td><td>${D.esc(x.signals.join('; '))}</td></tr>`).join('')+'</table>')}},'Print / PDF');
  return h('div',{class:'card'},h('h3',{},'Results ('+a.filter(x=>x.status==='done').length+' completed of '+a.length+')'),h('div',{class:'row'},csvB,prB),h('p',{class:'note'},'Signals are soft hints (for example copied-sounding answers, leaving the page, very fast answers). They are not proof of cheating. Please speak to the candidate before deciding.'),
   a.length?a.map(x=>h('details',{class:'pc'},h('summary',{},h('b',{},x.name),' ',x.phone?x.phone+' ':'',h('span',{class:'tag '+(x.status==='done'?'ok':'warn')},x.status),x.score!=null?h('span',{class:'tag'},'Score '+x.score):null,x.signals.map(s=>h('span',{class:'tag bad'},s))),
    h('div',{},Object.entries(x.modules).map(([k,v])=>h('div',{class:'note'},k+': score '+v.score+(v.wpm!=null?', '+v.wpm+' WPM, '+v.accuracy+'% accuracy':'')+(v.correct!=null?', '+v.correct+'/'+v.total+' correct':''))),
     x.voice.map((v,i)=>h('div',{style:'margin:8px 0'},h('div',{class:'note'},'Q'+(i+1)+': '+v.q+' (score '+v.score+')'),h('div',{},'"'+(v.text||'')+'"'),v.followup?h('div',{class:'note'},'Follow-up: '+v.followup):null,v.fu_text_answer?h('div',{},'"'+v.fu_text_answer+'"'):null,h('div',{class:'note'},[v.notes,v.late?'Answered late':''].filter(Boolean).join(' - ')))),
     view?null:h('button',{class:'sm',onclick:async()=>{await send('/api/hub/pipeline',{name:x.name,phone:x.phone,role_title:c.role_title,stage:'Screened',score:x.score,source:'screening'});alert('Added to Pipeline.')}},'Add to pipeline')))):h('p',{class:'note'},'No candidates yet.'))}
 }

// ================= recruiter: resume screener
function vScreen(r){const view=ME.org_role==='viewer';let rows=[];const roleSel=h('select',{onchange:()=>{const t=D.ROLES[roleSel.value];if(t){must.value=t.must.join(', ');nice.value=t.nice.join(', ');yrs.value=t.years}}},h('option',{value:''},'Start from a role template (optional)'),Object.entries(D.ROLES).map(([k,v])=>h('option',{value:k},v.label)));
 const must=h('input',{type:'text',placeholder:'Must-have skills, comma separated'}),nice=h('input',{type:'text',placeholder:'Nice-to-have skills'}),yrs=h('input',{type:'number',min:0,max:40,value:0}),loc=h('input',{type:'text',placeholder:'City (optional)'}),area=h('textarea',{rows:8,placeholder:'Paste resumes here. Separate each resume with a line containing only ---'}),file=h('input',{type:'file',accept:'.txt,text/plain',multiple:'multiple'});
 const out=h('div',{}),e=h('div',{class:'err'});
 file.onchange=async()=>{for(const f of file.files){area.value+=(area.value?'\n---\n':'')+await f.text()}file.value=''};
 async function go(){e.textContent='';const res=area.value.split(/^\s*-{3,}\s*$/m).map(t=>t.trim()).filter(t=>t.length>20).map(t=>({text:t}));if(!res.length){e.textContent='Paste at least one resume (plain text). Separate several with ---.';return}
  try{const d=await send('/api/hub/screen',{resumes:res,must:must.value.split(','),nice:nice.value.split(','),min_years:+yrs.value||0,location:loc.value});rows=d.results;draw()}catch(x){e.textContent=x.message}}
 function draw(){out.replaceChildren(h('div',{class:'row'},h('button',{class:'sm',onclick:()=>{audit('export_csv');dl('shortlist.csv',toCsv([['Rank','Name','Email','Phone','City','Years','Skills','Score','Flags']].concat(rows.map((x,i)=>[i+1,x.name,x.email,x.phone,x.city,x.years,(x.skills||[]).join('; '),x.score,x.flags.join('; ')]))),'text/csv')}},'Shortlist CSV'),
  h('button',{class:'sm ghost',onclick:()=>{audit('print_report');printHtml('Shortlist','<h2>Shortlist</h2><table border=1 cellpadding=6><tr><th>#</th><th>Name</th><th>Contact</th><th>Years</th><th>Score</th><th>Flags</th></tr>'+rows.map((x,i)=>`<tr><td>${i+1}</td><td>${D.esc(x.name)}</td><td>${D.esc(x.email+' '+x.phone)}</td><td>${x.years}</td><td>${x.score}</td><td>${D.esc(x.flags.join('; '))}</td></tr>`).join('')+'</table>')}},'Print / PDF')),
  h('div',{class:'tw'},h('table',{},h('tr',{},['#','Candidate','Years','Score','Notes',''].map(x=>h('th',{},x))),rows.map((x,i)=>h('tr',{},h('td',{},i+1),h('td',{},h('b',{},x.name||'(name not found)'),h('div',{class:'note'},[x.email,x.phone,x.city].filter(Boolean).join(' - '))),h('td',{},x.years),h('td',{},h('b',{},x.score)),
   h('td',{},x.duplicate_of!=null?h('span',{class:'tag warn'},'Duplicate'):null,x.knockout?h('span',{class:'tag bad'},'Missing a must-have'):h('span',{class:'tag ok'},'Meets must-haves'),x.flags.map(f=>h('div',{class:'note'},f))),
   h('td',{},view?null:h('button',{class:'sm',onclick:async ev=>{await send('/api/hub/pipeline',{name:x.name||'Candidate',phone:x.phone||'',email:x.email||'',stage:'Screened',score:x.score,source:'resume'});ev.target.textContent='Added';ev.target.disabled=true}},'+ Pipeline')))))))}
 r.append(...head('Resume Screener','Free and instant. It reads plain-text resumes, pulls out contact, skills and experience, and ranks them against your criteria with simple rules. It does not use AI, so unusual wording can be missed. Please check the top and bottom of the list yourself.'),
  h('div',{class:'card'},roleSel,lbl('Must-have skills',must),lbl('Nice-to-have skills',nice),lbl('Minimum years of experience',yrs),lbl('Location',loc),lbl('Resumes (plain text; PDF: open and copy the text)',area),h('div',{},file),e,h('button',{onclick:go},'Screen resumes')),out)}

// ================= recruiter: pipeline
async function vPipe(r){const view=ME.org_role==='viewer';const d=await get('/api/hub/pipeline');let items=d.items;const board=h('div',{class:'cols'});
 function draw(){board.replaceChildren(...d.stages.map(s=>h('div',{class:'col'},h('b',{},s+' ('+items.filter(i=>i.stage===s).length+')'),...items.filter(i=>i.stage===s).map(i=>h('div',{class:'pc'},h('b',{},i.name),i.score!=null?h('span',{class:'tag'},'Score '+Math.round(i.score)):null,h('div',{class:'note'},[i.role_title,i.phone,i.email].filter(Boolean).join(' - ')),
   h('div',{class:'note'},i.notes||''),view?null:h('div',{},h('select',{onchange:async ev=>{await send('/api/hub/pipeline/'+i.id,{stage:ev.target.value},'PATCH');i.stage=ev.target.value;draw()}},d.stages.map(x=>h('option',{value:x,selected:x===i.stage?'selected':null},x))),
    h('div',{class:'row'},h('button',{class:'sm ghost',onclick:async()=>{const n=prompt('Note for '+i.name,i.notes||'');if(n==null)return;await send('/api/hub/pipeline/'+i.id,{notes:n},'PATCH');i.notes=n;draw()}},'Note'),i.phone?h('a',{class:'sm',href:wa(i.phone,''),target:'_blank',rel:'noopener'},'WhatsApp'):null,h('button',{class:'sm ghost',onclick:async()=>{if(!confirm('Remove '+i.name+'?'))return;await send('/api/hub/pipeline/'+i.id,{},'DELETE');items=items.filter(x=>x!==i);draw()}},'Remove'))))))))}
 const nm=h('input',{type:'text',placeholder:'Name',maxlength:80}),ph=h('input',{type:'tel',placeholder:'Phone'}),rl=h('input',{type:'text',placeholder:'Role'}),er=h('div',{class:'err'});
 r.append(...head('Pipeline','Move candidates from New to Offer. Everyone in your company sees the same board.'),view?null:h('div',{class:'card'},h('h3',{},'Add candidate'),nm,ph,rl,er,h('button',{onclick:async()=>{if(!nm.value.trim()){er.textContent='Enter a name.';return}try{await send('/api/hub/pipeline',{name:nm.value,phone:ph.value,role_title:rl.value});vRender('h-pipe')}catch(e){er.textContent=e.message}}},'Add')),
  h('div',{class:'row'},h('button',{class:'sm ghost',onclick:()=>dl('pipeline.csv',toCsv([['Name','Phone','Email','Role','Stage','Score','Notes']].concat(items.map(i=>[i.name,i.phone,i.email,i.role_title,i.stage,i.score,i.notes]))),'text/csv')},'Download CSV')),board);draw()}

// ================= recruiter: hiring kit
function vKit(r){const co=ME.company||'';
 const roleSel=h('select',{},Object.entries(D.ROLES).map(([k,v])=>h('option',{value:k},v.label)));const out=h('div',{});
 const sec=(t,...k)=>h('div',{class:'card'},h('h3',{},t),...k);
 const roleCard=sec('Role template',roleSel,h('div',{class:'row'},h('button',{class:'sm',onclick:()=>show(()=>{const t=D.ROLES[roleSel.value];return h('div',{},h('h3',{},t.label),h('pre',{},t.jd),h('p',{class:'note'},'Add salary, location and shift details yourself.'),h('button',{class:'sm',onclick:ev=>copy(t.jd,ev.target)},'Copy job description'))})},'Job description'),
  h('button',{class:'sm',onclick:()=>show(()=>{const t=D.ROLES[roleSel.value];const html=D.scorecard(t.label,t.criteria);return h('div',{},h('div',{class:'tw',innerHTML:null}),(()=>{const d=h('div',{class:'tw'});d.innerHTML=html;return d})(),h('button',{class:'sm',onclick:()=>printHtml('Scorecard',html)},'Print scorecard'))})},'Scorecard sheet'),
  h('button',{class:'sm',onclick:()=>show(()=>{const t=D.ROLES[roleSel.value];const rows=[['Skill','Score 1-5','Evidence']].concat(t.criteria.map(c=>[c,'','']));return h('div',{},h('p',{},'Rubric: 1 = cannot do it, 3 = can do it with some help, 5 = does it well without help. Use the same rubric for every candidate.'),h('button',{class:'sm',onclick:()=>dl('scorecard.csv',toCsv(rows),'text/csv')},'Download scorecard CSV'))})},'Rubric (CSV)')));
 function show(fn){out.replaceChildren(fn());out.scrollIntoView({behavior:'smooth'})}
 // message templates
 const mt=h('select',{},[['invite','Invite to screening'],['interview','Interview invite'],['reminder','Interview reminder'],['reject','Polite rejection'],['offer','Selected / offer']].map(([a,b])=>h('option',{value:a},b))),ml=h('select',{},[['hinglish','Hinglish'],['en','English'],['ar','Arabic']].map(([a,b])=>h('option',{value:a},b)));
 const v={name:h('input',{type:'text',placeholder:'Candidate name'}),phone:h('input',{type:'tel',placeholder:'Candidate phone'}),role:h('input',{type:'text',placeholder:'Role'}),date:h('input',{type:'text',placeholder:'Date, e.g. 12 Oct'}),time:h('input',{type:'text',placeholder:'Time, e.g. 11 AM'}),place:h('input',{type:'text',placeholder:'Place / address'}),link:h('input',{type:'text',placeholder:'Screening link (optional)'})};const pv=h('pre',{});
 const upd=()=>{pv.textContent=D.fill(D.MSG[mt.value][ml.value],{company:co||'[Company]',min:12,...Object.fromEntries(Object.entries(v).map(([k,e])=>[k,e.value]))});wl.href=wa(v.phone.value,pv.textContent)};const wl=h('a',{class:'sm',target:'_blank',rel:'noopener'},'Open in WhatsApp');
 [mt,ml,...Object.values(v)].forEach(e=>e.addEventListener('input',upd));
 const msgCard=sec('Message templates (WhatsApp)',mt,ml,...Object.values(v),pv,h('div',{class:'row'},h('button',{class:'sm',onclick:ev=>copy(pv.textContent,ev.target)},'Copy'),wl));upd();
 // scheduler
 const s={t:h('input',{type:'text',placeholder:'Interview with candidate name'}),at:h('input',{type:'datetime-local'}),m:h('select',{},[15,20,30,45,60].map(x=>h('option',{value:x,selected:x===30?'selected':null},x+' minutes'))),p:h('input',{type:'text',placeholder:'Place or video link'})};const se=h('div',{class:'err'});
 const schedCard=sec('Interview scheduler',h('p',{class:'note'},'Makes a calendar file (.ics). Open it to add the slot to Google, Outlook or Apple calendar, or attach it to a message. Times use this device clock.'),s.t,s.at,s.m,s.p,se,h('button',{class:'sm',onclick:()=>{se.textContent='';if(!s.at.value||!s.t.value){se.textContent='Enter a title and a date and time.';return}dl('interview.ics',D.ics({title:s.t.value,start:s.at.value,mins:+s.m.value,place:s.p.value,desc:'Scheduled with MockRep'}),'text/calendar')}},'Download .ics'));
 // letters
 const L={name:h('input',{type:'text',placeholder:'Candidate name'}),role:h('input',{type:'text',placeholder:'Job title'}),company:h('input',{type:'text',value:co,placeholder:'Company'}),date:h('input',{type:'text',placeholder:'Letter date'}),joining:h('input',{type:'text',placeholder:'Joining date'}),place:h('input',{type:'text',placeholder:'Work location'}),accept:h('input',{type:'text',placeholder:'Accept by (date)'}),signer:h('input',{type:'text',placeholder:'Signer name and title'})};
 const val=()=>Object.fromEntries(Object.entries(L).map(([k,e])=>[k,e.value.trim()]));
 const letters=sec('Offer letter and reference check',h('p',{class:'note'},'Templates only. We add no salary numbers. Please have them checked against your local labour rules.'),...Object.values(L),h('div',{class:'row'},
  h('button',{class:'sm',onclick:()=>show(()=>{const t=D.offerLetter(val());return h('div',{},h('pre',{},t),h('button',{class:'sm',onclick:ev=>copy(t,ev.target)},'Copy'),h('button',{class:'sm ghost',onclick:()=>printHtml('Offer letter','<pre style="white-space:pre-wrap;font:inherit">'+D.esc(t)+'</pre>')},'Print / PDF'))})},'Offer letter'),
  h('button',{class:'sm',onclick:()=>show(()=>{const t=D.refCheck(val());return h('div',{},h('pre',{},t),h('button',{class:'sm',onclick:ev=>copy(t,ev.target)},'Copy'),h('button',{class:'sm ghost',onclick:()=>printHtml('Reference check','<pre style="white-space:pre-wrap;font:inherit">'+D.esc(t)+'</pre>')},'Print / PDF'))})},'Reference check form')));
 r.append(...head('Hiring Kit','Ready-made templates. Free, no AI.'),roleCard,msgCard,schedCard,letters,out)}

// ================= recruiter: company and team
async function vTeam(r){const o=await get('/api/hub/org');const own=o.org_role==='owner';const er=h('div',{class:'err'});
 const nm=h('input',{type:'text',value:o.name,maxlength:80,placeholder:'Company name'}),col=h('input',{type:'text',value:o.brand_color,maxlength:7,placeholder:'#5b8cff'}),lg=h('input',{type:'file',accept:'image/png,image/jpeg,image/webp'});let logo=o.logo||'';
 lg.onchange=()=>{const f=lg.files[0];if(!f)return;const im=new Image();im.onload=()=>{const s=Math.min(1,160/Math.max(im.width,im.height)),c=document.createElement('canvas');c.width=Math.round(im.width*s);c.height=Math.round(im.height*s);c.getContext('2d').drawImage(im,0,0,c.width,c.height);logo=c.toDataURL('image/png');prev.src=logo};im.src=URL.createObjectURL(f)};
 const prev=h('img',{src:logo||null,style:'max-height:50px;display:block;margin:6px 0',alt:''});
 const apiOut=h('div',{});
 const aud=h('div',{});
 r.append(...head('Company & Team'),h('div',{class:'card'},h('h3',{},'Your company page'),h('p',{class:'note'},'Your name, colour and logo appear on the screening page candidates see.'),lbl('Company name',nm),lbl('Brand colour (hex)',col),lbl('Logo (small image)',lg),prev,er,own?h('button',{onclick:async()=>{er.textContent='';try{await send('/api/hub/org',{name:nm.value,brand_color:col.value,logo},'PATCH');ME.company=nm.value;er.textContent='Saved.'}catch(e){er.textContent=e.message}}},'Save'):h('p',{class:'note'},'Only the owner can change this.')),
  h('div',{class:'card'},h('h3',{},'Team'),h('div',{class:'tw'},h('table',{},o.team.map(t=>h('tr',{},h('td',{},t.email),h('td',{},t.org_role),h('td',{},own&&t.org_role!=='owner'?h('button',{class:'sm ghost',onclick:async()=>{if(confirm('Remove '+t.email+' from your company? They keep a candidate account.')){await send('/api/hub/org/team/'+t.id,{},'DELETE');vRender('h-team')}}},'Remove'):null))))),
   own?h('div',{},h('p',{class:'note'},'Share a code so a colleague can sign up as a recruiter and join your company. Recruiter code gives full access, viewer code is read-only.'),h('p',{},'Recruiter code: ',h('b',{},o.invite_code)),h('p',{},'Viewer code: ',h('b',{},o.viewer_code)),h('button',{class:'sm ghost',onclick:async()=>{if(confirm('Old codes will stop working. Continue?')){await send('/api/hub/org/rotate-codes');vRender('h-team')}}},'Make new codes')):null),
  own?h('div',{class:'card'},h('h3',{},'API access'),h('p',{class:'note'},'Download your results into other systems. Send the key in the X-API-Key header to /api/v1/results (add ?format=csv for CSV). A new key replaces the old one and is shown once.'),apiOut,h('button',{class:'sm',onclick:async()=>{const k=await send('/api/hub/org/apikey');apiOut.replaceChildren(h('pre',{},k.api_key),h('button',{class:'sm',onclick:ev=>copy(k.api_key,ev.target)},'Copy key'))}},o.has_api_key?'Replace API key':'Create API key')):null,
  h('div',{class:'card'},h('h3',{},'Activity log'),h('button',{class:'sm ghost',onclick:async()=>{const a=await get('/api/hub/audit');aud.replaceChildren(h('div',{class:'tw'},h('table',{},a.items.map(i=>h('tr',{},h('td',{},when(i.ts)),h('td',{},i.user_email),h('td',{},i.action),h('td',{},i.target))))))}},'Show recent activity'),aud))}

// ================= candidate: skill tests (practice)
function vSkills(r){const out=h('div',{});const cards=[['typing','Typing test','60 seconds. See your speed and accuracy.'],['reading','Reading aloud','Read a passage aloud. Checks how much of it was recognised.'],['quiz','English and customer quiz','10 questions with answers shown after.'],['aptitude','Aptitude','12 questions: numbers, logic, data checking.']];
 r.append(...head('Skill Tests','Free practice. Nothing is saved. These are the same kinds of tests recruiters use.'),...cards.map(([k,t,d])=>h('div',{class:'card'},h('h3',{},t),h('p',{class:'note'},d),h('button',{class:'sm',onclick:()=>practice(k)},'Start'))),out);
 async function practice(k){const g=await get('/api/practice/'+k);const seed=g.seed;const SR=window.SpeechRecognition||window.webkitSpeechRecognition;const er=h('div',{class:'err'});
  if(k==='typing'){let t0=null,iv=null,done=false;const ta=h('textarea',{rows:5,autocomplete:'off',spellcheck:'false'}),tm=h('div',{class:'note'},'Timer starts when you type');['paste','drop','cut'].forEach(e=>ta.addEventListener(e,x=>x.preventDefault()));
   const fin=async()=>{if(done)return;done=true;clearInterval(iv);const secs=t0?(Date.now()-t0)/1000:60;const res=await send('/api/practice/typing',{seed,typed:ta.value,secs});out.replaceChildren(h('div',{class:'card'},h('h3',{},'Result'),h('p',{},res.wpm+' words per minute, '+res.accuracy+'% accuracy. Score '+res.score+'/100.'),h('button',{class:'sm',onclick:()=>practice(k)},'Try again')))};
   ta.addEventListener('input',()=>{if(!t0){t0=Date.now();iv=setInterval(()=>{const l=60-Math.floor((Date.now()-t0)/1000);tm.textContent=l+' seconds left';if(l<=0)fin()},1000)}});
   out.replaceChildren(h('div',{class:'card'},h('div',{class:'pass'},g.text),ta,tm,h('button',{class:'sm',onclick:()=>ta.value.trim()&&fin()},'Finish')))}
  else if(k==='reading'){const live=h('div',{class:'pc'},'Tap the button and read aloud');let rec=null;
   const b=h('button',{class:'sm',onclick:()=>{if(!SR){er.textContent='Speech recognition is not available in this browser. Use Chrome on Android or a computer.';return}if(rec){rec.stop();return}rec=new SR();rec.lang='en-IN';rec.continuous=true;rec.interimResults=true;let tx='';b.textContent='Stop';
    rec.onresult=e=>{tx='';for(let i=0;i<e.results.length;i++)tx+=e.results[i][0].transcript+' ';live.textContent=tx};rec.onend=async()=>{rec=null;b.textContent='Start';const res=await send('/api/practice/reading',{seed,said:tx});out.replaceChildren(h('div',{class:'card'},h('h3',{},'Result'),h('p',{},'About '+res.match+'% of the passage was recognised. Score '+res.score+'/100.'),h('p',{class:'note'},'Speech recognition can miss words because of accent, noise or the browser. Use this as a rough guide.'),h('button',{class:'sm',onclick:()=>practice(k)},'Try again')))};rec.start()}},'Start');
   out.replaceChildren(h('div',{class:'card'},h('div',{class:'pass'},g.text),live,er,b))}
  else{const ans=g.items.map(()=>-1);out.replaceChildren(h('div',{class:'card'},g.items.map((it,qi)=>h('div',{style:'margin:12px 0'},h('b',{},(qi+1)+'. '+it.q),it.o.map((o,oi)=>h('label',{class:'consent'},h('input',{type:'radio',name:'q'+qi,onchange:()=>ans[qi]=oi}),h('span',{},o))))),h('button',{class:'sm',onclick:async()=>{const res=await send('/api/practice/'+k,{seed,answers:ans});out.replaceChildren(h('div',{class:'card'},h('h3',{},res.correct+' of '+res.total+' correct'),g.items.map((it,qi)=>h('div',{class:'pc'},h('b',{},it.q),h('div',{},(ans[qi]===res.correct_answers[qi]?'Correct: ':'Right answer: ')+it.o[res.correct_answers[qi]]))),h('button',{class:'sm',onclick:()=>practice(k)},'Try again')))}},'Submit')))}
  out.scrollIntoView({behavior:'smooth'})}}

// ================= wiring
const RENDER={'h-dash':vDash,'h-camp':vCamp,'h-screen':vScreen,'h-pipe':vPipe,'h-kit':vKit,'h-team':vTeam,'h-skills':vSkills};
let busy=0;
async function vRender(v){const r=root();if(!r||!RENDER[v])return;const tok=++busy;
 const recView=v!=='h-skills';if(!ME&&!(v==='h-skills')){return need('recruiter')}
 if(recView&&(!ME||ME.role!=='recruiter'))return need('recruiter');if(!recView&&ME&&ME.role==='recruiter')return need('candidate');
 const wrap=h('div',{});r.replaceChildren(h('p',{class:'note'},'Loading...'));try{await RENDER[v](wrap);if(tok===busy)r.replaceChildren(wrap)}catch(e){if(tok===busy)r.replaceChildren(h('div',{class:'card'},h('p',{class:'err'},e.message||'Something went wrong.'),h('button',{class:'sm',onclick:()=>vRender(v)},'Try again')))}}
function menu(){const d=$('drawer');if(!d)return;d.querySelectorAll('[data-hub]').forEach(x=>x.remove());const rec=ME&&ME.role==='recruiter';
 const anchor=d.querySelector('button[data-v=home]');const btn=(v,i,t,s)=>{const b=h('button',{'data-v':v,'data-hub':'1'},h('i',{},i),t,s?h('small',{},s):null);return b};
 const items=rec?[h('div',{class:'dgroup','data-hub':'1'},'Hiring'),btn('h-dash','\u{1F4CA}','Dashboard'),btn('h-camp','\u{1F4DE}','Screening Campaigns','Voice links, tests, results'),btn('h-screen','\u{1F4C4}','Resume Screener','Rank resumes free'),btn('h-pipe','\u{1F5C2}','Pipeline','Candidate board'),btn('h-kit','\u{1F9F0}','Hiring Kit','Templates, scorecards, scheduler'),btn('h-team','\u{1F3E2}','Company & Team','Brand, team, API')]:[h('div',{class:'dgroup','data-hub':'1'},'Skill tests'),btn('h-skills','\u{1F3AF}','Skill Tests','Typing, reading, quiz, aptitude')];
 let ref=anchor;for(const it of items){ref.after(it);ref=it}
 const rb=d.querySelector('button[data-v=recruiter]');if(rb&&rec){rb.lastChild.textContent='AI Recruiter Mode';ref.after(rb)}
 // recruiter accounts see recruiter tools only; candidates and guests never see recruiter-only items
 const CAND=['interview','prep','bank','review','builder','match','star','brief','nego','code'];
 d.querySelectorAll('.dgroup').forEach(g=>{if(['Practice','Your resume','More tools'].includes(g.textContent.trim()))g.classList.toggle('hide',!!rec)});
 d.querySelectorAll('button[data-v]').forEach(c=>{if(CAND.includes(c.dataset.v))c.classList.toggle('hide',!!rec);if(c.dataset.v==='recruiter')c.classList.toggle('hide',!rec)});
 // the recruiter group heading stays visible
}
function onView(){const v=document.body.dataset.view;if(v&&v.startsWith('h-')){$('viewTitle').textContent=VIEWS[v]||'';vRender(v)}}
function init(){M=window.__mr;if(!M)return;const st=h('style',{},STYLE);document.head.append(st);const hr=h('div',{id:'hubRoot'});const lay=document.querySelector('.layout');lay.before(hr);
 Object.assign(M.TITLES,VIEWS);
 // lite mode switch in the menu
 const lite=h('button',{id:'dLite','data-act':'lite',style:'display:grid'},h('i',{},'\u26A1'),'Low-data mode: '+(document.body.classList.contains('lite')?'on':'off'));
 try{if(localStorage.getItem('mr_lite')==='1')document.body.classList.add('lite')}catch(e){}
 lite.firstChild.nextSibling;lite.lastChild.textContent='Low-data mode: '+(document.body.classList.contains('lite')?'on':'off');
 lite.onclick=()=>{const on=document.body.classList.toggle('lite');try{localStorage.setItem('mr_lite',on?'1':'0')}catch(e){}lite.lastChild.textContent='Low-data mode: '+(on?'on':'off')};
 const dl2=$('dLogin');if(dl2)dl2.before(lite);
 new MutationObserver(onView).observe(document.body,{attributes:true,attributeFilter:['data-view']});
 const sync=async()=>{try{const j=await get('/api/auth/me');ME=j.user;if(ME&&ME.role==='recruiter'){try{const o=await get('/api/hub/org');ME.company=o.name}catch(e){}}}catch(e){ME=null}menu();const v=document.body.dataset.view;if(v&&v.startsWith('h-'))vRender(v);
  if(ME&&ME.role==='recruiter'&&['prep','interview','review','match','nego','star','brief','bank','code','builder'].includes(v))M.setView('h-dash')};
 window.addEventListener('mr:me',sync);sync().then(()=>{const hv=(location.hash||'').slice(1);if(RENDER[hv])M.setView(hv,false)})}
document.addEventListener('change',e=>{if(e.target.name==='acRole'){const w=$('acInvWrap');if(w)w.classList.toggle('hide',e.target.value!=='recruiter')}});
if(window.__mr)init();else window.addEventListener('mr:ready',init);
})();
