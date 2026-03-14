from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routes.ivr_routes import router
from database.models import create_tables, seed_data
import os

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    # Prefer repo-root .env, but also support backend/services/.env (current project layout)
    _here = os.path.dirname(__file__)
    load_dotenv(os.path.join(_here, "..", ".env"))
    load_dotenv(os.path.join(_here, "services", ".env"))
except Exception:
    pass

app = FastAPI()

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

create_tables()
seed_data()

app.include_router(router, prefix="/ivr")

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    @app.get("/")
    def begin():
        return {"message": "Hospital IVR is running"}

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