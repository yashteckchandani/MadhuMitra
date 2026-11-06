import {Text,View} from 'react-native';
import {Button,Card,Copy,Input} from '../services/ui';

type Question={key:string; label:string; type:'choice'|'multi'|'number'|'text'; options?:string[]; dependsOn?:string; when?:string; max?:number; min?:number};
const yesNo=['Yes','No'];
const ynd=['Yes','No',"Don't know"];
export const openingQuestions=[
  {key:'unconscious_or_weak',label:'Unconscious, sleepy, or very weak right now'},
  {key:'vomiting_breathing_or_pain',label:'Vomiting with fast or deep breathing, or severe stomach pain'},
  {key:'cold_sweat_or_weakness',label:'Cold sweat with shivering, or sudden weakness'},
  {key:'infected_foot_wound',label:'Festering or badly infected foot wound'},
];
export const symptoms:Question[]=[
 {key:'sugar_symptoms',label:'Sugar symptoms these days',type:'multi',options:['More thirst','Frequent urination','Much more hunger','Weight falling without trying']},
 {key:'other_symptoms',label:'Other problems these days',type:'multi',options:['Tired quickly','Blurred vision','Tingling or numbness','Repeated itching or fungal patches','Burning while urinating','None']},
 {key:'slow_healing_wound',label:'A wound ever took more than a week to heal?',type:'choice',options:ynd},
];
export const historyQuestions:Question[]=[
 {key:'sugar_tested_before',label:'Blood sugar tested before?',type:'choice',options:ynd},
 {key:'last_sugar_test',label:'Last blood sugar test (years ago)',type:'choice',options:['Under 1','1–3','3–5','5–10','10+',"Don't know"]},
 {key:'treatment_since',label:'On treatment since (years)',type:'choice',options:['Under 1','1–3','3–5','5–10','10+','Never diagnosed']},
 {key:'diabetes_medicine',label:'Currently on diabetes medicine?',type:'choice',options:yesNo},
 {key:'medicine_type',label:'Type of diabetes medicine',type:'choice',options:['Tablets','Insulin','Both'],dependsOn:'diabetes_medicine',when:'Yes'},
 {key:'high_bp',label:'Known high BP or taking BP medicine?',type:'choice',options:ynd},
 {key:'family_diabetes',label:'Family member with diabetes?',type:'choice',options:ynd},
 {key:'family_conditions',label:'Family member with high BP or heart trouble',type:'multi',options:['High BP','Heart attack or stroke','None',"Don't know"]},
 {key:'eye_check',label:'Last eye check (years ago)',type:'choice',options:['Under 1','1–2','2+','Never',"Don't know"]},
 {key:'tobacco',label:'Tobacco or paan masala use',type:'choice',options:['None','Smoke','Chew','Both']},
 {key:'tobacco_per_day',label:'Tobacco use per day',type:'number',min:0,max:500},
 {key:'alcohol',label:'Alcohol use',type:'choice',options:['Never','Sometimes','Daily']},
 {key:'walks_daily',label:'Walks daily?',type:'choice',options:['Yes','Sometimes','No']},
 {key:'barefoot',label:'Often walks barefoot outside?',type:'choice',options:yesNo},
];
export const womensQuestions:Question[]=[
 {key:'pregnant',label:'Pregnant?',type:'choice',options:yesNo},
 {key:'pregnancy_month',label:'Pregnancy month',type:'number',dependsOn:'pregnant',when:'Yes',min:1,max:9},
 {key:'pregnancy_sugar_test',label:'Sugar test in this pregnancy',type:'choice',options:['Done','Not yet',"Don't know"],dependsOn:'pregnant',when:'Yes'},
 {key:'past_pregnancy_sugar',label:'Past pregnancy with a sugar problem?',type:'choice',options:ynd},
 {key:'heavy_baby',label:'Baby born very heavy (about 4 kg or more)?',type:'choice',options:ynd},
 {key:'pregnancy_loss',label:'Earlier pregnancy ended on its own?',type:'choice',options:ynd},
 {key:'irregular_periods',label:'Periods very irregular or skipped?',type:'choice',options:ynd},
 {key:'recurrent_urine_infection',label:'Recurring urine infection or discharge?',type:'choice',options:ynd},
];
export const examination:Question[]=[
 {key:'pulse',label:'Pulse (per minute)',type:'number',min:1,max:300},
 {key:'height_feet',label:'Height (feet)',type:'number',min:0,max:8},
 {key:'height_inches',label:'Height (additional inches)',type:'number',min:0,max:11},
 {key:'waist_band',label:'Waist band (cm)',type:'choice',options:['80 or less','81–90','more than 90','90 or less','91–100','more than 100','No tape']},
 {key:'foot_exam',label:'Feet examination',type:'multi',options:['Wound or sore','Cracked skin between toes','Toes bent inward or shoes no longer fit','History of amputation','History of previous ulcer','None']},
 {key:'mouth_exam',label:'Mouth examination',type:'multi',options:['Bleeding gums or loose teeth','Pain','Dry mouth','Bad breath','Difficulty opening mouth or chewing','None']},
];
export function examinationForSex(sex:string):Question[]{return examination.map(q=>q.key!=='waist_band'?q:{...q,options:sex==='Female'?['80 or less','81–90','more than 90','No tape']:sex==='Male'?['90 or less','91–100','more than 100','No tape']:q.options})}
export const followUpQuestions:Question[]=[
 {key:'medicine_taken',label:'Medicine taken since the last visit?',type:'choice',options:yesNo},
 {key:'medicine_not_taken_reason',label:'If no, why?',type:'choice',options:['Cost','Forgot','Side-effects','Stopped'],dependsOn:'medicine_taken',when:'No'},
 {key:'new_feet_or_gums_problem',label:'New problem with feet or gums?',type:'choice',options:yesNo},
 {key:'low_episode',label:'Any low episode since the last visit?',type:'choice',options:yesNo},
 {key:'new_symptoms_text',label:'New symptoms in the patient’s own words',type:'text'},
];
export function validateAnswers(answers:Record<string,any>, questions:Question[]):string|null{
 for(const q of questions){const v=answers[q.key];if(q.type==='number'&&v!==undefined&&v!==null&&v!==''){if(!Number.isInteger(v)||v<(q.min??0)||v>(q.max??999999))return `Check ${q.label.toLowerCase()}.`;}}
 return null;
}
export function QuestionFields({questions,answers,onChange}:{questions:Question[];answers:Record<string,any>;onChange:(v:Record<string,any>)=>void}){
 return <>{questions.map(q=>{if(q.dependsOn&&answers[q.dependsOn]!==q.when)return null;const val=answers[q.key];if(q.type==='text'||q.type==='number')return <Input key={q.key} label={q.label} value={val===undefined||val===null?'':String(val)} keyboardType={q.type==='number'?'number-pad':'default'} onChangeText={(v:string)=>onChange({...answers,[q.key]:v===''?undefined:q.type==='number'?Number(v):v})}/>;
 return <Card key={q.key}><Text style={{fontWeight:'700',color:'#193a3a'}}>{q.label}</Text>{q.type==='multi'&&<Copy>Select all that apply.</Copy>}<View style={{gap:6}}>{q.options?.map(option=>{const selected=q.type==='multi'?(val||[]).includes(option):val===option;return <Button key={option} label={(selected?'✓ ':'')+option} secondary={!selected} onPress={()=>{const next={...answers};if(q.type==='multi'){const current:string[]=val||[];const exclusive=option==='None'||option==="Don't know";next[q.key]=selected?current.filter(x=>x!==option):exclusive?[option]:[...current.filter(x=>x!=='None'&&x!=="Don't know"),option]}else{next[q.key]=selected?undefined:option;if(q.key==='pregnant'&&next[q.key]!=='Yes'){delete next.pregnancy_month;delete next.pregnancy_sugar_test}if(q.key==='diabetes_medicine'&&next[q.key]!=='Yes')delete next.medicine_type;if(q.key==='medicine_taken'&&next[q.key]!=='No')delete next.medicine_not_taken_reason}onChange(next)}}/>})}</View></Card>})}</>
}
