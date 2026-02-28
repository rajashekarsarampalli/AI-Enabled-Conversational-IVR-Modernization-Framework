from database.connection import get_connection
from database.patient_service import get_or_create_patient


def check_billing(phone):

    patient_id = get_or_create_patient(phone)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT total_amount, paid_amount, due_amount
        FROM billing
        WHERE patient_id = ?
        ORDER BY bill_date DESC
        LIMIT 1
        """, (patient_id,))

        bill = cursor.fetchone()

        if bill is None:

            return {
                "state": "billing_result",
                "message": "We could not find any billing records associated with your account."
            }

        return {
            "state": "billing_result",
            "message": f"Your latest bill is {bill['total_amount']} rupees. Amount paid is {bill['paid_amount']} rupees. Outstanding balance is {bill['due_amount']} rupees."
        }
    finally:
        conn.close()