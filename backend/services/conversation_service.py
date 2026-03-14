from services.intent_service import detect_intent, extract_phone, extract_department, generate_response
from services.hospital_info_service import answer_hospital_query
from services.appointment_service import book_appointment
from services.billing_service import check_billing
from services.lab_service import check_lab_reports
from database.connection import get_connection
from datetime import datetime

# ──── IN-MEMORY SESSION STORE ────

sessions = {}


def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = {
            "state": "welcome",
            "phone": None,
            "intent": None,
            "department_id": None,
            "last_info_topic": None,
            "history": []
        }
    return sessions[session_id]


def reset_session(session_id):
    sessions[session_id] = {
        "state": "welcome",
        "phone": None,
        "intent": None,
        "department_id": None,
        "last_info_topic": None,
        "history": []
    }
    return sessions[session_id]


def get_departments_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT department_id, name FROM departments")
    departments = cursor.fetchall()
    conn.close()
    return [{"id": d["department_id"], "name": d["name"]} for d in departments]


def process_message(session_id, user_text):
    """Main conversation handler — state machine that processes user input."""

    session = get_session(session_id)
    state = session["state"]
    user_text = user_text.strip()
    normalized_text = user_text.lower()

    # Log user message
    session["history"].append({"role": "user", "text": user_text})

    # Handle reset commands anytime
    if normalized_text in ("reset", "start over", "restart", "main menu", "go back", "menu"):
        session = reset_session(session_id)
        return _welcome_response(session, session_id)

    # ──── STATE: WELCOME ────
    if state == "welcome":
        if normalized_text in ("hi", "hello", "hey", "start", "begin"):
            return _welcome_response(session, session_id)
        session["state"] = "awaiting_intent"
        state = "awaiting_intent"

    # ──── STATE: AWAITING INTENT ────
    if state == "awaiting_intent":
        result = detect_intent(user_text)
        intent = result["intent"]
        session["intent_source"] = result.get("source", "keywords")

        info_result = answer_hospital_query(user_text, session.get("last_info_topic"))

        if intent == "hospital_info" and info_result:
            session["intent"] = intent
            session["last_info_topic"] = info_result["topic"]
            return _respond(
                session,
                session_id,
                info_result["message"],
                state="awaiting_intent",
                suggestions=info_result["suggestions"]
            )

        if intent is None:
            if info_result:
                session["intent"] = "hospital_info"
                session["last_info_topic"] = info_result["topic"]
                return _respond(
                    session,
                    session_id,
                    info_result["message"],
                    state="awaiting_intent",
                    suggestions=info_result["suggestions"]
                )

            return _respond(session, session_id,
                "I'm sorry, I didn't understand that. You can say things like:\n"
                "• \"Book an appointment\"\n"
                "• \"Check my lab reports\"\n"
                "• \"Check my bill\"\n"
                "• \"Emergency\"\n"
                "• \"Connect to reception\"\n"
                "• \"What services do you offer?\"",
                state="awaiting_intent",
                suggestions=["Book Appointment", "Lab Reports", "Billing", "Services", "Offers", "Reception"]
            )

        session["intent"] = intent

        # Extract any entities already in the text
        if result["entities"].get("phone"):
            session["phone"] = result["entities"]["phone"]
        if result["entities"].get("department_id"):
            session["department_id"] = result["entities"]["department_id"]

        return _route_intent(session, session_id, result)

    # ──── STATE: AWAITING PHONE ────
    elif state == "awaiting_phone":
        phone = extract_phone(user_text)
        if not phone:
            # Maybe user typed digits without exactly 10
            digits = ''.join(c for c in user_text if c.isdigit())
            if len(digits) == 10:
                phone = digits
            else:
                return _respond(session, session_id,
                    "Please provide a valid 10-digit phone number.",
                    state="awaiting_phone"
                )
        session["phone"] = phone
        return _after_phone(session, session_id)

    # ──── STATE: AWAITING DEPARTMENT ────
    elif state == "awaiting_department":
        dept_id = extract_department(user_text)
        if dept_id is None:
            departments = get_departments_list()
            dept_names = [d["name"] for d in departments]
            return _respond(session, session_id,
                "I couldn't identify that department. Please choose from:\n" +
                ", ".join(d["name"] for d in departments),
                state="awaiting_department",
                suggestions=dept_names
            )
        session["department_id"] = dept_id
        return _after_department(session, session_id)

    # ──── STATE: AWAITING EMERGENCY CONFIRM ────
    elif state == "awaiting_emergency_confirm":
        if any(w in user_text.lower() for w in ["yes", "confirm", "ok", "sure", "proceed"]):
            conn = get_connection()
            cursor = conn.cursor()
            e_type = session.get("emergency_type", "ambulance")
            cursor.execute("""
                INSERT INTO emergency_calls (phone, call_time, status, type)
                VALUES (?, ?, ?, ?)
            """, (session.get("phone", "unknown"), datetime.now().isoformat(), "connected", e_type))
            conn.commit()
            conn.close()
            return _respond(session, session_id,
                f"Emergency {e_type} services have been notified. Help is on the way. "
                "Please stay calm and stay on the line.",
                state="done",
                suggestions=["Main Menu"]
            )
        else:
            return _respond(session, session_id,
                "Emergency request cancelled. How else can I help you?",
                state="awaiting_intent",
                suggestions=["Book Appointment", "Lab Reports", "Billing", "Reception"]
            )

    # ──── STATE: DONE ────
    elif state == "done":
        session = reset_session(session_id)
        return _welcome_response(session, session_id)

    # Fallback
    session["state"] = "awaiting_intent"
    return _respond(session, session_id,
        "How can I help you today?",
        state="awaiting_intent",
        suggestions=["Book Appointment", "Lab Reports", "Billing", "Services", "Offers", "Reception"]
    )


# ──── INTERNAL HELPERS ────

def _welcome_response(session, session_id):
    return _respond(session, session_id,
        "Welcome to Springs Hospital! How can I help you today?\n\n"
        "You can say things like:\n"
        "• \"I'd like to book an appointment\"\n"
        "• \"Check my lab reports\"\n"
        "• \"What's my billing status?\"\n"
        "• \"I need emergency help\"\n"
        "• \"Connect me to reception\"\n"
        "• \"What services or offers are available?\"",
        state="awaiting_intent",
        suggestions=["Book Appointment", "Lab Reports", "Billing", "Services", "Offers", "Reception"]
    )


def _route_intent(session, session_id, result):
    """Route to the right flow based on detected intent."""
    intent = session["intent"]

    if intent == "appointment":
        if session["phone"] and session["department_id"]:
            return _do_booking(session, session_id)
        elif session["phone"]:
            return _ask_department(session, session_id)
        else:
            return _respond(session, session_id,
                "I'd be happy to help you book an appointment. "
                "First, please provide your 10-digit phone number.",
                state="awaiting_phone"
            )

    elif intent == "lab":
        if session["phone"]:
            return _do_lab_check(session, session_id)
        return _respond(session, session_id,
            "I'll check your lab reports. Please provide your 10-digit phone number.",
            state="awaiting_phone"
        )

    elif intent == "billing":
        if session["phone"]:
            return _do_billing_check(session, session_id)
        return _respond(session, session_id,
            "I'll check your billing status. Please provide your 10-digit phone number.",
            state="awaiting_phone"
        )

    elif intent == "emergency":
        e_type = result["entities"].get("emergency_type", "ambulance")
        session["emergency_type"] = e_type
        return _respond(session, session_id,
            f"You've selected {e_type} emergency services. "
            "Do you confirm you need emergency assistance? (Yes/No)",
            state="awaiting_emergency_confirm",
            suggestions=["Yes", "No"]
        )

    elif intent == "reception":
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reception_calls (phone, call_time, status)
            VALUES (?, ?, ?)
        """, (session.get("phone", "unknown"), datetime.now().isoformat(), "connected"))
        conn.commit()
        conn.close()
        return _respond(session, session_id,
            "I'm connecting you to the front desk now. Please hold while we transfer your call.\n\n"
            "Is there anything else I can help you with?",
            state="awaiting_intent",
            suggestions=["Book Appointment", "Lab Reports", "Billing", "Main Menu"]
        )

    elif intent == "hospital_info":
        info_result = answer_hospital_query(
            session["history"][-1]["text"],
            session.get("last_info_topic")
        )
        if info_result:
            session["last_info_topic"] = info_result["topic"]
            return _respond(
                session,
                session_id,
                info_result["message"],
                state="awaiting_intent",
                suggestions=info_result["suggestions"]
            )

    return _respond(session, session_id,
        "I'm not sure how to help with that. Could you try again?",
        state="awaiting_intent",
        suggestions=["Book Appointment", "Lab Reports", "Billing", "Services", "Offers", "Reception"]
    )


def _after_phone(session, session_id):
    """After phone is collected, route based on intent."""
    intent = session["intent"]

    if intent == "appointment":
        if session["department_id"]:
            return _do_booking(session, session_id)
        return _ask_department(session, session_id)

    elif intent == "lab":
        return _do_lab_check(session, session_id)

    elif intent == "billing":
        return _do_billing_check(session, session_id)

    # Shouldn't reach here, but handle gracefully
    return _respond(session, session_id,
        "Thank you. How can I help you?",
        state="awaiting_intent",
        suggestions=["Book Appointment", "Lab Reports", "Billing", "Services"]
    )


def _ask_department(session, session_id):
    departments = get_departments_list()
    dept_names = [d["name"] for d in departments]
    return _respond(session, session_id,
        "Which department would you like to book with?\n\n" +
        ", ".join(d["name"] for d in departments),
        state="awaiting_department",
        suggestions=dept_names
    )


def _after_department(session, session_id):
    return _do_booking(session, session_id)


def _do_booking(session, session_id):
    result = book_appointment(session["phone"], session["department_id"])
    return _respond(session, session_id,
        result["message"] + "\n\nIs there anything else I can help you with?",
        state="awaiting_intent",
        suggestions=["Lab Reports", "Billing", "Main Menu"]
    )


def _do_lab_check(session, session_id):
    result = check_lab_reports(session["phone"])
    msg = result["message"]
    if "reports" in result:
        for r in result["reports"]:
            msg += f"\n  • {r['report_name']} — {r['status']} ({r['date']})"
    return _respond(session, session_id,
        msg + "\n\nIs there anything else I can help you with?",
        state="awaiting_intent",
        suggestions=["Book Appointment", "Billing", "Main Menu"]
    )


def _do_billing_check(session, session_id):
    result = check_billing(session["phone"])
    return _respond(session, session_id,
        result["message"] + "\n\nIs there anything else I can help you with?",
        state="awaiting_intent",
        suggestions=["Book Appointment", "Lab Reports", "Main Menu"]
    )


def _respond(session, session_id, message, state, suggestions=None):
    """Build response and update session. Uses Groq to humanize if available."""
    session["state"] = state

    # Get the last user message for context
    last_user_text = ""
    for turn in reversed(session["history"]):
        if turn["role"] == "user":
            last_user_text = turn["text"]
            break

    # Use Groq to make the response conversational
    spoken_message = generate_response(message, last_user_text, session["history"])

    session["history"].append({"role": "system", "text": spoken_message})

    response = {
        "session_id": session_id,
        "state": state,
        "message": spoken_message,
        "intent": session.get("intent"),
        "intent_source": session.get("intent_source", "keywords"),
        "entities": {
            "phone": session.get("phone"),
            "department_id": session.get("department_id"),
        },
        "history": session["history"]
    }
    if suggestions:
        response["suggestions"] = suggestions
    return response
