from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_from_directory
import sqlite3
import os
import csv
from dotenv import load_dotenv
from pathlib import Path
import razorpay
import hmac, hashlib
from flask_cors import CORS

# Try to import error classes; fall back if SDK version doesn't expose them
try:
    from razorpay.errors import RazorpayError
except Exception:
    class RazorpayError(Exception): ...

# --------------------------------------------------------------------------------------
# App & Config
# --------------------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")  # change in prod

DB_PATH = "data/database.db"
CSV_PATH = "data/students.csv"

# Load RZP keys from key.env (local) or env (prod)
BASE_DIR = Path(__file__).resolve().parent
key_env_path = BASE_DIR / "key.env"
print("Loading keys from:", key_env_path)
load_dotenv(key_env_path, override=True)

RAZORPAY_KEY_ID = (os.getenv("RAZORPAY_KEY_ID") or "").strip()
RAZORPAY_KEY_SECRET = (os.getenv("RAZORPAY_KEY_SECRET") or "").strip()

# Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Simple helper
def _prefix(s): return (s[:8] + "…" + s[-4:]) if s else ""

print("[RZP] key_id:", _prefix(RAZORPAY_KEY_ID) or "<missing>")

# --------------------------------------------------------------------------------------
# CORS (Frontend origins)
# --------------------------------------------------------------------------------------
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5000")

CORS(
    app,
    resources={r"/*": {"origins": [FRONTEND_ORIGIN]}},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
# --------------------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------------------
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

def json_error(message, status=400, **extra):
    resp = {"ok": False, "error": message}
    resp.update(extra)
    return jsonify(resp), status

# --------------------------------------------------------------------------------------
# Static helpers (favicon to avoid 404)
# --------------------------------------------------------------------------------------
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

# --------------------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------------------
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

@app.route('/news')
def news(): return render_template('news.html')

@app.route('/achievements')
def achievements(): return render_template('achievements.html')

@app.route('/appointment')
def appointment(): return render_template('appointment.html')

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

# --------------------------------------------------------------------------------------
# Registration + Payment (pages & APIs)
# --------------------------------------------------------------------------------------
@app.route('/registration', methods=['GET','POST'])
def registration():
    if request.method == 'POST':
        data = request.get_json(force=True, silent=True) or {}
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO students (name,father_name,dob,class,academy_join,duration,contact,aadhaar,payment_id)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (data.get('name'), data.get('father_name'), data.get('dob'), data.get('class'),
              data.get('academy_join'), data.get('duration'), data.get('contact'),
              data.get('aadhaar'), data.get('payment_id')))
        conn.commit(); conn.close()
        return jsonify({'success': True, 'message': 'Registered and payment saved.'})
    return render_template('registration_payment.html')

@app.route('/razorpay')
def razorpay_page(): return render_template('razorpay.html')

@app.route('/get_key')
def get_key(): return jsonify({"key": RAZORPAY_KEY_ID})

# ---------- Create Order ----------
# POST /create_order -> { id, amount, currency, key }
@app.route("/create_order", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    try:
        # Ensure keys present
        if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
            return jsonify({"error": "Server misconfigured: missing Razorpay keys"}), 500

        # Expect paise from client; support 'rupees' fallback and small-value heuristic
        if "rupees" in data:
            amount_paise = int(data.get("rupees", 0)) * 100
        else:
            amount_paise = int(data.get("amount", 0))  # expected paise

        if 0 < amount_paise < 100:
            amount_paise = amount_paise * 100  # treat tiny values as rupees by mistake

        if amount_paise <= 0:
            return jsonify({"error": "Invalid amount (send paise, e.g., ₹1 -> 100)"}), 400

        order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1
        })
        return jsonify({
            "id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key": RAZORPAY_KEY_ID
        }), 201
    except RazorpayError as e:
        # Surface any SDK error details
        return jsonify({"error": "RazorpayError", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Exception", "message": str(e)}), 400

# Backward-compatible alias (if any old client still calls dash path)
@app.route("/create-order", methods=["POST"])
def create_order_alias():
    return create_order()

# ---------- Verify Payment ----------
# POST /verify-payment -> { ok: true } on success
@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    try:
        data = request.get_json(silent=True) or {}
        rp_payment_id = data.get('razorpay_payment_id')
        rp_order_id = data.get('razorpay_order_id')
        rp_signature = data.get('razorpay_signature')
        if not all([rp_payment_id, rp_order_id, rp_signature]):
            return jsonify({"ok": False, "error": "Missing parameters"}), 400

        body = f"{rp_order_id}|{rp_payment_id}".encode()
        expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, rp_signature):
            return jsonify({"ok": True}), 200
        return jsonify({"ok": False, "error": "signature_mismatch"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

# Payment pages (HTML)
@app.route("/payment_success_page")
def payment_success_page(): return render_template("payment_success.html")

@app.route("/payment_failed")
def payment_failed(): return render_template('payment_failed.html')

@app.route("/razorpay/callback", methods=["GET","POST"])
def razorpay_callback():
    rp_payment_id, rp_order_id, rp_signature = request.values.get("razorpay_payment_id"), request.values.get("razorpay_order_id"), request.values.get("razorpay_signature")
    if not all([rp_payment_id, rp_order_id, rp_signature]): return redirect("/payment_failed")
    body = f"{rp_order_id}|{rp_payment_id}".encode()
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, rp_signature): return redirect("/payment_success_page")
    return redirect("/payment_failed")

@app.route("/payment-lookup")
def payment_lookup():
    pid = request.args.get("pid")
    if not pid: return jsonify({"error": "pass ?pid=payment_id"}), 400
    try:
        data = razorpay_client.payment.fetch(pid)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --------------------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------------------
@app.route("/_rzp_diag")
def _rzp_diag():
    mode = "LIVE" if RAZORPAY_KEY_ID.startswith("rzp_live_") else ("TEST" if RAZORPAY_KEY_ID.startswith("rzp_test_") else "UNKNOWN")
    return {"ok": bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET), "mode": mode, "key_id_prefix": _prefix(RAZORPAY_KEY_ID)}

@app.route("/health")
def health():
    return {"ok": True, "service": "kvs-backend", "mode": ("LIVE" if RAZORPAY_KEY_ID.startswith("rzp_live_") else "TEST")}

# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    # Bind 0.0.0.0 so it’s reachable on LAN; disable debug in prod
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
