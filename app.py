from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
import os
 
app = Flask(__name__)

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

@app.route('/dashboard')
def dashboard():
    students = []
    try:
        with open('data/students.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                students.append(row)
    except FileNotFoundError:
        pass
    return render_template('dashboard.html', students=students)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        return jsonify({'message': 'Login attempted', 'username': username})
    return render_template('login.html')

# ==============================
# New merged Registration+Payment
# ==============================
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        data = request.get_json()

        # Find the next S.No
        sno = 1
        if os.path.exists('data/students.csv'):
            with open('data/students.csv', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                snos = [int(row['S.No']) for row in reader if row['S.No'].isdigit()]
                if snos:
                    sno = max(snos) + 1

        student = {
            'S.No': str(sno),
            'Name': data.get('name'),
            'Father Name': data.get('father_name'),
            'DOB': data.get('dob'),
            'Class': data.get('class'),
            'Academy Join': data.get('academy_join'),
            'Mobile No.': data.get('contact'),
            'Payment ID': data.get('payment_id')
        }

        os.makedirs('data', exist_ok=True)
        file_exists = os.path.isfile('data/students.csv')
        with open('data/students.csv', 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['S.No', 'Name', 'Father Name', 'DOB', 'Class', 'Academy Join', 'Mobile No.', 'Payment ID']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(student)

        return jsonify({'status': 'success', 'message': 'Registered and payment saved.'})

    return render_template('registration_payment.html')

@app.route('/edit/<sno>', methods=['GET', 'POST'])
def edit_student(sno):
    students = []
    with open('data/students.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            students.append(row)
    student = next((s for s in students if s['S.No'] == sno), None)
    if not student:
        return "Student not found", 404

    if request.method == 'POST':
        student['Name'] = request.form.get('name')
        student['Father Name'] = request.form.get('father_name')
        student['DOB'] = request.form.get('dob')
        student['Class'] = request.form.get('class')
        student['Academy Join'] = request.form.get('academy_join')
        student['Mobile No.'] = request.form.get('contact')
        with open('data/students.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['S.No', 'Name', 'Father Name', 'DOB', 'Class', 'Academy Join', 'Mobile No.', 'Payment ID']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(students)
        return redirect(url_for('dashboard'))
    return render_template('edit_student.html', student=student)

@app.route('/delete/<sno>')
def delete_student(sno):
    students = []
    with open('data/students.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            students.append(row)
    students = [s for s in students if s['S.No'] != sno]
    with open('data/students.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['S.No', 'Name', 'Father Name', 'DOB', 'Class', 'Academy Join', 'Mobile No.', 'Payment ID']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(students)
    return redirect(url_for('dashboard'))

@app.route('/sports')
def sports():
    return render_template('sports.html')

@app.route('/achievements')
def achievements():
    return render_template('achievements.html')

@app.route('/appointment')
def appointment():
    return render_template('appointment.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
