// v2 contract and planner. base.js is the pinned, reviewed Recall Flow validator.
import * as base from './base.js';
import {safeParse} from './safe-json.js';
export {safeParse};
export const VERSION='2.0';
export const {canonical,clone,keyQ,packKey,grade,safeFilename,validateAttachment,validateQuestion}=base;
export const emptyState=()=>({schema_version:VERSION,kind:'backup',packs:[],sessions:[],assessments:[],plans:[],attachments:[]});
const fail=m=>{throw Error(m)};
const check=(ok,m)=>ok||fail(m);
const utcDate=x=>new Date(x).toISOString().slice(0,10);
const norm=x=>x.replace(/\s+/gu,' ').trim();
const timestamp=x=>typeof x==='string'&&/(Z|[+-]\d\d:\d\d)$/.test(x)&&Number.isFinite(Date.parse(x));
function safeTree(x,depth=0){check(depth<=64,'JSON层级过深');if(x&&typeof x==='object'){check(!Array.isArray(x)||x.length<=5000,'数组过长');for(const [k,v]of Object.entries(x)){check(!['__proto__','constructor','prototype'].includes(k),'禁止的JSON键');safeTree(v,depth+1)}}else if(typeof x==='number')check(Number.isFinite(x),'禁止非有限数值')}
function sourceKey(s){return `${s.source_id}@${s.source_version}@${s.extraction_revision}`}
function packDetails(p){
 check(timestamp(p.created_at),'学习包created_at需要时区');
 for(const s of p.sources){
  check(/^[0-9a-f]{64}$/.test(s.source_version),'来源缺少原件SHA256');
  check(Number.isInteger(s.extraction_revision)&&s.extraction_revision>=1,'来源提取版本非法');
  check(typeof s.confidence==='number'&&s.confidence>=0&&s.confidence<=1&&typeof s.confirmed==='boolean','来源置信/确认状态非法');
  check(typeof s.extraction_method==='string'&&s.extraction_method.trim(),'来源缺少提取方式');
 }
 const refs=(rows)=>{check(Array.isArray(rows)&&rows.length>0,'知识点/卡片/题目必须有出处');for(const r of rows){const s=p.sources.find(s=>s.source_id===r.source_id);check(s&&s.source_version===r.source_version&&s.extraction_revision===r.extraction_revision,'来源版本不匹配');check(typeof r.excerpt==='string'&&norm(r.excerpt)&&norm(s.extracted_text).includes(norm(r.excerpt)),'引用不在提取文本中');check(s.extraction_status==='extracted'&&(s.confidence>=.85||s.confirmed),'资料待提取或低置信，须先确认');check(typeof r.locator==='string'&&r.locator.trim(),'缺少页码/区域/段落定位')}};
 for(const c of p.concepts){check(typeof c.summary==='string'&&c.summary.trim(),'知识点缺少整理摘要');refs(c.source_refs)}
 for(const x of [...p.cards,...p.questions]){refs(x.source_refs);if(x.available_on)check(/^\d{4}-\d{2}-\d{2}$/.test(x.available_on)&&utcDate(x.available_on)===x.available_on,'available_on非法')}
 for(const c of p.cards)if(c.type==='cloze')check((c.front.match(/\{\{c1::[^{}]+\}\}/g)||[]).length===1&&(c.front.match(/\{\{/g)||[]).length===1,'v2支持一个简单c1填空');
}
export function validateDoc(d){
 safeTree(d);check(d&&d.schema_version===VERSION,'需要schema_version 2.0；旧稿不会自动当新版导入');
 if(d.kind==='backup'){
  for(const k of ['packs','sessions','assessments','plans','attachments'])check(Array.isArray(d[k]),`缺少${k}`);
  for(const [k,kind]of [['packs','learning_pack'],['sessions','session'],['assessments','assessment'],['plans','plan']])for(const x of d[k]){check(x.kind===kind,'备份成员类型错误');validateDoc(x)}
  d.attachments.forEach(validateAttachment);return validateState(d);
 }
 base.validateDoc({...d,schema_version:base.VERSION});
 if(d.kind==='learning_pack')packDetails(d);
 if(d.kind==='session'){
  check(timestamp(d.started_at)&&timestamp(d.ended_at),'session时间须有时区');
  for(const a of d.attempts){check(timestamp(a.answered_at),'回答时间须有时区');if(a.assisted!==undefined)check(typeof a.assisted==='boolean','assisted必须为布尔值')}
 }
 if(d.kind==='assessment')check(timestamp(d.created_at),'评估时间须有时区');
 if(d.kind==='plan')check(timestamp(d.created_at),'计划时间须有时区');
 return d;
}
const unique=(xs,key,label)=>{const seen=new Set;for(const x of xs){const k=key(x);check(!seen.has(k),`${label}身份重复`);seen.add(k)}};
export function validateState(s){
 const qs=new Map,notes=new Map,sources=new Map,attempts=new Map;
 for(const [k,key]of [['packs',packKey],['sessions',x=>x.session_id],['assessments',x=>x.assessment_id],['plans',x=>x.plan_id],['attachments',x=>x.filename]])unique(s[k],key,k);
 for(const p of s.packs){for(const source of p.sources){const k=sourceKey(source);check(!sources.has(k)||canonical(sources.get(k))===canonical(source),'同一来源提取版本内容冲突');sources.set(k,source)}for(const q of p.questions){const k=`${p.pack_id}:${keyQ(q)}`;check(!qs.has(k)||canonical(qs.get(k))===canonical(q),'改题必须升级question.version');qs.set(k,q)}for(const c of p.cards){const k=`${p.pack_id}:${c.note_id}`;check(!notes.has(k)||notes.get(k)===c.type,'同一note_id禁止Basic/Cloze换型');notes.set(k,c.type)}}
 for(const session of s.sessions){const p=s.packs.find(p=>p.pack_id===session.pack_id&&p.revision===session.pack_revision);check(p,'回答所用学习包版本缺失');for(const a of session.attempts){check(!attempts.has(a.attempt_id),'attempt_id跨session重复');check(p.questions.some(q=>canonical(q)===canonical(a.question_snapshot)),'原题快照与归档版本不符');attempts.set(a.attempt_id,{a,session})}}
 const assessed=new Map;
 for(const e of [...s.assessments].sort((a,b)=>Date.parse(a.created_at)-Date.parse(b.created_at))){
  check(e.session_ids.every(id=>s.sessions.some(s=>s.session_id===id)),'评估缺少session');
  for(const r of e.results){const t=attempts.get(r.attempt_id);check(t&&e.session_ids.includes(t.session.session_id),'评估引用未知attempt');check(t.a.question_snapshot.kind==='open','不得用AI覆盖选择题确定判分');check(t.a.response.includes(r.evidence_quote),'评估引用必须来自原答');check(Date.parse(e.created_at)>=Date.parse(t.a.answered_at),'评估早于回答');const prior=assessed.get(r.attempt_id);check(!prior||(e.supersedes===prior.assessment_id&&Date.parse(e.created_at)>Date.parse(prior.created_at)),'再次评估必须明确supersedes且时间更晚');assessed.set(r.attempt_id,e)}
 }
 for(const plan of s.plans){const p=s.packs.find(p=>p.pack_id===plan.pack_id&&p.revision===plan.pack_revision);check(p,'计划的学习包缺失');check(utcDate(p.created_at)<plan.date,'计划使用未来创建的学习包');for(const id of plan.evidence_session_ids){const t=s.sessions.find(x=>x.session_id===id&&x.pack_id===p.pack_id);check(t&&utcDate(t.ended_at)<plan.date,'计划证据时间越界')}for(const i of [...plan.items,...plan.deferred])check(i.item_type==='card'?p.cards.some(c=>c.note_id===i.item_id):p.questions.some(q=>q.question_id===i.item_id&&q.version===i.question_version),'计划引用未知内容')}
 return s;
}
export function importDoc(state,doc){
 validateDoc(doc);const next=clone(state);let added=0;
 const merge=(field,items,key)=>{for(const x of items){const prior=next[field].find(y=>key(x)===key(y));if(prior)check(canonical(prior)===canonical(x),`${field}不可变身份冲突；请使用新修订`);else{next[field].push(clone(x));added++}}};
 const fields={learning_pack:['packs',packKey],session:['sessions',x=>x.session_id],assessment:['assessments',x=>x.assessment_id],plan:['plans',x=>x.plan_id]};
 if(doc.kind==='backup'){for(const [field,key]of Object.values(fields))merge(field,doc[field],key);merge('attachments',doc.attachments,x=>x.filename)}else{check(fields[doc.kind],'不支持的文档');const [field,key]=fields[doc.kind];merge(field,[doc],key)}
 validateState(next);return {state:next,added};
}
export function loadText(state,text){return importDoc(state,safeParse(text))}
export const latestPacks=s=>s.packs.filter(p=>!s.packs.some(q=>q.pack_id===p.pack_id&&q.revision>p.revision));
export function evidence(s,packId){const out=[];const evaluations=new Map;for(const e of [...s.assessments].sort((a,b)=>Date.parse(a.created_at)-Date.parse(b.created_at)))for(const r of e.results)evaluations.set(r.attempt_id,{...r,evaluator:e.evaluator,assessment_id:e.assessment_id});for(const sess of s.sessions.filter(x=>x.pack_id===packId))for(const a of sess.attempts){const assessment=evaluations.get(a.attempt_id);out.push({...a,session_id:sess.session_id,effective_status:a.assisted?'ungradable':assessment?.status||a.grade.status,assessment})}return out.sort((a,b)=>Date.parse(a.answered_at)-Date.parse(b.answered_at)||a.attempt_id.localeCompare(b.attempt_id))}
export function conceptStats(s,p){const ev=evidence(s,p.pack_id);return p.concepts.map(c=>{const rows=ev.filter(a=>a.question_snapshot.concept_ids.includes(c.concept_id));const graded=rows.filter(a=>['correct','incorrect','partial'].includes(a.effective_status));const last=graded.at(-1)||rows.at(-1);const recent=graded.slice(-6),failed=recent.filter(a=>['incorrect','partial'].includes(a.effective_status)),failedDays=new Set(failed.map(a=>utcDate(a.answered_at)));let successDays=new Set;for(const a of [...recent].reverse()){if(a.effective_status!=='correct')break;successDays.add(utcDate(a.answered_at))}const correct=graded.filter(a=>a.effective_status==='correct');const days=new Set(correct.map(a=>utcDate(a.answered_at)));let status='unseen';if(rows.length){if(!graded.length)status='pending';else if(failedDays.size>=2&&successDays.size<2)status=last.effective_status==='correct'?'recovering':'weak';else if(last.effective_status!=='correct')status='check';else if(last.confidence<=2)status='uncertain';else if(days.size>=3&&recent.slice(-3).length===3&&recent.slice(-3).every(a=>a.effective_status==='correct'&&a.confidence>=3))status='stable';else status='improving'}return {...c,rows,last,correct:correct.length,status,failure_days:failedDays.size,pending:rows.filter(a=>['pending','ungradable'].includes(a.effective_status)).map(a=>a.attempt_id)}})}
const hash=text=>{let a=2166136261,b=2654435761;for(const c of text){a=Math.imul(a^c.charCodeAt(0),16777619)>>>0;b=Math.imul(b^c.charCodeAt(0),2246822519)>>>0}return a.toString(16).padStart(8,'0')+b.toString(16).padStart(8,'0')};
export function generatePlan(s,p,day,budget=20){
 check(/^\d{4}-\d{2}-\d{2}$/.test(day)&&utcDate(day)===day,'计划日期非法');check(Number.isInteger(budget)&&budget>=1&&budget<=240,'预算1至240分钟');check(utcDate(p.created_at)<day,'没有截止日前可用的学习包');
 const past={...s,sessions:s.sessions.filter(x=>utcDate(x.ended_at)<day)};const pastIds=new Set(past.sessions.map(x=>x.session_id));past.assessments=s.assessments.filter(x=>utcDate(x.created_at)<day&&x.session_ids.every(id=>pastIds.has(id)));
 const stats=conceptStats(past,p),byId=new Map(stats.map(x=>[x.concept_id,x]));const rank={weak:0,check:1,recovering:2,uncertain:2,pending:3,improving:4,stable:4,unseen:5};const weak=new Set(stats.filter(c=>rank[c.status]<=3).map(c=>c.concept_id)),deps=new Set;
 const addDeps=id=>{for(const d of byId.get(id).prerequisites)if(!deps.has(d)){deps.add(d);addDeps(d)}};for(const id of weak)addDeps(id);
 const ordered=[],seen=new Set;const visit=c=>{if(seen.has(c.concept_id))return;seen.add(c.concept_id);for(const id of c.prerequisites)visit(byId.get(id));ordered.push(c)};[...stats].sort((a,b)=>rank[a.status]-rank[b.status]||a.concept_id.localeCompare(b.concept_id)).forEach(visit);
 const items=[],deferred=[],added=new Set,blocked=new Set;let used=0;
 const qLatest=p.questions.filter(q=>!p.questions.some(x=>x.question_id===q.question_id&&x.version>q.version));
 for(const c of ordered){const prereq=deps.has(c.concept_id),hot=weak.has(c.concept_id);const unresolved=c.prerequisites.some(id=>['weak','check','recovering','pending','uncertain','unseen'].includes(byId.get(id).status));const age=c.last?Math.floor((Date.parse(day)-Date.parse(utcDate(c.last.answered_at)))/86400000):0;const interval=c.status==='stable'?4:c.status==='improving'?2:1;const due=c.last&&age>=interval;
  if(!prereq&&!hot&&!due&&c.status!=='unseen')continue;
  const category=prereq||hot?'weakness':due?'due':'new';
  const reason=prereq?`前置知识 ${c.title} 优先复核，再处理依赖它的弱项`:c.status==='weak'?`至少两个不同日期存在错误证据，补练 ${c.title}`:c.status==='check'?`单次错误仅作为复核信号，不认定持续薄弱`:c.status==='recovering'?`最近已答对，正在改善；单次成功不足以永久掌握`:c.status==='pending'?`开放题/辅助回答待宿主AI评估，不当作答错`:c.status==='uncertain'?`正确性与信心分离，低信心安排检索`:due?`间隔${age}天，按${interval}天规则复习；不等同Anki调度`:`剩余预算加入新内容 ${c.title}`;
  const candidates=[...p.cards.filter(x=>x.concept_ids.includes(c.concept_id)).map(x=>({item_type:'card',item_id:x.note_id,minutes:x.estimated_minutes,category,reason,_x:x})),...qLatest.filter(x=>x.concept_ids.includes(c.concept_id)).map(x=>({item_type:'question',item_id:x.question_id,question_version:x.version,minutes:x.estimated_minutes,category,reason,_x:x}))];
  for(const raw of candidates){const k=raw.item_type+':'+raw.item_id;if(added.has(k))continue;added.add(k);const {_x,...item}=raw;let why='';if(_x.available_on&&_x.available_on>day)why='内容尚未到可用日期';else if(c.prerequisites.some(id=>blocked.has(id)))why='前置内容因预算延后，依赖项一并延后';else if(category==='new'&&unresolved)why='前置知识尚无足够证据，延后新内容';else if(used+item.minutes>budget)why='超出剩余时间预算，明确延后';if(why){deferred.push({...item,reason:why});blocked.add(c.concept_id)}else{items.push(item);used+=item.minutes}}
 }
 const ev=evidence(past,p.pack_id),identity={pack:p,day,budget,sessions:past.sessions.filter(x=>x.pack_id===p.pack_id),assessments:past.assessments,items,deferred};
 return {schema_version:VERSION,kind:'plan',plan_id:`plan-${hash(canonical(identity))}`,pack_id:p.pack_id,pack_revision:p.revision,date:day,budget_minutes:budget,producer:'deterministic-local',created_at:day+'T00:00:00Z',evidence_session_ids:[...new Set(ev.map(a=>a.session_id))],items,deferred};
}
export const displayStatus={weak:'多日证据需补练',check:'单次错误待复核',recovering:'改善中仍需验证',uncertain:'答对但信心不足',pending:'待外部评估',improving:'正在巩固',stable:'多日稳定证据',unseen:'尚未练习'};
