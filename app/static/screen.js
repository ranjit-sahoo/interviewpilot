(()=>{'use strict';
const $=id=>document.getElementById(id);const app=$('app');
const ORIG=decodeURIComponent(location.pathname.split('/').pop());
let TOKEN=ORIG,INFO=null,PLAN=null,LANG='en',leaves=0,STATE={};
try{if(/^(1|true)$/.test(new URLSearchParams(location.search).get('lite')||'')||localStorage.getItem('mr_lite')==='1')document.body.classList.add('lite')}catch(e){}
const T={
en:{hello:'Welcome',intro:'This is a short first-round screening for the role of',time:'It takes about',min:'minutes. Please sit somewhere quiet.',
 priv:'Your privacy: your voice is turned into text by your own phone or browser. We do NOT record or store any audio. Only the text of your answers and your test scores are saved, they are shown to the recruiter, and they are deleted automatically after',days:'days. You can delete them yourself any time after finishing.',
 consent:'I agree to this, and I understand a recruiter will see my answers and scores.',name:'Your full name',phone:'Mobile number (with country code if outside India)',start:'Start',need:'Please tick the consent box.',
 mic:'Voice answers need a microphone. When the browser asks, tap Allow. Speak clearly in your own words. You cannot type the answers.',nomic:'This browser cannot capture speech. Please open this link in Chrome on Android or a computer.',
 q:'Question',of:'of',speak:'Tap to start answering',stop:'Done answering',left:'seconds left',listening:'Listening... speak now',next:'Next',followup:'One more question',submit:'Submit',
 typing:'Typing test',typeit:'Type this text exactly. The timer starts when you begin typing. Pasting is switched off.',reading:'Reading aloud',readit:'Tap the button and read this aloud clearly.',quiz:'Quiz',apt:'Aptitude test',
 done:'All done. Thank you!',doneTxt:'Your answers have been sent to the recruiter. You cannot take this screening again.',del:'Delete my data now',deleted:'Your data has been deleted.',confirm:'Delete all your answers and scores permanently?',
 closed:'This screening link is not available',tooShort:'Please answer in a few sentences.',notheard:'We could not hear anything. Check your microphone and try again.',saving:'Saving...',leaveWarn:'Please stay on this page during the screening.',retry:'Try again',resume:'You can continue where you stopped.'},
hinglish:{hello:'Swagat hai',intro:'Yeh ek chhota first-round screening hai is role ke liye:',time:'Isme lagbhag',min:'minute lagenge. Please kisi shant jagah baithiye.',
 priv:'Aapki privacy: aapki awaaz aapke phone/browser mein text ban jaati hai. Hum koi AUDIO record ya save NAHI karte. Sirf aapke jawab ka text aur test ke score save hote hain, recruiter ko dikhte hain, aur',days:'din baad apne aap delete ho jaate hain. Finish ke baad aap khud bhi kabhi bhi delete kar sakte hain.',
 consent:'Main sahmat hoon, aur samajhta/samajhti hoon ki recruiter mere jawab aur score dekhega.',name:'Aapka poora naam',phone:'Mobile number',start:'Shuru karein',need:'Please consent box tick karein.',
 mic:'Voice jawab ke liye microphone chahiye. Browser puchhe to Allow dabayein. Saaf aur apne shabdon mein boliye. Jawab type nahi kar sakte.',nomic:'Is browser mein speech nahi chalta. Please link ko Android ke Chrome ya computer par kholiye.',
 q:'Sawaal',of:'/',speak:'Jawab dena shuru karein',stop:'Jawab ho gaya',left:'second bache',listening:'Sun rahe hain... boliye',next:'Aage',followup:'Ek aur sawaal',submit:'Submit',
 typing:'Typing test',typeit:'Yeh text bilkul waise hi type karein. Timer typing shuru karte hi chalega. Paste band hai.',reading:'Zor se padhna',readit:'Button dabayein aur yeh saaf awaaz mein padhiye.',quiz:'Quiz',apt:'Aptitude test',
 done:'Ho gaya. Dhanyavaad!',doneTxt:'Aapke jawab recruiter ko bhej diye gaye hain. Yeh screening dobara nahi de sakte.',del:'Mera data abhi delete karein',deleted:'Aapka data delete ho gaya.',confirm:'Aapke saare jawab aur score hamesha ke liye delete karein?',
 closed:'Yeh screening link available nahi hai',tooShort:'Please kuch vakyon mein jawab dein.',notheard:'Kuch sunai nahi diya. Microphone check karke phir koshish karein.',saving:'Save ho raha hai...',leaveWarn:'Screening ke dauran is page par rahiye.',retry:'Phir koshish karein',resume:'Aap wahin se aage badh sakte hain jahan ruke the.'},
hi:{hello:'स्वागत है',intro:'यह इस पद के लिए एक छोटा पहले राउंड का स्क्रीनिंग है:',time:'इसमें लगभग',min:'मिनट लगेंगे। कृपया किसी शांत जगह बैठें।',
 priv:'आपकी प्राइवेसी: आपकी आवाज़ आपके फ़ोन/ब्राउज़र में ही टेक्स्ट बनती है। हम कोई ऑडियो रिकॉर्ड या सेव नहीं करते। सिर्फ़ आपके जवाबों का टेक्स्ट और टेस्ट स्कोर सेव होते हैं, रिक्रूटर को दिखते हैं, और',days:'दिन बाद अपने आप डिलीट हो जाते हैं। पूरा करने के बाद आप खुद भी कभी भी डिलीट कर सकते हैं।',
 consent:'मैं सहमत हूँ, और समझता/समझती हूँ कि रिक्रूटर मेरे जवाब और स्कोर देखेगा।',name:'आपका पूरा नाम',phone:'मोबाइल नंबर',start:'शुरू करें',need:'कृपया सहमति बॉक्स पर टिक करें।',
 mic:'आवाज़ वाले जवाब के लिए माइक्रोफ़ोन चाहिए। ब्राउज़र पूछे तो Allow दबाएँ। साफ़ और अपने शब्दों में बोलें। जवाब टाइप नहीं कर सकते।',nomic:'यह ब्राउज़र आवाज़ पहचान नहीं सकता। कृपया लिंक को Android के Chrome या कंप्यूटर पर खोलें।',
 q:'सवाल',of:'/',speak:'जवाब देना शुरू करें',stop:'जवाब पूरा हुआ',left:'सेकंड बचे',listening:'सुन रहे हैं... बोलिए',next:'आगे',followup:'एक और सवाल',submit:'जमा करें',
 typing:'टाइपिंग टेस्ट',typeit:'यह टेक्स्ट बिल्कुल वैसा ही टाइप करें। टाइप शुरू करते ही टाइमर चलेगा। पेस्ट बंद है।',reading:'ज़ोर से पढ़ना',readit:'बटन दबाएँ और यह साफ़ आवाज़ में पढ़ें।',quiz:'क्विज़',apt:'एप्टीट्यूड टेस्ट',
 done:'हो गया। धन्यवाद!',doneTxt:'आपके जवाब रिक्रूटर को भेज दिए गए हैं। यह स्क्रीनिंग दोबारा नहीं दे सकते।',del:'मेरा डेटा अभी डिलीट करें',deleted:'आपका डेटा डिलीट हो गया।',confirm:'आपके सभी जवाब और स्कोर हमेशा के लिए डिलीट करें?',
 closed:'यह स्क्रीनिंग लिंक उपलब्ध नहीं है',tooShort:'कृपया कुछ वाक्यों में जवाब दें।',notheard:'कुछ सुनाई नहीं दिया। माइक्रोफ़ोन जाँचकर फिर कोशिश करें।',saving:'सेव हो रहा है...',leaveWarn:'स्क्रीनिंग के दौरान इस पेज पर रहें।',retry:'फिर कोशिश करें',resume:'आप जहाँ रुके थे वहीं से आगे बढ़ सकते हैं।'},
ar:{hello:'مرحبًا',intro:'هذه مقابلة أولية قصيرة للوظيفة:',time:'تستغرق حوالي',min:'دقائق. يرجى الجلوس في مكان هادئ.',
 priv:'خصوصيتك: يتم تحويل صوتك إلى نص على هاتفك أو متصفحك. نحن لا نسجل ولا نحفظ أي صوت. يتم حفظ نص إجاباتك ونتائج الاختبارات فقط، ويراها المسؤول عن التوظيف، وتُحذف تلقائيًا بعد',days:'يومًا. يمكنك حذفها بنفسك في أي وقت بعد الانتهاء.',
 consent:'أوافق، وأفهم أن مسؤول التوظيف سيرى إجاباتي ونتائجي.',name:'الاسم الكامل',phone:'رقم الجوال (مع رمز الدولة)',start:'ابدأ',need:'يرجى تحديد مربع الموافقة.',
 mic:'الإجابات الصوتية تحتاج إلى ميكروفون. اضغط "السماح" عند الطلب. تحدث بوضوح وبكلماتك. لا يمكن كتابة الإجابات.',nomic:'هذا المتصفح لا يدعم التعرف على الكلام. افتح الرابط في Chrome على أندرويد أو على الكمبيوتر.',
 q:'السؤال',of:'من',speak:'اضغط لبدء الإجابة',stop:'انتهيت من الإجابة',left:'ثانية متبقية',listening:'نستمع إليك... تحدث الآن',next:'التالي',followup:'سؤال إضافي',submit:'إرسال',
 typing:'اختبار الكتابة',typeit:'اكتب هذا النص كما هو. يبدأ المؤقت عند بدء الكتابة. اللصق غير متاح.',reading:'القراءة بصوت عالٍ',readit:'اضغط الزر واقرأ هذا النص بصوت واضح.',quiz:'اختبار قصير',apt:'اختبار القدرات',
 done:'تم. شكرًا لك!',doneTxt:'تم إرسال إجاباتك إلى مسؤول التوظيف. لا يمكنك إعادة هذه المقابلة.',del:'احذف بياناتي الآن',deleted:'تم حذف بياناتك.',confirm:'حذف جميع إجاباتك ونتائجك نهائيًا؟',
 closed:'رابط المقابلة غير متاح',tooShort:'يرجى الإجابة في بضع جمل.',notheard:'لم نسمع شيئًا. تحقق من الميكروفون وحاول مرة أخرى.',saving:'جارٍ الحفظ...',leaveWarn:'يرجى البقاء في هذه الصفحة أثناء المقابلة.',retry:'حاول مرة أخرى',resume:'يمكنك المتابعة من حيث توقفت.'}};
const t=k=>(T[LANG]&&T[LANG][k])||T.en[k]||k;
function h(tag,attrs,...kids){const e=document.createElement(tag);for(const k in (attrs||{})){if(k==='class')e.className=attrs[k];else if(k.startsWith('on'))e.addEventListener(k.slice(2),attrs[k]);else if(attrs[k]!==false&&attrs[k]!=null)e.setAttribute(k,attrs[k])}
 for(const c of kids.flat())if(c!=null&&c!==false)e.append(c.nodeType?c:document.createTextNode(c));return e}
async function api(path,opt){const r=await fetch(path,Object.assign({headers:{'Content-Type':'application/json'}},opt||{}));let j={};try{j=await r.json()}catch(e){}
 if(!r.ok){const m=j.detail&&(typeof j.detail==='string'?j.detail:'Please check your entries.');const er=new Error(m||'Something went wrong. Please try again.');er.status=r.status;throw er}return j}
const post=(p,b)=>api(p,{method:'POST',body:JSON.stringify(b)});
function setLang(l){LANG=l;document.documentElement.lang=l==='hinglish'?'en':l;document.documentElement.dir=l==='ar'?'rtl':'ltr';$('lang').value=l;try{localStorage.setItem('mr_slang',l)}catch(e){}}
$('lang').onchange=e=>{setLang(e.target.value);if(STATE.render)STATE.render()};
document.addEventListener('visibilitychange',()=>{if(document.hidden&&STATE.live)leaves++});
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
const rlang=()=>({hi:'hi-IN',ar:'ar-AE'}[INFO&&INFO.campaign.lang==='hi'?'hi':INFO&&INFO.campaign.lang==='ar'?'ar':LANG]||'en-IN');
// speech capture: returns controller {stop()}; calls onText(final+interim), tracks think time and pauses
function listen(onText,onEnd){let final='',interim='',t0=Date.now(),first=null,last=Date.now(),pauses=0,stopped=false,rec;
 function mk(){rec=new SR();rec.lang=rlang();rec.continuous=true;rec.interimResults=true;
  rec.onresult=ev=>{const now=Date.now();if(first===null)first=(now-t0)/1000;if(now-last>2500)pauses++;last=now;interim='';for(let i=ev.resultIndex;i<ev.results.length;i++){const r=ev.results[i];if(r.isFinal)final+=r[0].transcript+' ';else interim+=r[0].transcript}onText((final+interim).trim())};
  rec.onerror=ev=>{if(ev.error==='not-allowed'||ev.error==='service-not-allowed'){stopped=true;onEnd({text:final.trim(),denied:true})}};
  rec.onend=()=>{if(!stopped){try{mk();rec.start()}catch(e){}}else if(!rec.__done){rec.__done=1;onEnd({text:(final+interim).trim(),think:first===null?(Date.now()-t0)/1000:first,secs:(Date.now()-t0)/1000,pauses})}};
  return rec}
 rec=mk();try{rec.start()}catch(e){}
 return{stop(){stopped=true;try{rec.stop()}catch(e){}setTimeout(()=>{if(!rec.__done){rec.__done=1;onEnd({text:(final+interim).trim(),think:first===null?(Date.now()-t0)/1000:first,secs:(Date.now()-t0)/1000,pauses})}},900)}}}
function countdown(secs,el,bar,onZero){let left=secs,iv=setInterval(()=>{left--;el.textContent=left+' '+t('left');el.classList.toggle('low',left<=10);bar.style.width=(100-100*left/secs)+'%';if(left<=0){clearInterval(iv);onZero()}},1000);el.textContent=left+' '+t('left');return()=>clearInterval(iv)}
function show(...n){app.replaceChildren(...n.flat().filter(Boolean))}
function fail(m){STATE={};show(h('div',{class:'card'},h('h1',{},t('closed')),h('p',{class:'mute'},m)))}

// ---------- start / consent
function startScreen(){
 const c=INFO.campaign,mins=Math.max(5,Math.round(((c.modules.includes('voice')?c.n*(c.secs+40):0)+(c.modules.length-(c.modules.includes('voice')?1:0))*150)/60));
 STATE.render=startScreen;
 const name=h('input',{type:'text',id:'nm',maxlength:80,autocomplete:'name','aria-label':t('name'),placeholder:t('name'),value:INFO.name&&INFO.name!=='Candidate'?INFO.name:''});
 const ph=h('input',{type:'tel',id:'ph',maxlength:30,autocomplete:'tel','aria-label':t('phone'),placeholder:t('phone')});
 const cb=h('input',{type:'checkbox',id:'cb'});const err=h('div',{class:'err',role:'alert'});
 const needVoice=c.modules.includes('voice')||c.modules.includes('reading');
 let saved=null;try{saved=localStorage.getItem('mr_s_'+ORIG)}catch(e){}
 show(h('div',{class:'card'},h('h1',{},t('hello')+(INFO.name&&!INFO.open?', '+INFO.name:'')),h('p',{},t('intro')+' ',h('b',{},c.role)+'. ',t('time')+' ',h('b',{},String(mins)),' '+t('min')),
  needVoice?h('p',{class:'mute'},t('mic')):null,h('p',{class:'mute'},t('priv')+' ',h('b',{},String(c.retention_days)+' '),t('days')),
  INFO.open?[name,ph]:(INFO.name?null:name),
  h('label',{class:'c',for:'cb'},cb,h('span',{},t('consent'))),err,saved?h('p',{class:'mute'},t('resume')):null,
  h('button',{onclick:async ev=>{err.textContent='';if(!cb.checked){err.textContent=t('need');return}
   if(needVoice&&c.modules.includes('voice')&&!SR){err.textContent=t('nomic');return}
   ev.target.disabled=true;try{const r=await post('/api/s/'+encodeURIComponent(ORIG)+'/start',{name:name.value,phone:ph.value,consent:true});TOKEN=r.token;PLAN=r.plan;STATE.prog=r.progress;STATE.pending=r.pending_followup;try{localStorage.setItem('mr_s_'+ORIG,TOKEN)}catch(e){}
    if(r.plan.modules.includes('voice')&&SR&&navigator.mediaDevices&&navigator.mediaDevices.getUserMedia){try{const s=await navigator.mediaDevices.getUserMedia({audio:true});s.getTracks().forEach(x=>x.stop())}catch(e){err.textContent=t('mic');ev.target.disabled=false;return}}
    run()}catch(e){err.textContent=e.message;ev.target.disabled=false}}},t('start'))))}

// ---------- sequence
const MODS=['voice','typing','reading','quiz','aptitude'];
function run(){STATE.live=true;const mods=MODS.filter(m=>PLAN.modules.includes(m));const doneKey={typing:'typing',reading:'reading',quiz:'quiz',aptitude:'apt'};
 const todo=mods.filter(m=>m==='voice'?(STATE.prog.voice_done<PLAN.voice.length):!(STATE.prog.modules_done||[]).includes(doneKey[m]));
 STATE.todo=todo;STATE.total=mods.length;next()}
function next(){const m=STATE.todo.shift();if(!m)return finish();({voice:voiceFlow,typing:typingFlow,reading:readingFlow,quiz:()=>mcqFlow('quiz'),aptitude:()=>mcqFlow('aptitude')})[m]()}
async function finish(){STATE.live=false;show(h('div',{class:'card'},h('p',{class:'mute'},t('saving'))));try{await post('/api/s/'+encodeURIComponent(TOKEN)+'/finish',{leaves});}catch(e){return fail(e.message)}
 STATE.render=finish2;finish2()}
function finish2(){const msg=h('p',{class:'mute'});show(h('div',{class:'card'},h('h1',{},t('done')),h('p',{},t('doneTxt')),h('p',{class:'mute'},t('priv')+' ',h('b',{},String(INFO.campaign.retention_days)+' '),t('days')),
  h('button',{class:'ghost',onclick:async()=>{if(!confirm(t('confirm')))return;try{await api('/api/s/'+encodeURIComponent(TOKEN)+'/mine',{method:'DELETE'});msg.textContent=t('deleted')}catch(e){msg.textContent=e.message}}},t('del')),msg))}

// ---------- voice questions
function voiceFlow(){let i=STATE.pending?STATE.pending.idx:STATE.prog.voice_done;const pend=STATE.pending;STATE.pending=null;
 const total=PLAN.voice.length;
 function ask(idx,text,isFu){
  STATE.render=()=>ask(idx,text,isFu);
  const tm=h('div',{class:'timer'}),bar=h('i'),live=h('div',{class:'live'},t('speak')),err=h('div',{class:'err',role:'alert'});let ctl=null,stopT=null,sent=false,fin=null;
  const btn=h('button',{onclick:()=>{if(ctl){ctl.stop();btn.disabled=true;return}
    live.textContent=t('listening');btn.textContent=t('stop');btn.classList.add('red');
    stopT=countdown(PLAN.secs,tm,bar,()=>{if(ctl)ctl.stop()});
    ctl=listen(tx=>{live.textContent=tx||t('listening')},async r=>{if(sent)return;sent=true;stopT&&stopT();
     if(r.denied){err.textContent=t('mic');sent=false;ctl=null;btn.disabled=false;btn.textContent=t('speak');btn.classList.remove('red');return}
     if(!r.text||r.text.split(/\s+/).length<2){err.textContent=t('notheard');sent=false;ctl=null;btn.disabled=false;btn.textContent=t('speak');btn.classList.remove('red');live.textContent=t('speak');return}
     btn.disabled=true;live.textContent=t('saving');
     try{const res=await post('/api/s/'+encodeURIComponent(TOKEN)+'/voice',{idx,text:r.text,think:r.think||0,secs:r.secs||0,pauses:r.pauses||0,followup:!!isFu,leaves});
      if(isFu){idx+1<total?ask(idx+1,PLAN.voice[idx+1].q,false):next()}else ask2(idx,res.follow_up)}catch(e){err.textContent=e.message;sent=false;ctl=null;btn.disabled=false;btn.textContent=t('retry');btn.classList.remove('red')}})}},t('speak'));
  show(h('div',{class:'card'},h('div',{class:'mute'},(isFu?t('followup')+' - ':'')+t('q')+' '+(idx+1)+' '+t('of')+' '+total),h('div',{class:'q'},text),tm,h('div',{class:'bar'},bar),live,err,btn));tm.textContent=PLAN.secs+' '+t('left')}
 function ask2(idx,fu){ask(idx,fu,true)}
 if(pend)ask(pend.idx,pend.text,true);else ask(i,PLAN.voice[i].q,false)}

// ---------- typing
function typingFlow(){STATE.render=typingFlow;const passage=PLAN.typing;let t0=null,tmr=null;const ta=h('textarea',{rows:5,'aria-label':t('typing'),autocomplete:'off',autocorrect:'off',autocapitalize:'off',spellcheck:'false'}),err=h('div',{class:'err'});const tm=h('div',{class:'timer'});let sent=false;
 async function send(){if(sent)return;sent=true;clearInterval(tmr);const secs=t0?(Date.now()-t0)/1000:60;try{await post('/api/s/'+encodeURIComponent(TOKEN)+'/module',{module:'typing',typed:ta.value,secs:Math.min(secs,600),leaves});next()}catch(e){err.textContent=e.message;sent=false}}
 ['paste','drop','cut'].forEach(ev=>ta.addEventListener(ev,e=>e.preventDefault()));
 ta.addEventListener('input',()=>{if(!t0){t0=Date.now();tmr=setInterval(()=>{const l=Math.max(0,60-Math.floor((Date.now()-t0)/1000));tm.textContent=l+' '+t('left');tm.classList.toggle('low',l<=10);if(l<=0)send()},1000)}});
 show(h('div',{class:'card'},h('h2',{},t('typing')),h('p',{class:'mute'},t('typeit')),h('div',{class:'pass'},passage),ta,tm,err,h('button',{onclick:()=>{if(ta.value.trim().length<3){err.textContent=t('tooShort');return}send()}},t('submit'))))}

// ---------- reading aloud
function readingFlow(){STATE.render=readingFlow;const passage=PLAN.reading,live=h('div',{class:'live'},t('speak')),err=h('div',{class:'err'});let ctl=null,sent=false;
 const btn=h('button',{onclick:()=>{if(ctl){ctl.stop();btn.disabled=true;return}if(!SR){err.textContent=t('nomic');return}live.textContent=t('listening');btn.textContent=t('stop');btn.classList.add('red');
  ctl=listen(tx=>{live.textContent=tx||t('listening')},async r=>{if(sent)return;sent=true;try{await post('/api/s/'+encodeURIComponent(TOKEN)+'/module',{module:'reading',said:r.text||'',leaves});next()}catch(e){err.textContent=e.message;sent=false;btn.disabled=false;btn.classList.remove('red');btn.textContent=t('retry');ctl=null}})}},t('speak'));
 show(h('div',{class:'card'},h('h2',{},t('reading')),h('p',{class:'mute'},t('readit')),h('div',{class:'pass'},passage),live,err,btn))}

// ---------- quiz / aptitude
function mcqFlow(mod){STATE.render=()=>mcqFlow(mod);const items=PLAN[mod],ans=items.map(()=>-1),err=h('div',{class:'err'});let sent=false;
 const secs=mod==='quiz'?300:420,tm=h('div',{class:'timer'});const stop=countdown(secs,tm,{style:{}},()=>send());
 async function send(){if(sent)return;sent=true;stop();try{await post('/api/s/'+encodeURIComponent(TOKEN)+'/module',{module:mod,answers:ans,leaves});next()}catch(e){err.textContent=e.message;sent=false}}
 show(h('div',{class:'card'},h('h2',{},t(mod==='quiz'?'quiz':'apt')),tm,items.map((it,qi)=>h('div',{style:'margin:14px 0'},h('div',{style:'font-weight:600'},(qi+1)+'. '+it.q),it.o.map((o,oi)=>h('label',{class:'opt'},h('input',{type:'radio',name:mod+qi,onchange:()=>{ans[qi]=oi}}),h('span',{},o))))),err,h('button',{onclick:send},t('submit'))))}

// ---------- boot
(async()=>{let l='en';try{l=localStorage.getItem('mr_slang')||''}catch(e){}
 try{INFO=await api('/api/s/'+encodeURIComponent(ORIG))}catch(e){setLang(l||'en');return fail(e.message)}
 setLang(l||INFO.campaign.lang||'en');document.title=(INFO.campaign.name||'Screening')+' - '+(INFO.brand.name||'MockRep');
 if(INFO.brand.color)document.documentElement.style.setProperty('--brand',INFO.brand.color);
 const b=$('brand');if(INFO.brand.logo)b.append(h('img',{src:INFO.brand.logo,alt:''}));b.append(INFO.brand.name||'MockRep');
 if(INFO.status==='done')return show(h('div',{class:'card'},h('h1',{},t('done')),h('p',{},t('doneTxt'))));
 startScreen()})();
})();
