import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_generate_resume_endpoint():
    payload = {
        "name": "Praveen Bolla",
        "email": "praveen@example.com",
        "phone": "+91 9876543210",
        "github": "https://github.com/Praveennanloo",
        "linkedin": "https://linkedin.com/in/praveen-bolla",
        "job_title": "Embedded Software Engineer",
        "company": "Bosch",
        "job_description": "We need an engineer skilled in Embedded C, RTOS, STM32, and CAN protocol.",
        "user_skills": ["Embedded C", "RTOS", "STM32", "UART"]
    }
    
    response = client.post("/api/generate-resume", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert "ats_score" in data
    assert "Embedded C" in data["matched_keywords"]
    assert "\\documentclass" in data["latex_code"]
