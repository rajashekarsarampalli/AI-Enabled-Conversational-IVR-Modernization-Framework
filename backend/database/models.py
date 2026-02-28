from database.connection import get_connection


def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON")

    # PATIENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE
    )
    """)

    # DEPARTMENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        department_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    # DOCTORS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        department_id INTEGER,
        FOREIGN KEY (department_id) REFERENCES departments(department_id)
    )
    """)

    # APPOINTMENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_id INTEGER,
        date TEXT,
        status TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
    )
    """)

    # LAB REPORTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_reports (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        report_name TEXT,
        status TEXT,
        date TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
    )
    """)

    # BILLING
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS billing (
        bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        appointment_id INTEGER,
        total_amount REAL,
        paid_amount REAL,
        due_amount REAL,
        bill_date TEXT,
        description TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
        FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
    )
    """)

    # EMERGENCY CALL LOGS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emergency_calls (
        call_id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        call_time TEXT,
        status TEXT,
        type TEXT
    )
    """)

    # RECEPTION CALL LOGS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reception_calls (
        call_id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        call_time TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()


def seed_data():

    conn = get_connection()
    cursor = conn.cursor()

    # SEED DEPARTMENTS
    departments = [
        "General Medicine",
        "Cardiology",
        "Orthopedics",
        "Pediatrics",
        "Dermatology",
        "ENT"
    ]

    for dept in departments:
        cursor.execute(
            "INSERT OR IGNORE INTO departments (name) VALUES (?)",
            (dept,)
        )

    # SEED DOCTORS
    doctors = [
        ("Dr. Sharma", 1),
        ("Dr. Patel", 2),
        ("Dr. Reddy", 3),
        ("Dr. Gupta", 4),
        ("Dr. Singh", 5),
        ("Dr. Rao", 6)
    ]

    for name, dept_id in doctors:
        cursor.execute(
            "SELECT doctor_id FROM doctors WHERE name = ?",
            (name,)
        )
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO doctors (name, department_id) VALUES (?, ?)",
                (name, dept_id)
            )

    conn.commit()
    conn.close()