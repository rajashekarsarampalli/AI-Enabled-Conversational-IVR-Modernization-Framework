from database.connection import get_connection


def get_or_create_patient(phone):

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT patient_id FROM patients WHERE phone=?",
            (phone,)
        )

        row = cursor.fetchone()

        if row:
            return row["patient_id"]

        cursor.execute(
            "INSERT INTO patients(phone) VALUES(?)",
            (phone,)
        )

        patient_id = cursor.lastrowid

        conn.commit()

        return patient_id
    finally:
        conn.close()