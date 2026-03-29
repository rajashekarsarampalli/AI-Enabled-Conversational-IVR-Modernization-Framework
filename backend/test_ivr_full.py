import pytest
from fastapi.testclient import TestClient
from main import app
import os
from unittest.mock import patch

client = TestClient(app)

# ---- UNIT TESTS ----
def test_start_menu():
    resp = client.get("/ivr/start")
    assert resp.status_code == 200
    data = resp.json()
    assert "state" in data and data["state"] == "main_menu"
    assert "options" in data

def test_collect_phone():
    resp = client.get("/ivr/collect-phone")
    assert resp.status_code == 200
    assert "Please enter your 10-digit phone number" in resp.json()["message"]

# ---- INTEGRATION TESTS ----
def test_appointments_menu():
    resp = client.get("/ivr/appointments")
    assert resp.status_code == 200
    assert "Appointments department" in resp.json()["message"]

def test_departments_list():
    resp = client.get("/ivr/departments")
    assert resp.status_code == 200
    assert "departments" in resp.json()["state"] or "Please select the department" in resp.json()["message"]

# ---- E2E TESTS ----
def test_full_booking_flow(monkeypatch):
    # Simulate booking an appointment end-to-end
    # 1. Start
    resp = client.get("/ivr/start")
    assert resp.status_code == 200
    # 2. Appointments menu
    resp = client.get("/ivr/appointments")
    assert resp.status_code == 200
    # 3. List departments
    resp = client.get("/ivr/departments")
    assert resp.status_code == 200
    # 4. Book appointment (mock DB)
    with patch("services.appointment_service.book_appointment") as mock_book:
        mock_book.return_value = {"message": "Appointment booked!"}
        resp = client.post("/ivr/book", json={"phone": "9876543210", "department_id": 1})
        assert resp.status_code == 200
        msg = resp.json()["message"].lower()
        assert (
            "appointment has been confirmed" in msg
            or "already have an appointment scheduled" in msg
        )

# ---- PERFORMANCE TESTS ----
def test_ivr_start_performance():
    import time
    start = time.time()
    for _ in range(30):
        resp = client.get("/ivr/start")
        assert resp.status_code == 200
    elapsed = time.time() - start
    assert elapsed < 3  # 30 requests should be fast (mocked)

# ---- MORE INTEGRATION/E2E TESTS CAN BE ADDED FOR LAB, BILLING, EMERGENCY, RECEPTION ----
