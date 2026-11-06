import copy, os, shutil, tempfile, unittest, uuid
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import main

class MobileTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();shutil.copytree(Path(__file__).resolve().parents[1]/'data',Path(cls.tmp.name)/'data');main.D=Path(cls.tmp.name)/'data';cls.c=TestClient(main.app)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def login(self,user,role,password):
  r=self.c.post('/api/v1/mobile/auth/login',json={'user_id':user,'role':role,'password':password});self.assertEqual(r.status_code,200);return {'Authorization':'Bearer '+r.json()['access_token']}
 def test_scoping_and_auth(self):
  self.assertEqual(self.c.get('/api/v1/mobile/bootstrap').status_code,401)
  h=self.login('asha001','asha','Asha@123');data=self.c.get('/api/v1/mobile/bootstrap',headers=h).json();self.assertGreater(len(data['patients']),0);self.assertTrue(all(p['asha_worker_id']=='ASHA001' for p in data['patients']));self.assertEqual(self.c.post('/api/v1/mobile/patients/PAT002/chat',headers=h,json={'question':'last visit'}).status_code,404)
 def test_visit_retry_is_idempotent(self):
  h=self.login('asha001','asha','Asha@123');data=self.c.get('/api/v1/mobile/bootstrap',headers=h).json();p=data['patients'][0];pid=p['patient_id'];before=len(main.hist(pid)['visits']);opening={k:'No' for k in ['unconscious_or_weak','vomiting_breathing_or_pain','cold_sweat_or_weakness','infected_foot_wound']};op={'operation_id':str(uuid.uuid4()),'kind':'visit_create','payload':{'patient_id':pid,'record':{'visit_date':'2099-01-01','medical_unit_id':p['medical_unit_id'],'opening':opening,'follow_up':{},'glucose_value':123}}};a=self.c.post('/api/v1/mobile/sync/push',headers=h,json=op);b=self.c.post('/api/v1/mobile/sync/push',headers=h,json=op);self.assertEqual(a.status_code,200,a.text);self.assertEqual(a.json(),b.json());self.assertEqual(len(main.hist(pid)['visits']),before+1);op['payload']['record']['glucose_value']=124;self.assertEqual(self.c.post('/api/v1/mobile/sync/push',headers=h,json=op).status_code,409)
if __name__=='__main__':unittest.main()

class MobileEnrollmentTest(MobileTest):
 def test_patient_then_visit_and_retry(self):
  auth=self.login('asha001','asha','Asha@123'); op={'operation_id':str(uuid.uuid4()),'kind':'patient_create','payload':{'name':'Synthetic Mobile Test','date_of_birth':'1980-01-01','gender':'Other','village':'Demo','address':'Demo','medical_unit_id':'MU001','asha_worker_id':'ASHA001'}}
  a=self.c.post('/api/v1/mobile/sync/push',headers=auth,json=op); b=self.c.post('/api/v1/mobile/sync/push',headers=auth,json=op);self.assertEqual(a.status_code,200,a.text);self.assertEqual(a.json(),b.json());pid=a.json()['patient_id'];self.assertEqual(len([p for p in main.read('patients.json') if p['patient_id']==pid]),1)
  opening={k:'No' for k in ['unconscious_or_weak','vomiting_breathing_or_pain','cold_sweat_or_weakness','infected_foot_wound']};visit={'operation_id':str(uuid.uuid4()),'kind':'visit_create','payload':{'patient_id':pid,'record':{'visit_date':'2026-11-06','medical_unit_id':'MU001','opening':opening,'baseline':{}}}};r=self.c.post('/api/v1/mobile/sync/push',headers=auth,json=visit);self.assertEqual(r.status_code,200,r.text);self.assertEqual(len(main.hist(pid)['visits']),1)

class MobileQuestionnaireTest(MobileTest):
 def test_detailed_baseline_and_followup(self):
  auth=self.login('asha001','asha','Asha@123')
  patient={'operation_id':str(uuid.uuid4()),'kind':'patient_create','payload':{'name':'Questionnaire Test','date_of_birth':'1985-02-10','gender':'Female','village':'Demo','address':'Demo','medical_unit_id':'MU001','asha_worker_id':'ASHA001'}}
  result=self.c.post('/api/v1/mobile/sync/push',headers=auth,json=patient);self.assertEqual(result.status_code,200,result.text);pid=result.json()['patient_id']
  opening={k:'No' for k in ['unconscious_or_weak','vomiting_breathing_or_pain','cold_sweat_or_weakness','infected_foot_wound']}
  baseline={'sugar_symptoms':['More thirst','Frequent urination'],'slow_healing_wound':'Yes','diabetes_medicine':'Yes','medicine_type':'Tablets','family_conditions':['High BP'],'pregnant':'Yes','pregnancy_month':5,'pregnancy_sugar_test':'Done','pulse':83,'height_feet':5,'height_inches':3,'waist_band':'81–90','foot_exam':['Wound or sore'],'mouth_exam':['Dry mouth']}
  record={'visit_date':'2099-01-01','medical_unit_id':'MU001','opening':opening,'baseline':baseline,'glucose_value':155,'glucose_type':'fasting','systolic':120,'diastolic':80,'weight':63}
  body={'operation_id':str(uuid.uuid4()),'kind':'visit_create','payload':{'patient_id':pid,'record':record}};r=self.c.post('/api/v1/mobile/sync/push',headers=auth,json=body);self.assertEqual(r.status_code,200,r.text);h=main.hist(pid);self.assertEqual(h['visits'][-1]['baseline']['pregnancy_month'],5);self.assertEqual(h['visits'][-1]['baseline']['foot_exam'],['Wound or sore']);self.assertEqual(h['visits'][-1]['glucose']['value'],155)
  follow={'medicine_taken':'No','medicine_not_taken_reason':'Forgot','new_feet_or_gums_problem':'Yes','low_episode':'No','new_symptoms_text':'Tired'};body={'operation_id':str(uuid.uuid4()),'kind':'visit_create','payload':{'patient_id':pid,'record':{'visit_date':'2099-02-01','medical_unit_id':'MU001','opening':opening,'follow_up':follow}}};r=self.c.post('/api/v1/mobile/sync/push',headers=auth,json=body);self.assertEqual(r.status_code,200,r.text);self.assertEqual(main.hist(pid)['visits'][-1]['follow_up'],follow)
