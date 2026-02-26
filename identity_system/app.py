from flask import Flask, request, render_template, redirect
import sqlite3
from datetime import datetime
import os

print("Current working directory:", os.getcwd())
print("Templates folder exists:", os.path.exists("templates"))

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.debug = True

# ========================
# قاعدة اتصال لكل طلب
# ========================
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ========================
# إنشاء الجداول
# ========================
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
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
                    status TEXT
                )''')
    conn.commit()
    conn.close()

# ========================
# توليد معرف فريد
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
# الصفحة الرئيسية
# ========================
@app.route("/")
def index():
    return render_template("index.html")

# ========================
# إنشاء هوية
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

        uid = generate_id(user_type)

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""INSERT INTO People (id,type,first_name,last_name,dob,place_of_birth,
                            nationality,gender,email,phone,status)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (uid,user_type,first_name,last_name,dob,place_of_birth,nationality,gender,email,phone,status))
            conn.commit()
            conn.close()
        except Exception as e:
            return f"Error creating identity: {e}"

        return f"Identity created! ID: {uid} <br><a href='/'>Home</a>"

    return render_template("create.html")

# ========================
# عرض جميع الهويات
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
# عرض هوية مفردة
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
    return render_template("view.html", person=person)

# ========================
# تعديل هوية
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
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        status = request.form.get("status")
        cur.execute("UPDATE People SET first_name=?, last_name=?, status=? WHERE id=?",
                    (first_name,last_name,status,uid))
        conn.commit()
        conn.close()
        return redirect(f"/view/{uid}")

    conn.close()
    return render_template("edit.html", person=person)

# ========================
# البحث عن هوية
# ========================
@app.route("/search", methods=["GET","POST"])
def search():
    results = []
    if request.method == "POST":
        query = request.form.get("query","")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM People WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ?",
                    (f"%{query}%","%{query}%","%{query}%"))
        results = cur.fetchall()
        conn.close()
    return render_template("search.html", results=results)

# ========================
# تشغيل التطبيق
# ========================
if __name__ == "__main__":
    init_db()
    print("Starting Flask server...")
    app.run(debug=True, host="127.0.0.1", port=5000)