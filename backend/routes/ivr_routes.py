from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

from services.appointment_service import book_appointment
from services.lab_service import check_lab_reports
from services.billing_service import check_billing
from services.conversation_service import process_message, reset_session
from services.speech import text_to_speech, get_voices
from database.connection import get_connection

router = APIRouter()


class PhoneInput(BaseModel):
    phone: str


class BookingInput(BaseModel):
    phone: str
    department_id: int


class EmergencyInput(BaseModel):
    phone: str
    type: str


class ConversationInput(BaseModel):
    session_id: Optional[str] = None
    text: str


class TTSInput(BaseModel):
    text: str
    voice: str = "asteria"


# ──── LEVEL 0: MAIN MENU ────


@router.get("/start")
def start():

    return {
        "state": "main_menu",
        "message": "Thank you for calling Springs Hospital. Please listen carefully as our menu options may have changed.",
        "options": {
            "1": "Appointments",
            "2": "Lab Reports",
            "3": "Billing",
            "4": "Reception",
            "5": "Emergency"
        }
    }


# ──── PHONE COLLECTION ────


@router.get("/collect-phone")
def collect_phone():

    return {
        "state": "collect_phone",
        "message": "Please enter your 10-digit phone number followed by the pound key."
    }


# ──── LEVEL 1: APPOINTMENTS ────


@router.get("/appointments")
def appointments_menu():

    return {
        "state": "appointments_menu",
        "message": "You have reached the Appointments department. Please select from the following options.",
        "options": {
            "1": "Book a New Appointment",
            "2": "Return to Main Menu"
        }
    }


@router.get("/departments")
def list_departments():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT department_id, name FROM departments")
    departments = cursor.fetchall()
    conn.close()

    if not departments:
        return {
            "state": "departments",
            "message": "We're sorry, no departments are currently available. Please try again later."
        }

    options = {
        str(d["department_id"]): d["name"]
        for d in departments
    }

    options["0"] = "Return to Appointments Menu"

    return {
        "state": "departments",
        "message": "Please select the department you would like to book an appointment with.",
        "options": options
    }


@router.post("/book")
def book(data: BookingInput):

    return book_appointment(data.phone, data.department_id)


# ──── LEVEL 1: LAB REPORTS ────


@router.get("/lab")
def lab_menu():

    return {
        "state": "lab_menu",
        "message": "You have reached the Laboratory department. Please select from the following options.",
        "options": {
            "1": "Check Your Lab Reports",
            "2": "Return to Main Menu"
        }
    }


@router.post("/lab/check")
def lab_check(data: PhoneInput):

    return check_lab_reports(data.phone)


# ──── LEVEL 1: BILLING ────


@router.get("/billing")
def billing_menu():

    return {
        "state": "billing_menu",
        "message": "You have reached the Billing department. Please select from the following options.",
        "options": {
            "1": "Check Your Billing Status",
            "2": "Return to Main Menu"
        }
    }


@router.post("/billing/check")
def billing_check(data: PhoneInput):

    return check_billing(data.phone)


# ──── LEVEL 1: EMERGENCY ────


@router.get("/emergency")
def emergency_menu():

    return {
        "state": "emergency_menu",
        "message": "You have reached Emergency Services. If this is a life-threatening emergency, please select from the following.",
        "options": {
            "1": "Request an Ambulance",
            "2": "Report a Fire Emergency",
            "3": "Return to Main Menu"
        }
    }


@router.post("/emergency/confirm")
def emergency_confirm(data: EmergencyInput):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO emergency_calls
    (phone, call_time, status, type)
    VALUES (?, ?, ?, ?)
    """, (
        data.phone,
        datetime.now().isoformat(),
        "connected",
        data.type
    ))

    conn.commit()
    conn.close()

    return {
        "state": "emergency",
        "message": f"Please stay on the line. We are connecting you to {data.type} emergency services now.",
        "action": "transfer_call",
        "number": "108"
    }


# ──── LEVEL 1: RECEPTION ────


@router.get("/reception")
def reception_menu():

    return {
        "state": "reception_menu",
        "message": "You have reached the Reception desk. How may we direct your call?",
        "options": {
            "1": "General Inquiry",
            "2": "Speak to the Front Desk",
            "3": "Return to Main Menu"
        }
    }


@router.post("/reception/inquiry")
def reception_inquiry(data: PhoneInput):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reception_calls
    (phone, call_time, status)
    VALUES (?, ?, ?)
    """, (
        data.phone,
        datetime.now().isoformat(),
        "inquiry"
    ))

    conn.commit()
    conn.close()

    return {
        "state": "reception_inquiry",
        "message": "Please hold while we connect you to our general inquiry line.",
        "action": "transfer_call",
        "number": "+919876543210"
    }


@router.post("/reception/connect")
def reception_connect(data: PhoneInput):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reception_calls
    (phone, call_time, status)
    VALUES (?, ?, ?)
    """, (
        data.phone,
        datetime.now().isoformat(),
        "connected"
    ))

    conn.commit()
    conn.close()

    return {
        "state": "reception",
        "message": "Please hold while we transfer you to the front desk. Your call is important to us.",
        "action": "transfer_call",
        "number": "+919876543210"
    }


# ──── CONVERSATIONAL AI ENDPOINT ────


@router.post("/converse")
def converse(data: ConversationInput):
    session_id = data.session_id or str(uuid.uuid4())
    return process_message(session_id, data.text)


@router.post("/converse/reset")
def converse_reset(data: ConversationInput):
    session_id = data.session_id or str(uuid.uuid4())
    reset_session(session_id)
    return process_message(session_id, "hi")


# ──── DEEPGRAM TTS ────


@router.get("/tts/voices")
def tts_voices():
    return get_voices()


@router.post("/tts/speak")
def tts_speak(data: TTSInput):
    try:
        audio_bytes = text_to_speech(data.text, data.voice)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        return {"error": str(e)}