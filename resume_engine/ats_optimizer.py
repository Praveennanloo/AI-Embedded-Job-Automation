import re
from typing import List, Dict, Iterable, Tuple


class ATSOptimizer:
    EMBEDDED_CORE_SKILLS = [
        "Embedded C",
        "C++",
        "Assembly",
        "Embedded Linux",
        "RTOS",
        "FreeRTOS",
        "ARM Cortex-M",
        "ARM",
        "ARM Cortex-A",
        "STM32",
        "ESP32",
        "Microcontrollers",
        "UART",
        "SPI",
        "I2C",
        "CAN",
        "GPIO",
        "PWM",
        "ADC",
        "Device Drivers",
        "Linux",
        "BSP",
        "Yocto",
        "U-Boot",
        "GDB",
        "Oscilloscope",
        "Logic Analyzer",
        "Git",
        "CMake",
        "Make",
        "Makefile",
    ]

    KEYWORD_SYNONYMS = {
        "embedded c": "Embedded C",
        "embedded-c": "Embedded C",
        "embedded_c": "Embedded C",
        "c plus plus": "C++",
        "c++": "C++",
        "cpp": "C++",
        "freertos": "FreeRTOS",
        "free rtos": "FreeRTOS",
        "arm cortex m": "ARM Cortex-M",
        "arm cortex-m": "ARM Cortex-M",
        "arm cortex a": "ARM Cortex-A",
        "arm cortex-a": "ARM Cortex-A",
        "device driver": "Device Drivers",
        "device drivers": "Device Drivers",
        "linux kernel": "Linux",
        "yocto project": "Yocto",
        "yocto": "Yocto",
        "u boot": "U-Boot",
        "u-boot": "U-Boot",
        "makefile": "Make",
        "make file": "Make",
        "embedded linux": "Embedded Linux",
        "microcontroller": "Microcontrollers",
        "microcontrollers": "Microcontrollers",
        "micro-controller": "Microcontrollers",
        "linux": "Linux",
        "rtos": "RTOS",
        "arm": "ARM",
        "stm32": "STM32",
        "esp32": "ESP32",
        "uart": "UART",
        "spi": "SPI",
        "i2c": "I2C",
        "can": "CAN",
        "gpio": "GPIO",
        "git": "Git",
        "make": "Make",
        "c": "C",
    }

    @staticmethod
    def normalize_keyword(raw: str) -> str:
        if raw is None:
            return ""
        text = str(raw).strip()
        if not text:
            return ""

        lowered = text.lower().replace("_", " ")
        lowered = re.sub(r"[^a-z0-9+]+", " ", lowered)
        lowered = re.sub(r"\s+", " ", lowered).strip()
        if not lowered:
            return ""

        direct_lookup = ATSOptimizer.KEYWORD_SYNONYMS.get(lowered)
        if direct_lookup:
            return direct_lookup

        exact_match = next(
            (skill for skill in ATSOptimizer.EMBEDDED_CORE_SKILLS if skill.lower() == lowered),
            None,
        )
        if exact_match:
            return exact_match

        tokens = [part for part in lowered.split() if part]
        normalized_tokens = []
        for token in tokens:
            token_map = {
                "c": "C",
                "arm": "ARM",
                "linux": "Linux",
                "gpio": "GPIO",
                "spi": "SPI",
                "i2c": "I2C",
                "uart": "UART",
                "can": "CAN",
                "rtos": "RTOS",
                "git": "Git",
                "make": "Make",
                "cpp": "C++",
            }
            if token in token_map:
                normalized_tokens.append(token_map[token])
            else:
                normalized_tokens.append(token[:1].upper() + token[1:])
        return " ".join(normalized_tokens)

    def extract_keywords(self, job_description: str) -> List[str]:
        """Extract embedded-systems skills from a job description."""
        if not job_description:
            return []

        normalized_text = re.sub(r"[^a-zA-Z0-9+\s-]", " ", job_description.lower())
        normalized_text = re.sub(r"\s+", " ", normalized_text).strip()
        found = []
        seen = set()

        for skill in self.EMBEDDED_CORE_SKILLS:
            canonical = self.normalize_keyword(skill)
            search_values = [canonical.lower()]
            for alias, mapped in self.KEYWORD_SYNONYMS.items():
                if mapped == canonical:
                    search_values.append(alias)
            for value in search_values:
                candidate_values = {value.lower()}
                if "+" in value:
                    candidate_values.add(value.lower().replace("+", ""))
                if "-" in value:
                    candidate_values.add(value.lower().replace("-", " "))
                if any(term in normalized_text for term in candidate_values):
                    if canonical.lower() not in seen:
                        seen.add(canonical.lower())
                        found.append(canonical)
                    break

        return found

    @staticmethod
    def _candidate_skill_set(profile: dict) -> set[str]:
        skills = profile.get("skills", []) if isinstance(profile, dict) else []
        cleaned = set()
        for skill in skills or []:
            normalized = ATSOptimizer.normalize_keyword(skill)
            if normalized:
                cleaned.add(normalized.lower())
        return cleaned

    @staticmethod
    def _experience_matches(profile: dict, job_description: str) -> bool:
        if not isinstance(profile, dict):
            return True
        jd_text = (job_description or "").lower()
        profile_exp = str(profile.get("experience", "") or "").lower()

        if "fresher" in profile_exp or "graduate" in profile_exp or "trainee" in profile_exp or "intern" in profile_exp:
            return any(term in jd_text for term in ["fresher", "graduate", "entry level", "trainee", "intern", "junior"])
        if "5+ years" in profile_exp or "senior" in profile_exp or "experienced" in profile_exp:
            return any(term in jd_text for term in ["senior", "experienced", "lead", "5+ years", "5 years", "3+ years"])
        if any(term in jd_text for term in ["fresher", "graduate", "intern", "trainee", "junior"]):
            return True
        return True

    @staticmethod
    def _education_matches(profile: dict, job_description: str) -> bool:
        if not isinstance(profile, dict):
            return True
        jd_text = (job_description or "").lower()
        if not any(term in jd_text for term in ["btech", "be", "b.e", "ece", "electronics", "degree", "graduate", "engineering"]):
            return True
        education = str(profile.get("education", "") or "").lower()
        if not education:
            return True
        return any(term in education for term in ["btech", "be", "ece", "electronics", "engineering", "graduate", "degree"])

    @staticmethod
    def _role_from_jd(job_description: str) -> str:
        jd = (job_description or "").lower()
        if "embedded linux" in jd:
            return "Embedded Linux Engineer"
        if "embedded c" in jd or "embedded software" in jd:
            return "Embedded C Engineer"
        if "firmware" in jd:
            return "Firmware Engineer"
        if "rtos" in jd:
            return "RTOS Engineer"
        if "device driver" in jd or "linux driver" in jd:
            return "Device Driver Engineer"
        if "embedded" in jd:
            return "Embedded Engineer"
        return "Embedded Engineer"

    def analyze_ats(self, job_description: str, profile: dict = None) -> Dict[str, object]:
        profile = profile or {}
        job_description = job_description or ""

        jd_keywords = self.extract_keywords(job_description)
        if not jd_keywords:
            return {
                "ats_score": 0,
                "matched_keywords": [],
                "missing_keywords": [],
                "important_missing_keywords": [],
                "skill_matches": [],
                "skill_gaps": [],
                "experience_match": True,
                "education_match": True,
                "role_match": self._role_from_jd(job_description),
                "ats_recommendations": ["No ATS keywords detected in the job description."],
            }

        profile_skill_set = self._candidate_skill_set(profile)
        matched = []
        missing = []
        seen_matched = set()
        seen_missing = set()

        for keyword in jd_keywords:
            canonical_key = self.normalize_keyword(keyword).lower()
            if canonical_key in profile_skill_set:
                if canonical_key not in seen_matched:
                    seen_matched.add(canonical_key)
                    matched.append(self.normalize_keyword(keyword))
            else:
                if canonical_key not in seen_missing:
                    seen_missing.add(canonical_key)
                    missing.append(self.normalize_keyword(keyword))

        jd_lower = job_description.lower()
        required_match = re.search(r"required\s*:\s*(.*?)(?:preferred\s*:|$)", jd_lower, re.I | re.S)
        preferred_match = re.search(r"preferred\s*:\s*(.*)$", jd_lower, re.I | re.S)

        required_keywords = self.extract_keywords(required_match.group(1)) if required_match else list(jd_keywords)
        preferred_keywords = self.extract_keywords(preferred_match.group(1)) if preferred_match else []

        required_missing = [
            item for item in missing
            if self.normalize_keyword(item).lower() in {self.normalize_keyword(k).lower() for k in required_keywords}
        ]
        preferred_missing = [
            item for item in missing
            if self.normalize_keyword(item).lower() in {self.normalize_keyword(k).lower() for k in preferred_keywords}
        ]

        if not required_missing and "required" not in jd_lower and "must have" not in jd_lower:
            required_missing = list(missing)

        important_missing = []
        for item in required_missing + preferred_missing:
            if item not in important_missing:
                important_missing.append(item)

        optional_missing = [item for item in missing if item not in important_missing]

        ats_score = 0
        if jd_keywords:
            ats_score = int((len(matched) / len(jd_keywords)) * 100)
        ats_score = max(0, min(ats_score, 100))

        recommendations = []
        if important_missing:
            recommendations.append(f"Add important ATS keywords: {', '.join(important_missing[:5])}.")
        if optional_missing:
            recommendations.append(f"Optional keywords to consider: {', '.join(optional_missing[:3])}.")
        if not matched:
            recommendations.append("No direct ATS match was found for the current candidate profile.")
        if not recommendations:
            recommendations.append("Current profile aligns well with the job description.")

        return {
            "ats_score": ats_score,
            "matched_keywords": matched,
            "missing_keywords": missing,
            "important_missing_keywords": important_missing,
            "skill_matches": matched,
            "skill_gaps": missing,
            "experience_match": self._experience_matches(profile, job_description),
            "education_match": self._education_matches(profile, job_description),
            "role_match": self._role_from_jd(job_description),
            "ats_recommendations": recommendations,
        }

    def calculate_ats_match(
        self,
        resume_skills: List[str],
        jd_keywords: List[str],
    ) -> Dict[str, object]:
        """Compare resume skills against keywords extracted from the job description."""
        if not jd_keywords:
            return {
                "match_score": 100,
                "matched_keywords": list(resume_skills or []),
                "missing_keywords": [],
            }

        resume_set = {self.normalize_keyword(skill).lower() for skill in resume_skills if self.normalize_keyword(skill)}
        matched = []
        missing = []
        seen_matched = set()
        seen_missing = set()

        for keyword in jd_keywords:
            normalized = self.normalize_keyword(keyword)
            if not normalized:
                continue
            if normalized.lower() in resume_set:
                if normalized.lower() not in seen_matched:
                    seen_matched.add(normalized.lower())
                    matched.append(normalized)
            else:
                if normalized.lower() not in seen_missing:
                    seen_missing.add(normalized.lower())
                    missing.append(normalized)

        score = int((len(matched) / len(jd_keywords)) * 100)
        return {
            "match_score": max(0, min(score, 100)),
            "matched_keywords": matched,
            "missing_keywords": missing,
        }
