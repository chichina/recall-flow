import fs from 'node:fs';
import {safeParse,emptyState,validateDoc,importDoc,latestPacks,generatePlan,conceptStats,evidence} from '../assets/web/core.js';
try{
 const req=safeParse(fs.readFileSync(0,'utf8'));let state=req.state||emptyState();validateDoc(state);let added=0;
 for(const d of req.documents||[]){const r=importDoc(state,d);state=r.state;added+=r.added}
 if(req.action==='merge'||req.action==='validate')process.stdout.write(JSON.stringify({state,added}));
 else if(req.action==='review'){
  const packs=state.packs.filter(p=>(!req.pack_id||p.pack_id===req.pack_id)&&new Date(p.created_at).toISOString().slice(0,10)<req.day);
  const pack=packs.sort((a,b)=>b.revision-a.revision)[0];if(!pack)throw Error('截止日前没有可用学习包');
  const past={...state,sessions:state.sessions.filter(s=>new Date(s.ended_at).toISOString().slice(0,10)<req.day)};
  const ids=new Set(past.sessions.map(s=>s.session_id));past.assessments=state.assessments.filter(e=>new Date(e.created_at).toISOString().slice(0,10)<req.day&&e.session_ids.every(id=>ids.has(id)));
  const plan=generatePlan(state,pack,req.day,req.budget||20),rows=evidence(past,pack.pack_id),stats=conceptStats(past,pack);
  const pending=rows.filter(a=>a.effective_status==='pending');
  const summary={schema_version:'2.0',kind:'review_evidence',pack_id:pack.pack_id,pack_revision:pack.revision,as_of:req.as_of,target_date:req.day,attempt_count:rows.length,actual_seconds:rows.reduce((n,a)=>n+a.elapsed_ms/1000,0),excluded_future_sessions:state.sessions.length-past.sessions.length,concepts:stats,pending_assessment:pending,planning_note:'确定性证据统计；语义评估与错因解释由宿主AI提供，自评不等于正确性。'};
  state=importDoc(state,plan).state;process.stdout.write(JSON.stringify({state,plan,summary,pack}));
 }else throw Error('unknown action');
}catch(e){process.stderr.write(String(e.message));process.exitCode=2}
