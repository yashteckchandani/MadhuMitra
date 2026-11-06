from datetime import date
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

YesNo = Literal['Yes', 'No']
YesNoDK = Literal['Yes', 'No', "Don't know"]
class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
class Enrollment(StrictModel):
    name: str = Field(min_length=1,max_length=100)
    date_of_birth: date
    gender: Literal['Male','Female','Other']
    village: str = Field(min_length=1,max_length=120)
    address: str = Field(min_length=1,max_length=300)
    contact: str = Field(default='',max_length=20,pattern=r'^[0-9+ -]*$')
    aadhaar_number: str = Field(default='',pattern=r'^(\d{12})?$',repr=False)
    abha_number: str = Field(default='',max_length=20,pattern=r'^[0-9-]*$')
    medical_unit_id: str
    asha_worker_id: str
    @model_validator(mode='after')
    def dob_valid(self):
        if self.date_of_birth > date.today() or self.date_of_birth.year < 1900: raise ValueError('Enter a valid date of birth')
        return self
class Opening(StrictModel):
    unconscious_or_weak: YesNo
    vomiting_breathing_or_pain: YesNo
    cold_sweat_or_weakness: YesNo
    infected_foot_wound: YesNo
class Baseline(StrictModel):
    sugar_symptoms: List[Literal['More thirst','Frequent urination','Much more hunger','Weight falling without trying']] = []
    other_symptoms: List[Literal['Tired quickly','Blurred vision','Tingling or numbness','Repeated itching or fungal patches','Burning while urinating','None']] = []
    slow_healing_wound: Optional[YesNoDK] = None
    sugar_tested_before: Optional[YesNoDK] = None
    last_sugar_test: Optional[Literal['Under 1','1–3','3–5','5–10','10+','Don\'t know']] = None
    treatment_since: Optional[Literal['Under 1','1–3','3–5','5–10','10+','Never diagnosed']] = None
    diabetes_medicine: Optional[YesNo] = None
    medicine_type: Optional[Literal['Tablets','Insulin','Both']] = None
    high_bp: Optional[YesNoDK] = None
    family_diabetes: Optional[YesNoDK] = None
    family_conditions: List[Literal['High BP','Heart attack or stroke','None',"Don't know"]] = []
    eye_check: Optional[Literal['Under 1','1–2','2+','Never',"Don't know"]] = None
    tobacco: Optional[Literal['None','Smoke','Chew','Both']] = None
    tobacco_per_day: Optional[int] = Field(default=None,ge=0,le=500)
    alcohol: Optional[Literal['Never','Sometimes','Daily']] = None
    walks_daily: Optional[Literal['Yes','Sometimes','No']] = None
    barefoot: Optional[YesNo] = None
    pregnant: Optional[YesNo] = None
    pregnancy_month: Optional[int] = Field(default=None,ge=1,le=9)
    pregnancy_sugar_test: Optional[Literal['Done','Not yet',"Don't know"]] = None
    past_pregnancy_sugar: Optional[YesNoDK] = None
    heavy_baby: Optional[YesNoDK] = None
    pregnancy_loss: Optional[YesNoDK] = None
    irregular_periods: Optional[YesNoDK] = None
    recurrent_urine_infection: Optional[YesNoDK] = None
    pulse: Optional[int] = Field(default=None,gt=0,le=300)
    height_feet: Optional[int] = Field(default=None,ge=0,le=8)
    height_inches: Optional[int] = Field(default=None,ge=0,le=11)
    waist_band: Optional[Literal['80 or less','81–90','more than 90','90 or less','91–100','more than 100','No tape']] = None
    foot_exam: List[Literal['Wound or sore','Cracked skin between toes','Toes bent inward or shoes no longer fit','History of amputation','History of previous ulcer','None']] = []
    mouth_exam: List[Literal['Bleeding gums or loose teeth','Pain','Dry mouth','Bad breath','Difficulty opening mouth or chewing','None']] = []
    @model_validator(mode='after')
    def validate_related(self):
        if self.medicine_type and self.diabetes_medicine != 'Yes': raise ValueError('Medicine type requires current diabetes medicine')
        if self.pregnancy_month and self.pregnant != 'Yes': raise ValueError('Pregnancy month requires pregnant = Yes')
        if self.pregnancy_sugar_test and self.pregnant != 'Yes': raise ValueError('Pregnancy sugar test requires pregnant = Yes')
        for vals in (self.other_symptoms,self.family_conditions,self.foot_exam,self.mouth_exam):
            if ('None' in vals or "Don't know" in vals) and len(vals)>1: raise ValueError('None or Don’t know cannot be combined with other choices')
        return self
class FollowUp(StrictModel):
    medicine_taken: Optional[YesNo] = None
    medicine_not_taken_reason: Optional[Literal['Cost','Forgot','Side-effects','Stopped']] = None
    new_feet_or_gums_problem: Optional[YesNo] = None
    low_episode: Optional[YesNo] = None
    new_symptoms_text: str = Field(default='',max_length=2000)
    @model_validator(mode='after')
    def validate_reason(self):
        if self.medicine_not_taken_reason and self.medicine_taken != 'No': raise ValueError('Reason requires medicine taken = No')
        return self
class SehatRecord(StrictModel):
    visit_date: date
    medical_unit_id: str
    opening: Opening
    baseline: Optional[Baseline] = None
    follow_up: Optional[FollowUp] = None
    glucose_value: Optional[float] = Field(default=None,gt=0,lt=1000)
    glucose_type: Literal['fasting','postprandial','random','unspecified'] = 'unspecified'
    systolic: Optional[int] = Field(default=None,gt=0,lt=300)
    diastolic: Optional[int] = Field(default=None,gt=0,lt=200)
    weight: Optional[float] = Field(default=None,gt=0,lt=500)
    observations: str = Field(default='',max_length=2000)
    medication_notes: str = Field(default='',max_length=2000)
    priority: Literal['RED','PURPLE','YELLOW','GREEN'] = 'GREEN'
    priority_reason: str = Field(default='',max_length=1000)
    follow_up_date: Optional[date] = None
    @model_validator(mode='after')
    def validate_record(self):
        if (self.systolic is None)!=(self.diastolic is None): raise ValueError('Both blood pressure values are required')
        if self.priority != 'GREEN' and not self.priority_reason: raise ValueError('Priority reason is required')
        if 'Yes' in self.opening.model_dump().values(): raise ValueError('Opening warning present: stop the form and seek immediate clinical assistance')
        return self
