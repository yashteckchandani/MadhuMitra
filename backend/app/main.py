import os,json,hashlib,hmac,secrets,tempfile,threading,uuid,re
from pathlib import Path
from datetime import date,datetime,timezone
from typing import Optional,List,Literal
from fastapi import FastAPI,HTTPException,Depends,Response,Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from dotenv import load_dotenv
from . import gemini
from .sehat import Enrollment, SehatRecord

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

D=Path(os.getenv('DATA_DIR',Path(__file__).resolve().parents[1]/'data')); lock=threading.RLock(); sessions={}
app=FastAPI(title='ASHA Diabetic Assist',version='1.0')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:3000').split(','),allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
def read(name):
 with open(D/name) as f:return json.load(f)
def write(name,data):
 path=D/name; path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f: json.dump(data,f,indent=2); f.flush(); os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def hist(pid):
 if not any(x['patient_id']==pid for x in read('patients.json')):raise HTTPException(404,'Patient not found')
 return read(f'patient_histories/{pid}.json')
def user(req:Request):
 u=sessions.get(req.cookies.get('asha_session',''))
 if not u:raise HTTPException(401,'Please sign in')
 return u
def role(r):
 def check(u=Depends(user)):
  if u['role']!=r:raise HTTPException(403,'Access denied')
  return u
 return check
Ddoc=Depends(role('doctor')); Dadmin=Depends(role('admin'))
class Login(BaseModel):
 user_id:str; password:str; role:Literal['doctor','admin']
class Chat(BaseModel): question:str=Field(min_length=1,max_length=1000)
class Record(BaseModel):
 visit_date:date; medical_unit_id:str; glucose_value:Optional[float]=Field(default=None,gt=0,lt=1000); glucose_type:Literal['fasting','postprandial','random','unspecified']='unspecified'; glucose_unit:Literal['mg/dL','mmol/L']='mg/dL'; systolic:Optional[int]=Field(default=None,gt=0,lt=300); diastolic:Optional[int]=Field(default=None,gt=0,lt=200); weight:Optional[float]=Field(default=None,gt=0,lt=500); symptoms:List[str]=[]; medication_notes:str=''; observations:str=''; priority:Literal['RED','PURPLE','YELLOW','GREEN']='GREEN'; priority_reason:str=''; follow_up_date:Optional[date]=None
class Unit(BaseModel):
 name:str=Field(min_length=1,max_length=100); type:str='PHC'; district:str; block:str; village:str; address:str; contact:str; status:Literal['Active','Inactive']='Active'
class Worker(BaseModel):
 name:str=Field(min_length=1,max_length=100); contact:str; medical_unit_id:str; village:str; district:str; joining_date:date; status:Literal['Active','Inactive']='Active'
def serial(x): return json.loads(x.model_dump_json())
def enriched():
 units={x['unit_id']:x for x in read('medical_units.json')}; workers={x['asha_id']:x for x in read('asha_workers.json')}; out=[]
 for p in read('patients.json'):
  p={k:v for k,v in p.items() if k not in ('aadhaar_number','abha_number','mobile_operation_id','mobile_operation_hash','mobile_operation_user')}
  if p.get('date_of_birth'):
   born=date.fromisoformat(p['date_of_birth']);today=date.today();p['age']=today.year-born.year-((today.month,today.day)<(born.month,born.day))
  h=hist(p['patient_id']); vs=sorted(h['visits'],key=lambda x:x['visit_date'],reverse=True); latest=vs[0] if vs else {}; out.append({**p,'priority':latest.get('priority',p['priority']),'priority_reason':latest.get('priority_reason',''),'last_visit':latest.get('visit_date'),'visit_count':len(vs),'unit_name':units.get(p['medical_unit_id'],{}).get('name','Unknown'),'worker_name':workers.get(p['asha_worker_id'],{}).get('name','Unknown')})
 return out
def sorted_priority(ps):return sorted(ps,key=lambda p:({'RED':0,'PURPLE':1,'YELLOW':2,'GREEN':3}[p['priority']],p.get('last_visit') or '9999'))
@app.get('/api/v1/health')
def health():return {'status':'ok'}
@app.post('/api/v1/auth/login')
def login(body:Login,response:Response):
 u=next((x for x in read('users.json') if x['id']==body.user_id and x['role']==body.role),None); hashed=hashlib.pbkdf2_hmac('sha256',body.password.encode(),b'asha-demo',200000).hex()
 if not u or not hmac.compare_digest(u['password_hash'],hashed):raise HTTPException(401,'Invalid user ID, password, or role')
 token=secrets.token_urlsafe(32); sessions[token]={k:u[k] for k in ('id','name','role')}; response.set_cookie('asha_session',token,httponly=True,samesite='lax',secure=os.getenv('COOKIE_SECURE')=='true',max_age=28800); return sessions[token]
@app.get('/api/v1/auth/me')
def me(u=Depends(user)):return u
@app.post('/api/v1/auth/logout')
def logout(req:Request,response:Response):
 sessions.pop(req.cookies.get('asha_session',''),None);response.delete_cookie('asha_session');return {'ok':True}
@app.get('/api/v1/patients')
def patients(q:str='',u=Ddoc):return [p for p in enriched() if q.lower() in (p['name']+' '+p['patient_id']).lower()]
@app.get('/api/v1/doctor/enrollment-options')
def enrollment_options(u=Ddoc):
 return {'units':[{'unit_id':x['unit_id'],'name':x['name']} for x in read('medical_units.json') if x['status']=='Active'],'workers':[{'asha_id':x['asha_id'],'name':x['name'],'medical_unit_id':x['medical_unit_id']} for x in read('asha_workers.json') if x['status']=='Active']}
def enroll(b:Enrollment,u,operation_id=None,operation_hash=None):
 with lock:
  units=read('medical_units.json'); workers=read('asha_workers.json')
  if not any(x['unit_id']==b.medical_unit_id and x['status']=='Active' for x in units):raise HTTPException(422,'Select an active medical unit')
  if not any(x['asha_id']==b.asha_worker_id and x['medical_unit_id']==b.medical_unit_id and x['status']=='Active' for x in workers):raise HTTPException(422,'Select an active ASHA worker assigned to the unit')
  patients=read('patients.json')
  if operation_id:
   existing=next((x for x in patients if x.get('mobile_operation_id')==operation_id),None)
   if existing:
    if existing.get('mobile_operation_hash')!=operation_hash or existing.get('mobile_operation_user')!=u['id']:raise HTTPException(409,'Operation ID already used')
    return {'patient_id':existing['patient_id'],'name':existing['name']}
  if b.aadhaar_number and any(x.get('aadhaar_number')==b.aadhaar_number for x in patients):raise HTTPException(409,'A patient with this Aadhaar number is already enrolled')
  today=date.today(); age=today.year-b.date_of_birth.year-((today.month,today.day)<(b.date_of_birth.month,b.date_of_birth.day))
  pid='PAT-'+(hashlib.sha256(operation_id.encode()).hexdigest()[:20].upper() if operation_id else uuid.uuid4().hex[:12].upper()); p={**serial(b),'patient_id':pid,'age':age,'registered_at':today.isoformat(),'priority':'GREEN'}
  if operation_id:p.update(mobile_operation_id=operation_id,mobile_operation_hash=operation_hash,mobile_operation_user=u['id'])
  path=f'patient_histories/{pid}.json'; write(path,{'patient_id':pid,'history_version':0,'visits':[],'summary':None})
  try:
   patients.append(p);write('patients.json',patients)
  except Exception:
   (D/path).unlink(missing_ok=True);raise
 return {'patient_id':pid,'name':p['name']}
@app.post('/api/v1/patients',status_code=201)
def enroll_web(b:Enrollment,u=Ddoc):return enroll(b,u)
@app.get('/api/v1/doctor/dashboard')
def doctor_dashboard(u=Ddoc):
 ps=sorted_priority(enriched());return {'total_patients':len(ps),'urgent_cases':sum(p['priority']=='RED' for p in ps),'follow_up':sum(p['priority'] in ('PURPLE','YELLOW') for p in ps),'recent_visits':sum(p['visit_count'] for p in ps),'priority_cases':[p for p in ps if p['priority']!='GREEN']}
@app.get('/api/v1/doctor/priority-cases')
def priority(u=Ddoc):return sorted_priority([p for p in enriched() if p['priority']!='GREEN'])
@app.get('/api/v1/patients/{pid}')
def patient(pid:str,u=Ddoc):
 p=next((p for p in enriched() if p['patient_id']==pid),None)
 if not p:raise HTTPException(404,'Patient not found')
 return p
@app.get('/api/v1/patients/{pid}/history')
def history(pid:str,u=Ddoc):return hist(pid)
def record(pid:str,b:SehatRecord,u,operation_id=None,operation_hash=None):
 if not any(x['unit_id']==b.medical_unit_id and x['status']=='Active' for x in read('medical_units.json')):raise HTTPException(422,'Select an active medical unit')
 with lock:
  h=hist(pid)
  if operation_id:
   existing=next((v for v in h['visits'] if v.get('mobile_operation_id')==operation_id),None)
   if existing:
    if existing.get('mobile_operation_hash')!=operation_hash or existing.get('provider_id')!=u['id']:raise HTTPException(409,'Operation ID already used')
    return existing
  has_baseline=any(v.get('form_type')=='baseline' or v.get('baseline') is not None for v in h['visits'])
  if (b.baseline is None)==(b.follow_up is None):raise HTTPException(422,'Submit exactly one baseline or follow-up form')
  if has_baseline and b.baseline is not None:raise HTTPException(409,'A baseline has already been recorded; use the follow-up form')
  if not h['visits'] and b.baseline is None:raise HTTPException(422,'The first record must use the baseline form')
  p=next(x for x in read('patients.json') if x['patient_id']==pid)
  if b.baseline and p['gender']!='Female' and any(getattr(b.baseline,k) is not None for k in ('pregnant','pregnancy_month','pregnancy_sugar_test','past_pregnancy_sugar','heavy_baby','pregnancy_loss','irregular_periods','recurrent_urine_infection')):raise HTTPException(422,'Women’s health questions are only applicable when sex is female')
  symptoms=(b.baseline.sugar_symptoms+b.baseline.other_symptoms if b.baseline else ([b.follow_up.new_symptoms_text] if b.follow_up.new_symptoms_text else []))
  medication_notes=b.medication_notes
  if b.baseline and b.baseline.diabetes_medicine:
   medication_notes='; '.join(filter(None,[medication_notes, 'Currently on diabetes medicine: '+b.baseline.diabetes_medicine + ((' ('+b.baseline.medicine_type+')') if b.baseline.medicine_type else '')]))
  v={'visit_id':'VIS-'+uuid.uuid4().hex[:12].upper(),'visit_date':b.visit_date.isoformat(),'medical_unit_id':b.medical_unit_id,'provider_id':u['id'],'form_type':'baseline' if b.baseline is not None else 'follow_up','opening':serial(b.opening),'baseline':serial(b.baseline) if b.baseline else None,'follow_up':serial(b.follow_up) if b.follow_up else None,'glucose':{'value':b.glucose_value,'unit':'mg/dL','type':b.glucose_type} if b.glucose_value is not None else None,'blood_pressure':{'systolic':b.systolic,'diastolic':b.diastolic,'unit':'mmHg'} if b.systolic else None,'weight':b.weight,'symptoms':[s for s in symptoms if s!='None'],'medication_notes':medication_notes,'observations':b.observations,'priority':b.priority,'priority_reason':b.priority_reason,'follow_up_date':b.follow_up_date.isoformat() if b.follow_up_date else None,'created_at':datetime.now(timezone.utc).isoformat()}
  if operation_id:v.update(mobile_operation_id=operation_id,mobile_operation_hash=operation_hash)
  h['visits'].append(v);h['history_version']+=1;write(f'patient_histories/{pid}.json',h)
 return v
@app.post('/api/v1/patients/{pid}/records',status_code=201)
def record_web(pid:str,b:SehatRecord,u=Ddoc):return record(pid,b,u)

def answer(h,q):
 q=q.lower();vs=sorted(h['visits'],key=lambda x:x['visit_date'],reverse=True)
 if any(x in q for x in ['diagnos','treat','prescrib','dosage','dose','should i','recommend','medicine should']):return 'I can only retrieve recorded history. Clinical decisions remain with qualified professionals.'
 if not vs:return 'No visits have been recorded.'
 if ('glucose' in q or 'sugar' in q) and ('blood pressure' in q or re.search(r'\bbp\b',q)):
  return 'Glucose: '+answer(h,q.replace('blood pressure','').replace('bp',''))+'\n\nBlood pressure: '+answer(h,q.replace('glucose','').replace('sugar','').replace('bp','blood pressure'))
 if 'glucose' in q or 'sugar' in q:
  rows=[v for v in vs if v.get('glucose') and v['glucose'].get('value') is not None][:3 if any(x in q for x in ['three','3','trend','readings']) else 1]
  return '; '.join(f"{v['visit_date']} ({v['visit_id']}): {v['glucose']['value']} {v['glucose']['unit']} ({v['glucose']['type']})" for v in rows) or 'No glucose readings recorded.'
 if 'blood pressure' in q or re.search(r'\bbp\b',q):
  rows=vs[:3] if any(x in q for x in ['three','3']) else vs
  return '; '.join(f"{v['visit_date']} ({v['visit_id']}): {v['blood_pressure']['systolic']}/{v['blood_pressure']['diastolic']} mmHg" for v in rows if v.get('blood_pressure')) or 'No blood pressure readings recorded.'
 if 'how many' in q or 'visit count' in q:return f"{len(vs)} visits recorded."
 if 'last visit' in q or 'latest visit' in q:return f"Latest visit: {vs[0]['visit_date']} ({vs[0]['visit_id']})."
 if 'symptom' in q:return '; '.join(f"{v['visit_date']} ({v['visit_id']}): {', '.join(v['symptoms'])}" for v in vs if v.get('symptoms')) or 'No symptoms recorded.'
 if 'medication' in q:return '; '.join(f"{v['visit_date']} ({v['visit_id']}): {v['medication_notes']}" for v in vs if v.get('medication_notes')) or 'No medication details recorded.'
 if 'urgent' in q or 'priority' in q:return '; '.join(f"{v['visit_date']} ({v['visit_id']}): {v['priority']} — {v.get('priority_reason','')}" for v in vs if v.get('priority')!='GREEN') or 'No priority flags recorded.'
 if 'summar' in q:return f"{len(vs)} visits recorded. Latest visit {vs[0]['visit_date']} ({vs[0]['visit_id']}). "+answer(h,'latest glucose')
 return 'This question cannot be retrieved in fallback mode. Try asking about visits, glucose, blood pressure, symptoms, medications, or priority history.'
@app.post('/api/v1/patients/{pid}/chat')
def chat(pid:str,b:Chat,u=Ddoc):
 h=hist(pid); references=re.findall(r'PAT\d+',b.question.upper())
 if any(ref!=pid.upper() for ref in references):return {'answer':'This assistant can only retrieve the selected patient’s history.','mode':'deterministic'}
 # Refuse obvious clinical requests before any model call.
 if any(x in b.question.lower() for x in ['diagnos','treat','prescrib','dosage','dose','should i','recommend','medicine should']):
  return {'answer':'I can only retrieve recorded history. Clinical decisions remain with qualified professionals.','mode':'deterministic'}
 try:
  intent=gemini.classify(b.question)
  if intent is not None:return {'answer':gemini.render(h,intent),'mode':'gemini'}
 except RuntimeError:
  return {'answer':answer(h,b.question),'mode':'fallback','notice':'Gemini is unavailable; using local history retrieval.'}
 return {'answer':answer(h,b.question),'mode':'fallback','notice':'Gemini is not configured; using local history retrieval.'}
@app.get('/api/v1/patients/{pid}/summary')
def summary(pid:str,u=Ddoc):
 h=hist(pid);s=h.get('summary');return {'summary':s,'stale':bool(s and s['history_version']!=h['history_version'])}
@app.post('/api/v1/patients/{pid}/summary/generate')
def generate(pid:str,u=Ddoc):
 with lock:
  h=hist(pid);s={'text':answer(h,'summarize'),'mode':'deterministic','generated_at':datetime.now(timezone.utc).isoformat(),'history_version':h['history_version']};h['summary']=s;write(f'patient_histories/{pid}.json',h)
 return {'summary':s,'stale':False}
@app.get('/api/v1/admin/patients')
def admin_patients(u=Dadmin):return enriched()
def unit_stats():
 ps=enriched();ws=read('asha_workers.json');return [{**x,'patient_count':sum(p['medical_unit_id']==x['unit_id'] for p in ps),'worker_count':sum(w['medical_unit_id']==x['unit_id'] for w in ws),'visit_count':sum(p['visit_count'] for p in ps if p['medical_unit_id']==x['unit_id'])} for x in read('medical_units.json')]
def worker_stats():
 ps=enriched();return [{**w,'patient_count':sum(p['asha_worker_id']==w['asha_id'] for p in ps),'visit_count':sum(p['visit_count'] for p in ps if p['asha_worker_id']==w['asha_id'])} for w in read('asha_workers.json')]
@app.get('/api/v1/admin/dashboard')
def admin_dashboard(u=Dadmin):
 ps=enriched();units=unit_stats();ws=worker_stats();return {'total_units':len(units),'total_patients':len(ps),'total_workers':len(ws),'total_visits':sum(p['visit_count'] for p in ps),'active_priority':sum(p['priority']!='GREEN' for p in ps),'units':units,'priority_distribution':[{ 'name':flag,'value':sum(p['priority']==flag for p in ps)} for flag in ['RED','PURPLE','YELLOW','GREEN']]}
@app.get('/api/v1/admin/statistics')
def stats(u=Dadmin):return admin_dashboard(u)
@app.get('/api/v1/admin/medical-units')
def units(u=Dadmin):return unit_stats()
@app.get('/api/v1/admin/medical-units/{uid}')
def unit(uid:str,u=Dadmin):
 x=next((x for x in unit_stats() if x['unit_id']==uid),None)
 if not x:raise HTTPException(404,'Unit not found')
 return {**x,'workers':[w for w in worker_stats() if w['medical_unit_id']==uid],'patients':[p for p in enriched() if p['medical_unit_id']==uid]}
@app.post('/api/v1/admin/medical-units',status_code=201)
def add_unit(b:Unit,u=Dadmin):
 with lock:
  xs=read('medical_units.json');x={'unit_id':'MU-'+uuid.uuid4().hex[:8].upper(),**serial(b)};xs.append(x);write('medical_units.json',xs)
 return x
@app.patch('/api/v1/admin/medical-units/{uid}')
def edit_unit(uid:str,b:Unit,u=Dadmin):
 if b.status=='Inactive' and any(w['medical_unit_id']==uid and w['status']=='Active' for w in read('asha_workers.json')):raise HTTPException(409,'Reassign or deactivate active workers first')
 with lock:
  xs=read('medical_units.json');x=next((x for x in xs if x['unit_id']==uid),None)
  if not x:raise HTTPException(404,'Unit not found')
  x.update(serial(b));write('medical_units.json',xs);return x
@app.delete('/api/v1/admin/medical-units/{uid}')
def delete_unit(uid:str,u=Dadmin):
 if any(w['medical_unit_id']==uid and w['status']=='Active' for w in read('asha_workers.json')):raise HTTPException(409,'Reassign or deactivate active workers first')
 x=unit(uid,u);return edit_unit(uid,Unit(**{**x,'status':'Inactive'}),u)
@app.get('/api/v1/admin/asha-workers')
def workers(u=Dadmin):return worker_stats()
@app.get('/api/v1/admin/asha-workers/{wid}')
def worker(wid:str,u=Dadmin):
 x=next((x for x in worker_stats() if x['asha_id']==wid),None)
 if not x:raise HTTPException(404,'Worker not found')
 return {**x,'patients':[p for p in enriched() if p['asha_worker_id']==wid]}
def valid_unit(uid):
 if not any(x['unit_id']==uid and x['status']=='Active' for x in read('medical_units.json')):raise HTTPException(422,'Select an active unit')
@app.post('/api/v1/admin/asha-workers',status_code=201)
def add_worker(b:Worker,u=Dadmin):
 valid_unit(b.medical_unit_id)
 with lock:
  xs=read('asha_workers.json');x={'asha_id':'ASHA-'+uuid.uuid4().hex[:8].upper(),**serial(b)};xs.append(x);write('asha_workers.json',xs)
 return x
@app.patch('/api/v1/admin/asha-workers/{wid}')
def edit_worker(wid:str,b:Worker,u=Dadmin):
 if b.status=='Inactive' and any(p['asha_worker_id']==wid for p in read('patients.json')):raise HTTPException(409,'Worker has assigned patients; reassignment is required before deactivation')
 valid_unit(b.medical_unit_id)
 with lock:
  xs=read('asha_workers.json');x=next((x for x in xs if x['asha_id']==wid),None)
  if not x:raise HTTPException(404,'Worker not found')
  x.update(serial(b));write('asha_workers.json',xs);return x
@app.delete('/api/v1/admin/asha-workers/{wid}')
def delete_worker(wid:str,u=Dadmin):
 x=worker(wid,u)
 if x['patient_count']:raise HTTPException(409,'Worker has assigned patients; reassignment is required before deactivation')
 return edit_worker(wid,Worker(**{**x,'status':'Inactive'}),u)

from .mobile import router as mobile_router
app.include_router(mobile_router)
