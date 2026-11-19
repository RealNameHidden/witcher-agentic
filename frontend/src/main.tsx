import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {ArrowDown,ArrowRight,Check,ChevronDown,FlaskConical,Layers,LoaderCircle,Play,RefreshCw,Sparkles,Square,Swords,WandSparkles} from 'lucide-react';
import Markdown from 'react-markdown';
import {demoEvents,type TraceEvent} from './demo';
import {agentNames,pipelineState} from './pipeline';
import './hunt.css';

const specialists=[
  {id:'PotionAgent',label:'Potions',nickname:'The Bottle Goblin',icon:FlaskConical,color:'green',job:'Find a potion you actually have.',quip:'Side effects? Character building.'},
  {id:'OilAgent',label:'Blade oils',nickname:'The Blade Buff',icon:Swords,color:'blue',job:'Match the monster to the right oil.',quip:'Polish first. Stab later.'},
  {id:'RitualAgent',label:'Rituals & curses',nickname:'The Hexpert',icon:WandSparkles,color:'purple',job:'Check whether a ritual makes sense.',quip:'Probably not a curse. Probably.'},
];
type Health={provider:string;model:string;ready:boolean;detail:string;access_required?:boolean};
function App(){
  const [events,setEvents]=useState<TraceEvent[]>([]);
  const [monster,setMonster]=useState('Katakan');
  const [mode,setMode]=useState<'live'|'demo'>('live');
  const [running,setRunning]=useState(false);
  const [health,setHealth]=useState<Health>();
  const [error,setError]=useState('');
  const [accessKey,setAccessKey]=useState('');
  const [keyOpen,setKeyOpen]=useState(true);
  const [elapsed,setElapsed]=useState(0);
  const abort=useRef<AbortController|null>(null);
  const timer=useRef<ReturnType<typeof setInterval>|null>(null);
  const runToken=useRef(0);
  const state=pipelineState(events,running);
  async function refresh(){try{const r=await fetch('/api/health');if(!r.ok)throw Error();setHealth(await r.json());}catch{setHealth({provider:'offline',model:'',ready:false,detail:'The server is not responding. Refresh the connection to retry.'});}}
  useEffect(()=>{void refresh();return()=>{abort.current?.abort();if(timer.current)clearInterval(timer.current);};},[]);
  useEffect(()=>{if(!running)return;const start=Date.now();const tick=setInterval(()=>setElapsed(Math.floor((Date.now()-start)/1000)),1000);return()=>clearInterval(tick);},[running]);
  function stop(){runToken.current++;abort.current?.abort();if(timer.current)clearInterval(timer.current);timer.current=null;setRunning(false);}
  async function start(demo=false){
    stop();const token=++runToken.current;setEvents([]);setError('');setElapsed(0);setKeyOpen(false);setMode(demo?'demo':'live');setRunning(true);
    if(demo){let index=0;timer.current=setInterval(()=>{const event=demoEvents[index++];setEvents(old=>[...old,event]);if(index===demoEvents.length){if(timer.current)clearInterval(timer.current);timer.current=null;setRunning(false);}},950);return;}
    const controller=new AbortController();abort.current=controller;
    try{
      const response=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json',...(accessKey?{'Authorization':`Bearer ${accessKey}`}:{})},body:JSON.stringify({monster:monster.trim()}),signal:controller.signal});
      if(!response.ok)throw Error((await response.json()).error||'Could not start the hunt.');
      if(!response.body)throw Error('Streaming is unavailable in this browser.');
      const reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';let completed=false;
      function accept(line:string){if(!line.trim())return;const event=JSON.parse(line) as TraceEvent;if(token!==runToken.current)return;setEvents(old=>[...old,event]);if(event.kind==='error'){setError(event.text||'Run failed.');completed=true;}if(event.kind==='final')completed=true;}
      while(true){const {done,value}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const lines=buffer.split('\n');buffer=lines.pop()||'';for(const line of lines)accept(line);}
      buffer+=decoder.decode();if(buffer.trim())accept(buffer);
      if(!completed)throw Error('The connection closed before the plan was finished. Try again.');
    }catch(e){if(!controller.signal.aborted&&token===runToken.current)setError(e instanceof Error?e.message:'Connection failed.');}
    finally{if(token===runToken.current)setRunning(false);}
  }
  const managerWorking=state.active==='MagenticManager';
  const currentTitle=state.activeAgents.length>1?`${state.activeAgents.length} specialists are working in parallel`:state.active?`${agentNames[state.active]||state.active} is working`:running?'Starting the hunt…':state.final?'Your encounter plan is ready':error?'The hunt was interrupted':events.length?'Hunt stopped':'Ready when you are';
  const managerReply=events.findLast(e=>e.agent==='MagenticManager'&&e.kind==='agent_end'&&e.text);
  return <main className="hunt-app">
    <header className="masthead"><span>THE WITCHER <b>✦</b> DEPARTMENT OF BAD IDEAS</span><details className="connection"><summary><i className={health?.ready?'online':''}/>{health?.ready?'Model connected':'Connection'}<ChevronDown size={13}/></summary><div><strong>{health?.provider} · {health?.model}</strong><p>{health?.detail}</p><button onClick={()=>void refresh()}><RefreshCw size={13}/>Refresh connection</button></div></details></header>
    <section className="intro"><span className="eyebrow">KAER MORHEN · CONTRACT PLANNING OFFICE</span><h1>One monster. <em>One plan.</em></h1><p>Watch the committee do the dangerous thinking.</p></section>
    <section className="contract" aria-label="Start an encounter"><div className="contract-controls"><Swords size={28}/><label htmlFor="monster"><span>WHO ARE WE HUNTING?</span><input id="monster" value={monster} maxLength={120} disabled={running} onChange={e=>setMonster(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!running&&health?.ready&&monster.trim()&&(!health?.access_required||accessKey.trim()))void start();}}/></label>{running?<button className="main-button stop" onClick={stop}><Square size={15}/>Stop hunt</button>:<button className="main-button" disabled={!health?.ready||!monster.trim()||(health?.access_required&&!accessKey.trim())} onClick={()=>void start()}><Play size={16}/>Start live hunt<ArrowRight size={17}/></button>}<button className="replay-button" disabled={running} onClick={()=>void start(true)}>Try a sample</button></div>
      {health?.access_required&&<details className="key-settings" open={keyOpen} onToggle={e=>setKeyOpen(e.currentTarget.open)}><summary>{accessKey?'Access key entered':'Unlock live hunts with your access key'}<ChevronDown size={12}/></summary><label htmlFor="access-key">Test access key<input id="access-key" type="password" autoComplete="off" value={accessKey} onChange={e=>setAccessKey(e.target.value)} placeholder="Paste your key"/></label><small>Protects paid model calls. Sample replay needs no key.</small></details>}
      {!health?.ready&&<p className="connection-note">{health?.detail||'Checking connection…'} You can still try a sample.</p>}
    </section>
    <section className={`pipeline-board ${running?'is-running':''}`} aria-labelledby="pipeline-title">
      <div className="section-heading"><div><span className="section-number">01</span><h2 id="pipeline-title">The hunt, as it happens</h2></div><span className="mode-label">{mode==='demo'?'SAMPLE REPLAY · NO MODEL CALLS':state.final?'HUNT COMPLETE':'LIVE AGENT PIPELINE'}</span></div>
      <div className={`now-banner ${running?'busy':''} ${state.final?'finished':''}`} role="status" aria-live="polite"><span className="now-symbol">{running?<LoaderCircle className="spin" size={26}/>:state.final?<Check size={27}/>:<Swords size={25}/>}</span><div><span className="overline">{running?'WORKING NOW':state.final?'ALL DONE':'HUNT STATUS'}</span><strong>{currentTitle}</strong><p>{running?(state.active?state.activityText:'Connecting to the agents'):state.final?'The manager has combined the specialists’ findings.':events.length?'Your partial work is still available below.':'Name a monster above, or try a sample to see the team in action.'}</p></div>{running&&mode==='live'&&<time>{elapsed}s</time>}</div>
      {state.final&&<a className="plan-jump" href="#decisions-title">Read the final decisions <ArrowDown size={15}/></a>}
      {error&&<div className="run-error" role="alert"><strong>The committee hit a snag.</strong><p>{error}</p></div>}
      <article className={`manager-card ${managerWorking?'working':''}`}><div className="manager-heading"><span className="character-icon gold"><Layers size={27}/></span><div><h3>The Ringmaster <small>Manager</small></h3><p>Assigns the work. Reviews the findings. Calls the shots.</p></div><span className={`state-badge ${managerWorking?'active':state.final?'done':''}`}>{managerWorking?<><LoaderCircle className="spin" size={15}/>Working now</>:state.final?<><Check size={15}/>Plan delivered</>:state.active?'Work delegated':'On standby'}</span></div>
        <div className="manager-message"><span className="overline">{state.latest?'LATEST MANAGER DECISION':managerWorking?'MANAGER AT WORK':'THE MANAGER’S DESK'}</span><strong>{state.latest?.title||(managerWorking?state.managerTask:'“Three specialists. Let’s keep them pointed at the same monster.”')}</strong>{state.latest?<div className="readable"><Markdown>{state.latest.text}</Markdown></div>:<p>{managerWorking?'The manager is preparing the plan. Its published assignment will appear here.':'The actual assignment and review updates will appear here during a run.'}</p>}{state.latest?.reason&&<p className="decision-reason"><b>Why this agent:</b> {state.latest.reason}</p>}</div>
        {state.assignments.length>1&&<details className="assignment-history"><summary>Earlier manager decisions ({state.assignments.length-1})<ChevronDown size={14}/></summary><ol>{state.assignments.slice(0,-1).map(item=><li key={item.id}><strong>{item.title}</strong><div className="readable"><Markdown>{item.text}</Markdown></div></li>)}</ol></details>}
      </article>
      <div className="handoff" aria-hidden="true"><ArrowDown size={21}/><span>{state.activeAgents.length>1?'Parallel research · manager waits for all three':state.active&&state.active!=='MagenticManager'?`${agentNames[state.active]} is still researching`:managerWorking?'Manager is planning or reviewing':'Plan → parallel research → manager review'}</span><ArrowDown size={21}/></div>
      <div className="specialist-row">{specialists.map(agent=>{
        const Icon=agent.icon;const status=state.statuses[agent.id];const working=status==='working';
        const response=events.findLast(e=>e.agent===agent.id&&e.kind==='agent_end'&&e.text);
        return <article key={agent.id} className={`specialist-card ${agent.color} ${status}`} aria-label={`${agentNames[agent.id]}: ${working?'working now':status==='done'?'findings ready':status==='stopped'?'stopped':'waiting'}`}>
          <div className="specialist-top"><span className={`character-icon ${agent.color}`}><Icon size={32}/><span className="eyes">••</span></span><span className={`state-badge ${working?'active':status==='done'?'done':''}`}>{working?<><LoaderCircle className="spin" size={15}/>WORKING NOW</>:status==='done'?<><Check size={15}/>Findings ready</>:status==='stopped'?'Stopped':'Waiting'}</span></div>
          <h3>{agent.label}</h3><span className="nickname">{agent.nickname}</span>
          <p className="specialist-job">{working?state.activityByAgent[agent.id]:status==='done'?'Research complete. Findings sent to the manager.':agent.job}</p>
          {working&&<div className="work-progress"><span/></div>}
          {response?<details className="findings" open><summary>Read findings<ChevronDown size={14}/></summary><div className="readable"><Markdown>{response.text||''}</Markdown></div></details>:<p className="quip">“{agent.quip}”</p>}
        </article>;
      })}</div>
      <p className="pipeline-caption">Specialists research in parallel. The manager reviews only after all three return. Highlighted cards show actual activity.</p>
    </section>
    <section className={`decisions-board ${state.final?'ready':''}`} aria-labelledby="decisions-title"><div className="section-heading"><div><span className="section-number">02</span><h2 id="decisions-title">{mode==='demo'?'Sample final decisions':'Final decisions'}</h2></div><Sparkles size={23}/></div>{state.final?<div className="final-answer readable"><Markdown>{state.final.text||''}</Markdown></div>:<div className="decision-placeholder"><span>Potions</span><span>Blade oils</span><span>Rituals & curses</span><p>{running?'The specialists are gathering evidence. The manager’s final plan will appear here.':'One clear encounter plan, once the team has done its homework.'}</p></div>}</section>
    <details className="technical-details"><summary>Behind the scenes <span>Tool calls & full execution log</span><ChevronDown size={16}/></summary><p>Recorded outputs and evidence, not private reasoning tokens.</p>{managerReply&&<details><summary>Latest manager output</summary><div className="readable"><Markdown>{managerReply.text||''}</Markdown></div></details>}<div className="raw-events">{events.length?events.map(event=><details key={event.id}><summary><time>+{event.elapsed.toFixed(1)}s</time><b>{agentNames[event.agent]||event.agent}</b><span>{event.title}</span></summary><pre>{event.text||event.kind.replaceAll('_',' ')}</pre></details>):<p>No events yet. Start a hunt to record them.</p>}</div></details>
    <footer><span>WITCHER MAGENTIC · THE COMMITTEE IS IN SESSION</span><span>{mode==='demo'?'Scripted sample. No model or wiki calls.':'Microsoft Agent Framework · Azure Foundry'}</span></footer>
  </main>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
