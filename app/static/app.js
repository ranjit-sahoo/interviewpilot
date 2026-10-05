if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const ul=a=>(a&&a.length)?'<ul>'+a.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>':'';
let fuOn=true,country=null,countryTouched=false,detKey='',sid=null,nsid=null,voice=false;
const wakeT=setTimeout(()=>$('wake').classList.remove('hide'),3000);
fetch('/health').then(r=>r.json()).then(h=>{if(h.mock_mode)$('mock').classList.remove('hide')}).catch(()=>{}).finally(()=>{clearTimeout(wakeT);$('wake').classList.add('hide')});

async function api(url,opts){
  let r;try{r=await fetch(url,opts)}catch(e){throw new Error('Network problem. Check your connection and try again.')}
  const j=await r.json().catch(()=>({}));
  if(!r.ok)throw new Error(typeof j.detail==='string'?j.detail:(r.status===422?'Please check your input.':'Request failed'));
  return j;
}
const post=(url,body)=>api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
async function busy(btn,label,fn){const t=btn.textContent;btn.disabled=true;btn.textContent=label;try{await fn()}finally{btn.disabled=false;btn.textContent=t}}
function role(){const v=$('role').value.trim();if(!v)throw new Error('Enter your target role.');return v}
function resumeText(){const v=$('resume').value.trim();if(v.length<30)throw new Error('Paste your resume text or upload a PDF/TXT file.');return v}
function profErr(m){$('profErr').textContent=m||''}

// ---- tabs
$('tabs').onclick=e=>{const t=e.target.dataset&&e.target.dataset.t;if(!t)return;
  document.querySelectorAll('#tabs button').forEach(b=>b.classList.toggle('on',b.dataset.t===t));
  ['prep','review','match','interview','star','brief','nego','bank','code','builder','recruiter','history'].forEach(x=>$('t-'+x).classList.toggle('hide',x!==t));if(t==='code')cpLoad();if(t==='history'&&typeof histLoad==='function')histLoad();profErr('')};

// ---- question bank
let bankAll=[],bankFilter='all';
fetch('/api/companies').then(r=>r.json()).then(j=>{$('bankCos').innerHTML=j.companies.map(r=>`<option value="${esc(r)}">`).join('')}).catch(()=>{});
fetch('/api/bank/roles').then(r=>r.json()).then(j=>{$('bankRoles').innerHTML=j.roles.map(r=>`<option value="${esc(r)}">`).join('')}).catch(()=>{});
function bankCard(q){return `<div class="cand"><span class="pill">${esc(q.type)}</span><span class="pill">${esc(q.level)}</span><p><b>${esc(q.question)}</b></p>${q.hint?`<details><summary>How to answer</summary><p>${esc(q.hint)}</p></details>`:''}</div>`}
function bankRender(){
  const shown=bankAll.filter(q=>bankFilter==='all'||q.type===bankFilter);
  $('bankOut').innerHTML=shown.length?shown.map(bankCard).join(''):'<p class="note">No questions in this filter.</p>';
  document.querySelectorAll('#bankFilter button').forEach(b=>b.classList.toggle('on',b.dataset.f===bankFilter));
}
$('bankFilter').onclick=e=>{if(e.target.dataset.f){bankFilter=e.target.dataset.f;bankRender()}};
async function bankGo(ai){
  $('bankErr').textContent='';
  try{
    const r=($('bankRole').value||$('role').value).trim(),co=$('bankCo').value.trim();
    const d=await post('/api/bank',{role:r,company:co,country:country||'US',ai:!!ai});
    let html='';
    if(d.profile){const p=d.profile;html+=`<div class="cand"><b>${esc(p.name)}</b> <span class="pill">${esc(p.country)}</span><span class="pill">${esc(p.kind)}</span><p>Typical rounds: ${esc(p.rounds)}</p><p>Focus:</p>${ul(p.focus)}<p>Tip: ${esc(p.tip)}</p><div class="note">${esc(p.note)}</div>${d.company?'':'<button class="ghost" id="bankAi">Generate company-style questions (AI)</button>'}</div>`}
    if(d.company_error)html+=`<p class="note">${esc(d.company_error)}</p>`;
    if(d.company)html+=`<h3>${esc(d.company.company)} style</h3><p class="note">${esc(d.company.note)}</p>`+d.company.questions.map(bankCard).join('')+`<h3>${esc(d.role)} questions</h3>`;
    $('bankCoOut').innerHTML=html;
    bankAll=d.questions;bankFilter='all';
    $('bankFilter').innerHTML=['all','technical','behavioral','scenario'].map(f=>`<button data-f="${f}">${f}</button>`).join('');
    bankRender();
    const ba=$('bankAi');if(ba)ba.onclick=()=>busy(ba,'Generating...',()=>bankGo(true));
  }catch(e){$('bankErr').textContent=e.message}
}
$('btnBank').onclick=()=>busy($('btnBank'),'Loading...',()=>bankGo(false));

// ---- coding practice
let cpId=null,cpLevel=0,cpDrafts={};
async function cpLoad(){
  if($('cpList').dataset.ok)return;
  try{const j=await api('/api/coding/problems');$('cpList').dataset.ok=1;
    $('cpList').innerHTML='<p class="note">Pick a problem, write your solution, and get an AI review of correctness, edge cases and complexity.</p>'+
      j.problems.map(p=>`<div class="cand"><span class="pill">${esc(p.level)}</span><span class="pill">${esc(p.topic)}</span><p><b>${esc(p.title)}</b></p><button class="alt" data-p="${esc(p.id)}">Practice</button></div>`).join('')}
  catch(e){$('cpList').innerHTML=`<div class="err">${esc(e.message)}</div>`}
}
$('cpList').onclick=async e=>{const id=e.target.dataset&&e.target.dataset.p;if(!id)return;
  try{const p=await api('/api/coding/problems/'+encodeURIComponent(id));cpId=id;cpLevel=0;
    $('cpTitle').textContent=p.title;$('cpLevel').textContent=p.level;$('cpTopic').textContent=p.topic;$('cpStmt').textContent=p.statement;
    $('cpLang').innerHTML=p.languages.map(l=>`<option>${l}</option>`).join('');$('cpLang').dataset.st=JSON.stringify(p.starters);
    const d=cpDrafts[id];$('cpCode').value=d&&d.code||p.starters[p.languages[0]];if(d&&d.lang)$('cpLang').value=d.lang;
    $('cpHints').innerHTML='';$('cpOut').innerHTML='';$('cpErr').textContent='';
    $('cpList').classList.add('hide');$('cpWork').classList.remove('hide')}
  catch(err){alert(err.message)}};
$('cpBack').onclick=()=>{cpDrafts[cpId]={code:$('cpCode').value,lang:$('cpLang').value};$('cpWork').classList.add('hide');$('cpList').classList.remove('hide')};
$('cpLang').onchange=()=>{const st=JSON.parse($('cpLang').dataset.st||'{}'),cur=$('cpCode').value.trim();
  if(!cur||Object.values(st).some(v=>v.trim()===cur))$('cpCode').value=st[$('cpLang').value]||''};
$('cpCode').onkeydown=e=>{if(e.key==='Tab'&&!e.shiftKey){e.preventDefault();const t=e.target,a=t.selectionStart;t.setRangeText('    ',a,t.selectionEnd,'end')}};
$('cpHint').onclick=()=>busy($('cpHint'),'Thinking...',async()=>{
  $('cpErr').textContent='';cpLevel=Math.min(3,cpLevel+1);
  try{const h=await post('/api/coding/problems/'+cpId+'/hint',{level:cpLevel,code:$('cpCode').value});
    $('cpHints').insertAdjacentHTML('beforeend',`<div class="w g"><b>Hint ${h.level}</b><br>${esc(h.hint)}</div>`)}
  catch(e){$('cpErr').textContent=e.message}});
$('cpEval').onclick=()=>busy($('cpEval'),'Reviewing...',async()=>{
  $('cpErr').textContent='';$('cpOut').innerHTML='';
  try{const r=await post('/api/coding/problems/'+cpId+'/evaluate',{language:$('cpLang').value,code:$('cpCode').value});
    const vt={correct:'Looks correct',partially_correct:'Partly correct',incorrect:'Needs work'}[r.verdict];
    $('cpOut').innerHTML=`<div class="score">${esc(r.score)}/10</div><h3>${esc(vt)}</h3><p>${esc(r.summary)}</p>`+
      (r.bugs.length?'<h4>Bugs and missed cases</h4>'+ul(r.bugs):'')+
      `<h4>Complexity</h4><p>Time ${esc(r.complexity.time)}, space ${esc(r.complexity.space)}. ${r.complexity.optimal?'Optimal.':'Can be improved.'} ${esc(r.complexity.note)}</p>`+
      (r.better_approach?`<h4>Better approach</h4><p>${esc(r.better_approach)}</p>`:'')+
      (r.style.length?'<h4>Style</h4>'+ul(r.style):'')+(r.next_step?`<div class="w g"><b>Next step</b><br>${esc(r.next_step)}</div>`:'')+'<p><button class="ghost" data-save="code">Save this review to my history</button></p>';lastReview={title:$('cpTitle').textContent,code:$('cpCode').value,language:$('cpLang').value,result:r}}
  catch(e){$('cpErr').textContent=e.message}});

// ---- resume builder
const RB_KEY='ip_resume_v1',RB_EMPTY=()=>({name:'',title:'',email:'',phone:'',location:'',links:[],summary:'',experience:[],education:[],skills:[],projects:[]});
let RB=RB_EMPTY(),rbT=null;
try{const d=JSON.parse(localStorage.getItem(RB_KEY)||'null');if(d&&typeof d==='object')RB=Object.assign(RB_EMPTY(),d)}catch(e){}
const csv=v=>String(v||'').split(',').map(x=>x.trim()).filter(Boolean);
function rbSave(){clearTimeout(rbT);rbT=setTimeout(()=>{try{localStorage.setItem(RB_KEY,JSON.stringify(RB))}catch(e){}},400)}
function rbPrevRender(){
  const r=RB,h=[];const contact=[r.email,r.phone,r.location,...r.links].filter(Boolean).map(esc).join(' &middot; ');
  h.push(`<div class="hd"><h1>${esc(r.name)||'Your Name'}</h1>${r.title?`<div>${esc(r.title)}</div>`:''}<div class="m">${contact}</div></div>`);
  if(r.summary)h.push(`<h2>Summary</h2><div>${esc(r.summary)}</div>`);
  if(r.experience.length)h.push('<h2>Experience</h2>'+r.experience.map(e=>`<div class="r"><span>${esc(e.role)}${e.company?', '+esc(e.company):''}</span><span class="m">${esc(e.dates)}</span></div>${ul(e.bullets)}`).join(''));
  if(r.projects.length)h.push('<h2>Projects</h2>'+r.projects.map(p=>`<div><b>${esc(p.name)}</b> ${esc(p.details)}</div>`).join(''));
  if(r.education.length)h.push('<h2>Education</h2>'+r.education.map(e=>`<div class="r"><span>${esc(e.degree)}${e.school?', '+esc(e.school):''}</span><span class="m">${esc(e.dates)}</span></div>`).join(''));
  if(r.skills.length)h.push(`<h2>Skills</h2><div>${r.skills.map(esc).join(', ')}</div>`);
  $('rbPrev').innerHTML=h.join('');rbSave();
}
function rbInp(cls,idx,key,label,val,area){return `<label>${label}</label>${area?`<textarea class="${cls}" data-i="${idx}" data-k="${key}" style="min-height:80px">${esc(val)}</textarea>`:`<input class="${cls}" data-i="${idx}" data-k="${key}" value="${esc(val)}" maxlength="200">`}`}
function rbFormRender(){
  for(const k of ['name','title','email','phone','location','summary'])$('rb_'+k).value=RB[k]||'';
  $('rb_links').value=RB.links.join(', ');$('rb_skills').value=RB.skills.join(', ');
  $('rbExp').innerHTML=RB.experience.map((e,i)=>`<div class="rbe">${rbInp('rx',i,'role','Role',e.role)}${rbInp('rx',i,'company','Company',e.company)}${rbInp('rx',i,'dates','Dates',e.dates)}${rbInp('rx',i,'bullets','Bullets (one per line)',(e.bullets||[]).join('\n'),true)}<button class="ghost" data-pol="${i}">Improve bullets with AI</button><button class="ghost" data-del="rx${i}">Remove</button></div>`).join('');
  $('rbEdu').innerHTML=RB.education.map((e,i)=>`<div class="rbe">${rbInp('ed',i,'degree','Degree',e.degree)}${rbInp('ed',i,'school','School',e.school)}${rbInp('ed',i,'dates','Dates',e.dates)}<button class="ghost" data-del="ed${i}">Remove</button></div>`).join('');
  $('rbPrj').innerHTML=RB.projects.map((e,i)=>`<div class="rbe">${rbInp('pj',i,'name','Name',e.name)}${rbInp('pj',i,'details','Details',e.details,true)}<button class="ghost" data-del="pj${i}">Remove</button></div>`).join('');
  rbPrevRender();
}
for(const k of ['name','title','email','phone','location','summary'])$('rb_'+k).oninput=e=>{RB[k]=e.target.value;rbPrevRender()};
$('rb_links').oninput=e=>{RB.links=csv(e.target.value);rbPrevRender()};$('rb_skills').oninput=e=>{RB.skills=csv(e.target.value);rbPrevRender()};
$('rbForm').addEventListener('input',e=>{const t=e.target,i=+t.dataset.i,k=t.dataset.k;if(isNaN(i)||!k)return;
  const arr=t.classList.contains('rx')?RB.experience:t.classList.contains('ed')?RB.education:t.classList.contains('pj')?RB.projects:null;if(!arr||!arr[i])return;
  arr[i][k]=k==='bullets'?t.value.split('\n').map(x=>x.trim()).filter(Boolean):t.value;rbPrevRender()});
$('rbAddExp').onclick=()=>{if(RB.experience.length<10){RB.experience.push({role:'',company:'',dates:'',bullets:[]});rbFormRender()}};
$('rbAddEdu').onclick=()=>{if(RB.education.length<6){RB.education.push({degree:'',school:'',dates:''});rbFormRender()}};
$('rbAddPrj').onclick=()=>{if(RB.projects.length<6){RB.projects.push({name:'',details:''});rbFormRender()}};
$('rbForm').onclick=async e=>{const d=e.target.dataset||{};
  if(d.del){const m=/^(rx|ed|pj)(\d+)$/.exec(d.del);if(m){({rx:RB.experience,ed:RB.education,pj:RB.projects})[m[1]].splice(+m[2],1);rbFormRender()}}
  if(d.pol!==undefined){const i=+d.pol,ex=RB.experience[i];$('rbErr').textContent='';
    await busy(e.target,'Improving...',async()=>{try{const r=await post('/api/builder/polish',{role:RB.title||$('role').value,bullets:ex.bullets,country:country||'US'});ex.bullets=r.bullets;rbFormRender()}catch(er){$('rbErr').textContent=er.message}})}};
$('rbSum').onclick=()=>busy($('rbSum'),'Writing...',async()=>{$('rbErr').textContent='';
  const facts=RB.experience.map(e=>`${e.role} at ${e.company}: ${(e.bullets||[]).join('; ')}`).join('\n')+'\nSkills: '+RB.skills.join(', ');
  try{const r=await post('/api/builder/summary',{role:RB.title||$('role').value,facts,country:country||'US'});RB.summary=r.summary;rbFormRender()}catch(e){$('rbErr').textContent=e.message}});
$('rbFill').onclick=()=>busy($('rbFill'),'Reading...',async()=>{$('rbErr').textContent='';
  try{if(RB.experience.length&&!confirm('Replace what you have in the builder with your pasted resume?'))return;
    RB=Object.assign(RB_EMPTY(),await post('/api/builder/parse',{resume:resumeText()}));rbFormRender()}catch(e){$('rbErr').textContent=e.message}});
$('rbTpl').onchange=e=>{$('rbPrev').className=e.target.value};
$('rbPrint').onclick=()=>{rbPrevRender();window.print()};
rbFormRender();

// ---- interview prep pack (hero)
const qCard=(q,i)=>`<div class="cand"><span class="pill">${esc(q.type)}</span><p><b>${i+1}. ${esc(q.question)}</b></p>${q.why_asked?`<div class="note">Why they ask: ${esc(q.why_asked)}</div>`:''}<details><summary>Model answer</summary><p>${esc(q.model_answer)}</p></details></div>`;
const cCard=q=>`<div class="cand"><span class="pill">${esc(q.level)}</span><span class="pill">${esc(q.language)}</span><p><b>${esc(q.title)}</b></p><p>${esc(q.problem)}</p><details><summary>Approach and solution</summary><p>${esc(q.approach)}</p><pre style="white-space:pre-wrap;background:var(--card2);padding:10px;border-radius:10px;overflow-x:auto">${esc(q.solution)}</pre><div class="note">${esc(q.complexity)}</div></details></div>`;
let lastPrep=null;
function showPrep(d,c,jdUsed,saved){
  let h=`<div class="note">Tailored for the ${esc(d.country)} market${jdUsed?' and your job description':''}.</div>`;
  if(d.focus.length)h+='<h3>Revise these first</h3>'+ul(d.focus);
  h+='<h3>Likely questions with model answers</h3>'+d.questions.map(qCard).join('');
  if(d.coding_profile)h+='<div id="prepCode"><h3>Coding questions for your profile</h3>'+(c?codeHtml(c):'<p class="note">Preparing coding questions...</p>')+'</div>';
  h+='<p><button class="ghost" data-pdf="prep">Download prep pack as PDF</button></p>';
  if(!saved)h+='<p><button class="ghost" id="saveBtn" data-save="prep">Save this pack to my history</button></p>';
  $('prepOut').innerHTML=h;wireCode();
}
const codeHtml=c=>c.coding_questions.length?c.coding_questions.map(cCard).join('')+'<p><button class="ghost" id="prepToCode">Practice coding with AI review</button></p>':'<p class="note">Could not prepare coding questions right now. Try the Coding Practice tab.</p>';
const wireCode=()=>{const b=$('prepToCode');if(b)b.onclick=()=>document.querySelector('[data-t=code]').click()};
$('btnPrep').onclick=()=>busy($('btnPrep'),'Building your pack (about 10 s)...',async()=>{
  $('prepErr').textContent='';$('prepOut').innerHTML='';lastPrep=null;
  try{const r=resumeText(),ro=role(),jd=$('jd').value.trim();
    if(!countryTouched&&!country)await detect();
    const d=await post('/api/prep',{resume:r,role:ro,jd,country:country||'US'});
    lastPrep={role:ro,jd:!!jd,pack:d,coding:null};showPrep(d,null,!!jd);
    if(d.coding_profile)post('/api/prep/coding',{resume:r,role:ro,jd,country:country||'US'}).then(c=>{lastPrep.coding=c;const el=$('prepCode');if(el){el.innerHTML='<h3>Coding questions for your profile</h3>'+codeHtml(c);wireCode()}})
      .catch(()=>{const el=$('prepCode');if(el)el.innerHTML='<h3>Coding questions</h3><p class="note">Could not load coding questions right now. Try the Coding Practice tab.</p>'});
  }catch(e){$('prepErr').textContent=e.message}});

// ---- accounts and history
let me=null,persistent=false,lastReview=null;
async function refreshMe(){try{const j=await api('/api/auth/me');me=j.user;persistent=j.persistent;if(me)endGuide()}catch(e){me=null}
  $('acctInfo').textContent=me?`Logged in as ${me.email}`:'Guest mode: everything works without an account. Log in only if you want to save your work.';
  $('acctOpen').classList.toggle('hide',!!me);$('acctHist').classList.toggle('hide',!me);$('acctOut').classList.toggle('hide',!me);$('tabHist').classList.toggle('hide',!me);
  if(me)$('acctForm').classList.add('hide')}
$('acctOpen').onclick=()=>$('acctForm').classList.toggle('hide');
async function authGo(path){$('acErr').textContent='';
  try{await post(path,{email:$('acEmail').value,password:$('acPw').value});$('acPw').value='';await refreshMe()}catch(e){$('acErr').textContent=e.message}}
$('acLogin').onclick=()=>busy($('acLogin'),'...',()=>authGo('/api/auth/login'));
$('acReg').onclick=()=>busy($('acReg'),'...',()=>authGo('/api/auth/register'));
$('acctOut').onclick=async()=>{await post('/api/auth/logout',{});await refreshMe();document.querySelector('[data-t=prep]').click()};
$('acctHist').onclick=()=>document.querySelector('[data-t=history]').click();
async function saveItem(kind,title,data,btn){
  if(!me){alert('Log in or create a free account (top of the page) to save.');return}
  await busy(btn,'Saving...',async()=>{try{await post('/api/history',{kind,title,data});btn.textContent='Saved';btn.disabled=true}catch(e){alert(e.message)}})}
document.body.addEventListener('click',e=>{const k=e.target.dataset&&e.target.dataset.save;if(!k)return;
  if(k==='prep'&&lastPrep)saveItem('prep',`Prep pack: ${lastPrep.role}`,lastPrep,e.target);
  if(k==='code'&&lastReview)saveItem('code_review',`Code review: ${lastReview.title}`,lastReview,e.target);
  if(k==='star'&&lastStar)saveItem('star',`STAR: ${(lastStar.question||'answer').slice(0,60)}`,lastStar,e.target);
  if(k==='brief'&&lastBrief)saveItem('brief',`Brief: ${lastBrief.company}`,lastBrief,e.target);
  if(k==='resume')saveItem('resume',`Resume: ${RB.name||RB.title||'draft'}`,RB,e.target)});
const fmt=t=>new Date(t*1000).toLocaleDateString();
async function histLoad(){
  $('histNote').textContent=persistent?'Your saved work. Only you can see it.':'Your saved work. Note: storage is temporary on this server right now and may reset.';
  $('histDel').classList.remove('hide');$('histView').innerHTML='';progLoad();
  try{const j=await api('/api/history');$('histList').innerHTML=j.items.length?j.items.map(i=>`<div class="cand"><span class="pill">${esc(i.kind)}</span><span class="pill">${fmt(i.created)}</span><p><b>${esc(i.title)}</b></p><button class="alt" data-open="${esc(i.id)}">Open</button><button class="ghost" data-rm="${esc(i.id)}">Delete</button></div>`).join(''):'<p class="note">Nothing saved yet. Use "Save" on a prep pack, code review or resume.</p>'}
  catch(e){$('histList').innerHTML=`<div class="err">${esc(e.message)}</div>`}}
$('histList').onclick=async e=>{const d=e.target.dataset||{};
  if(d.rm&&confirm('Delete this item?')){try{await api('/api/history/'+d.rm,{method:'DELETE'});histLoad()}catch(er){alert(er.message)}}
  if(d.open){try{const it=await api('/api/history/'+d.open),x=it.data;
    if(it.kind==='prep'){document.querySelector('[data-t=prep]').click();lastPrep=x;showPrep(x.pack,x.coding,x.jd,true)}
    else if(it.kind==='resume'){RB=Object.assign(RB_EMPTY(),x);rbFormRender();document.querySelector('[data-t=builder]').click()}
    else if(it.kind==='star'){$('histView').innerHTML='<div class="starOut">'+starHtml(x)+'</div>';starBind(x)}
    else if(it.kind==='brief'){$('histView').innerHTML=briefHtml(x)}
    else if(it.kind==='code_review'){$('histView').innerHTML=`<h3>${esc(it.title)}</h3><div class="score">${esc(x.result.score)}/10</div><p>${esc(x.result.summary)}</p>`+(x.result.bugs.length?ul(x.result.bugs):'')+`<pre style="white-space:pre-wrap;background:var(--card2);padding:10px;border-radius:10px">${esc(x.code)}</pre>`}
    else $('histView').innerHTML=`<pre style="white-space:pre-wrap">${esc(JSON.stringify(x,null,2))}</pre>`}catch(er){alert(er.message)}}};
$('histDel').onclick=async()=>{if(!confirm('Delete your account and everything saved? This cannot be undone.'))return;
  try{await api('/api/auth/account',{method:'DELETE'});await refreshMe();document.querySelector('[data-t=prep]').click()}catch(e){alert(e.message)}};
refreshMe();

// ---- country
function setCountry(c,touched){country=c;if(touched)countryTouched=true;document.querySelectorAll('#countries button').forEach(b=>b.classList.toggle('on',b.dataset.c===c))}
$('countries').onclick=e=>{if(e.target.dataset.c){setCountry(e.target.dataset.c,true);$('detNote').textContent='- you chose '+e.target.dataset.c}};
async function detect(){
  const r=$('resume').value.trim(),j=$('jd').value.trim();const key=r.slice(0,200)+'|'+j.slice(0,100)+r.length;
  if(r.length<30||countryTouched||key===detKey)return;detKey=key;
  $('detNote').textContent='- detecting...';
  try{const d=await post('/api/detect-country',{resume:r,jd:j});if(!countryTouched){setCountry(d.country,false);
    $('detNote').textContent=`- detected ${d.country} (${d.confidence} confidence). Tap to change`}}
  catch(e){$('detNote').textContent='- could not detect, please choose'}
}
$('resume').addEventListener('blur',detect);$('jd').addEventListener('blur',detect);
let detTimer=null;const detSoon=()=>{clearTimeout(detTimer);detTimer=setTimeout(()=>{if($('resume').value.trim().length>=80)detect()},1200)};
$('resume').addEventListener('input',detSoon);$('jd').addEventListener('input',detSoon);
fetch('/api/geo').then(r=>r.json()).then(g=>{if(g.country&&!country&&!countryTouched){setCountry(g.country,false);$('detNote').textContent=`- we guessed ${g.country} from your location. Paste your resume and we will confirm. Tap to change`}}).catch(()=>{});
async function ensureCountry(){await detect();if(!country)setCountry('US',false);return country}

$('file').onchange=async()=>{const f=$('file').files[0];if(!f)return;profErr('');
  const fd=new FormData();fd.append('file',f);
  try{const d=await api('/api/extract',{method:'POST',body:fd});$('resume').value=d.text;detect()}catch(e){profErr(e.message)}};

// ---- resume review
$('btnReview').onclick=()=>busy($('btnReview'),'Reviewing...',async()=>{profErr('');
  try{const fd=new FormData();fd.append('role',role());fd.append('resume',resumeText());fd.append('jd',$('jd').value);fd.append('country',await ensureCountry());
    const d=await api('/api/resume/review',{method:'POST',body:fd});
    $('reviewOut').innerHTML=`<h2>Resume review <span class="score">${esc(d.score)}/10</span></h2><p>${esc(d.overall)}</p><h3>Weaknesses and how to fix them</h3>`
    +(d.weaknesses||[]).map(w=>`<div class="w"><b>${esc(w.issue)}</b><br>${esc(w.why_it_hurts)}<br><span class="fix">Fix: ${esc(w.fix)}</span></div>`).join('')
    +((d.rewrite_examples||[]).length?'<h3>Rewrite examples</h3>'+d.rewrite_examples.map(x=>`<div class="ba"><div><small>Before</small><br>${esc(x.before)}</div><div><small>After</small><br>${esc(x.after)}</div></div>`).join(''):'')
    +((d.strengths||[]).length?'<h3>Strengths</h3>'+ul(d.strengths):'')
  }catch(e){profErr(e.message)}});

// ---- JD match
$('btnMatch').onclick=()=>busy($('btnMatch'),'Comparing...',async()=>{profErr('');
  try{if($('jd').value.trim().length<30)throw new Error('Paste the job description above to compare against.');
    const d=await post('/api/match',{resume:resumeText(),role:role(),jd:$('jd').value,country:await ensureCountry()});
    $('matchOut').innerHTML=`<h2>ATS match <span class="score">${esc(d.match_score)}%</span></h2><p>${esc(d.verdict)}</p>
    <h3>Keywords found</h3><div class="kw">${(d.matched_keywords||[]).map(k=>`<span class="ok">${esc(k)}</span>`).join('')||'<span class="note">none</span>'}</div>
    <h3>Missing keywords</h3><div class="kw">${(d.missing_keywords||[]).map(k=>`<span class="miss">${esc(k)}</span>`).join('')||'<span class="note">none</span>'}</div>
    <h3>Gaps and fixes</h3>${(d.gaps||[]).map(g=>`<div class="w"><b>${esc(g.gap)}</b><br><span class="fix">Fix: ${esc(g.fix)}</span></div>`).join('')}
    ${(d.tailored_bullets||[]).length?'<h3>Tailored rewrites</h3>'+d.tailored_bullets.map(x=>`<div class="ba"><div><small>Before</small><br>${esc(x.before)}</div><div><small>After</small><br>${esc(x.after)}</div></div>`).join(''):''}`;
  }catch(e){profErr(e.message)}});

// ---- voice (Web Speech API)
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;const TTS=window.speechSynthesis;
let rec=null,listening=false,baseText='';
$('voiceNote').textContent=(SR&&TTS)?'Voice mode: the interviewer asks aloud and you answer by speaking. Your browser will ask for microphone permission once.':'Voice mode needs Chrome, Edge or Safari. Typing works everywhere.';
function setMode(v){if(v&&!(SR&&TTS)){$('voiceNote').textContent='Voice is not supported in this browser. Use Chrome, Edge or Safari, or type your answers.';return}
  voice=v;$('mText').classList.toggle('on',!v);$('mVoice').classList.toggle('on',v);$('micBar').classList.toggle('hide',!v);$('voiceOpts').classList.toggle('hide',!v);if(v)refreshVoices();if(!v){stopMic();if(TTS)TTS.cancel()}}
$('mText').onclick=()=>setMode(false);$('mVoice').onclick=()=>{warmSpeech();setMode(true)};
const VK='ip_voice';let prefs={accent:null,voice:'',rate:1.0,v:2};try{const sv=JSON.parse(localStorage.getItem(VK)||'{}');if(sv&&typeof sv==='object'){if(sv.v!==2){delete sv.rate;delete sv.voice}prefs=Object.assign(prefs,sv);prefs.v=2}prefs.rate=Math.min(1.1,Math.max(0.6,Number(prefs.rate)||1.0))}catch(e){}
function savePrefs(){try{localStorage.setItem(VK,JSON.stringify(prefs))}catch(e){}}
function voiceScore(v){const n=v.name.toLowerCase();let sc=0;if(/natural|neural|online/.test(n))sc+=5;if(/google/.test(n))sc+=4;if(/samantha|karen|daniel|rishi|veena|ravi|heera|neerja|prabhat|aria|jenny|guy/.test(n))sc+=3;if(!v.localService)sc+=2;if(/compact|espeak|-x-.*-local/.test(n))sc-=3;return sc}
function voicesFor(lang){if(!TTS)return[];const all=TTS.getVoices().filter(v=>v.lang&&v.lang.replace('_','-').toLowerCase()===lang.toLowerCase());
  const base=lang.slice(0,2);const pool=all.length?all:TTS.getVoices().filter(v=>v.lang&&v.lang.toLowerCase().startsWith(base));return pool.sort((a,b)=>voiceScore(b)-voiceScore(a))}
function refreshVoices(){if(!TTS)return;const acc=prefs.accent||'en-US';$('vAccent').value=acc;
  const vs=voicesFor(acc);$('vVoice').innerHTML=vs.length?vs.map(v=>`<option value="${esc(v.name)}">${esc(v.name)}</option>`).join(''):'<option value="">Browser default</option>';
  if(vs.some(v=>v.name===prefs.voice))$('vVoice').value=prefs.voice;else $('vVoice').value=vs[0]?vs[0].name:'';
  $('vRate').value=prefs.rate;$('vRateVal').textContent=prefs.rate.toFixed(2)+'x'+(prefs.rate<=0.85?' (slow and clear)':prefs.rate>=0.95?' (natural pace)':'')}
if(TTS){TTS.onvoiceschanged=refreshVoices;refreshVoices()}
$('vAccent').onchange=()=>{prefs.accent=$('vAccent').value;prefs.voice='';savePrefs();refreshVoices()};
$('vVoice').onchange=()=>{prefs.voice=$('vVoice').value;savePrefs()};
$('vRate').oninput=()=>{prefs.rate=parseFloat($('vRate').value);savePrefs();$('vRateVal').textContent=prefs.rate.toFixed(2)+'x'};
$('vTest').onclick=()=>speak('Hello, welcome to your interview. Please tell me about yourself, and take your time.',null,true);
// Natural playback: a few long chunks (whole sentences, ~220 chars) with no artificial pauses. Many tiny utterances sounded halting.
function chunks(text){const s=String(text).replace(/\s+/g,' ').trim().match(/[^.!?]+[.!?]*/g)||[String(text)];const out=[];let cur='';
  for(const x of s){if(cur&&(cur+' '+x).length>220){out.push(cur);cur=x.trim()}else cur=(cur?cur+' ':'')+x.trim()}if(cur)out.push(cur);return out}
let warmed=false;function warmSpeech(){if(!TTS||warmed)return;warmed=true;try{const u=new SpeechSynthesisUtterance(' ');u.volume=0;TTS.speak(u)}catch(e){}}
function speak(text,onend,force){if(!(voice||force)||!TTS){onend&&onend();return}TTS.cancel();
  const acc=prefs.accent||'en-US';const list=voicesFor(acc);let vi=Math.max(0,list.findIndex(x=>x.name===prefs.voice));
  const parts=chunks(text);let i=0,done=false,tries=0;const fin=()=>{if(!done){done=true;onend&&onend()}};
  const next=()=>{if(i>=parts.length)return fin();const t=parts[i];const u=new SpeechSynthesisUtterance(t);u.lang=acc;if(list[vi])u.voice=list[vi];u.rate=prefs.rate;u.pitch=1;
    u.onend=()=>{i++;tries=0;next()};
    u.onerror=ev=>{if(ev&&(ev.error==='canceled'||ev.error==='interrupted'))return;if(tries++<1&&list.length>1){vi=(vi+1)%list.length;next()}else fin()};
    TTS.speak(u)};next()}
function startMic(){if(!SR||listening)return;rec=new SR();rec.lang=prefs.accent||'en-US';rec.continuous=true;rec.interimResults=true;baseText=$('ans').value.trim();
  rec.onresult=e=>{let t='';for(let i=0;i<e.results.length;i++)t+=e.results[i][0].transcript;$('ans').value=(baseText?baseText+' ':'')+t.trim()};
  rec.onerror=e=>{listening=false;$('btnMic').textContent='Start speaking';$('micState').textContent=e.error==='not-allowed'?'Microphone blocked. Allow it in the browser address bar, or switch to Type.':e.error==='no-speech'?'No speech heard. Try again.':'Mic problem ('+e.error+'). You can type instead.'};
  rec.onend=()=>{listening=false;$('btnMic').textContent='Start speaking';if(!$('micState').textContent.startsWith('Mic')&&!$('micState').textContent.includes('blocked'))$('micState').innerHTML='Review or edit your answer, then submit.'};
  try{rec.start();listening=true;$('btnMic').textContent='Stop';$('micState').innerHTML='<span class="live">Listening...</span> speak your answer';}catch(e){$('micState').textContent='Could not start the microphone.'}}
function stopMic(){if(rec&&listening){try{rec.stop()}catch(e){}}listening=false}
$('btnMic').onclick=()=>listening?stopMic():startMic();
$('btnSpeak').onclick=()=>speak($('qtext').textContent);

// ---- interview
$('btnStart').onclick=()=>busy($('btnStart'),'Preparing questions...',async()=>{profErr('');
  try{const d=await post('/api/session',{resume:$('resume').value.trim(),role:role(),jd:$('jd').value,country:await ensureCountry(),level:$('ivLevel').value,followups:$('ivFu').checked});
    sid=d.session_id;fuOn=$('ivFu').checked;$('fb').innerHTML='';$('report').classList.add('hide');$('interview').classList.remove('hide');showQ(d.question,d.number,d.total)
  }catch(e){profErr(e.message)}});
function showQ(q,n,t,fu){curFu=!!fu;retryMode=false;$('btnAns').textContent='Submit answer';if(!voice)$('fb').innerHTML='';$('qnum').textContent=fu?`Question ${n} of ${t} - follow-up ${fu.n}`:`Question ${n} of ${t}`;$('qtype').textContent=fu?'follow-up':q.type;$('qtext').textContent=q.question;$('ans').value='';$('btnAns').disabled=false;$('micState').textContent='';
  $('interview').scrollIntoView({behavior:'smooth',block:'start'});speak(q.question,()=>{if(voice&&!listening)startMic()})}
let curFu=false,wasFu=false,lastText='',retryMode=false,retryInfo={left:3};
function fbHtml(d,f){const s=f.scores||{},cm=f.communication||{},m=cm.metrics||{};const fl=Object.entries(m.fillers||{}).map(([k,v])=>`"${esc(k)}" x${v}`).join(', ');
  return `<h3>Feedback</h3><div class="bars">${['clarity','depth','correctness','star'].map(k=>`<div class="bar"><b>${esc(s[k])}/5</b>${k==='star'?'STAR':k}</div>`).join('')}</div>
      <p>${esc(f.feedback)}</p><div class="w g"><b>A stronger answer</b><br>${esc(f.stronger_answer)}${f.stronger_answer_note?`<p class="note">${esc(f.stronger_answer_note)}</p>`:''}</div>${ul(f.tips)}
      <h3>Communication</h3><p><span class="pill">Fluency ${esc(cm.fluency)}/5</span><span class="pill">${esc(cm.tone)}</span><span class="pill">${esc(m.word_count)} words</span><span class="pill">${esc(m.filler_total||0)} filler words</span></p>
      ${fl?`<p class="note">Fillers: ${fl}</p>`:''}${m.too_short?'<p class="note">Answer was short. Aim for 60-90 seconds with an example.</p>':''}${ul(cm.language_notes)}${cm.tip?`<p><b>Tip:</b> ${esc(cm.tip)}</p>`:''}
      ${(!fuOn&&f.followup)?`<p><b>Interviewer follow-up:</b> ${esc(f.followup)}</p>`:''}${d.difficulty?`<p class="pill">Interviewer made the next question ${d.difficulty==='harder'?'harder: you answered strongly':'a little easier: let us build up'}</p>`:''}`}
function drawRetry(){const a=$('retryArea');if(!a)return;
  if(voice||wasFu||retryInfo.left<=0){a.innerHTML=retryInfo.left<=0&&!wasFu?'<p class="note">You used all 3 retries on this question. Move on when you are ready.</p>':'';return}
  a.innerHTML=`<p><button class="ghost" id="btnRetry">Try this answer again${retryInfo.left<3?` (${retryInfo.left} left)`:''}</button></p><div class="note">Improve it using the feedback, then see how your score changes.</div>`;
  $('btnRetry').onclick=()=>{retryMode=true;$('ans').value=lastText;$('btnAns').disabled=false;$('btnAns').textContent='Score my new attempt';$('ans').focus();$('ans').scrollIntoView({behavior:'smooth',block:'center'});a.innerHTML='<p class="note">Edit your answer above, then press "Score my new attempt".</p>'}}
function cmpHtml(r){const d=(r.new_avg-r.previous_avg),fs=r.first_scores||{};const first=['clarity','depth','correctness'].map(k=>+fs[k]).filter(x=>!isNaN(x));const a0=first.length?first.reduce((x,y)=>x+y,0)/first.length:r.previous_avg;
  const tot=r.new_avg-a0;
  return `<div class="cmp"><b>Attempt ${r.attempt}</b><span>Average ${a0.toFixed(1)} → <b>${r.new_avg.toFixed(1)}</b> out of 5</span><span class="${tot>0.04?'up':tot<-0.04?'down':''}">${tot>0.04?'▲ +'+tot.toFixed(1)+' better than your first answer':tot<-0.04?'▼ '+tot.toFixed(1)+' lower than your first answer (your best score is kept)':'same as your first answer'}</span></div>`}
$('btnAns').onclick=async()=>{stopMic();if(TTS)TTS.cancel();$('ansErr').textContent='';
  const text=$('ans').value.trim();if(!text){$('ansErr').textContent='Give an answer first.';return}
  $('btnAns').disabled=true;$('busy').classList.remove('hide');
  if(retryMode){try{const r=await post(`/api/session/${sid}/retry`,{answer:text});retryMode=false;lastText=text;retryInfo.left=r.retries_left;
      $('fbBody').innerHTML=cmpHtml(r)+fbHtml({},r.feedback);$('btnAns').textContent='Submit answer';$('btnAns').disabled=true;drawRetry();$('fbBody').scrollIntoView({behavior:'smooth',block:'start'})}
    catch(e){$('ansErr').textContent=e.message;$('btnAns').disabled=false}finally{$('busy').classList.add('hide')}return}
  try{const d=await post(`/api/session/${sid}/answer`,{answer:text});const f=d.feedback,s=f.scores||{},cm=f.communication||{},m=cm.metrics||{};
    const fl=Object.entries(m.fillers||{}).map(([k,v])=>`"${esc(k)}" x${v}`).join(', ');
    wasFu=curFu;lastText=text;retryInfo={left:3};
    $('fb').innerHTML=`<div id="fbBody">${fbHtml(d,f)}</div><div id="retryArea"></div><div id="nextArea"></div>`;
    drawRetry();
    $('busy').classList.add('hide');
    if(d.finished){$('btnAns').disabled=true;$('nextArea').innerHTML='<button id="btnRep">See my session report</button>';$('btnRep').onclick=loadReport}
    else if(d.followup){$('nextArea').innerHTML='<p class="note">The interviewer wants to dig deeper into your answer.</p><button id="btnNext">Answer the follow-up</button>';let went=false;
      const go=()=>{if(went)return;went=true;showQ(d.followup,d.number,d.total,d.followup)};
      $('btnNext').onclick=()=>{if(TTS)TTS.cancel();go()};if(voice)go()}
    else{$('nextArea').innerHTML='<button id="btnNext">Next question</button>';let went=false;
      const go=()=>{if(went)return;went=true;showQ(d.next_question,d.number,d.total)};
      $('btnNext').onclick=()=>{if(TTS)TTS.cancel();go()};
      if(voice)speak('Feedback. '+(f.feedback||'')+' Next question.',go)}
  }catch(e){$('ansErr').textContent=e.message;$('btnAns').disabled=false;$('busy').classList.add('hide')}};
async function loadReport(){$('ansErr').textContent='';const ra=$('retryArea');if(ra)ra.innerHTML='';
  try{const r=await api(`/api/session/${sid}/report`);lastReport=r;const el=$('report');el.classList.remove('hide');
  el.innerHTML=`<h2>Session report <span class="score">${esc(r.overall_score)}/5</span></h2><p>${esc(r.summary)}</p>
   ${r.communication_summary?`<h3>Communication</h3><p>${esc(r.communication_summary)}</p>`:''}
   <h3>Strengths</h3>${ul(r.strengths)}<h3>Gaps</h3>${ul(r.gaps)}
   <h3>7-day practice plan</h3><ol>${(r.plan_7_days||[]).map(x=>`<li><b>Day ${esc(x.day)}:</b> ${esc(x.task)}</li>`).join('')}</ol><p><button class="ghost" data-pdf="report">Download report as PDF</button></p>${me?'<p class="note">Your scores (not your answers) were added to My History > Your progress.</p>':'<p class="note">Log in to track your scores over time.</p>'}`;
  el.insertAdjacentHTML('beforeend',`<h3>Share your result</h3><p class="note">Create a clean score card for LinkedIn or WhatsApp. It shows only your score, role and strengths, never your resume.</p>
   <input type="text" id="cardName" maxlength="40" placeholder="Your name on the card (optional)"><button id="btnCard" class="alt">Create share card</button><div id="cardOut"></div>`);
  $('btnCard').onclick=()=>busy($('btnCard'),'Designing your card...',async()=>{
    try{const c=await post(`/api/session/${sid}/card`,{name:$('cardName').value});const t=encodeURIComponent(`I scored ${c.score}/5 in an AI mock interview on MockRep (${c.verdict}). Try yours free: `);
      $('cardOut').innerHTML=`<img src="${esc(c.image)}" alt="Your score card" style="max-width:100%;border-radius:14px;margin-top:12px"><div class="shareRow">
        <a href="https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(c.url)}" target="_blank" rel="noopener"><button type="button">Share on LinkedIn</button></a>
        <a href="https://wa.me/?text=${t}${encodeURIComponent(c.url)}" target="_blank" rel="noopener"><button type="button" class="alt">Share on WhatsApp</button></a>
        ${navigator.share?'<button type="button" class="alt" id="cardShare">Share…</button>':''}<button type="button" class="ghost" id="cardCopy">Copy link</button><a href="${esc(c.image)}" download="mockrep-score.png"><button type="button" class="ghost">Download image</button></a></div>`;
      if($('cardShare'))$('cardShare').onclick=()=>navigator.share({title:'My MockRep score',text:`I scored ${c.score}/5 in an AI mock interview on MockRep.`,url:c.url}).catch(()=>{});
      $('cardCopy').onclick=async e=>{try{await navigator.clipboard.writeText(c.url);e.target.textContent='Copied'}catch(_){prompt('Copy this link',c.url)}}}
    catch(e){$('ansErr').textContent=e.message}});
  el.scrollIntoView({behavior:'smooth'})}catch(e){$('ansErr').textContent=e.message}}

// ---- STAR builder
let lastStar=null,lastBrief=null;
const starHtml=d=>`<h3>Your STAR answer</h3>${d.opener?`<p class="note">Start with: <i>${esc(d.opener)}</i></p>`:''}
  ${[['Situation',d.situation],['Task',d.task],['Action',d.action],['Result',d.result]].map(([k,v])=>`<div class="blk"><b>${k}</b><br>${esc(v)}</div>`).join('')}
  <h3>Say it like this</h3><div class="w g say">${esc(d.spoken_answer)}</div><button class="ghost" id="stCopy">Copy answer</button>
  ${d.missing&&d.missing.length?`<h3>Make it stronger: add these</h3>${ul(d.missing)}`:''}${d.tips&&d.tips.length?`<h3>Delivery tips</h3>${ul(d.tips)}`:''}
  <p><button class="ghost" data-save="star">Save to my history</button></p>`;
function starBind(d){const b=$('stCopy');if(b)b.onclick=async()=>{try{await navigator.clipboard.writeText(d.spoken_answer);b.textContent='Copied'}catch(e){}}}
$('btnStar').onclick=()=>busy($('btnStar'),'Building your answer...',async()=>{$('starErr').textContent='';
  try{const d=await post('/api/star',{experience:$('stExp').value,question:$('stQ').value,role:$('role').value,country:country||'US'});
    lastStar=Object.assign({question:$('stQ').value},d);$('starOut').innerHTML=starHtml(d);starBind(d)}catch(e){$('starErr').textContent=e.message}});
// ---- company brief
const bfCountry=()=>{$('bfCountry').textContent=`Adapted to: ${country||'US'} (change the Country chips at the top of the page)`};
document.querySelector('[data-t=brief]').addEventListener('click',()=>{bfCountry();if(!$('bfRole').value)$('bfRole').value=$('role').value});
fetch('/api/companies').then(r=>r.json()).then(j=>{$('bfList').innerHTML=j.companies.map(c=>`<option value="${esc(c)}">`).join('')}).catch(()=>{});
const sec=(t,h)=>h?`<div class="cand"><b>${t}</b>${h}</div>`:'';
const briefHtml=d=>`<h2>${esc(d.company)} <span class="pill">${esc(d.country)} view</span></h2><p>${esc(d.summary)}</p>${d.market_note?`<p class="note">${esc(d.market_note)}</p>`:''}
  ${sec('Interview process',d.process.length?'<ol>'+d.process.map(x=>`<li>${esc(x)}</li>`).join('')+'</ol>':'')}${sec('What they ask',ul(d.question_style))}
  ${sec('Culture',ul(d.culture))}${sec('Recent focus areas',ul(d.recent_focus))}
  ${d.why_join?`<div class="w g"><b>Your "why this company" angle</b><br>${esc(d.why_join)}</div>`:''}${sec('Smart questions to ask them',ul(d.ask_them))}${sec('Avoid these mistakes',ul(d.watch_out))}
  <p class="note">${esc(d.caution)} <a href="${esc(/^https:\/\//.test(d.news_url||"")?d.news_url:"#")}" target="_blank" rel="noopener">See the latest news</a></p><p><button class="ghost" data-save="brief">Save to my history</button></p>`;
$('btnBrief').onclick=()=>busy($('btnBrief'),'Researching...',async()=>{$('briefErr').textContent='';
  try{const d=await post('/api/company-brief',{company:$('bfCo').value,role:$('bfRole').value||$('role').value,country:country||'US'});lastBrief=d;$('briefOut').innerHTML=briefHtml(d)}catch(e){$('briefErr').textContent=e.message}});

// ---- negotiation
function bubble(who,t){const d=document.createElement('div');d.className='bubble '+(who==='recruiter'?'r':'c');d.innerHTML=`<small class="note">${who==='recruiter'?'Recruiter':'You'}</small><br>${esc(t)}`;$('chat').appendChild(d);d.scrollIntoView({behavior:'smooth',block:'nearest'})}
$('btnNego').onclick=()=>busy($('btnNego'),'Setting up...',async()=>{profErr('');$('negoErr').textContent='';
  try{const d=await post('/api/negotiation',{resume:$('resume').value.trim(),role:role(),country:await ensureCountry(),current:$('curpay').value});
    nsid=d.session_id;$('chat').innerHTML='';$('negoRep').innerHTML='';$('negoBox').classList.remove('hide');const s=d.scenario;
    $('negoInfo').textContent=`Estimated market range: ${s.market_range}. Goal: ${s.goal} (figures are AI estimates, verify with real salary data.)`;bubble('recruiter',s.opening_message);$('btnSay').disabled=false
  }catch(e){profErr(e.message)}});
$('btnSay').onclick=async()=>{const m=$('negoMsg').value.trim();if(!m)return;$('negoErr').textContent='';$('btnSay').disabled=true;$('negoBusy').classList.remove('hide');
  try{bubble('candidate',m);$('negoMsg').value='';const d=await post(`/api/negotiation/${nsid}/say`,{message:m});bubble('recruiter',d.recruiter_reply);
    const c=d.coach||{};const el=document.createElement('div');el.className='w g';el.innerHTML=`<b>Coach</b> (offer now: ${esc(d.current_offer)}, turn ${d.turn}/${d.max_turns})<br>Worked: ${esc(c.what_worked)}<br>Improve: ${esc(c.what_to_improve)}<br>Try saying: <i>${esc(c.better_line)}</i>`;$('chat').appendChild(el);
    if(d.finished){$('btnSay').disabled=true;$('negoErr').textContent='Negotiation finished. Get your coaching report.'}else $('btnSay').disabled=false
  }catch(e){$('negoErr').textContent=e.message;$('btnSay').disabled=false}$('negoBusy').classList.add('hide')};
$('btnNegoRep').onclick=()=>busy($('btnNegoRep'),'Preparing report...',async()=>{$('negoErr').textContent='';
  try{const r=await api(`/api/negotiation/${nsid}/report`);$('btnSay').disabled=true;
    $('negoRep').innerHTML=`<h2>Negotiation debrief <span class="score">${esc(r.score)}/5</span></h2><p>${esc(r.outcome)}</p><h3>What you did well</h3>${ul(r.strengths)}<h3>Mistakes to avoid</h3>${ul(r.mistakes)}<h3>Say this in a real negotiation</h3>${ul(r.script)}<h3>Next steps</h3>${ul(r.next_steps)}`}
  catch(e){$('negoErr').textContent=e.message}});

// ---- recruiter mode
let candN=0;
function addCand(){if(document.querySelectorAll('.cand').length>=10){$('scrErr').textContent='Maximum 10 candidates.';return}candN++;
  const d=document.createElement('div');d.className='cand';d.innerHTML=`<input type="text" class="cn" maxlength="80" placeholder="Candidate name" aria-label="Candidate name"><textarea class="cr" placeholder="Paste resume text..." aria-label="Resume"></textarea>
  <input type="file" class="cf" accept=".pdf,.txt" aria-label="Upload resume"> <button class="ghost rm">Remove</button>`;
  d.querySelector('.rm').onclick=()=>d.remove();
  d.querySelector('.cf').onchange=async e=>{const f=e.target.files[0];if(!f)return;const fd=new FormData();fd.append('file',f);
    try{const r=await api('/api/extract',{method:'POST',body:fd});d.querySelector('.cr').value=r.text;if(!d.querySelector('.cn').value)d.querySelector('.cn').value=f.name.replace(/\.[^.]+$/,'')}catch(x){$('scrErr').textContent=x.message}};
  $('cands').appendChild(d)}
$('btnAddCand').onclick=addCand;addCand();addCand();
$('btnScreen').onclick=async()=>{$('scrErr').textContent='';profErr('');$('btnScreen').disabled=true;$('scrBusy').classList.remove('hide');
  try{const cs=[...document.querySelectorAll('.cand')].map((d,i)=>({name:d.querySelector('.cn').value||'Candidate '+(i+1),resume:d.querySelector('.cr').value})).filter(c=>c.resume.trim().length>=30);
    if(!cs.length)throw new Error('Add at least one candidate resume.');
    const d=await post('/api/recruiter/screen',{role:role(),jd:$('jd').value,country:await ensureCountry(),candidates:cs});
    $('scrOut').innerHTML='<h2>Ranked candidates</h2>'+d.ranked.map((r,i)=>`<div class="w g"><b>#${i+1} ${esc(r.name)}</b> <span class="score" style="font-size:22px">${esc(r.score)}</span>/100 <span class="rec-${esc(r.recommendation)}"><b>${esc(r.recommendation)}</b></span>
      <br>${esc(r.summary)}<br><b>Strengths</b>${ul(r.strengths)}<b>Risks</b>${ul(r.risks)}<b>Phone-screen questions</b>${ul(r.screening_questions)}</div>`).join('')
      +d.failed.map(f=>`<div class="w"><b>${esc(f.name)}</b>: ${esc(f.error)}</div>`).join('')
  }catch(e){$('scrErr').textContent=e.message}$('btnScreen').disabled=false;$('scrBusy').classList.add('hide')};

// ---- progress chart
const SK=[['clarity','Clarity','#9be000'],['depth','Depth','#5b8cff'],['correctness','Correctness','#ffb84d'],['star','STAR','#ff6b7a'],['fluency','Fluency','#c18bff']];
function chartSvg(pts){const W=600,H=260,L=36,R=14,T=14,B=34,n=pts.length,x=i=>n===1?(L+W-R)/2:L+i*(W-L-R)/(n-1),y=v=>T+(5-v)*(H-T-B)/4;
  let g='';for(let v=1;v<=5;v++)g+=`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="rgba(255,255,255,.09)"/><text x="${L-8}" y="${y(v)+4}" fill="#9aa6c0" font-size="12" text-anchor="end">${v}</text>`;
  const step=Math.max(1,Math.ceil(n/6));pts.forEach((p,i)=>{if(i%step===0||i===n-1)g+=`<text x="${x(i)}" y="${H-10}" fill="#9aa6c0" font-size="11.5" text-anchor="middle">${esc(fmt(p.created))}</text>`});
  SK.forEach(([k,,col])=>{const s=pts.map((p,i)=>[i,p.scores[k]]).filter(a=>typeof a[1]==='number');if(!s.length)return;
    if(s.length>1)g+=`<polyline fill="none" stroke="${col}" stroke-width="2.5" stroke-linejoin="round" points="${s.map(a=>x(a[0])+','+y(a[1])).join(' ')}"/>`;
    s.forEach(a=>{g+=`<circle cx="${x(a[0])}" cy="${y(a[1])}" r="4" fill="${col}"><title>${esc(k)} ${a[1]}</title></circle>`})});
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Your scores per skill over your mock interviews">${g}</svg><div class="legend">${SK.map(([,l,c])=>`<span><i style="background:${c}"></i>${l}</span>`).join('')}</div>`}
async function progLoad(){const b=$('progBox');b.innerHTML='<p class="note">Loading...</p>';
  try{const j=await api('/api/progress'),pts=j.points||[];
    if(!pts.length){b.innerHTML='<p class="note">Finish a mock interview and open the session report. Your scores per skill will appear here so you can see yourself improve. Only scores are kept, never your answers.</p>';return}
    const last=pts[pts.length-1],first=pts[0];
    b.innerHTML=chartSvg(pts)+`<p class="note">${pts.length} session${pts.length>1?'s':''}. Latest overall score: <b>${esc(last.overall??'-')}/5</b>${pts.length>1&&first.overall!=null&&last.overall!=null?` (first: ${esc(first.overall)}/5)`:''}. Only your scores are stored, never your answers or resume.</p>`}
  catch(e){b.innerHTML=`<div class="err">${esc(e.message)}</div>`}}

// ---- PDF (browser print dialog: choose "Save as PDF")
let lastReport=null;
function printDoc(html){$('prArea').innerHTML=html;document.body.classList.add('pr');setTimeout(()=>window.print(),50)}
window.addEventListener('afterprint',()=>{document.body.classList.remove('pr');$('prArea').innerHTML=''});
const today=()=>new Date().toLocaleDateString(undefined,{year:'numeric',month:'long',day:'numeric'});
document.body.addEventListener('click',e=>{const k=e.target.dataset&&e.target.dataset.pdf;if(!k)return;
  if(k==='report'&&lastReport){const r=lastReport;printDoc(`<h1>Interview practice report</h1><p>${esc($('role').value.trim())} - ${esc(today())} - Overall ${esc(r.overall_score)}/5</p><h2>Summary</h2><p>${esc(r.summary)}</p>${r.communication_summary?`<h2>Communication</h2><p>${esc(r.communication_summary)}</p>`:''}<h2>Strengths</h2>${ul(r.strengths)}<h2>Gaps</h2>${ul(r.gaps)}<h2>7-day practice plan</h2><ol>${(r.plan_7_days||[]).map(x=>`<li><b>Day ${esc(x.day)}:</b> ${esc(x.task)}</li>`).join('')}</ol><p style="margin-top:18px;color:#555">Made with MockRep. AI feedback is guidance, not a guarantee.</p>`)}
  if(k==='prep'&&lastPrep){const d=lastPrep.pack;printDoc(`<h1>Interview prep pack: ${esc(lastPrep.role)}</h1><p>${esc(today())} - tailored for the ${esc(d.country)} market</p>${d.focus&&d.focus.length?`<h2>Revise these first</h2>${ul(d.focus)}`:''}<h2>Likely questions with model answers</h2>${d.questions.map((q,i)=>`<div class="q"><p><b>${i+1}. ${esc(q.question)}</b> (${esc(q.type)})</p>${q.why_asked?`<p><i>Why they ask: ${esc(q.why_asked)}</i></p>`:''}<p>${esc(q.model_answer)}</p></div>`).join('')}${lastPrep.coding&&lastPrep.coding.coding_questions&&lastPrep.coding.coding_questions.length?`<h2>Coding questions</h2>${ul(lastPrep.coding.coding_questions.map(c=>(c.title||'')+': '+(c.problem||'')))}`:''}<p style="margin-top:18px;color:#555">Made with MockRep. Replace example details in model answers with your real experience.</p>`)}});

// ---- first-time guided start
const SEEN='ip_seen';
const endGuide=()=>{document.body.classList.remove('guided');try{localStorage.setItem(SEEN,'1')}catch(e){}};
try{if(!localStorage.getItem(SEEN)&&!/[?&]full=1/.test(location.search))document.body.classList.add('guided')}catch(e){}
$('guideAll').onclick=e=>{e.preventDefault();endGuide()};
$('guideSkip').onclick=()=>{endGuide();$('tabs').scrollIntoView({behavior:'smooth'})};
$('btnPrep').addEventListener('click',()=>{if(document.body.classList.contains('guided')){const iv=setInterval(()=>{if(!$('btnPrep').disabled){clearInterval(iv);if($('prepOut').innerHTML.trim()){endGuide();$('prepOut').scrollIntoView({behavior:'smooth'})}}},400);setTimeout(()=>clearInterval(iv),90000)}});

// ---- waitlist
$('wlBtn').onclick=()=>busy($('wlBtn'),'Joining...',async()=>{$('wlMsg').textContent='';
  try{const j=await post('/api/waitlist',{email:$('wlEmail').value});$('wlMsg').textContent=j.new?'You are on the list. Thank you!':'You are already on the list. Thank you!';$('wlEmail').value=''}catch(e){$('wlMsg').textContent=e.message}});
