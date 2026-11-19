export type TraceEvent={id:string;kind:string;agent:string;title:string;text?:string;elapsed:number;call_id?:string;phase?:string;targets?:string[]};
const sample:Omit<TraceEvent,'id'|'elapsed'>[]=[
  {kind:'run_start',agent:'MagenticManager',title:'Sample encounter: Katakan'},
  {kind:'agent_start',agent:'MagenticManager',title:'Planning the research'},
  {kind:'agent_end',agent:'MagenticManager',title:'Research plan ready'},
  {kind:'decision',agent:'MagenticManager',title:'Research assigned to all three specialists',phase:'research',targets:['PotionAgent','OilAgent','RitualAgent'],text:'Sample manager plan — research these independently, at the same time:\n\n- **Potion Agent:** check weaknesses and available potions.\n- **Oil Agent:** check blade preparation and oil stock.\n- **Ritual Agent:** check whether there is evidence of a curse.\n\nI will review all three reports before writing the final plan.'},
  {kind:'agent_start',agent:'PotionAgent',title:'Researching potions'},
  {kind:'agent_start',agent:'OilAgent',title:'Researching blade oils'},
  {kind:'agent_start',agent:'RitualAgent',title:'Researching rituals and curses'},
  {kind:'tool_start',agent:'PotionAgent',title:'inspect_bestiary',call_id:'demo-bestiary',text:'{"monster_name":"Katakan"}'},
  {kind:'tool_start',agent:'OilAgent',title:'inspect_inventory',call_id:'demo-inventory',text:'{}'},
  {kind:'tool_start',agent:'RitualAgent',title:'read_witcher_ritual_and_curse_lore',call_id:'demo-ritual',text:'{}'},
  {kind:'tool_end',agent:'PotionAgent',title:'inspect_bestiary',call_id:'demo-bestiary',text:'Sample result: Katakan. Weaknesses include Black Blood and Vampire Oil.'},
  {kind:'tool_end',agent:'OilAgent',title:'inspect_inventory',call_id:'demo-inventory',text:'Sample inventory: Black Blood × 1, Vampire Oil × 1.'},
  {kind:'tool_end',agent:'RitualAgent',title:'read_witcher_ritual_and_curse_lore',call_id:'demo-ritual',text:'Sample reference only. This replay performs no actual wiki request.'},
  {kind:'agent_end',agent:'PotionAgent',title:'Potion findings ready',text:'Sample recommendation: Black Blood matches the sample bestiary. Live research must also verify stock and potion lore.'},
  {kind:'agent_end',agent:'OilAgent',title:'Oil findings ready',text:'Sample recommendation: Vampire Oil matches the target and is in stock. Live research should check game-specific oil mechanics.'},
  {kind:'agent_end',agent:'RitualAgent',title:'Ritual findings ready',text:'Sample assessment: this encounter does not establish a curse. Do not invent a ritual without evidence.'},
  {kind:'decision',agent:'MagenticManager',title:'Reviewing all three specialists',phase:'review',targets:['MagenticManager'],text:'All three specialists have returned. I am checking the findings together before composing the final plan.'},
  {kind:'agent_start',agent:'MagenticManager',title:'Reviewing and combining findings'},
  {kind:'agent_end',agent:'MagenticManager',title:'Final plan ready'},
  {kind:'final',agent:'MagenticManager',title:'Sample encounter plan',text:'### Potions\n**Black Blood** matches the sample bestiary weakness.\n\n### Blade oil\n**Vampire Oil** matches the sample target and is available.\n\n### Rituals & curses\n**No supported ritual.** No curse is established in this example.\n\nThis is a scripted parallel-workflow demonstration, not a wiki-verified or model-generated answer.'},
];
export const demoEvents:TraceEvent[]=sample.map((event,index)=>({...event,id:`demo-${index}`,elapsed:Number((index*.75).toFixed(2))}));
