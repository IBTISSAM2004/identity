from flask import Flask, request, render_template, redirect, jsonify
import sqlite3
from datetime import datetime
import os
import re
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

from dotenv import load_dotenv
import os
import smtplib
from email.message import EmailMessage

# ========================
# Load environment variables
# ========================
load_dotenv()
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# ========================
# Send confirmation email
# ========================
def send_confirmation(address, uid):
    msg = EmailMessage()
    msg['Subject'] = 'Identity Created'
    msg['From'] = EMAIL_USER
    msg['To'] = address
    msg.set_content(f"""Hello,

Your university identity has been successfully created.

Your ID: {uid}

If you did not request this identity, please contact administration.

University Identity Management System
""")
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"Email sent to {address}")
    except Exception as e:
        print(f"Email sending failed to {address}: {e}")

print("Current working directory:", os.getcwd())
print("Templates folder exists:", os.path.exists("templates"))

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.debug = True

# ========================
# Database Connection
# ========================
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ========================
# Status Lifecycle Rules
# ========================
VALID_TRANSITIONS = {
    'Pending': ['Active'],  # Pending can only go to Active
    'Active': ['Suspended', 'Inactive'],  # Active can go to Suspended or Inactive
    'Suspended': ['Active', 'Inactive'],  # Suspended can go to Active or Inactive
    'Inactive': ['Archived'],  # Inactive can only go to Archived
    'Archived': []  # Archived cannot transition anywhere (final state)
}

def is_valid_transition(current_status, new_status, status_changed_at=None):
    """Check if transition from current_status to new_status is allowed"""
    if current_status == new_status:
        return True  # Same status is allowed
    if current_status not in VALID_TRANSITIONS:
        return False  # Invalid current status
    if new_status not in VALID_TRANSITIONS[current_status]:
        return False  # Not in allowed transitions
    
    # Special rule: Inactive → Archived only after 5 years
    if current_status == 'Inactive' and new_status == 'Archived':
        if status_changed_at:
            try:
                changed_date = datetime.fromisoformat(status_changed_at)
                age_days = (datetime.now() - changed_date).days
                if age_days < 365 * 5:  # Less than 5 years
                    return False
            except:
                pass
    return True

# ========================
# Initialize Database
# ========================
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # base table
    cur.execute('''CREATE TABLE IF NOT EXISTS People (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    dob TEXT,
                    place_of_birth TEXT,
                    nationality TEXT,
                    gender TEXT,
                    email TEXT UNIQUE,
                    phone TEXT,
                    status TEXT,
                    status_changed_at TEXT
                )''')
    # additional optional columns for categories
    extra_cols = [
        'national_id TEXT',
        'diploma_type TEXT',
        'diploma_year INTEGER',
        'major TEXT',
        'entry_year INTEGER',
        'student_status TEXT',
        'faculty_rank TEXT',
        'appointment_start TEXT',
        'primary_department TEXT',
        'secondary_departments TEXT',
        'office_location TEXT',
        'phd_institution TEXT',
        'research_areas TEXT',
        'contract_type TEXT',
        'contract_start TEXT',
        'contract_end TEXT',
        'teaching_hours INTEGER',
        'staff_department TEXT',
        'job_title TEXT',
        'grade TEXT',
        'staff_entry_date TEXT'
    ]
    for col in extra_cols:
        try:
            cur.execute(f"ALTER TABLE People ADD COLUMN {col}")
        except Exception:
            pass  # column already exists

    # audit table for tracking changes
    cur.execute('''CREATE TABLE IF NOT EXISTS Audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT,
                    changed_at TEXT,
                    field TEXT,
                    old_value TEXT,
                    new_value TEXT
                )''')
    
    # Add status_changed_at column if not exists
    try:
        cur.execute("ALTER TABLE People ADD COLUMN status_changed_at TEXT")
    except Exception:
        pass  # column already exists
    conn.commit()
    conn.close()

# ========================
# Generate Unique ID
# ========================

  

def generate_id(user_type):
    year = datetime.now().year
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM People WHERE type=?", (user_type,))
    number = cur.fetchone()[0] + 1
    conn.close()
    prefix = {"Student":"STU", "PhD":"PHD", "Faculty":"FAC", "Staff":"STF"}.get(user_type,"TMP")
    return f"{prefix}{year}{number:05d}"

# ========================
# Home Page
# ========================
@app.route("/")
def index():
    return render_template("index.html")

# ========================
# Validate User Data
# ========================
def validate_user_data(data):
    """Validate user data before creating identity"""
    errors = []
    
    # Check for empty fields
    required_fields = ['first_name', 'last_name', 'email', 'dob', 'type']
    for field in required_fields:
        if not data.get(field) or str(data.get(field)).strip() == '':
            errors.append(f"{field.replace('_', ' ')} cannot be empty")

    # duplicate check: same name + dob + same type (allow different types for same person)
    if data.get('first_name') and data.get('last_name') and data.get('dob') and data.get('type'):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM People WHERE lower(first_name)=? AND lower(last_name)=? AND dob=? AND type=?",
            (data['first_name'].strip().lower(), data['last_name'].strip().lower(), data['dob'], data['type'])
        )
        if cur.fetchone()[0] > 0:
            errors.append("An identity with the same name, date of birth, and type already exists")
        conn.close()
    
    # Check first name (at least 2 characters)
    first_name = str(data.get('first_name', '')).strip()
    if first_name and len(first_name) < 2:
        errors.append("First name must be at least 2 characters")
    # also check last name exists (same requirement)
    last_name = str(data.get('last_name', '')).strip()
    if last_name and len(last_name) < 2:
        errors.append("Last name must be at least 2 characters")

    # type‑specific required fields
    if data.get('type') == 'Student':
        if not data.get('national_id') or not str(data.get('national_id')).strip():
            errors.append("Student national ID is required")
    if data.get('type') == 'Faculty':
        if not data.get('faculty_rank') or not str(data.get('faculty_rank')).strip():
            errors.append("Faculty rank is required")
        if not data.get('primary_department') or not str(data.get('primary_department')).strip():
            errors.append("Primary department is required")
    if data.get('type') == 'Staff':
        if not data.get('staff_department') or not str(data.get('staff_department')).strip():
            errors.append("Staff department is required")
        if not data.get('job_title') or not str(data.get('job_title')).strip():
            errors.append("Job title is required")
    
    # Check email validity
    email = str(data.get('email', '')).strip()
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if email and not re.match(email_regex, email):
        errors.append("Invalid email format")
    
    # Check if email is not duplicate
    if email:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM People WHERE email=? COLLATE NOCASE", (email.lower(),))
        count = cur.fetchone()[0]
        conn.close()
        if count > 0:
            errors.append("Email already exists")
    
    # Check phone number (numbers only)
    phone = str(data.get('phone', '')).strip()
    if phone and not phone.isdigit():
        errors.append("Phone must contain only numbers")
    
    # Check birth date
    dob = data.get('dob')
    if dob:
        try:
            dob_date = datetime.strptime(dob, '%Y-%m-%d')
            today = datetime.now()
            
            # Check if date is not in future
            if dob_date > today:
                errors.append("Birth date cannot be in the future")
            
            # Check age (>=16 for students)
            age = (today - dob_date).days / 365.25
            user_type = data.get('type')
            if user_type == 'Student' and age < 16:
                errors.append("You must be at least 16 years old")
        except ValueError:
            errors.append("Invalid date format")
    
    return errors

# ========================
# Create Identity
# ========================
@app.route("/create", methods=["GET","POST"])
def create():
    if request.method == "POST":
        user_type = request.form.get("type")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        dob = request.form.get("dob")
        place_of_birth = request.form.get("place_of_birth")
        nationality = request.form.get("nationality")
        gender = request.form.get("gender")
        email = request.form.get("email")
        phone = request.form.get("phone")
        status = "Pending"
        # category-specific values
        national_id = request.form.get("national_id")
        diploma_type = request.form.get("diploma_type")
        diploma_year = request.form.get("diploma_year")
        entry_year = request.form.get("entry_year")
        faculty_rank = request.form.get("faculty_rank")
        primary_department = request.form.get("primary_department")
        staff_department = request.form.get("staff_department")
        job_title = request.form.get("job_title")
        staff_entry_date = request.form.get("staff_entry_date")
        
        # Validate data
        validation_data = {
            'type': user_type,
            'first_name': first_name,
            'last_name': last_name,
            'dob': dob,
            'email': email,
            'phone': phone,
            'national_id': national_id,
            'faculty_rank': faculty_rank,
            'primary_department': primary_department,
            'staff_department': staff_department,
            'job_title': job_title
        }
        
        errors = validate_user_data(validation_data)
        if errors:
            return render_template("create.html", errors=errors)

        uid = generate_id(user_type)

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            now = datetime.now().isoformat()
            cur.execute("""INSERT INTO People (id,type,first_name,last_name,dob,place_of_birth,
                            nationality,gender,email,phone,status,status_changed_at,
                            national_id,diploma_type,diploma_year,entry_year,
                            faculty_rank,primary_department,
                            staff_department,job_title,staff_entry_date)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (uid,user_type,first_name.strip(),last_name.strip(),dob,place_of_birth,nationality,gender,email.strip().lower(),phone,status,now,
                         national_id,diploma_type,diploma_year,entry_year,
                         faculty_rank,primary_department,
                         staff_department,job_title,staff_entry_date))
            conn.commit()
            conn.close()
            # send confirmation email (print if failure)
            if email:
                send_confirmation(email.strip().lower(), uid)
            return render_template("success.html", 
                                 uid=uid,
                                 identity_type=user_type,
                                 first_name=first_name.strip(),
                                 last_name=last_name.strip(),
                                 email=email.strip().lower(),
                                 status=status,
                                 national_id=national_id,
                                 diploma_type=diploma_type,
                                 entry_year=entry_year,
                                 faculty_rank=faculty_rank,
                                 primary_department=primary_department,
                                 staff_department=staff_department,
                                 job_title=job_title,
                                 staff_entry_date=staff_entry_date)
        except Exception as e:
            return render_template("error.html", error=str(e))

    return render_template("create.html")

# ========================
# View All Identities
# ========================
@app.route("/view_all")
def view_all():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM People")
    people = cur.fetchall()
    conn.close()
    return render_template("view_all.html", people=people)

# ========================
# View Single Identity
# ========================
@app.route("/view/<uid>")
def view(uid):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM People WHERE id=?", (uid,))
    person = cur.fetchone()
    conn.close()
    if not person:
        return "Identity not found"
    # fetch audit history
    conn2 = get_db_connection()
    cur2 = conn2.cursor()
    cur2.execute("SELECT * FROM Audit WHERE person_id=? ORDER BY changed_at DESC", (uid,))
    audits = cur2.fetchall()
    conn2.close()
    return render_template("view.html", person=person, audits=audits)

# ========================
# Delete identity
# ========================
@app.route("/delete/<uid>", methods=["POST"])
def delete(uid):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM People WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return redirect("/view_all")

# ========================
# Edit Identity
# ========================
@app.route("/edit/<uid>", methods=["GET","POST"])
def edit(uid):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM People WHERE id=?", (uid,))
    person = cur.fetchone()
    if not person:
        conn.close()
        return "Identity not found"

    if request.method == "POST":
        # Check if trying to edit Archived status (not allowed)
        if person['status'] == 'Archived':
            conn.close()
            return render_template("edit.html", person=person, error="Cannot edit archived identities")
        
        # collect editable fields
        fields = ['first_name','last_name','status','national_id','diploma_type','diploma_year',
                  'entry_year','faculty_rank','primary_department','staff_department','job_title','staff_entry_date']
        changes = []
        new_status = request.form.get('status')
        old_status = person['status']
        
        # Validate status transition
        if new_status and new_status != old_status:
            if not is_valid_transition(old_status, new_status, person['status_changed_at']):
                conn.close()
                from_to = f"{old_status} → {new_status}"
                if old_status == 'Inactive' and new_status == 'Archived':
                    years_ago = (datetime.now() - datetime.fromisoformat(person['status_changed_at'])).days / 365
                    return render_template("edit.html", person=person, 
                                         error=f"Cannot transition {from_to}: Inactive status requires 5 years before archiving (current: {years_ago:.1f} years)")
                else:
                    return render_template("edit.html", person=person, 
                                         error=f"Invalid status transition: {from_to} is not allowed")
        
        for f in fields:
            new = request.form.get(f)
            old = person[f] if person[f] is not None else ''
            if str(new) != str(old):
                changes.append((f, old, new))
                if f == 'status':
                    # Also update status_changed_at when status changes
                    cur.execute(f"UPDATE People SET {f}=?, status_changed_at=? WHERE id=?", (new, datetime.now().isoformat(), uid))
                else:
                    cur.execute(f"UPDATE People SET {f}=? WHERE id=?", (new, uid))
        if changes:
            now = datetime.now().isoformat()
            for f,old,new in changes:
                cur.execute("INSERT INTO Audit (person_id,changed_at,field,old_value,new_value) VALUES (?,?,?,?,?)",
                            (uid, now, f, old, new))
        conn.commit()
        conn.close()
        return redirect(f"/view/{uid}")

    conn.close()
    return render_template("edit.html", person=person)

# ========================
# Search Identity
# ========================
@app.route("/search", methods=["GET","POST"])
def search():
    results = []
    if request.method == "POST":
        query = request.form.get("query","").strip()
        type_filter = request.form.get("type_filter","")
        status_filter = request.form.get("status_filter","")
        year_filter = request.form.get("year_filter","").strip()
        department_filter = request.form.get("department_filter","").strip()
        
        conn = get_db_connection()
        cur = conn.cursor()
        sql = "SELECT * FROM People WHERE 1=1"
        params = []
        
        # Search by name or email
        if query:
            sql += " AND (first_name LIKE ? OR last_name LIKE ? OR email LIKE ?)"
            params.extend([f"%{query}%"]*3)
        
        # Filter by type
        if type_filter:
            sql += " AND type=?"
            params.append(type_filter)
        
        # Filter by status
        if status_filter:
            sql += " AND status=?"
            params.append(status_filter)
        
        # Filter by year
        if year_filter:
            sql += " AND (entry_year=? OR diploma_year=?)"
            params.extend([year_filter]*2)
        
        # Filter by department
        if department_filter:
            sql += " AND (primary_department LIKE ? OR staff_department LIKE ?)"
            params.extend([f"%{department_filter}%"]*2)
        
        sql += " ORDER BY first_name, last_name"
        cur.execute(sql, tuple(params))
        results = cur.fetchall()
        conn.close()
    
    return render_template("search.html", results=results)

# ========================
# Run Application
# ========================
if __name__ == "__main__":
    init_db()
    print("Starting Flask server...")
    app.run(debug=True, host="127.0.0.1", port=5000)
   
   

