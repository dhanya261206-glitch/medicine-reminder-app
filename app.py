from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import date

app = Flask(__name__)

# ---------------- DATABASE ----------------

conn = sqlite3.connect("medicine.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age TEXT,
    caregiver TEXT,
    phone TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    medicine_name TEXT,
    dosage TEXT,
    time TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    medicine_name TEXT,
    status TEXT,
    date TEXT
)
""")

conn.commit()

# ---------------- HOME ----------------

@app.route("/", methods=["GET", "POST"])
def home():

    message = ""

    if request.method == "POST":

        name = request.form["name"]
        age = request.form["age"]
        caregiver = request.form["caregiver"]
        phone = request.form["phone"]

        cursor.execute(
            """
            INSERT INTO patients
            (name, age, caregiver, phone)
            VALUES (?, ?, ?, ?)
            """,
            (name, age, caregiver, phone)
        )

        conn.commit()

        message = "Patient details saved successfully!"

    # Patients
    search = request.args.get("search", "")

    if search:

        cursor.execute("""
        SELECT id, name, age
        FROM patients
        WHERE name LIKE ?
        ORDER BY id DESC
        """,
        ('%' + search + '%',))

    else:

        cursor.execute("""
        SELECT id, name, age
        FROM patients
        ORDER BY id DESC
        """)
    patients = cursor.fetchall()

    # Medicines
    cursor.execute("""
    SELECT id, patient_id, medicine_name, dosage, time
    FROM medicines
    ORDER BY id DESC
    """)
    medicines = cursor.fetchall()

    # History grouped by patient
    cursor.execute("""
    SELECT id, name
    FROM patients
    ORDER BY name
    """)
    patient_records = cursor.fetchall()

    patient_history = {}

    for patient in patient_records:

        patient_id = patient[0]
        patient_name = patient[1]

        cursor.execute("""
        SELECT id, medicine_name, status, date
        FROM history
        WHERE patient_id=?
        ORDER BY id DESC
        """, (patient_id,))

        patient_history[patient_name] = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM patients")
        total_patients = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM medicines")
        total_medicines = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM history WHERE status='Taken'")
        total_taken = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM history WHERE status='Missed'")
        total_missed = cursor.fetchone()[0]

    return render_template(
        "index.html",
        message=message,
        patients=patients,
        medicines=medicines,
        patient_history=patient_history,
        total_patients=total_patients,
        total_medicines=total_medicines,
        total_taken=total_taken,
        total_missed=total_missed
    )

# ---------------- ADD MEDICINE ----------------

@app.route("/add_medicine", methods=["POST"])
def add_medicine():

    patient_id = request.form["patient_id"]
    medicine_name = request.form["medicine_name"]
    dosage = request.form["dosage"]
    med_time = request.form["time"]

    cursor.execute("""
    INSERT INTO medicines
    (patient_id, medicine_name, dosage, time)
    VALUES (?, ?, ?, ?)
    """,
    (
        patient_id,
        medicine_name,
        dosage,
        med_time
    ))

    conn.commit()

    return redirect("/")

# ---------------- MARK TAKEN ----------------

@app.route("/mark_taken/<int:medicine_id>")
def mark_taken(medicine_id):

    cursor.execute("""
    SELECT patient_id, medicine_name
    FROM medicines
    WHERE id=?
    """, (medicine_id,))

    medicine = cursor.fetchone()

    if medicine:

        cursor.execute("""
        INSERT INTO history
        (patient_id, medicine_name, status, date)
        VALUES (?, ?, ?, ?)
        """,
        (
            medicine[0],
            medicine[1],
            "Taken",
            str(date.today())
        ))

        conn.commit()

    return redirect("/")

# ---------------- MARK MISSED ----------------

@app.route("/mark_missed/<int:medicine_id>")
def mark_missed(medicine_id):

    today = str(date.today())

    cursor.execute("""
        SELECT patient_id, medicine_name
        FROM medicines
        WHERE id=?
    """, (medicine_id,))

    data = cursor.fetchone()

    patient_id = data[0]
    medicine_name = data[1]

    # get patient name
    cursor.execute("SELECT name FROM patients WHERE id=?", (patient_id,))
    patient_name = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO history (patient_id, medicine_name, status, date)
        VALUES (?, ?, ?, ?)
    """, (patient_id, medicine_name, "Missed", today))

    conn.commit()

    sms_text = send_sms_demo(patient_name, medicine_name, "MISSED")

    return render_template("sms_alert.html", sms=sms_text)


# ---------------- DELETE PATIENT ----------------

@app.route("/delete_patient/<int:patient_id>")
def delete_patient(patient_id):

    cursor.execute(
        "DELETE FROM history WHERE patient_id=?",
        (patient_id,)
    )

    cursor.execute(
        "DELETE FROM medicines WHERE patient_id=?",
        (patient_id,)
    )

    cursor.execute(
        "DELETE FROM patients WHERE id=?",
        (patient_id,)
    )

    conn.commit()

    return redirect("/")


# ---------------- DELETE MEDICINE ----------------

@app.route("/delete_medicine/<int:medicine_id>")
def delete_medicine(medicine_id):

    cursor.execute(
        "DELETE FROM medicines WHERE id=?",
        (medicine_id,)
    )

    conn.commit()

    return redirect("/")


# ---------------- DELETE HISTORY ----------------

@app.route("/delete_history/<int:history_id>")
def delete_history(history_id):

    cursor.execute(
        "DELETE FROM history WHERE id=?",
        (history_id,)
    )

    conn.commit()

    return redirect("/")


@app.route("/edit_patient/<int:patient_id>", methods=["GET", "POST"])
def edit_patient(patient_id):

    if request.method == "POST":

        name = request.form["name"]
        age = request.form["age"]
        caregiver = request.form["caregiver"]
        phone = request.form["phone"]

        cursor.execute("""
        UPDATE patients
        SET name=?, age=?, caregiver=?, phone=?
        WHERE id=?
        """,
        (
            name,
            age,
            caregiver,
            phone,
            patient_id
        ))

        conn.commit()

        return redirect("/")

    cursor.execute(
        "SELECT * FROM patients WHERE id=?",
        (patient_id,)
    )

    patient = cursor.fetchone()

    return render_template(
        "edit_patient.html",
        patient=patient
    )

from datetime import date
from tkinter import messagebox  # (ignore if already removed from Flask version)

def send_sms_demo(patient_name, medicine_name, status):

    today = str(date.today())

    sms_message = (
        f"📱 SMS ALERT SENT\n\n"
        f"Patient: {patient_name}\n"
        f"Medicine: {medicine_name}\n"
        f"Status: {status}\n"
        f"Date: {today}"
    )

    print(sms_message)  # shows in terminal

    return sms_message


@app.route("/edit_medicine/<int:medicine_id>",
           methods=["GET", "POST"])
def edit_medicine(medicine_id):

    if request.method == "POST":

        medicine_name = request.form["medicine_name"]
        dosage = request.form["dosage"]
        med_time = request.form["time"]

        cursor.execute("""
        UPDATE medicines
        SET medicine_name=?,
            dosage=?,
            time=?
        WHERE id=?
        """,
        (
            medicine_name,
            dosage,
            med_time,
            medicine_id
        ))

        conn.commit()

        return redirect("/")

    cursor.execute(
        "SELECT * FROM medicines WHERE id=?",
        (medicine_id,)
    )

    medicine = cursor.fetchone()

    return render_template(
        "edit_medicine.html",
        medicine=medicine
    )

@app.route("/check_reminders")
def check_reminders():

    from datetime import datetime

    current_time = datetime.now().strftime("%H:%M")

    cursor.execute("""
    SELECT medicine_name
    FROM medicines
    WHERE time=?
    """, (current_time,))

    medicines = cursor.fetchall()

    reminders = []

    for medicine in medicines:
        reminders.append(medicine[0])

    return {"reminders": reminders}


# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
