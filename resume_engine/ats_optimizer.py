import re
from typing import List, Dict

class ATSOptimizer:
    EMBEDDED_CORE_SKILLS = [
        "Embedded C", "C++", "Assembly", "Embedded Linux", "RTOS", "FreeRTOS",
        "ARM Cortex-M", "STM32", "ESP32", "Microcontrollers", "UART", "SPI",
        "I2C", "CAN", "GPIO", "PWM", "ADC", "Device Drivers", "BSP", "GDB",
        "Oscilloscope", "Logic Analyzer", "Git", "CMake", "Makefile"
    ]

    def extract_keywords(self, job_description: str) -> List[str]:
        found_keywords = []
        text = job_description.lower()
        for skill in self.EMBEDDED_CORE_SKILLS:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text):
                found_keywords.append(skill)
        return found_keywords

    def calculate_ats_match(self, resume_skills: List[str], jd_keywords: List[str]) -> Dict[str, object]:
        if not jd_keywords:
            return {"match_score": 100, "matched": resume_skills, "missing": []}

        resume_set = {s.lower() for s in resume_skills}
        matched = [k for k in jd_keywords if k.lower() in resume_set]
        missing = [k for k in jd_keywords if k.lower() not in resume_set]

        score = int((len(matched) / len(jd_keywords)) * 100)

        return {
            "match_score": score,
            "matched_keywords": matched,
            "missing_keywords": missing
        }
