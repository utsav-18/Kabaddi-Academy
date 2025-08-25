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

# === FIXED AMOUNT ===
FIXED_AMOUNT_RUPEES = 199
FIXED_AMOUNT_PAISE = FIXED_AMOUNT_RUPEES * 100  # 19900

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

    # --- ensure new columns exist for kit/shoe sizes ---
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(students)")
        cols = {row[1] for row in cur.fetchall()}  # column names
        if "kit_size" not in cols:
            cur.execute("ALTER TABLE students ADD COLUMN kit_size TEXT")
        if "shoe_size" not in cols:
            cur.execute("ALTER TABLE students ADD COLUMN shoe_size INTEGER")
        conn.commit()
    except Exception as e:
        print("Column ensure failed:", e)

    # Optional CSV import for first run
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
            return redirect(request.args.get("next") or url_for("registration"))
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

        # --- validate kit_size ---
        allowed_sizes = {"XS","S","M","XL","XXL"}
        kit_size = (data.get('kit_size') or "").upper().strip()
        if kit_size not in allowed_sizes:
            return jsonify({'success': False, 'error': 'Invalid kit size'}), 400

        # --- validate shoe_size (integer only, positive) ---
        shoe_raw = str(data.get('shoe_size', '')).strip()
        if not shoe_raw.isdigit():
            return jsonify({'success': False, 'error': 'Invalid shoe size (integer only)'}), 400
        shoe_size = int(shoe_raw)
        if shoe_size <= 0:
            return jsonify({'success': False, 'error': 'Invalid shoe size (must be > 0)'}), 400

        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO students
                (name, father_name, dob, class, academy_join, duration,
                 contact, aadhaar, payment_id, kit_size, shoe_size)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get('name'), data.get('father_name'), data.get('dob'), data.get('class'),
            data.get('academy_join'), data.get('duration'), data.get('contact'),
            data.get('aadhaar'), data.get('payment_id'), kit_size, shoe_size
        ))
        conn.commit(); conn.close()
        return jsonify({'success': True, 'message': 'Registered and payment saved.'})

    # GET: show page with fixed amount provided
    return render_template('registration_payment.html',
                           amount=FIXED_AMOUNT_RUPEES,
                           fixed_amount=FIXED_AMOUNT_RUPEES)

@app.route('/razorpay')
def razorpay_page(): return render_template('razorpay.html')

@app.route('/get_key')
def get_key(): return jsonify({"key": RAZORPAY_KEY_ID})

# ---------- Create Order (FIXED ₹199 ONLY) ----------
@app.route("/create_order", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}

    # Reject attempts to override amount from client
    if ("amount" in data and int(data.get("amount") or 0) not in (0, FIXED_AMOUNT_PAISE)) or \
       ("rupees" in data and int(data.get("rupees") or 0) not in (0, FIXED_AMOUNT_RUPEES)):
        return jsonify({"error": f"Amount is locked to ₹{FIXED_AMOUNT_RUPEES} only."}), 400

    try:
        if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
            return jsonify({"error": "Server misconfigured: missing Razorpay keys"}), 500

        order = razorpay_client.order.create({
            "amount": FIXED_AMOUNT_PAISE,   # 19900 paise
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
        return jsonify({"error": "RazorpayError", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Exception", "message": str(e)}), 400

# Backward-compatible alias
@app.route("/create-order", methods=["POST"])
def create_order_alias():
    return create_order()

# ---------- Verify Payment ----------
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
        if not hmac.compare_digest(expected, rp_signature):
            return jsonify({"ok": False, "error": "signature_mismatch"}), 400

        # Optional extra check: payment fetch & amount verification
        try:
            payment_data = razorpay_client.payment.fetch(rp_payment_id)
            if int(payment_data.get("amount", -1)) != FIXED_AMOUNT_PAISE or payment_data.get("currency") != "INR":
                return jsonify({"ok": False, "error": "amount_mismatch"}), 400
        except Exception:
            pass

        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

# ---------- Payment result pages ----------
@app.get("/payment_success_page")
def payment_success_page():
    return render_template("payment_success.html", amount=FIXED_AMOUNT_RUPEES)

@app.get("/payment_failed")
def payment_failed():
    return render_template("payment_failed.html", message=f"Payment is fixed at ₹{FIXED_AMOUNT_RUPEES}.")

# Aliases so either style works
@app.get("/payment-success")
def payment_success_alias():
    return redirect(url_for("payment_success_page"))

@app.get("/payment-failed")
def payment_failed_alias():
    return redirect(url_for("payment_failed"))

# ---------- Optional: Razorpay callback route ----------
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
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
