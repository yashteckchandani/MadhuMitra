import os, shutil, tempfile, unittest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import main

class APITest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(); shutil.copytree(Path(__file__).resolve().parents[1]/'data',Path(cls.temp.name)/'data'); main.D=Path(cls.temp.name)/'data'; cls.client=TestClient(main.app)
 @classmethod
 def tearDownClass(cls): cls.temp.cleanup()
 def login(self,role='doctor'):
  return self.client.post('/api/v1/auth/login',json={'user_id':role+'001','password':'Doctor@123' if role=='doctor' else 'Admin@123','role':role})
 def test_01_auth_and_permissions(self):
  self.assertEqual(self.client.get('/api/v1/patients').status_code,401)
  self.assertEqual(self.login().status_code,200)
  self.assertEqual(self.client.get('/api/v1/admin/dashboard').status_code,403)
  self.client.post('/api/v1/auth/logout')
  self.assertEqual(self.client.post('/api/v1/auth/login',json={'user_id':'doctor001','password':'bad','role':'doctor'}).status_code,401)
  self.assertEqual(self.login('admin').status_code,200)
  self.assertEqual(self.client.post('/api/v1/patients/PAT001/records',json={}).status_code,403)
  self.client.post('/api/v1/auth/logout')
 def test_02_history_and_append(self):
  self.login(); self.assertTrue(self.client.get('/api/v1/patients?q=PAT001').json()); self.assertEqual(self.client.get('/api/v1/patients/NOPE/history').status_code,404)
  old=self.client.get('/api/v1/patients/PAT001/history').json(); self.client.post('/api/v1/patients/PAT001/summary/generate'); r=self.client.post('/api/v1/patients/PAT001/records',json={'visit_date':'2099-11-05','medical_unit_id':'MU001','glucose_value':123,'priority':'GREEN','opening':{'unconscious_or_weak':'No','vomiting_breathing_or_pain':'No','cold_sweat_or_weakness':'No','infected_foot_wound':'No'},'follow_up':{}}); self.assertEqual(r.status_code,201)
  new=self.client.get('/api/v1/patients/PAT001/history').json();self.assertEqual(new['visits'][:-1],old['visits']);self.assertEqual(new['history_version'],old['history_version']+1);self.assertTrue(self.client.get('/api/v1/patients/PAT001/summary').json()['stale']);self.assertIn('123',self.client.post('/api/v1/patients/PAT001/chat',json={'question':'latest glucose'}).json()['answer']);self.assertIn('Clinical decisions',self.client.post('/api/v1/patients/PAT001/chat',json={'question':'recommend treatment'}).json()['answer']);self.client.post('/api/v1/auth/logout')
 def test_04_enrollment_and_sehat(self):
  self.login()
  body={'name':'Fictional Patient','date_of_birth':'1980-01-01','gender':'Female','village':'Demo village','address':'Demo address','medical_unit_id':'MU001','asha_worker_id':'ASHA001','aadhaar_number':'123456789012'}
  r=self.client.post('/api/v1/patients',json=body);self.assertEqual(r.status_code,201,r.text);pid=r.json()['patient_id']
  self.assertEqual(self.client.get('/api/v1/patients/'+pid+'/history').json()['visits'],[])
  self.assertNotIn('aadhaar_number',self.client.get('/api/v1/patients/'+pid).json())
  opening={'unconscious_or_weak':'No','vomiting_breathing_or_pain':'No','cold_sweat_or_weakness':'No','infected_foot_wound':'No'}
  record={'visit_date':'2026-11-06','medical_unit_id':'MU001','opening':opening,'baseline':{'sugar_symptoms':['More thirst'],'pregnant':'No'},'glucose_value':145,'glucose_type':'fasting','systolic':120,'diastolic':80}
  blocked={**record,'opening':{**opening,'infected_foot_wound':'Yes'}}
  self.assertEqual(self.client.post('/api/v1/patients/'+pid+'/records',json=blocked).status_code,422)
  self.assertEqual(self.client.post('/api/v1/patients/'+pid+'/records',json=record).status_code,201)
  self.assertEqual(self.client.post('/api/v1/patients/'+pid+'/records',json=record).status_code,409)
  follow={'visit_date':'2026-11-07','medical_unit_id':'MU001','opening':opening,'follow_up':{'medicine_taken':'Yes','new_symptoms_text':'Tired'},'glucose_value':110}
  self.assertEqual(self.client.post('/api/v1/patients/'+pid+'/records',json=follow).status_code,201)
  h=self.client.get('/api/v1/patients/'+pid+'/history').json();self.assertEqual([x['form_type'] for x in h['visits']],['baseline','follow_up']);self.assertEqual(h['visits'][0]['baseline']['sugar_symptoms'],['More thirst']);self.assertEqual(h['visits'][0]['glucose']['value'],145);self.assertEqual(h['visits'][0]['glucose']['type'],'fasting');self.assertEqual(h['visits'][1]['symptoms'],['Tired'])
  self.client.post('/api/v1/auth/logout')
 def test_03_admin_creation(self):
  self.login('admin');before=self.client.get('/api/v1/admin/dashboard').json()['total_units'];r=self.client.post('/api/v1/admin/medical-units',json={'name':'Test unit','type':'PHC','district':'Demo','block':'Demo','village':'Demo','address':'Demo','contact':'123','status':'Active'});self.assertEqual(r.status_code,201);self.assertEqual(self.client.get('/api/v1/admin/dashboard').json()['total_units'],before+1)
if __name__=='__main__':unittest.main()

class LegacySehatTest(APITest):
 def test_legacy_history_accepts_one_baseline(self):
  self.login();pid='PAT002';old=self.client.get('/api/v1/patients/'+pid+'/history').json();opening={k:'No' for k in ['unconscious_or_weak','vomiting_breathing_or_pain','cold_sweat_or_weakness','infected_foot_wound']};body={'visit_date':'2099-01-01','medical_unit_id':'MU002','opening':opening,'baseline':{'sugar_symptoms':['More thirst'],'high_bp':"Don't know",'foot_exam':['Wound or sore'],'pulse':84},'glucose_value':147,'glucose_type':'random'}
  r=self.client.post('/api/v1/patients/'+pid+'/records',json=body);self.assertEqual(r.status_code,201,r.text);self.assertEqual(r.json()['form_type'],'baseline');new=self.client.get('/api/v1/patients/'+pid+'/history').json();self.assertEqual(new['visits'][:-1],old['visits']);self.assertEqual(new['visits'][-1]['baseline']['foot_exam'],['Wound or sore']);self.assertEqual(self.client.post('/api/v1/patients/'+pid+'/records',json=body).status_code,409)
