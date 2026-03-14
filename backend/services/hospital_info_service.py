TOPIC_KEYWORDS = {
    "services": ["services", "service", "departments", "specialties", "specialities", "care", "treatments"],
    "offers": ["offers", "offer", "discount", "discounts", "package", "packages", "deal", "deals"],
    "timings": ["timing", "timings", "hours", "open", "close", "working hours", "when are you open"],
    "facilities": ["facility", "facilities", "rooms", "icu", "pharmacy", "ambulance", "admission"],
    "diagnostics": ["lab", "labs", "diagnostic", "diagnostics", "scan", "xray", "x-ray", "ecg", "reports", "tests"],
    "insurance": ["insurance", "cashless", "claim", "claims", "tpa", "coverage"],
}

DEPARTMENT_INFO = {
    "general medicine": "General Medicine handles fever, infections, diabetes follow-up, blood pressure care, and routine physician consultations.",
    "cardiology": "Cardiology supports heart checkups, ECG review, chest-pain evaluation, and follow-up for cardiac patients.",
    "orthopedics": "Orthopedics covers bone, joint, fracture, back-pain, and mobility-related consultations.",
    "pediatrics": "Pediatrics provides routine child consultations, fever care, growth monitoring, and child wellness visits.",
    "dermatology": "Dermatology helps with skin, acne, rash, pigmentation, and allergy-related consultations.",
    "ent": "ENT handles ear, nose, throat, sinus, and voice-related consultations.",
}

TOPIC_RESPONSES = {
    "services": (
        "We currently support General Medicine, Cardiology, Orthopedics, Pediatrics, Dermatology, and ENT. "
        "We also handle lab reports, billing help, reception support, and emergency assistance."
    ),
    "offers": (
        "Current demo offers include a full-body health checkup at 999 rupees, a cardiac screening package at 1499, "
        "a child wellness package at 799, and weekday dermatology consultations at 20 percent off."
    ),
    "timings": (
        "Our outpatient departments are available from 8 AM to 8 PM, Monday through Saturday. "
        "Lab collection runs from 7 AM to 7 PM daily, and emergency support is available 24 by 7."
    ),
    "facilities": (
        "We provide emergency support, ambulance coordination, diagnostics, reception help, consultation booking, and billing assistance. "
        "Patients can also get help with reports, front-desk guidance, and department routing."
    ),
    "diagnostics": (
        "Our diagnostics support includes routine lab tests, blood work, ECG, X-ray coordination, and report follow-up through the IVR."
    ),
    "insurance": (
        "We can guide patients on billing and insurance desk support. For exact cashless and TPA approval details, the front desk can confirm the active partners."
    ),
}

FOLLOW_UP_PHRASES = {
    "tell me more",
    "more",
    "what else",
    "anything else",
    "more details",
    "details",
}

SUGGESTIONS = {
    "services": ["Cardiology", "Diagnostics", "Timings", "Offers"],
    "offers": ["Timings", "Facilities", "Book Appointment", "Reception"],
    "timings": ["Offers", "Services", "Reception", "Book Appointment"],
    "facilities": ["Emergency", "Diagnostics", "Timings", "Reception"],
    "diagnostics": ["Lab Reports", "Timings", "Services", "Reception"],
    "insurance": ["Billing", "Reception", "Services", "Offers"],
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def _extract_department_topic(text: str):
    for department in DEPARTMENT_INFO:
        if department in text:
            return department
    if "heart" in text:
        return "cardiology"
    if any(word in text for word in ["bone", "joint", "fracture", "back pain"]):
        return "orthopedics"
    if any(word in text for word in ["child", "children", "baby", "kids"]):
        return "pediatrics"
    if any(word in text for word in ["skin", "acne", "rash"]):
        return "dermatology"
    if any(word in text for word in ["ear", "nose", "throat", "sinus"]):
        return "ent"
    return None


def _extract_topic(text: str, last_topic=None):
    department_topic = _extract_department_topic(text)
    if department_topic:
        return department_topic

    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return topic

    if text in FOLLOW_UP_PHRASES and last_topic:
        return last_topic

    if last_topic and text.startswith("what about"):
        remainder = text.replace("what about", "", 1).strip()
        if remainder:
            return _extract_topic(remainder, None) or _extract_department_topic(remainder) or last_topic

    if last_topic and len(text.split()) <= 3:
        return _extract_topic(f"{last_topic} {text}", None)

    return None


def answer_hospital_query(user_text: str, last_topic=None):
    text = _normalize(user_text)
    topic = _extract_topic(text, last_topic)
    if not topic:
        return None

    if topic in DEPARTMENT_INFO:
        message = (
            f"{DEPARTMENT_INFO[topic]} "
            "If you'd like, I can also help book an appointment in that department."
        )
        suggestions = ["Book Appointment", "Services", "Timings", "Offers"]
    else:
        message = TOPIC_RESPONSES[topic]
        suggestions = SUGGESTIONS.get(topic, ["Services", "Offers", "Timings", "Reception"])

    return {
        "topic": topic,
        "message": message,
        "suggestions": suggestions,
    }