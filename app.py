from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import sqlite3
import os
import csv

app = Flask(__name__)
app.secret_key = "supersecretkey"  # needed for sessions

DB_PATH = "data/database.db"
CSV_PATH = "data/students.csv"

# ======================
# Database Initialization
# ======================
def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Students table
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

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT,
            password TEXT
        )
    """)

    conn.commit()

    # --- One-time CSV -> DB import (if table empty and CSV exists) ---
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM students")
        count = cur.fetchone()[0]
        if count == 0 and os.path.isfile(CSV_PATH):
            with open(CSV_PATH, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = []
                for r in reader:
                    rows.append((
                        r.get('Name'),
                        r.get('Father Name'),
                        r.get('DOB'),
                        r.get('Class'),
                        r.get('Academy Join'),
                        r.get('Duration'),
                        r.get('Mobile No.'),
                        r.get('Aadhaar'),
                        r.get('Payment ID')
                    ))
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

# ======================
# Helpers
# ======================
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
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/admission')
def admission():
    return render_template('admission.html')

@app.route('/routes')
def show_routes():
    return '<br>'.join([str(rule) for rule in app.url_map.iter_rules()])

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route("/test")
def test():
    return render_template("forgot.html")


# ----------------------
# Dashboard (Student List) - requires login
# ----------------------
@app.route('/dashboard')
def dashboard():
    if not login_required():
        return redirect(url_for('login'))

    conn = get_conn(sqlite3.Row)  # rows behave like dicts
    cur = conn.cursor()
    cur.execute("SELECT * FROM students ORDER BY sno DESC")
    students = cur.fetchall()
    conn.close()
    return render_template('dashboard.html', students=students)

# ----------------------
# User Authentication
# ----------------------
@app.route('/login', methods=['GET', 'POST'])
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
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash("Login successful!", "success")
            # If user came here from register link, send them to registration
            next_url = request.args.get("next")
            return redirect(next_url or url_for("dashboard"))
        else:
            flash("Invalid credentials!", "danger")

    return render_template("login.html")

@app.route('/signup', methods=['GET', 'POST'])
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
            cur.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                        (username, email, password))
            conn.commit()
            conn.close()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists!", "danger")

    return render_template("signup.html")

# Forgot password route
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        username = request.form["username"].strip()
        new_password = request.form["new_password"].strip()

        if not username or not new_password:
            flash("Please fill all fields", "danger")
            return redirect(url_for("forgot"))

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user:
            cursor.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
            conn.commit()
            conn.close()
            flash("Password updated successfully. Please login.", "success")
            return redirect(url_for("login"))
        else:
            conn.close()
            flash("Username not found", "danger")
            return redirect(url_for("forgot"))

    return render_template("forgot.html")

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# ----------------------
# Student Registration + Payment (requires login)
# ----------------------
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        # Expecting JSON from your registration_payment.js
        data = request.get_json(force=True, silent=True) or {}

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO students (name, father_name, dob, class, academy_join, duration, contact, aadhaar, payment_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('name'),
            data.get('father_name'),
            data.get('dob'),
            data.get('class'),
            data.get('academy_join'),
            data.get('duration'),
            data.get('contact'),
            data.get('aadhaar'),
            data.get('payment_id')
        ))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Registered and payment saved.'})

    # Show the registration + payment page
    return render_template('registration_payment.html')


# ----------------------
# Edit Student (requires login)
# ----------------------
@app.route('/edit/<int:sno>', methods=['GET', 'POST'])
def edit_student(sno):
    if not login_required():
        return redirect(url_for('login', next=url_for('edit_student', sno=sno)))

    conn = get_conn()
    cur = conn.cursor()

    if request.method == "POST":
        cur.execute("""
            UPDATE students SET
                name=?, father_name=?, dob=?, class=?, academy_join=?, duration=?, contact=?, aadhaar=?
            WHERE sno=?
        """, (
            request.form.get('name'),
            request.form.get('father_name'),
            request.form.get('dob'),
            request.form.get('class'),
            request.form.get('academy_join'),
            request.form.get('duration'),
            request.form.get('contact'),
            request.form.get('aadhaar'),
            sno
        ))
        conn.commit()
        conn.close()
        flash("Student updated.", "success")
        return redirect(url_for("dashboard"))

    # Fetch one for form
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE sno=?", (sno,))
    student = cur.fetchone()
    conn.close()

    if not student:
        return "Student not found", 404
    return render_template("edit_student.html", student=student)

# ----------------------
# Delete Student (requires login)
# ----------------------
@app.route('/delete/<int:sno>')
def delete_student(sno):
    if not login_required():
        return redirect(url_for('login', next=url_for('delete_student', sno=sno)))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE sno=?", (sno,))
    conn.commit()
    conn.close()
    flash("Student deleted.", "info")
    return redirect(url_for("dashboard"))

# ----------------------
# Other Pages
# ----------------------
@app.route('/news')
def news():
    return render_template('news.html')

@app.route('/achievements')
def achievements():
    return render_template('achievements.html')

@app.route('/appointment')
def appointment():
    return render_template('appointment.html')

# ======================
# Run App
# ======================
if __name__ == '__main__':
    app.run(debug=True, port=5001)
