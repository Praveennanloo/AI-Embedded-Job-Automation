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


def test_ats_analysis_embedded_linux_jd():
    optimizer = ATSOptimizer()
    profile = {"skills": ["C", "Embedded Linux", "Linux", "ARM", "GPIO", "Git", "Make"]}
    jd = "We need an Embedded Linux Engineer with Linux, ARM Cortex-A, Yocto, U-Boot, C, and Device Drivers experience. Required: Embedded Linux, Linux, GPIO, Git, Make. Preferred: Yocto, U-Boot."

    result = optimizer.analyze_ats(job_description=jd, profile=profile)
    assert 0 <= result["ats_score"] <= 100
    assert "Embedded Linux" in result["matched_keywords"]
    assert "Yocto" in result["matched_keywords"] or "U-Boot" in result["matched_keywords"] or "Yocto" in result["important_missing_keywords"] or "U-Boot" in result["important_missing_keywords"]
    assert isinstance(result["ats_recommendations"], list)
    assert "ats_score" in result
    assert "role_match" in result and "experience_match" in result


def test_ats_analysis_embedded_c_trainee_jd():
    optimizer = ATSOptimizer()
    profile = {"skills": ["C", "Embedded C", "UART", "GPIO"], "experience": "fresher"}
    jd = "Junior Embedded C Engineer. Required skills: Embedded C, C, UART, GPIO, SPI. Need a fresh graduate or trainee."

    result = optimizer.analyze_ats(job_description=jd, profile=profile)
    assert "Embedded C" in result["matched_keywords"]
    assert "SPI" in result["missing_keywords"] or "SPI" in result["important_missing_keywords"]
    assert result["experience_match"] in {True, False}
    assert result["ats_score"] <= 100


def test_ats_analysis_missing_and_duplicate_keywords_are_normalized():
    optimizer = ATSOptimizer()
    profile = {"skills": ["Embedded C", "linux", "arm", "gpio", "git", "make", "c++"]}
    jd = "Embedded C, embedded-c, Linux, ARM, GPIO, Git, Make, C++, C++, Linux!!!"

    result = optimizer.analyze_ats(job_description=jd, profile=profile)
    assert len(result["matched_keywords"]) == len(set(k.lower() for k in result["matched_keywords"]))
    assert "Embedded C" in result["matched_keywords"]
    assert "Linux" in result["matched_keywords"]
    assert "C++" in result["matched_keywords"]


def test_ats_empty_or_partial_jd_is_handled_deterministically():
    optimizer = ATSOptimizer()
    empty = optimizer.analyze_ats(job_description="", profile={"skills": ["C", "Linux"]})
    partial = optimizer.analyze_ats(job_description="We need someone with C and Linux.", profile={"skills": ["C"]})

    assert empty["ats_score"] == 0
    assert empty["matched_keywords"] == []
    assert partial["ats_score"] >= 0 and partial["ats_score"] <= 100
    assert partial["matched_keywords"] == [] or "C" in partial["matched_keywords"]


def test_ats_repeated_calls_are_deterministic():
    optimizer = ATSOptimizer()
    jd = "Embedded C, RTOS, FreeRTOS, ARM, STM32, UART, SPI, GPIO, Git"
    profile = {"skills": ["C", "Embedded C", "RTOS", "ARM", "STM32", "UART", "GPIO"], "experience": "fresher"}

    first = optimizer.analyze_ats(job_description=jd, profile=profile)
    second = optimizer.analyze_ats(job_description=jd, profile=profile)
    assert first == second


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
