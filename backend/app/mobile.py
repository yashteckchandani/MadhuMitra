"""Assignment-scoped mobile read API. Sessions are intentionally local-demo only."""
import hashlib, hmac, secrets, time
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Literal
from . import main

router = APIRouter(prefix='/api/v1/mobile', tags=['mobile'])
sessions = {}
class Login(BaseModel):
 user_id: str = Field(max_length=80)
 password: str = Field(max_length=200)
 role: Literal['asha','doctor']

def auth(req:Request):
 token=req.headers.get('Authorization','').removeprefix('Bearer ')
 session=sessions.get(hashlib.sha256(token.encode()).hexdigest())
 if not session or session['expires'] < time.time(): raise HTTPException(401,'Mobile session expired; sign in online')
 user=next((u for u in main.read('users.json') if u['id']==session['id'] and u['role']==session['role']),None)
 if not user: raise HTTPException(401,'Account unavailable')
 if user['role']=='asha':
  worker=next((w for w in main.read('asha_workers.json') if w['asha_id']==user.get('asha_worker_id') and w['status']=='Active'),None)
  if not worker: raise HTTPException(403,'Worker account is inactive')
  return {'id':user['id'],'name':user['name'],'role':'asha','worker_id':worker['asha_id'],'unit_id':worker['medical_unit_id']}
 # Demo doctor is explicitly limited to one unit. Never infer unrestricted access.
 if user['id']!='doctor001':raise HTTPException(403,'No mobile jurisdiction configured')
 return {'id':user['id'],'name':user['name'],'role':'doctor','unit_id':'MU001'}

def allowed(u,p):
 return p['medical_unit_id']==u['unit_id'] and (u['role']!='asha' or p['asha_worker_id']==u['worker_id'])

@router.post('/auth/login')
def login(b:Login):
 user=next((u for u in main.read('users.json') if u['id']==b.user_id and u['role']==b.role),None)
 candidate=hashlib.pbkdf2_hmac('sha256',b.password.encode(),b'asha-demo',200000).hex()
 if not user or not hmac.compare_digest(user['password_hash'],candidate):raise HTTPException(401,'Invalid user ID, password, or role')
 token=secrets.token_urlsafe(32);expires=time.time()+8*3600
 sessions[hashlib.sha256(token.encode()).hexdigest()]={'id':user['id'],'role':user['role'],'expires':expires}
 return {'access_token':token,'expires_at':expires,'user':{'id':user['id'],'name':user['name'],'role':user['role']}}

@router.post('/auth/logout')
def logout(req:Request,u=Depends(auth)):
 token=req.headers.get('Authorization','').removeprefix('Bearer ');sessions.pop(hashlib.sha256(token.encode()).hexdigest(),None);return {'ok':True}

@router.get('/bootstrap')
def bootstrap(u=Depends(auth)):
 patients=[p for p in main.enriched() if allowed(u,p)]
 histories=[main.hist(p['patient_id']) for p in patients]
 units=[x for x in main.read('medical_units.json') if x['unit_id']==u['unit_id']]
 workers=[{'asha_id':w['asha_id'],'name':w['name'],'medical_unit_id':w['medical_unit_id']} for w in main.read('asha_workers.json') if w['medical_unit_id']==u['unit_id'] and w['status']=='Active']
 return {'user':u,'patients':patients,'histories':histories,'units':units,'workers':workers,'synced_at':time.time()}

@router.post('/patients/{patient_id}/chat')
def chat(patient_id:str,b:main.Chat,u=Depends(auth)):
 patient=next((p for p in main.read('patients.json') if p['patient_id']==patient_id),None)
 if not patient or not allowed(u,patient):raise HTTPException(404,'Patient not found')
 return main.chat(patient_id,b,u)

class Operation(BaseModel):
 operation_id: str = Field(pattern=r'^[a-f0-9-]{36}$')
 kind: Literal['patient_create','visit_create']
 payload: dict

@router.post('/sync/push')
def push(b:Operation,u=Depends(auth)):
 with main.lock:
  return push_locked(b,u)

def push_locked(b:Operation,u):
 import json
 from .sehat import Enrollment, SehatRecord
 from pydantic import ValidationError
 digest=hashlib.sha256(json.dumps({'kind':b.kind,'payload':b.payload},sort_keys=True,separators=(',',':')).encode()).hexdigest()
 for patient in main.read('patients.json'):
  if patient.get('mobile_operation_id')==b.operation_id:
   if b.kind!='patient_create' or patient.get('mobile_operation_hash')!=digest or patient.get('mobile_operation_user')!=u['id']:raise HTTPException(409,'Operation ID already used')
  for visit in main.hist(patient['patient_id'])['visits']:
   if visit.get('mobile_operation_id')==b.operation_id:
    if b.kind!='visit_create' or visit.get('mobile_operation_hash')!=digest or visit.get('provider_id')!=u['id']:raise HTTPException(409,'Operation ID already used')
 try:
  if b.kind=='patient_create':
   patient=Enrollment(**b.payload)
   if patient.medical_unit_id!=u['unit_id'] or (u['role']=='asha' and patient.asha_worker_id!=u['worker_id']):raise HTTPException(403,'Assignment is outside your scope')
   result=main.enroll(patient,u,operation_id=b.operation_id,operation_hash=digest)
   return {'operation_id':b.operation_id,'patient_id':result['patient_id']}
  patient_id=b.payload.get('patient_id');body=b.payload.get('record')
  patient=next((p for p in main.read('patients.json') if p['patient_id']==patient_id),None)
  if not patient or not allowed(u,patient):raise HTTPException(404,'Patient not found')
  record=SehatRecord(**body)
  if record.medical_unit_id!=u['unit_id']:raise HTTPException(403,'Unit is outside your scope')
  result=main.record(patient_id,record,u,operation_id=b.operation_id,operation_hash=digest)
  return {'operation_id':b.operation_id,'patient_id':patient_id,'visit_id':result['visit_id']}
 except ValidationError:raise HTTPException(422,'Invalid patient or record data')
