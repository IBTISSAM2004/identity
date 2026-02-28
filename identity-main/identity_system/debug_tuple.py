from datetime import datetime
user_type='Faculty'
first_name='KSHG'
last_name='LSKJDG'
dob='2001-02-22'
place_of_birth=''
nationality=''
gender=''
email='KJAHF@GMAIL.COM'
phone=''
status='Pending'
national_id=''
diploma_type=''
diploma_year=None
entry_year=None
faculty_rank=''
primary_department=''
staff_department=''
job_title=''
staff_entry_date=''
params=( 'uid',user_type,first_name.strip(),last_name.strip(),dob,place_of_birth,nationality,gender,email.strip().lower(),phone,status,
         national_id,diploma_type,diploma_year,entry_year,
         faculty_rank,primary_department,
         staff_department,job_title,staff_entry_date)
print('len',len(params))
print(params)
