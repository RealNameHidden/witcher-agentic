import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from 'typescript';
const source=await readFile(new URL('../src/pipeline.ts',import.meta.url),'utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const {pipelineState,decision}=await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
let sequence=0;
const event=(kind,agent='MagenticManager',extra={})=>({id:String(++sequence),kind,agent,title:kind,elapsed:sequence,...extra});
test('manager work is visible before the first plan',()=>{
  const state=pipelineState([event('agent_start')],true);
  assert.equal(state.active,'MagenticManager');assert.equal(state.activityText,'Planning the hunt');
});
test('real progress ledger becomes a readable assignment and selection reason',()=>{
  const item=decision(event('decision','MagenticManager',{text:JSON.stringify({next_speaker:{answer:'OilAgent',reason:'Potions are covered; oil is not.'},instruction_or_question:{answer:'Check Vampire Oil stock.'},is_request_satisfied:{answer:false}})}));
  assert.equal(item.title,'Assignment → Oil Agent');assert.equal(item.target,'OilAgent');assert.equal(item.text,'Check Vampire Oil stock.');assert.equal(item.reason,'Potions are covered; oil is not.');
});
test('specialist stays highlighted through tool calls; completed peers stay done',()=>{
  const events=[event('agent_start','PotionAgent'),event('agent_end','PotionAgent'),event('agent_start','OilAgent'),event('tool_start','OilAgent',{title:'read_witcher_oil_lore',call_id:'oil-1'})];
  const state=pipelineState(events,true);
  assert.equal(state.active,'OilAgent');assert.equal(state.statuses.OilAgent,'working');assert.equal(state.statuses.PotionAgent,'done');assert.equal(state.activityText,'Reading oil references');
  events.push(event('tool_end','OilAgent',{call_id:'oil-1'}));assert.equal(pipelineState(events,true).activityText,'Preparing a recommendation');
});
test('manager visibly reviews after a specialist finishes',()=>{
  const state=pipelineState([event('decision','MagenticManager',{text:'Plan'}),event('agent_start','OilAgent'),event('agent_end','OilAgent'),event('agent_start')],true);
  assert.equal(state.active,'MagenticManager');assert.match(state.activityText,/Reviewing Oil Agent/);
});
test('stop and failure clear working indicators and preserve partial findings',()=>{
  const events=[event('agent_start','PotionAgent'),event('agent_end','PotionAgent'),event('agent_start','RitualAgent')];
  assert.equal(pipelineState(events,false).active,undefined);assert.equal(pipelineState(events,false).statuses.RitualAgent,'stopped');assert.equal(pipelineState(events,false).statuses.PotionAgent,'done');assert.equal(pipelineState([...events,event('error')],true).active,undefined);
});
test('final output clears spinners without marking unvisited specialists complete',()=>{
  const state=pipelineState([event('agent_start','PotionAgent'),event('agent_end','PotionAgent'),event('agent_start'),event('final','MagenticManager',{text:'Final plan'})],true);
  assert.equal(state.active,undefined);assert.equal(state.statuses.PotionAgent,'done');assert.equal(state.statuses.RitualAgent,'waiting');assert.equal(state.final.text,'Final plan');
});
test('plain plan text and malformed ledger data remain readable',()=>{
  assert.equal(decision(event('decision','MagenticManager',{text:'Ask the specialists.'})).text,'Ask the specialists.');assert.equal(decision(event('decision','MagenticManager',{text:'{"bad":'})).text,'{"bad":');
});
test('all three agents stay active and retain independent tool activity',()=>{
  const events=[event('agent_start','PotionAgent'),event('agent_start','OilAgent'),event('agent_start','RitualAgent'),event('tool_start','PotionAgent',{call_id:'p',title:'inspect_inventory'}),event('tool_start','RitualAgent',{call_id:'r',title:'read_witcher_ritual_and_curse_lore'})];
  const state=pipelineState(events,true);
  assert.equal(state.activeAgents.length,3);
  for(const name of ['PotionAgent','OilAgent','RitualAgent'])assert.equal(state.statuses[name],'working');
  assert.equal(state.activityByAgent.PotionAgent,'Checking your supplies');
  assert.equal(state.activityByAgent.RitualAgent,'Checking rituals and curses');
  events.push(event('agent_end','PotionAgent'));
  const next=pipelineState(events,true);
  assert.deepEqual(next.activeAgents,['OilAgent','RitualAgent']);
  assert.equal(next.statuses.PotionAgent,'done');
});
test('review phase is readable after the parallel fan-in',()=>{
  const state=pipelineState([event('decision','MagenticManager',{phase:'review',text:'All three reports returned.'}),event('agent_start')],true);
  assert.equal(state.latest.phase,'review');
  assert.match(state.managerTask,/all three/);
});
test('stopping concurrent research clears every active indicator',()=>{
  const events=['PotionAgent','OilAgent','RitualAgent'].map(name=>event('agent_start',name));
  assert.equal(pipelineState(events,false).activeAgents.length,0);
  assert.equal(Object.values(pipelineState(events,false).statuses).filter(s=>s==='working').length,0);
  assert.equal(pipelineState([...events,event('error')],true).activeAgents.length,0);
});
