import app
from app import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

# attempt insert
cur.execute("""INSERT INTO People (id,type,first_name,last_name,dob,place_of_birth,
                            nationality,gender,email,phone,status,
                            national_id,diploma_type,diploma_year,entry_year,
                            faculty_rank,primary_department,
                            staff_department,job_title,staff_entry_date)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ('testid3','faculty','First','Last','2000-01-01','Place','Nation','M','a@b.com','1234567890','active',
             'NID','diploma','2020','2021','Professor','CS','Engineering','Teacher','2022-01-01'))
conn.commit()
print('insert succeeded, rowcount', cur.rowcount)
conn.close()
