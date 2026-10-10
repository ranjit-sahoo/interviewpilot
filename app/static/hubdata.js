// Static hiring-kit content: role templates, message templates, scorecards, letters. No AI, no salary numbers.
window.HUBDATA=(()=>{
const ROLES={
 bpo:{label:'BPO / Call Centre',must:['communication','customer service'],nice:['voice process','typing','excel'],years:0,
  jd:'We are hiring Customer Support Executives for our voice process.\n\nResponsibilities:\n- Handle inbound and outbound customer calls politely\n- Resolve queries and log details correctly\n- Meet quality and call-handling targets\n\nRequirements:\n- Clear spoken English (Hindi is a plus)\n- Basic computer and typing skills\n- Willing to work in shifts',
  criteria:['Spoken English clarity','Listening and politeness','Handling an angry customer','Typing and computer basics','Shift and notice-period fit']},
 hotel:{label:'Hotel & Hospitality',must:['guest','front office'],nice:['housekeeping','food and beverage','hospitality'],years:0,
  jd:'We are hiring Hospitality Associates.\n\nResponsibilities:\n- Welcome and assist guests\n- Keep service standards and cleanliness\n- Work with the team during busy hours\n\nRequirements:\n- Polite, well-groomed, good communication\n- Willing to work in shifts and on weekends',
  criteria:['Grooming and warmth','Guest handling','Teamwork under pressure','Communication','Availability for shifts']},
 cabin:{label:'Cabin Crew / Air Hostess',must:['communication','customer service'],nice:['hospitality','first aid','languages'],years:0,
  jd:'We are hiring Cabin Crew trainees.\n\nRequirements:\n- Good communication and a calm manner\n- Willingness to relocate and work irregular hours\n- Meets the airline height, age and medical rules (check the airline notice)',
  criteria:['Communication','Calm in emergencies','Service attitude','Teamwork','Grooming and presence']},
 airport:{label:'Airport Ground Staff',must:['customer service','communication'],nice:['check-in','baggage','computer'],years:0,
  jd:'We are hiring Ground Staff for check-in and passenger assistance.\n\nRequirements:\n- Good English and Hindi\n- Basic computer skills\n- Comfortable with shift duty and standing for long hours',
  criteria:['Communication','Handling queues and stress','Rule following','Computer basics','Shift fit']},
 dataentry:{label:'Data Entry / Back Office',must:['typing','excel'],nice:['ms office','accuracy'],years:0,
  jd:'We are hiring Data Entry Operators.\n\nResponsibilities:\n- Enter data accurately and on time\n- Check records for mistakes\n\nRequirements:\n- Typing speed 25+ WPM with good accuracy\n- Basic Excel',
  criteria:['Typing speed','Accuracy','Excel basics','Attention to detail','Reliability']},
 sales:{label:'Sales / Retail Executive',must:['sales','communication'],nice:['retail','target','customer service'],years:0,
  jd:'We are hiring Sales Executives.\n\nResponsibilities:\n- Greet customers and explain products\n- Meet monthly targets\n- Keep the counter and stock tidy\n\nRequirements:\n- Good communication\n- Target-driven attitude',
  criteria:['Communication','Customer handling','Target mindset','Product learning','Honesty']},
 itsupport:{label:'IT Support / Helpdesk',must:['troubleshooting','windows'],nice:['networking','ticketing','hardware'],years:1,
  jd:'We are hiring IT Support Executives.\n\nResponsibilities:\n- Fix desktop, laptop and printer issues\n- Log and close tickets\n\nRequirements:\n- Windows and basic networking knowledge\n- Clear communication with non-technical users',
  criteria:['Troubleshooting approach','Technical basics','Communication with users','Ticket discipline','Learning attitude']},
 accounts:{label:'Accounts / Finance Assistant',must:['tally','accounting'],nice:['gst','excel','tds'],years:1,
  jd:'We are hiring Accounts Assistants.\n\nResponsibilities:\n- Voucher entry and reconciliation\n- Support GST and month-end work\n\nRequirements:\n- Tally and Excel\n- Accuracy and honesty',
  criteria:['Accounting basics','Tally and Excel','Accuracy','Deadlines','Integrity']},
 driver:{label:'Driver / Logistics',must:['driving license'],nice:['route','delivery','vehicle maintenance'],years:1,
  jd:'We are hiring Drivers.\n\nRequirements:\n- Valid driving licence (check original)\n- Knows local routes, punctual, safe driver\n- Clean driving record',
  criteria:['Licence check','Safety attitude','Route knowledge','Punctuality','Behaviour with customers']},
 admin:{label:'Admin / Office Assistant',must:['ms office','communication'],nice:['filing','coordination','email'],years:0,
  jd:'We are hiring Office Assistants.\n\nResponsibilities:\n- Handle reception, files and basic office coordination\n\nRequirements:\n- Basic MS Office, good communication, organised',
  criteria:['Communication','Organisation','Computer basics','Reliability','Teamwork']},
 uae_retail:{label:'UAE: Retail / Sales Associate',must:['sales','customer service'],nice:['retail','arabic','english','hindi','pos'],years:0,
  jd:'We are hiring Retail Sales Associates for a store in the UAE.\n\nResponsibilities:\n- Welcome and assist customers of many nationalities\n- Keep displays and stock tidy\n- Handle billing\n\nRequirements:\n- Good spoken English (Arabic, Hindi or Urdu is a plus)\n- Customer-friendly and able to stand for long shifts\n\nAdd salary, visa and housing terms yourself as per UAE rules.',
  criteria:['Communication','Customer handling','Teamwork across cultures','Stamina and shift fit','Honesty with cash and stock']},
 uae_hospitality:{label:'UAE: Hotel / Restaurant Staff',must:['guest','service'],nice:['food and beverage','housekeeping','front office','english'],years:0,
  jd:'We are hiring Hospitality Staff for a hotel or restaurant in the UAE.\n\nResponsibilities:\n- Welcome guests and serve with care\n- Keep service and hygiene standards\n\nRequirements:\n- Good English, polite and well-groomed\n- Willing to work shifts\n\nAdd salary, visa and accommodation terms yourself as per UAE rules.',
  criteria:['Guest warmth','Handling complaints','Hygiene and safety','Communication','Shift fit']},
 uae_driver:{label:'UAE: Driver / Delivery',must:['driving license'],nice:['delivery','route','vehicle maintenance'],years:1,
  jd:'We are hiring Delivery Drivers in the UAE.\n\nRequirements:\n- Valid driving licence for the vehicle type (check the original; UAE licence or convertible foreign licence as per rules)\n- Knows routes, punctual, safe driver\n\nAdd salary, visa and vehicle terms yourself as per UAE rules.',
  criteria:['Licence check','Safety attitude','Route knowledge','Punctuality','Customer behaviour']},
 uae_security:{label:'UAE: Security / Front Desk',must:['security'],nice:['reception','cctv','first aid','english'],years:0,
  jd:'We are hiring Security and Front Desk staff in the UAE.\n\nResponsibilities:\n- Control entry, keep logs, report incidents\n\nRequirements:\n- Alert, honest, good communication\n- Any required licences or training as per UAE rules (please check)\n\nAdd salary and visa terms yourself.',
  criteria:['Alertness','Rule following','Communication','Calm under pressure','Honesty']}};
const MSG={
 invite:{en:'Hello {name}, this is {company}. We are hiring for {role}. Please complete a short online screening (about {min} minutes, voice answers on your phone): {link}\nIt is free for you. Thank you.',
  hinglish:'Namaste {name}, main {company} se. Hum {role} ke liye hire kar rahe hain. Please yeh chhota online screening complete karein (lagbhag {min} minute, phone par bolkar jawab): {link}\nAapke liye free hai. Dhanyavaad.',
  ar:'مرحبًا {name}، نحن {company}. نبحث عن {role}. يرجى إكمال مقابلة قصيرة عبر الإنترنت (حوالي {min} دقائق، إجابات صوتية من هاتفك): {link}\nمجانية لك. شكرًا.'},
 interview:{en:'Hello {name}, thank you for applying. We would like to invite you for an interview for {role} on {date} at {time}. Place: {place}. Please bring your ID and resume. Reply YES to confirm.',
  hinglish:'Namaste {name}, apply karne ke liye dhanyavaad. Hum aapko {role} ke interview ke liye bulana chahte hain: {date}, {time}. Jagah: {place}. Apna ID aur resume saath layein. Confirm karne ke liye YES likhein.',
  ar:'مرحبًا {name}، شكرًا لتقديمك. نود دعوتك لمقابلة وظيفة {role} بتاريخ {date} الساعة {time}. المكان: {place}. يرجى إحضار الهوية والسيرة الذاتية. اكتب نعم للتأكيد.'},
 reminder:{en:'Hello {name}, a reminder about your interview for {role} on {date} at {time}. Place: {place}. See you there.',
  hinglish:'Namaste {name}, {role} ke interview ka reminder: {date}, {time}. Jagah: {place}. Milte hain.',
  ar:'مرحبًا {name}، تذكير بمقابلتك لوظيفة {role} بتاريخ {date} الساعة {time}. المكان: {place}.'},
 reject:{en:'Hello {name}, thank you for your time. We will not be moving ahead with your application for {role} right now. We wish you the best and will keep your details in mind for future roles.',
  hinglish:'Namaste {name}, aapke samay ke liye dhanyavaad. Abhi hum {role} ke liye aapki application aage nahi badha rahe hain. Aapko shubhkamnayein.',
  ar:'مرحبًا {name}، شكرًا لوقتك. لن نتابع طلبك لوظيفة {role} في الوقت الحالي. نتمنى لك التوفيق.'},
 offer:{en:'Hello {name}, we are happy to share that you are selected for {role}. Our team will send the offer letter and joining details shortly.',
  hinglish:'Namaste {name}, khushi ki baat hai ki aap {role} ke liye select ho gaye hain. Offer letter aur joining details jaldi bhej di jayengi.',
  ar:'مرحبًا {name}، يسعدنا إبلاغك بأنه تم اختيارك لوظيفة {role}. سيصلك خطاب العرض وتفاصيل الانضمام قريبًا.'}};
function offerLetter(f){return `${f.company||'[Company name]'}\n[Company address]\n\nDate: ${f.date||'[Date]'}\n\nTo,\n${f.name||'[Candidate name]'}\n\nSubject: Offer of employment - ${f.role||'[Job title]'}\n\nDear ${f.name||'[Candidate name]'},\n\nWe are pleased to offer you the position of ${f.role||'[Job title]'} at ${f.company||'[Company name]'}. Your expected joining date is ${f.joining||'[Joining date]'} and your place of work will be ${f.place||'[Location]'}.\n\nYour compensation, working hours, probation period, notice period and benefits are as discussed and will be listed in the annexure: [add details]. This offer depends on satisfactory reference and document verification.\n\nPlease sign and return a copy of this letter to confirm your acceptance by ${f.accept||'[Date]'}.\n\nWe look forward to welcoming you.\n\nSincerely,\n${f.signer||'[Name, designation]'}\n${f.company||'[Company name]'}\n\nAccepted by: ____________________   Date: ____________\n\nNote: this is a general template, not legal advice. Please check it against the labour rules that apply to you.`}
function refCheck(f){return `Reference check - ${f.name||'[Candidate name]'} (${f.role||'[Role]'})\nReferee name / designation / company: ______________________\nPhone: ____________   Date and time of call: ____________\n\nBefore asking: say who you are, and that the candidate has given their name as a reference. Ask only job-related questions. Note exact words.\n\n1. How do you know the candidate, and for how long? ______________\n2. What was their job title and what did they do? ______________\n3. Dates of employment (from / to): ______________\n4. How was their attendance and punctuality? ______________\n5. What are their main strengths? ______________\n6. What should they improve? ______________\n7. How did they work with team members and customers? ______________\n8. Why did they leave? ______________\n9. Would you hire them again? (Yes / No / Depends) ______________\n10. Anything else we should know? ______________\n\nCalled by: ____________   Outcome: Positive / Mixed / Negative`}
function scorecard(role,criteria){const rows=criteria.map((c,i)=>`<tr><td>${i+1}</td><td>${esc(c)}</td><td></td><td></td><td></td></tr>`).join('');
 return `<h2>Interview scorecard - ${esc(role)}</h2><p>Candidate: ______________________ Interviewer: ______________________ Date: __________</p><p>Rate each item 1 (weak) to 5 (strong). Write one line of evidence. Score the answer you heard, not the person.</p><table border="1" cellspacing="0" cellpadding="8" style="width:100%;border-collapse:collapse"><tr><th>#</th><th>Skill</th><th>Score (1-5)</th><th>Evidence / notes</th><th>Red flag?</th></tr>${rows}</table><p>Total: ______ / ${criteria.length*5}</p><p>Decision: Hire / Hold / Reject &nbsp; Signature: ______________</p>`}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fill(tpl,v){return tpl.replace(/\{(\w+)\}/g,(m,k)=>v[k]!=null&&v[k]!==''?v[k]:m)}
function ics(o){const z=n=>String(n).padStart(2,'0'),f=d=>d.getUTCFullYear()+z(d.getUTCMonth()+1)+z(d.getUTCDate())+'T'+z(d.getUTCHours())+z(d.getUTCMinutes())+'00Z';
 const s=new Date(o.start),e=new Date(s.getTime()+(o.mins||30)*60000),esc2=x=>String(x||'').replace(/[\\;,]/g,m=>'\\'+m).replace(/\n/g,'\\n');
 return ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//MockRep//EN','BEGIN:VEVENT','UID:'+Date.now()+Math.random().toString(36).slice(2)+'@mockrep','DTSTAMP:'+f(new Date()),'DTSTART:'+f(s),'DTEND:'+f(e),'SUMMARY:'+esc2(o.title),'LOCATION:'+esc2(o.place),'DESCRIPTION:'+esc2(o.desc),'END:VEVENT','END:VCALENDAR'].join('\r\n')}
return{ROLES,MSG,offerLetter,refCheck,scorecard,fill,ics,esc}})();
