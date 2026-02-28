from fastapi import FastAPI
from routes.ivr_routes import router
from database.models import create_tables, seed_data

app = FastAPI()

create_tables()
seed_data()

app.include_router(router, prefix="/ivr")

@app.get("/")
def begin():
  return { "message": "Hospital Ivr is running"}

# IVR Simulator / Frontend
# ↓
# FastAPI Routes (ivr_routes.py)
# ↓
# Services Layer (business logic)
# ↓
# Database Layer
# ↓
# SQLite Database

#  You call the hospital...

# "Thank you for calling Springs Hospital."

# Press 1 → APPOINTMENTS
# Press 2 → LAB REPORTS
# Press 3 → BILLING
# Press 4 → RECEPTION
# Press 5 → EMERGENCY

# If you Press 1 — APPOINTMENTS

# "You have reached the Appointments department."

# Press 1 → Book a New Appointment
# Press 2 → Go Back

#     ↓ (if Press 1)

# "Please enter your 10-digit phone number."

#     ↓ (after entering phone)

# "Select a department:"
#   Press 1 → General Medicine
#   Press 2 → Cardiology
#   Press 3 → Orthopedics
#   Press 4 → Pediatrics
#   Press 5 → Dermatology
#   Press 6 → ENT
#   Press 0 → Go Back

#     ↓ (after selecting department)

# ✅ "Your appointment has been confirmed.
#     A consultation fee of 500 rupees has been
#     added to your bill."

# ❌ "You already have an appointment today."

# ❌ "No doctors available in this department."

# If you Press 2 — LAB REPORTS

# "You have reached the Laboratory department."

# Press 1 → Check Your Lab Reports
# Press 2 → Go Back

#     ↓ (if Press 1)

# "Please enter your 10-digit phone number."

#     ↓

# ✅ "Found 2 lab report(s)." + report details

# ❌ "We could not find any lab reports."

# If you Press 3 — BILLING

# "You have reached the Billing department."

# Press 1 → Check Your Billing Status
# Press 2 → Go Back

#     ↓ (if Press 1)

# "Please enter your 10-digit phone number."

#     ↓

# ✅ "Your latest bill is 500 rupees.
#     Amount paid is 0 rupees.
#     Outstanding balance is 500 rupees."

# ❌ "We could not find any billing records."

# If you Press 4 — RECEPTION

# "You have reached the Reception desk.
#  How may we direct your call?"

# Press 1 → General Inquiry
#             → "Please hold while we connect you
#                to our general inquiry line."
#             →  Transfers call

# Press 2 → Speak to the Front Desk
#             → "Please hold while we transfer you.
#                Your call is important to us."
#             →  Transfers call

# Press 3 → Go Back

# If you Press 5 — EMERGENCY

# "You have reached Emergency Services.
#  If this is a life-threatening emergency..."

# Press 1 → Request an Ambulance
#             → "Please stay on the line.
#                Connecting to ambulance services."
#             →  Dials 108

# Press 2 → Report a Fire Emergency
#             → "Please stay on the line.
#                Connecting to fire services."
#             →  Dials 108

# Press 3 → Go Back