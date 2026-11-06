import json, os, hashlib, sys
from pathlib import Path
from datetime import date, timedelta
D=Path(__file__).resolve().parents[1]/'data'
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,indent=2))
if (D/'users.json').exists() and '--reset' not in sys.argv:
 print('Data already exists; pass --reset to overwrite demo data.'); sys.exit(0)
def password(s): return hashlib.pbkdf2_hmac('sha256',s.encode(),b'asha-demo',200000).hex()
write(D/'users.json',[{'id':'doctor001','name':'Dr. Ananya Sharma','role':'doctor','password_hash':password('Doctor@123')},{'id':'admin001','name':'Arjun Verma','role':'admin','password_hash':password('Admin@123')},{'id':'asha001','name':'Asha Patil','role':'asha','asha_worker_id':'ASHA001','password_hash':password('Asha@123')}])
units=[{'unit_id':f'MU{i:03}','name':n,'type':'PHC','district':'Sehore (fictional demo)','block':f'Block {i}','village':f'Demo Village {i}','address':f'Demo Road {i}, Sehore','contact':f'90000000{i:02}','status':'Active'} for i,n in enumerate(['Aarogya PHC','Swasthya PHC','Jeevan PHC','Sahayata PHC','Umeed PHC'],1)]
workers=[{'asha_id':f'ASHA{i:03}','name':n,'contact':f'91000000{i:02}','medical_unit_id':f'MU{((i-1)//2)+1:03}','village':f'Demo Village {((i-1)//2)+1}','district':'Sehore (fictional demo)','joining_date':'2024-01-15','status':'Active'} for i,n in enumerate(['Asha Patil','Meera Rao','Kavita Joshi','Sunita Pal','Rekha Jain','Pooja Singh','Neha Soni','Radha Patel','Anita Das','Seema Roy'],1)]
write(D/'medical_units.json',units); write(D/'asha_workers.json',workers)
names=['Ramesh Kumar','Sita Devi','Mohan Lal','Kamla Bai','Rajesh Patel','Gita Sharma','Suresh Jain','Anita Verma','Ravi Singh','Radha Joshi','Dinesh Yadav','Shanti Devi','Mahesh Rao','Kiran Pal','Vijay Soni','Nirmala Das','Ashok Patil','Sarita Roy','Deepak Gupta','Lata Mehta','Prakash Shah','Reena Kumar','Manoj Singh','Poonam Jain','Vinod Patel']
patients=[]
for i,name in enumerate(names,1):
 unit=(i-1)%5+1; worker=(unit-1)*2+(i%2)+1; flag=['RED','PURPLE','YELLOW','GREEN','GREEN'][i%5]
 p={'patient_id':f'PAT{i:03}','name':name,'age':38+i%30,'gender':'Female' if i%2==0 else 'Male','village':f'Demo Village {unit}','contact':f'92000000{i:02}','medical_unit_id':f'MU{unit:03}','asha_worker_id':f'ASHA{worker:03}','registered_at':'2025-01-15','priority':flag}; patients.append(p)
 visits=[]
 for j in range(5):
  dt=date(2026,2,1)+timedelta(days=j*48+i)
  visits.append({'visit_id':f'VIS{i:03}{j+1:02}','visit_date':dt.isoformat(),'medical_unit_id':p['medical_unit_id'],'provider_id':'doctor001','glucose':{'value':120+(i*7+j*9)%85,'unit':'mg/dL','type':'fasting'},'blood_pressure':{'systolic':118+(i+j)%24,'diastolic':74+(i+j)%15,'unit':'mmHg'},'symptoms':['Fatigue'] if j%2==0 else [],'medication_notes':'No medication details recorded.','observations':'Routine follow-up recorded.','priority':flag if j==4 else 'GREEN','priority_reason':'Manually flagged for review.' if j==4 and flag!='GREEN' else '', 'follow_up_date':None,'created_at':dt.isoformat()+'T10:30:00Z'})
 write(D/'patient_histories'/f'PAT{i:03}.json',{'patient_id':p['patient_id'],'history_version':5,'visits':visits,'summary':None})
write(D/'patients.json',patients)
print('Synthetic demo data created.')
