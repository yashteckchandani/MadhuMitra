import json, os, unittest
from unittest.mock import patch
from backend.app import gemini

H={'visits':[{'visit_id':'V1','visit_date':'2026-01-01','glucose':{'value':100,'unit':'mg/dL','type':'fasting'}},{'visit_id':'V2','visit_date':'2026-02-01','glucose':{'value':140,'unit':'mg/dL','type':'random'}}]}
class GeminiTest(unittest.TestCase):
 def test_computed_stats(self):
  intent=gemini.HistoryIntent(intent='glucose',count=2,operation='average')
  self.assertIn('120.00 mg/dL',gemini.render(H,intent))
  self.assertIn('V2, V1',gemini.render(H,intent))
 def test_combined_readings(self):
  data={'visits':[{'visit_id':'V1','visit_date':'2026-01-01','glucose':{'value':100,'unit':'mg/dL','type':'fasting'},'blood_pressure':{'systolic':120,'diastolic':80,'unit':'mmHg'}}]}
  result=gemini.render(data,gemini.HistoryIntent(intent='glucose_and_blood_pressure',count=3,operation='list'))
  self.assertIn('100 mg/dL',result);self.assertIn('120/80',result)
 def test_refusal(self):
  self.assertIn('Clinical decisions',gemini.render(H,gemini.HistoryIntent(intent='refuse',count=1,operation='list')))
 def test_no_key(self):
  with patch.dict(os.environ,{'GEMINI_API_KEY':''}):self.assertIsNone(gemini.classify('last glucose'))
 def test_model_validated_and_question_only(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,*a):return json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"intent":"glucose","count":2,"operation":"average"}'}]}}]}).encode()
  with patch.dict(os.environ,{'GEMINI_API_KEY':'test-key'}),patch('backend.app.gemini.request.urlopen',return_value=Response()) as call:
   intent=gemini.classify('average glucose');self.assertEqual(intent.operation,'average')
   req=call.call_args.args[0];self.assertNotIn('V1',req.data.decode());self.assertNotIn('test-key',req.full_url)
 def test_invalid_response_rejected(self):
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,*a):return json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"intent":"diagnose","count":2,"operation":"list"}'}]}}]}).encode()
  with patch.dict(os.environ,{'GEMINI_API_KEY':'test-key'}),patch('backend.app.gemini.request.urlopen',return_value=Response()):
   with self.assertRaises(RuntimeError):gemini.classify('question')
if __name__=='__main__':unittest.main()
