from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
import os
import csv
from dotenv import load_dotenv
from pathlib import Path
import razorpay
import hmac, hashlib

# Try to import error classes; fall back if SDK version doesn't expose them
try:
    from razorpay.errors import RazorpayError, BadRequestError, ServerError, SignatureVerificationError
except Exception:
    class RazorpayError(Exception): ...
    BadRequestError = ServerError = SignatureVerificationError = RazorpayError

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change in prod

DB_PATH = "data/database.db"
CSV_PATH = "data/students.csv"

# ======================
# 🔑 Razorpay LIVE KEYS (from key.env or Render env)
# ======================
BASE_DIR = Path(__file__).resolve().parent
key_env_path = BASE_DIR / "key.env"
print("Loading keys from:", key_env_path)
load_dotenv(key_env_path, override=True)

RAZORPAY_KEY_ID = (os.getenv("RAZORPAY_KEY_ID") or "").strip()
RAZORPAY_KEY_SECRET = (os.getenv("RAZORPAY_KEY_SECRET") or "").strip()
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ======================
# Database Initialization
# ======================
def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            sno INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            father_name TEXT,
            dob TEXT,
            class TEXT,
            academy_join TEXT,
            duration TEXT,
            contact TEXT,
            aadhaar TEXT,
            payment_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT,
            password TEXT
        )
    """)
    conn.commit()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM students")
        count = cur.fetchone()[0]
        if count == 0 and os.path.isfile(CSV_PATH):
            with open(CSV_PATH, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = [(r.get('Name'), r.get('Father Name'), r.get('DOB'), r.get('Class'),
                         r.get('Academy Join'), r.get('Duration'), r.get('Mobile No.'),
                         r.get('Aadhaar'), r.get('Payment ID')) for r in reader]
                if rows:
                    cur.executemany("""
                        INSERT INTO students
                        (name, father_name, dob, class, academy_join, duration, contact, aadhaar, payment_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, rows)
                    conn.commit()
                    print(f"Imported {len(rows)} students from CSV into SQLite.")
    except Exception as e:
        print("CSV import skipped/failed:", e)
    conn.close()

init_db()

# Helpers
def get_conn(row_factory=None):
    conn = sqlite3.connect(DB_PATH)
    if row_factory:
        conn.row_factory = row_factory
    return conn

def login_required():
    if not session.get('user_id'):
        flash("Please login first.", "warning")
        return False
    return True

# ======================
# Routes
# ======================
@app.route('/')
def home(): return render_template('index.html')

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/admission')
def admission(): return render_template('admission.html')

@app.route('/routes')
def show_routes(): return '<br>'.join([str(rule) for rule in app.url_map.iter_rules()])

@app.route('/contact')
def contact(): return render_template('contact.html')

@app.route("/test")
def test(): return render_template("forgot.html")

@app.route('/dashboard')
def dashboard():
    if not login_required(): return redirect(url_for('login'))
    conn = get_conn(sqlite3.Row)
    cur = conn.cursor()
    cur.execute("SELECT * FROM students ORDER BY sno DESC")
    students = cur.fetchall()
    conn.close()
    return render_template('dashboard.html', students=students)

# Authentication
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cur.fetchone()
        conn.close()
        if user:
            session['user_id'], session['username'] = user[0], user[1]
            flash("Login successful!", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))
        else:
            flash("Invalid credentials!", "danger")
    return render_template("login.html")

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not email or not password:
            flash("All fields are required.", "warning")
            return render_template("signup.html")
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username,email,password) VALUES (?,?,?)", (username,email,password))
            conn.commit(); conn.close()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists!", "danger")
    return render_template("signup.html")

@app.route("/forgot", methods=["GET","POST"])
def forgot():
    if request.method == "POST":
        username = request.form["username"].strip()
        new_password = request.form["new_password"].strip()
        if not username or not new_password:
            flash("Please fill all fields", "danger"); return redirect(url_for("forgot"))
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor(); cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        if user:
            cur.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
            conn.commit(); conn.close()
            flash("Password updated successfully. Please login.", "success")
            return redirect(url_for("login"))
        conn.close(); flash("Username not found", "danger")
        return redirect(url_for("forgot"))
    return render_template("forgot.html")

@app.route('/logout')
def logout():
    session.clear(); flash("You have been logged out.", "info"); return redirect(url_for("login"))

# Registration + Payment
@app.route('/registration', methods=['GET','POST'])
def registration():
    if request.method == 'POST':
        data = request.get_json(force=True, silent=True) or {}
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO students (name,father_name,dob,class,academy_join,duration,contact,aadhaar,payment_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (data.get('name'), data.get('father_name'), data.get('dob'), data.get('class'),
              data.get('academy_join'), data.get('duration'), data.get('contact'), data.get('aadhaar'), data.get('payment_id')))
        conn.commit(); conn.close()
        return jsonify({'success': True, 'message': 'Registered and payment saved.'})
    return render_template('registration_payment.html')

@app.route('/edit/<int:sno>', methods=['GET','POST'])
def edit_student(sno):
    if not login_required(): return redirect(url_for('login', next=url_for('edit_student', sno=sno)))
    conn = get_conn(); cur = conn.cursor()
    if request.method == "POST":
        cur.execute("""
            UPDATE students SET name=?, father_name=?, dob=?, class=?, academy_join=?, duration=?, contact=?, aadhaar=? WHERE sno=?
        """, (request.form.get('name'), request.form.get('father_name'), request.form.get('dob'),
              request.form.get('class'), request.form.get('academy_join'), request.form.get('duration'),
              request.form.get('contact'), request.form.get('aadhaar'), sno))
        conn.commit(); conn.close(); flash("Student updated.","success"); return redirect(url_for("dashboard"))
    conn.row_factory = sqlite3.Row; cur = conn.cursor(); cur.execute("SELECT * FROM students WHERE sno=?", (sno,))
    student = cur.fetchone(); conn.close()
    if not student: return "Student not found", 404
    return render_template("edit_student.html", student=student)

@app.route('/delete/<int:sno>')
def delete_student(sno):
    if not login_required(): return redirect(url_for('login', next=url_for('delete_student', sno=sno)))
    conn = get_conn(); cur = conn.cursor(); cur.execute("DELETE FROM students WHERE sno=?", (sno,))
    conn.commit(); conn.close(); flash("Student deleted.","info"); return redirect(url_for("dashboard"))

@app.route('/news')
def news(): return render_template('news.html')

@app.route('/achievements')
def achievements(): return render_template('achievements.html')

@app.route('/appointment')
def appointment(): return render_template('appointment.html')

# ======================
# Razorpay Endpoints
# ======================
@app.route('/razorpay')
def razorpay_page(): return render_template('razorpay.html')

@app.route('/get_key')
def get_key(): return jsonify({"key": RAZORPAY_KEY_ID})

@app.route("/create_order", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    try:
        amount_rupees = int(data.get("amount", 1))
        if amount_rupees <= 0:
            return jsonify({"error": "Invalid amount"}), 400
        order = razorpay_client.order.create({"amount": amount_rupees * 100, "currency": "INR", "payment_capture": 1})
        return jsonify({
            "id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key": RAZORPAY_KEY_ID   # 👈 include key here
        })
    except RazorpayError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/create-order", methods=["POST"])
def create_order_alias():
    return create_order()

@app.route("/payment_success", methods=["POST"])
def payment_success():
    data = request.get_json(silent=True) or {}
    rp_payment_id, rp_order_id, rp_signature = data.get('razorpay_payment_id'), data.get('razorpay_order_id'), data.get('razorpay_signature')
    if not all([rp_payment_id, rp_order_id, rp_signature]):
        return jsonify({"status": "Missing parameters"}), 400
    body = f"{rp_order_id}|{rp_payment_id}".encode()
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, rp_signature):
        return jsonify({"status": "Payment verified successfully"}), 200
    return jsonify({"status": "Signature mismatch"}), 400

@app.route("/payment_failed")
def payment_failed(): return render_template('payment_failed.html')

@app.route("/razorpay/callback", methods=["GET","POST"])
def razorpay_callback():
    rp_payment_id, rp_order_id, rp_signature = request.values.get("razorpay_payment_id"), request.values.get("razorpay_order_id"), request.values.get("razorpay_signature")
    if not all([rp_payment_id, rp_order_id, rp_signature]): return redirect("/payment_failed")
    body = f"{rp_order_id}|{rp_payment_id}".encode()
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, rp_signature): return redirect("/payment_success")
    return redirect("/payment_failed")

@app.route("/payment-lookup")
def payment_lookup():
    pid = request.args.get("pid"); 
    if not pid: return jsonify({"error": "pass ?pid=payment_id"}), 400
    try:
        data = razorpay_client.payment.fetch(pid)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/payment_success_page")
def payment_success_page(): return render_template("payment_success.html")

@app.route("/_razorpay_diag")
def _razorpay_diag():
    kid = RAZORPAY_KEY_ID or ""
    mode = "LIVE" if kid.startswith("rzp_live_") else ("TEST" if kid.startswith("rzp_test_") else "UNKNOWN")
    return {"key_id_prefix": (kid[:12] + "...") if kid else "", "mode": mode}, 200

@app.route("/health")
def health():
    return {"status": "ok", "mode": ("LIVE" if RAZORPAY_KEY_ID.startswith("rzp_live_") else "TEST")}

if __name__ == '__main__':
    app.run(debug=True, port=5001)
