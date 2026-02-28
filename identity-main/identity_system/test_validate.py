from app import validate_user_data

sample = {
    'type': 'Faculty',
    'first_name': 'Test',
    'last_name': 'User',
    'dob': '1990-01-01',
    'email': 'test@ex.com',
    'phone': '0123456789',
    'national_id': 'NID',
    'faculty_rank': 'Lecturer',
    'primary_department': 'CS',
    'staff_department': '',
    'job_title': ''
}

print('validation errors:', validate_user_data(sample))
