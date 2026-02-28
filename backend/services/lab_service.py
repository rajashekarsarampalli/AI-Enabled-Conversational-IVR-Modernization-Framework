from database.connection import get_connection
from database.patient_service import get_or_create_patient


def check_lab_reports(phone):

    patient_id = get_or_create_patient(phone)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT report_name, status, date
        FROM lab_reports
        WHERE patient_id = ?
        ORDER BY date DESC
        """, (patient_id,))

        reports = cursor.fetchall()

        if not reports:

            return {
                "state": "lab_result",
                "message": "We could not find any lab reports associated with your account."
            }

        report_list = [
            {
                "report_name": r["report_name"],
                "status": r["status"],
                "date": r["date"]
            }
            for r in reports
        ]

        return {
            "state": "lab_result",
            "message": f"Found {len(reports)} lab report(s).",
            "reports": report_list
        }
    finally:
        conn.close()