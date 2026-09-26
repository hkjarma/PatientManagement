from flask import Flask, render_template, request, redirect, url_for
import re
import sqlite3

app = Flask(__name__)
DB_NAME = "patients.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                mobile TEXT NOT NULL,
                sex TEXT NOT NULL,
                age INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

from datetime import datetime

@app.route('/dashboard', methods=['GET'])
def dashboard():
    # Get search parameters from the query string
    name = request.args.get('name', '').strip()
    mobile = request.args.get('mobile', '').strip()
    created_date = request.args.get('created_date', '').strip()

    # Base query
    query = "SELECT id, name, mobile, sex, age, created_at FROM patients WHERE 1=1"
    params = []

    # Add filters based on search parameters
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if mobile:
        query += " AND mobile LIKE ?"
        params.append(f"%{mobile}%")
    if created_date:
        query += " AND DATE(created_at) = ?"
        params.append(created_date)

    query += " ORDER BY id DESC"

    # Execute the query
    conn = get_db_connection()
    patients = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('dashboard.html', patients=patients)

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ""
    message_type = ""

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        mobile = (request.form.get('mobile') or '').strip()
        sex = (request.form.get('sex') or '').strip()
        age = request.form.get('age')

        if not name or len(name) > 100:
            message = "Please enter a valid patient name."
            message_type = "error"
        elif not re.fullmatch(r"[0-9+()\-\s]{7,20}", mobile):
            message = "Please enter a valid mobile number."
            message_type = "error"
        elif sex not in {"Male", "Female", "Other"}:
            message = "Please select a valid sex."
            message_type = "error"
        else:
            try:
                age_value = int(age)
            except (TypeError, ValueError):
                message = "Please enter a valid age."
                message_type = "error"
            else:
                if age_value < 0 or age_value > 120:
                    message = "Age must be between 0 and 120."
                    message_type = "error"
                else:
                    try:
                        conn = get_db_connection()
                        conn.execute(
                            "INSERT INTO patients (name, mobile, sex, age) VALUES (?, ?, ?, ?)",
                            (name, mobile, sex, age_value),
                        )
                        conn.commit()
                        message = "Patient registered successfully."
                        message_type = "success"
                    except Exception:
                        message = "Unable to save patient data. Please try again."
                        message_type = "error"
                    finally:
                        conn.close()

    conn = get_db_connection()
    patients = conn.execute(
        "SELECT id, name, mobile, sex, age, created_at FROM patients ORDER BY id DESC LIMIT 20"
    ).fetchall()
    conn.close()

    return render_template('index.html', patients=patients, message=message, message_type=message_type)


@app.route('/delete/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('index'))


@app.route('/edit/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    conn = get_db_connection()
    patient = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    conn.close()

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        mobile = (request.form.get('mobile') or '').strip()
        sex = (request.form.get('sex') or '').strip()
        age = request.form.get('age')

        if not name or len(name) > 100:
            return render_template('edit.html', patient=patient, message="Please enter a valid patient name.")
        elif not re.fullmatch(r"[0-9+()\-\s]{7,20}", mobile):
            return render_template('edit.html', patient=patient, message="Please enter a valid mobile number.")
        elif sex not in {"Male", "Female", "Other"}:
            return render_template('edit.html', patient=patient, message="Please select a valid sex.")
        else:
            try:
                age_value = int(age)
                if age_value < 0 or age_value > 120:
                    return render_template('edit.html', patient=patient, message="Age must be between 0 and 120.")
                conn = get_db_connection()
                conn.execute(
                    "UPDATE patients SET name = ?, mobile = ?, sex = ?, age = ? WHERE id = ?",
                    (name, mobile, sex, age_value, patient_id),
                )
                conn.commit()
                conn.close()
                return redirect(url_for('index'))
            except Exception:
                return render_template('edit.html', patient=patient, message="Unable to update patient data.")

    return render_template('edit.html', patient=patient)


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)