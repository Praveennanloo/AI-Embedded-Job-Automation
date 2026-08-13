import pytest
from resume_engine.ats_optimizer import ATSOptimizer
from resume_engine.latex_generator import LatexResumeGenerator

def test_ats_keyword_extraction():
    optimizer = ATSOptimizer()
    jd = "Looking for an Embedded Software Engineer skilled in Embedded C, RTOS, and STM32 microcontrollers."
    keywords = optimizer.extract_keywords(jd)
    
    assert "Embedded C" in keywords
    assert "RTOS" in keywords
    assert "STM32" in keywords

def test_ats_match_score():
    optimizer = ATSOptimizer()
    resume_skills = ["Embedded C", "RTOS", "UART"]
    jd_keywords = ["Embedded C", "RTOS", "CAN", "SPI"]
    
    result = optimizer.calculate_ats_match(resume_skills, jd_keywords)
    assert result["match_score"] == 50
    assert "Embedded C" in result["matched_keywords"]
    assert "CAN" in result["missing_keywords"]

def test_latex_resume_generation():
    generator = LatexResumeGenerator(
        name="Praveen Bolla",
        email="praveen@example.com",
        phone="+91 9876543210",
        github="https://github.com/Praveennanloo",
        linkedin="https://linkedin.com/in/praveen-bolla"
    )
    
    latex_output = generator.generate_latex(
        matched_skills=["Embedded C", "FreeRTOS", "ARM Cortex-M"],
        job_title="Embedded Engineer Trainee",
        company="Bosch"
    )
    
    assert "Praveen Bolla" in latex_output
    assert "Embedded Engineer Trainee" in latex_output
    assert "Bosch" in latex_output
    assert "\\documentclass" in latex_output
