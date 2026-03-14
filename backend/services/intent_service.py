import re
import os
import json

# ──── GROQ CONFIG ────

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
USE_GROQ = bool(GROQ_API_KEY)

if USE_GROQ:
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)

GROQ_SYSTEM_PROMPT = """You are an intent detection system for a Hospital IVR (Springs Hospital).

Given a user message, return a JSON object with:
- "intent": one of ["appointment", "lab", "billing", "emergency", "reception", "hospital_info", null]
- "confidence": float 0.0 to 1.0
- "entities": object that may contain:
  - "phone": 10-digit phone number if mentioned, else null
  - "department": department name if mentioned, else null  
  - "department_id": integer 1-6 if department found, else null
  - "emergency_type": "ambulance" or "fire" if emergency, else null
    - "info_topic": one of ["services", "offers", "timings", "facilities", "diagnostics", "insurance"] if mentioned

Department mapping:
1=General Medicine, 2=Cardiology, 3=Orthopedics, 4=Pediatrics, 5=Dermatology, 6=ENT

Respond with ONLY valid JSON. No explanation."""

GROQ_RESPONSE_PROMPT = """You are Sara, a calm, friendly hospital phone assistant at Springs Hospital.
You are speaking on a live call, so every reply must sound like a real person talking.

Style:
- Keep it short and to the point: usually 1–2 sentences, maximum 3
- Sound warm, relaxed, and conversational; avoid corporate or robotic wording
- Use natural contractions (like "I'll", "we're", "you're") where they fit

Content rules:
- Keep all facts, numbers, dates, statuses, and next steps from the system message exactly
- Do not add medical advice or invent extra information
- Only repeat the hospital name when it actually helps clarity
- Do not recite menu text mechanically unless the system message clearly requires it
- Avoid generic filler like "Thank you for calling", "I understand your concern", or "Please listen carefully"
- If the system message asks a question, end with one clear spoken question
- Prefer simple spoken phrasing over written-style sentences"""

# ──── DEPARTMENT MAPPING ────

DEPARTMENT_MAP = {
    "general medicine": 1, "general": 1, "physician": 1, "fever": 1, "cold": 1, "cough": 1,
    "cardiology": 2, "heart": 2, "cardiac": 2, "chest pain": 2,
    "orthopedics": 3, "ortho": 3, "bone": 3, "fracture": 3, "joint": 3, "knee": 3, "back pain": 3,
    "pediatrics": 4, "pediatric": 4, "child": 4, "children": 4, "baby": 4, "kids": 4,
    "dermatology": 5, "skin": 5, "rash": 5, "acne": 5, "derma": 5,
    "ent": 6, "ear": 6, "nose": 6, "throat": 6, "sinus": 6,
}

# Words that need whole-word matching to avoid false positives (e.g. "ent" inside "appointment")
_WHOLE_WORD_DEPTS = {"ent", "general", "cold"}

# ──── INTENT KEYWORDS ────

INTENT_KEYWORDS = {
    "appointment": ["book", "appointment", "schedule", "doctor", "consult", "visit", "see a doctor", "checkup", "check up", "specialist", "need a doctor", "see a specialist"],
    "lab": ["lab", "report", "test", "result", "blood", "xray", "x-ray", "scan", "pathology", "laboratory"],
    "billing": ["bill", "billing", "payment", "pay", "due", "amount", "charge", "fee", "cost", "invoice", "balance"],
    "emergency": ["emergency", "ambulance", "urgent", "accident", "fire", "critical", "immediately", "help me"],
    "reception": ["reception", "front desk", "desk", "inquiry", "enquiry", "connect", "operator", "speak to someone", "talk to someone"],
    "hospital_info": ["services", "facilities", "offers", "discount", "discounts", "package", "packages", "timings", "hours", "open", "close", "insurance", "cashless", "departments"],
}


def detect_intent(text):
    """Detect user intent — uses Groq LLM if API key is set, otherwise falls back to keywords."""
    if USE_GROQ:
        result = _detect_intent_groq(text)
        if result and result.get("intent"):
            return result

    # Fallback to keyword-based detection
    return _detect_intent_keywords(text)


def _detect_intent_groq(text):
    """Use Groq LLM for smart intent detection."""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": GROQ_SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
            max_tokens=200,
        )

        raw = response.choices[0].message.content.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)

        # Validate and normalize
        valid_intents = {"appointment", "lab", "billing", "emergency", "reception", "hospital_info"}
        intent = parsed.get("intent")
        if intent and intent not in valid_intents:
            intent = None

        entities = parsed.get("entities", {})
        # Validate phone
        if entities.get("phone"):
            phone = ''.join(c for c in str(entities["phone"]) if c.isdigit())
            entities["phone"] = phone if len(phone) == 10 else None
        # Validate department_id
        if entities.get("department_id"):
            dept_id = entities["department_id"]
            if not isinstance(dept_id, int) or dept_id < 1 or dept_id > 6:
                entities["department_id"] = None

        return {
            "intent": intent,
            "confidence": round(float(parsed.get("confidence", 0.9)), 2),
            "entities": entities,
            "original_text": text,
            "source": "groq"
        }
    except Exception:
        # If Groq fails, fall through to keyword-based
        return None


def _detect_intent_keywords(text):
    """Fallback: keyword-based intent detection."""
    text_lower = text.lower().strip()

    intent = None
    confidence = 0.0
    entities = {}

    # Score each intent by counting keyword matches
    scores = {}
    for intent_name, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[intent_name] = score

    if scores:
        best_intent = max(scores, key=scores.get)
        total_keywords = len(INTENT_KEYWORDS[best_intent])
        intent = best_intent
        confidence = min(scores[best_intent] / max(total_keywords, 1), 1.0)

    # Extract phone number
    phone_match = re.search(r'\b(\d{10})\b', text)
    if phone_match:
        entities["phone"] = phone_match.group(1)

    # Extract department
    for dept_name, dept_id in DEPARTMENT_MAP.items():
        if dept_name in _WHOLE_WORD_DEPTS:
            if re.search(r'\b' + re.escape(dept_name) + r'\b', text_lower):
                entities["department"] = dept_name
                entities["department_id"] = dept_id
                break
        elif dept_name in text_lower:
            entities["department"] = dept_name
            entities["department_id"] = dept_id
            break

    # Extract emergency type
    if intent == "emergency":
        if "fire" in text_lower:
            entities["emergency_type"] = "fire"
        else:
            entities["emergency_type"] = "ambulance"

    return {
        "intent": intent,
        "confidence": round(confidence, 2),
        "entities": entities,
        "original_text": text,
        "source": "keywords"
    }


def extract_phone(text):
    """Extract a 10-digit phone number from text."""
    match = re.search(r'\b(\d{10})\b', text)
    return match.group(1) if match else None


def extract_department(text):
    """Extract department from text, return department_id or None."""
    text_lower = text.lower().strip()
    for dept_name, dept_id in DEPARTMENT_MAP.items():
        if dept_name in _WHOLE_WORD_DEPTS:
            if re.search(r'\b' + re.escape(dept_name) + r'\b', text_lower):
                return dept_id
        elif dept_name in text_lower:
            return dept_id
    # Also handle numeric input like "1", "2", etc.
    if text.strip().isdigit():
        dept_id = int(text.strip())
        if 1 <= dept_id <= 6:
            return dept_id
    return None


def generate_response(system_message, user_text, conversation_history=None):
    """Use Groq to make the bot response sound natural and conversational.
    Falls back to the original system_message if Groq is unavailable."""
    if not USE_GROQ:
        return system_message

    try:
        messages = [{"role": "system", "content": GROQ_RESPONSE_PROMPT}]

        # Add recent conversation history for context (last 4 turns)
        if conversation_history:
            recent = conversation_history[-4:]
            for turn in recent:
                role = "user" if turn["role"] == "user" else "assistant"
                messages.append({"role": role, "content": turn["text"]})

        # Ask Groq to rewrite the system message conversationally
        messages.append({
            "role": "user",
            "content": (
                f"The caller said: \"{user_text}\".\n\n"
                f"The system wants to reply with this information:\n\"{system_message}\".\n\n"
                "Rewrite this as if you are speaking to the caller in real time. "
                "Use plain, everyday language with no menu-style phrasing or numbered lists, "
                "and avoid repeating the same template phrases. "
                "Keep all facts, numbers, dates, and next steps exactly the same. "
                "Answer in 1–2 short sentences that sound natural when spoken aloud."
            ),
        })

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.9,
            max_tokens=180,
        )

        return response.choices[0].message.content.strip()
    except Exception:
        return system_message
