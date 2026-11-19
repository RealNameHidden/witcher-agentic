import type {TraceEvent} from './demo';
export const agentIds=['MagenticManager','PotionAgent','OilAgent','RitualAgent'];
export const agentNames:Record<string,string>={MagenticManager:'The Ringmaster',PotionAgent:'Potion Agent',OilAgent:'Oil Agent',RitualAgent:'Ritual Agent'};
const toolLabels:Record<string,string>={inspect_bestiary:'Checking the monster’s weaknesses',inspect_inventory:'Checking your supplies',read_witcher_potion_lore:'Reading potion references',read_witcher_oil_lore:'Reading oil references',read_witcher_ritual_and_curse_lore:'Checking rituals and curses'};
export type Assignment={id:string;title:string;text:string;target?:string;targets?:string[];phase?:string;reason?:string;satisfied?:boolean};
export function decision(event:TraceEvent):Assignment{
  if(event.phase){return {id:event.id,title:event.title,text:event.text||'',phase:event.phase,targets:event.targets,satisfied:event.phase==='review'};}
  try{
    const ledger=JSON.parse(event.text||'');
    if(ledger&&typeof ledger==='object'&&ledger.next_speaker){
      const target=typeof ledger.next_speaker.answer==='string'?ledger.next_speaker.answer:undefined;
      const satisfied=ledger.is_request_satisfied?.answer===true;
      return {id:event.id,target,satisfied,title:satisfied?'The evidence is ready. Writing the final plan.':`Assignment → ${agentNames[target||'']||target||'specialist'}`,text:String(ledger.instruction_or_question?.answer||'Review the collected evidence.'),reason:typeof ledger.next_speaker.reason==='string'?ledger.next_speaker.reason:undefined};
    }
  }catch{/* Plans and older replays carry plain text. */}
  return {id:event.id,title:event.title,text:event.text||''};
}
export function pipelineState(events:TraceEvent[],running:boolean){
  const final=events.findLast(e=>e.kind==='final');
  const failed=events.some(e=>e.kind==='error');
  const turns=events.filter(e=>e.kind==='agent_start'||e.kind==='agent_end');
  const lastByAgent=Object.fromEntries(agentIds.map(id=>[id,turns.findLast(e=>e.agent===id)]));
  const activeAgents=running&&!final&&!failed?agentIds.filter(id=>lastByAgent[id]?.kind==='agent_start'):[];
  const active=activeAgents.at(-1);
  const assignments=events.filter(e=>e.kind==='decision').map(decision);
  const latest=assignments.at(-1);
  const lastSpecialist=turns.findLast(e=>e.agent!=='MagenticManager'&&e.kind==='agent_end');
  const managerTask=latest?.phase==='review'?'Reviewing all three specialists and writing the final plan':latest?.satisfied?'Writing the final plan':!assignments.length?'Planning the hunt':lastSpecialist?`Reviewing ${agentNames[lastSpecialist.agent]||lastSpecialist.agent}’s findings`:'Assigning parallel research';
  const activityByAgent=Object.fromEntries(activeAgents.map(id=>{
    const tool=events.findLast(e=>e.agent===id&&e.kind==='tool_start'&&!events.some(done=>done.call_id===e.call_id&&(done.kind==='tool_end'||done.kind==='tool_error')));
    return [id,tool?(toolLabels[tool.title]||tool.title):id==='MagenticManager'?managerTask:'Preparing a recommendation'];
  }));
  const activityText=activeAgents.length>1?'Independent research is running at the same time.':activityByAgent[active||''];
  const statuses=Object.fromEntries(agentIds.map(id=>[id,activeAgents.includes(id)?'working':lastByAgent[id]?.kind==='agent_end'?'done':lastByAgent[id]?'stopped':'waiting']));
  return {final,failed,active,activeAgents,assignments,latest,activityText,activityByAgent,statuses,managerTask};
}
