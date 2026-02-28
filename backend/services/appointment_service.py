from database.connection import get_connection
from database.patient_service import get_or_create_patient

CONSULTATION_FEE = 500


def book_appointment(phone, department_id):
    
    patient_id = get_or_create_patient(phone)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # CHECK EXISTING (only today's confirmed appointments)
        cursor.execute("""
        SELECT d.name as doctor, a.date
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE a.patient_id = ?
        AND a.status = 'Confirmed'
        AND a.date = date('now')
        """, (patient_id,))

        existing = cursor.fetchone()

        if existing:

            return {
                "state": "booking_exists",
                "message": f"You already have an appointment scheduled with {existing['doctor']} on {existing['date']}. No further booking is required."
            }

        # GET DOCTOR
        cursor.execute("""
        SELECT doctor_id, name
        FROM doctors
        WHERE department_id = ?
        LIMIT 1
        """, (department_id,))

        doctor = cursor.fetchone()

        if doctor is None:

            return {
                "state": "error",
                "message": "We're sorry, no doctors are currently available in this department. Please try another department or call again later."
            }

        doctor_id = doctor["doctor_id"]

        # CREATE APPOINTMENT
        cursor.execute("""
        INSERT INTO appointments
        (patient_id, doctor_id, date, status)
        VALUES (?, ?, date('now'), 'Confirmed')
        """, (patient_id, doctor_id))

        appointment_id = cursor.lastrowid

        # CREATE BILL AUTOMATICALLY
        cursor.execute("""
        INSERT INTO billing
        (patient_id, appointment_id, total_amount, paid_amount, due_amount, bill_date, description)
        VALUES (?, ?, ?, ?, ?, date('now'), ?)
        """, (
            patient_id,
            appointment_id,
            CONSULTATION_FEE,
            0,
            CONSULTATION_FEE,
            "Consultation Fee"
        ))

        conn.commit()

        return {
            "state": "booking_confirmed",
            "message": f"Your appointment has been confirmed. A consultation fee of {CONSULTATION_FEE} rupees has been added to your bill. Thank you for choosing Springs Hospital."
        }
    finally:
        conn.close()