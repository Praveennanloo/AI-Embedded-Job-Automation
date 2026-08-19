import re
from collections import Counter
from typing import Iterable, List
from urllib.parse import urlparse

from config.settings import settings
from models.job import Job


class JobFilter:

    AI_RANKING_MAX_ADJUSTMENT = 8.0
    AI_RANKING_MIN_ADJUSTMENT = -8.0
    AI_RANKING_CONFIDENCE_WEIGHT = 1.0

    PRIMARY_EMBEDDED_KEYWORDS = [
        "embedded",
        "embedded c",
        "embedded linux",
        "embedded software",
        "embedded systems",
        "firmware",
        "device driver",
        "linux device driver",
        "driver development",
        "rtos",
        "freertos",
        "linux kernel",
        "kernel driver",
        "arm",
        "microcontroller",
        "mcu",
        "iot",
        "uart",
        "spi",
        "i2c",
        "gpio",
        "esp32",
        "stm32",
        "bsp",
        "u-boot",
        "yocto",
        "buildroot",
        "electronics",
        "ece",
    ]

    SUPPORTING_KEYWORDS = [
        "c",
        "c++",
        "linux",
        "embedded c",
        "embedded systems",
        "firmware",
        "driver",
        "iot",
        "arm",
        "mcu",
        "microcontroller",
        "rtos",
        "freertos",
        "uart",
        "spi",
        "i2c",
        "gpio",
        "esp32",
        "stm32",
        "embedded linux",
        "embedded software",
        "yocto",
        "buildroot",
        "bsp",
        "u-boot",
        "linux kernel",
    ]

    ENTRY_LEVEL_KEYWORDS = [
        "fresher",
        "graduate",
        "graduate engineer",
        "entry level",
        "entry-level",
        "junior",
        "trainee",
        "internship",
        "intern",
        "internship program",
        "0-1 years",
        "0-2 years",
        "0 year",
        "0-2 year",
    ]

    HARDWARE_CONTEXT_KEYWORDS = [
        "embedded",
        "firmware",
        "driver",
        "linux kernel",
        "device driver",
        "linux device driver",
        "kernel driver",
        "bsp",
        "u-boot",
        "yocto",
        "buildroot",
        "arm",
        "mcu",
        "microcontroller",
        "stm32",
        "esp32",
        "uart",
        "spi",
        "i2c",
        "gpio",
        "iot",
        "rtos",
        "freertos",
        "embedded c",
        "embedded software",
    ]

    GENERIC_UNRELATED_KEYWORDS = [
        "software engineer",
        "linux administrator",
        "linux admin",
        "frontend",
        "backend",
        "web developer",
        "cloud engineer",
        "devops",
        "data engineer",
        "crypto",
        "sales",
        "mechanical",
        "civil",
        "it support",
    ]

    @staticmethod
    def normalize_text(value):
        if value is None:
            return ""
        cleaned = str(value).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @staticmethod
    def title_case(value):
        text = JobFilter.normalize_text(value)
        if not text:
            return ""

        tokens = re.split(r"(\s+|/|,)", text)
        formatted = []
        for token in tokens:
            if token in {" ", "/", ","}:
                formatted.append(token)
                continue
            part = token.strip()
            if not part:
                continue
            if part.isupper() and len(part) <= 4:
                formatted.append(part)
                continue
            formatted.append(part[:1].upper() + part[1:].lower())

        return "".join(formatted).strip()

    @staticmethod
    def normalize_url(value):
        candidate = JobFilter.normalize_text(value)
        if not candidate:
            return ""

        try:
            parsed = urlparse(candidate)
        except ValueError:
            return ""

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""

        return parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower()).geturl().rstrip("/")

    @staticmethod
    def normalize_skill(skill):
        value = JobFilter.normalize_text(skill)
        if not value:
            return ""
        return JobFilter.title_case(value)

    @staticmethod
    def normalize_salary(value):
        cleaned = JobFilter.normalize_text(value)
        if not cleaned:
            return ""
        return cleaned

    @staticmethod
    def normalize_employment_type(value):
        cleaned = JobFilter.normalize_text(value)
        if not cleaned:
            return ""
        lowered = cleaned.lower()
        mapping = {
            "full time": "Full-time",
            "full-time": "Full-time",
            "part time": "Part-time",
            "part-time": "Part-time",
            "contract": "Contract",
            "contractor": "Contract",
            "temporary": "Temporary",
            "internship": "Internship",
            "intern": "Internship",
            "freelance": "Freelance",
            "permanent": "Permanent",
        }
        if lowered in mapping:
            return mapping[lowered]
        return JobFilter.title_case(cleaned)

    @staticmethod
    def normalize_remote_status(value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        candidate = JobFilter.normalize_text(value).lower()
        if not candidate:
            return False
        return candidate in {"true", "yes", "remote", "hybrid", "remote-only", "work from home"}

    @staticmethod
    def normalize_application_url(value):
        candidate = JobFilter.normalize_url(value)
        if candidate:
            return candidate
        return JobFilter.normalize_text(value)

    def _job_text(self, job: Job) -> str:
        description = getattr(job, "description", "")
        skill_text = " ".join(job.skills or []) if job.skills else ""
        text_parts = [
            job.title,
            job.company,
            job.location,
            job.experience,
            skill_text,
            description,
        ]
        return " ".join(part for part in text_parts if part)

    def normalize_job(self, job: Job) -> Job:
        seen_skills = set()
        normalized_skills = []

        for skill in job.skills or []:
            cleaned = self.normalize_skill(skill)
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen_skills:
                continue
            seen_skills.add(key)
            normalized_skills.append(cleaned)

        normalized = Job(
            title=self.title_case(job.title),
            company=self.title_case(job.company),
            location=self.title_case(job.location),
            experience=self.title_case(job.experience),
            source=self.title_case(job.source),
            url=self.normalize_url(job.url),
            description=self.normalize_text(getattr(job, "description", "")),
            skills=normalized_skills,
            posted_date=self.normalize_text(job.posted_date),
            source_job_id=self.normalize_text(getattr(job, "source_job_id", "")) or "",
            remote=self.normalize_remote_status(getattr(job, "remote", False)) or "remote" in (self.title_case(job.location) or "").lower(),
            salary=self.normalize_salary(getattr(job, "salary", "")),
            job_type=self.normalize_text(getattr(job, "job_type", "")),
            employment_type=self.normalize_employment_type(getattr(job, "employment_type", "")),
            application_url=self.normalize_application_url(getattr(job, "application_url", "")),
            score=getattr(job, "score", 0),
            status=job.status,
            match_score=job.match_score,
            rejection_reasons=list(getattr(job, "rejection_reasons", []) or []),
            match_breakdown=dict(getattr(job, "match_breakdown", {}) or {}),
        )
        return normalized

    def clean_job(self, job: Job) -> Job:
        return self.normalize_job(job)

    def identify_role(self, job: Job) -> str:
        title = self.normalize_text(getattr(job, "title", ""))
        if title:
            return title
        description = self.normalize_text(getattr(job, "description", ""))
        if not description:
            return "Unknown role"
        return description[:180]

    def identify_required_skills(self, job: Job) -> List[str]:
        text = self._job_text(job).lower()
        skills = list(getattr(job, "skills", []) or [])
        normalized_skills = [self.normalize_skill(skill) for skill in skills if self.normalize_skill(skill)]
        inferred = []

        for keyword in self.PRIMARY_EMBEDDED_KEYWORDS + self.SUPPORTING_KEYWORDS:
            if keyword.lower() in text and keyword not in [s.lower() for s in normalized_skills]:
                inferred.append(self.title_case(keyword))

        combined = normalized_skills + inferred
        ordered = []
        seen = set()
        for item in combined:
            key = item.lower()
            if key and key not in seen:
                seen.add(key)
                ordered.append(item)
        return ordered[:10]

    def identify_experience_level(self, job: Job) -> str:
        text = self._job_text(job).lower()
        for keyword in self.ENTRY_LEVEL_KEYWORDS:
            if keyword in text:
                return self.title_case(keyword)

        for pattern in [r"0\s*[-–]?\s*1\s*years?", r"0\s*[-–]?\s*2\s*years?", r"1\s*[-–]\s*3\s*years?", r"3\s*[-–]\s*5\s*years?"]:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                return match.group(0).strip()

        experience = self.normalize_text(getattr(job, "experience", ""))
        return experience if experience else "Not specified"

    def identify_ece_relevance(self, job: Job) -> dict:
        text = self._job_text(job).lower()
        embedded_hits = self._find_keyword_hits(text, self.PRIMARY_EMBEDDED_KEYWORDS)
        support_hits = self._find_keyword_hits(text, self.SUPPORTING_KEYWORDS)
        if self.document_matches_target(job):
            relevance = "High" if embedded_hits or "embedded" in text else "Medium"
            return {
                "is_relevant": True,
                "level": relevance,
                "signals": embedded_hits[:5] + support_hits[:5],
            }
        return {
            "is_relevant": False,
            "level": "Low",
            "signals": embedded_hits[:5] + support_hits[:5],
        }

    def identify_embedded_relevance(self, job: Job) -> dict:
        return self.identify_ece_relevance(job)

    def match_against_profile(self, job: Job, profile: dict = None) -> dict:
        profile = profile or {}
        profile_skills = {
            self.normalize_skill(skill).lower()
            for skill in profile.get("skills", []) or []
            if self.normalize_skill(skill)
        }
        required_skills = self.identify_required_skills(job)
        required_skill_keys = {skill.lower() for skill in required_skills}
        overlap = sorted({skill for skill in required_skill_keys if skill in profile_skills})
        score = min(len(overlap) * 10, 30)

        profile_experience = self.normalize_text(profile.get("experience") or "")
        job_experience = self.normalize_text(getattr(job, "experience", ""))
        experience_match = bool(profile_experience and job_experience and profile_experience.lower() in job_experience.lower()) or bool(profile_experience and job_experience and "fresher" in profile_experience.lower() and "fresher" in job_experience.lower())

        return {
            "profile_skills": sorted(profile_skills),
            "required_skills": required_skills,
            "overlap": [self.title_case(skill) for skill in overlap],
            "experience_match": experience_match,
            "score": score,
        }

    def calculate_relevance_score(self, job: Job, profile: dict = None) -> int:
        score = self.calculate_score(job)
        profile_match = self.match_against_profile(job, profile)
        if profile_match["overlap"]:
            score += min(len(profile_match["overlap"]) * 8, 20)
        if profile_match["experience_match"]:
            score += 5
        return max(0, min(score, 100))

    def explain_why_job_matches(self, job: Job, profile: dict = None) -> str:
        cleaned = self.clean_job(job)
        role = self.identify_role(cleaned)
        skills = self.identify_required_skills(cleaned)
        experience = self.identify_experience_level(cleaned)
        embedded = self.identify_ece_relevance(cleaned)
        profile_match = self.match_against_profile(cleaned, profile)

        reasons = [f"Role identified as '{role}'"]
        if skills:
            reasons.append(f"Required skills include {', '.join(skills[:5])}")
        if experience and experience.lower() != "not specified":
            reasons.append(f"Experience level is {experience}")
        if embedded["is_relevant"]:
            reasons.append(f"ECE/embedded relevance is {embedded['level']} based on '{', '.join(embedded['signals'][:3])}'")
        if profile_match["overlap"]:
            reasons.append(f"It overlaps with your profile on {', '.join(profile_match['overlap'][:5])}")

        return "; ".join(reasons) if reasons else "The job does not provide enough clean signal to explain a strong match."

    def understand_job_description(self, job: Job, profile: dict = None) -> dict:
        cleaned = self.clean_job(job)
        return {
            "clean_job": cleaned,
            "role": self.identify_role(cleaned),
            "required_skills": self.identify_required_skills(cleaned),
            "experience_level": self.identify_experience_level(cleaned),
            "ece_relevance": self.identify_ece_relevance(cleaned),
            "profile_match": self.match_against_profile(cleaned, profile),
            "relevance_score": self.calculate_relevance_score(cleaned, profile),
            "why_match": self.explain_why_job_matches(cleaned, profile),
        }

    def analyze_job(self, job: Job, profile: dict = None) -> dict:
        return self.understand_job_description(job, profile)

    def _identify_role_category(self, job: Job) -> str:
        text = self._job_text(job).lower()
        if not text:
            return "Unrelated"

        category_rules = [
            ("Embedded Linux", ["embedded linux", "linux driver", "linux kernel", "bsp", "u-boot", "yocto", "device tree", "linux device driver"]),
            ("Embedded C", ["embedded c", "embedded-c", "microcontroller c", "firmware c"]),
            ("Firmware", ["firmware", "firmware engineer", "embedded firmware"]),
            ("IoT", ["iot", "internet of things", "sensor node", "embedded iot"]),
            ("RTOS", ["rtos", "freertos", "embedded rtos", "real time operating system"]),
            ("Device Drivers", ["device driver", "kernel driver", "linux device driver", "driver development"]),
            ("Embedded Software", ["embedded software", "embedded systems", "embedded engineer"]),
            ("Electronics", ["electronics", "ece", "hardware", "pcb", "schematic"]),
        ]

        for category, keywords in category_rules:
            if any(keyword in text for keyword in keywords):
                return category

        if "embedded" in text or "microcontroller" in text or "arm" in text or "stm32" in text or "esp32" in text:
            return "Embedded Systems"

        return "Unrelated"

    def _profile_skill_set(self, profile: dict = None):
        profile = profile or {}
        skills = profile.get("skills", []) or []
        normalized = []
        for skill in skills:
            cleaned = self.normalize_skill(skill)
            if cleaned:
                normalized.append(cleaned.lower())
        return set(normalized)

    def _job_skill_labels(self, job: Job):
        skill_aliases = {
            "c": "C",
            "c++": "C++",
            "embedded c": "Embedded C",
            "embedded linux": "Embedded Linux",
            "linux": "Linux",
            "rtos": "RTOS",
            "freertos": "FreeRTOS",
            "arm": "ARM",
            "microcontroller": "Microcontroller",
            "microcontrollers": "Microcontrollers",
            "uart": "UART",
            "spi": "SPI",
            "i2c": "I2C",
            "can": "CAN",
            "gpio": "GPIO",
            "device driver": "Device Drivers",
            "device drivers": "Device Drivers",
            "u-boot": "U-Boot",
            "yocto": "Yocto",
            "git": "Git",
            "make": "Make",
            "python": "Python",
            "esp32": "ESP32",
            "stm32": "STM32",
            "iot": "IoT",
            "embedded systems": "Embedded Systems",
            "embedded software": "Embedded Software",
            "firmware": "Firmware",
        }

        detected = []
        seen = set()
        for skill in getattr(job, "skills", []) or []:
            label = self.normalize_skill(skill)
            if not label:
                continue
            key = label.lower()
            mapped = skill_aliases.get(key, label)
            if mapped.lower() not in seen:
                seen.add(mapped.lower())
                detected.append(mapped)

        text = self._job_text(job).lower()
        for alias, label in skill_aliases.items():
            if alias in text and label.lower() not in seen:
                seen.add(label.lower())
                detected.append(label)

        return detected

    def _experience_level(self, job: Job) -> str:
        text = self._job_text(job).lower()
        candidate = self.normalize_text(getattr(job, "experience", "")).lower()

        if any(term in text for term in ["fresher", "graduate engineer", "graduate", "entry level", "entry-level", "trainee", "internship", "intern"]):
            for term in ["fresher", "graduate engineer", "graduate", "entry level", "entry-level", "trainee", "internship", "intern"]:
                if term in text:
                    return self.title_case(term) if term != "entry level" else "Entry Level"

        if re.search(r"0\s*[-–]?\s*1\s*years?", text):
            return "0-1 years"
        if re.search(r"0\s*[-–]?\s*2\s*years?", text):
            return "0-2 years"
        if re.search(r"1\s*[-–]\s*2\s*years?", text):
            return "1-2 years"
        if re.search(r"\b5\+\s*years?\b|\b5\s*\+\s*years?\b|\b5\+\b", text):
            return "5+ years"
        if re.search(r"\b[2-4]\s*[-–]\s*[4-9]\s*years?\b|\b[2-4]\s*years?\b", text):
            return "Experienced"

        if candidate:
            return self.title_case(candidate)
        return "Not specified"

    def _location_match(self, job: Job) -> bool:
        location = self.normalize_text(getattr(job, "location", ""))
        if not location:
            return True
        reduced = location.lower()
        if getattr(job, "remote", False) or any(indicator in reduced for indicator in ["remote", "home based", "worldwide", "global"]):
            return True
        allowed = [keyword.lower() for keyword in settings.LOCATION_KEYWORDS]
        return any(keyword in reduced for keyword in allowed)

    def _determine_rejection_reasons(self, job: Job, role_category: str, matched_skills: list[str], profile_skills: set[str]) -> list[str]:
        reasons = []
        text = self._job_text(job).lower()

        if role_category == "Unrelated":
            reasons.append("Role is unrelated to embedded, firmware, or ECE work")
        elif not matched_skills:
            reasons.append("No strong skill overlap with the target ECE embedded profile")

        if not self.document_matches_target(job):
            reasons.append("No strong embedded or hardware-relevant Linux context")

        if settings.REQUIRE_ENTRY_LEVEL and not self.is_entry_level_or_intern(job):
            reasons.append("Experience requirement is not suitable for an ECE fresher target")

        if not self._location_match(job):
            reasons.append("Location is outside the allowed embedded target area")

        if profile_skills and matched_skills:
            missing = sorted(profile_skills - {skill.lower() for skill in matched_skills})
            if missing:
                reasons.append(f"Missing key profile skills: {', '.join(sorted(missing)[:3])}")

        return list(dict.fromkeys(reasons))

    def _experience_mismatch_penalty(self, profile: dict = None, experience_level: str = "") -> int:
        profile_text = self.normalize_text((profile or {}).get("experience", "")).lower()
        if not profile_text:
            return 0

        fresher_profile = any(token in profile_text for token in ["fresher", "entry", "trainee", "graduate", "intern"])
        if not fresher_profile:
            return 0

        level = self.normalize_text(experience_level).lower()
        if any(token in level for token in ["5+ years", "experienced", "senior", "lead", "manager"]):
            return 30
        if any(token in level for token in ["2-3 years", "3-5 years", "4 years", "5 years"]):
            return 20
        return 0

    def _ai_enrich_analysis(self, job: Job, profile: dict = None, orchestrator=None) -> dict:
        if orchestrator is None:
            try:
                from ai_engine.ai_orchestrator import AIConfig, AIOrchestrator
                from ai_engine import build_default_ai_registry
                from config.settings import settings

                if not getattr(settings, "AI_ENABLED", False):
                    return {"enabled": False, "status": "disabled"}

                registry = build_default_ai_registry()
                config = AIConfig(
                    enabled=True,
                    default_provider=getattr(settings, "AI_PROVIDER", "openai"),
                    required_fields=["result", "status"],
                )
                orchestrator = AIOrchestrator(config=config, registry=registry)
            except Exception:
                return {"enabled": False, "status": "disabled"}

        try:
            payload = {
                "job_title": getattr(job, "title", ""),
                "company": getattr(job, "company", ""),
                "description": getattr(job, "description", ""),
                "skills": list(getattr(job, "skills", []) or []),
                "experience_requirement": getattr(job, "experience", ""),
                "location": getattr(job, "location", ""),
                "employment_type": getattr(job, "employment_type", ""),
                "remote_status": bool(getattr(job, "remote", False)),
                "profile": profile or {},
            }
            response = orchestrator.run(task="job_description_understanding", payload=payload)
            if not response.success or not isinstance(response.payload, dict):
                return {
                    "enabled": True,
                    "status": "fallback",
                    "provider": getattr(response, "provider", "unknown"),
                    "reason": getattr(response, "error", "AI analysis failed"),
                }

            ai_payload = response.payload.get("result", response.payload)
            if not isinstance(ai_payload, dict):
                return {
                    "enabled": True,
                    "status": "fallback",
                    "provider": getattr(response, "provider", "unknown"),
                    "reason": "Malformed AI output",
                }

            if "status" not in ai_payload and "role_relevance" not in ai_payload and "candidate_suitability" not in ai_payload:
                return {
                    "enabled": True,
                    "status": "fallback",
                    "provider": getattr(response, "provider", "unknown"),
                    "reason": "Malformed AI output: missing required structured result fields",
                }

            return {
                "enabled": True,
                "status": "success",
                "provider": getattr(response, "provider", "unknown"),
                "model": getattr(response, "model", "unknown"),
                "role_relevance": ai_payload.get("role_relevance") or ai_payload.get("role_category") or ai_payload.get("role") or "Unknown",
                "embedded_relevance": ai_payload.get("embedded_relevance") or ai_payload.get("embedded") or "Unknown",
                "skill_relevance": ai_payload.get("skill_relevance") or ai_payload.get("skills") or [],
                "experience_suitability": ai_payload.get("experience_suitability") or ai_payload.get("experience_fit") or "Unknown",
                "candidate_suitability": ai_payload.get("candidate_suitability") or ai_payload.get("candidate_fit") or "Unknown",
                "missing_important_skills": ai_payload.get("missing_important_skills") or ai_payload.get("missing_skills") or [],
                "positive_matching_factors": ai_payload.get("positive_matching_factors") or ai_payload.get("positive_factors") or [],
                "concerns": ai_payload.get("concerns") or [],
                "recommendation": ai_payload.get("recommendation") or ai_payload.get("summary") or "",
                "confidence": ai_payload.get("confidence") or 0.0,
            }
        except Exception as exc:
            return {
                "enabled": True,
                "status": "fallback",
                "provider": "unknown",
                "reason": str(exc),
            }

    def analyze_job_intelligence(self, job: Job, profile: dict = None, orchestrator=None) -> dict:
        cleaned = self.clean_job(job)
        role_category = self._identify_role_category(cleaned)
        text = self._job_text(cleaned).lower()

        profile_skills = self._profile_skill_set(profile)
        job_skills = self._job_skill_labels(cleaned)
        matched_skills = []
        for skill in job_skills:
            skill_key = skill.lower()
            if skill_key in profile_skills or skill_key in {"c", "linux", "arm", "rtos", "gpio", "spi", "i2c", "uart", "embedded c", "embedded linux", "firmware", "iot", "microcontroller"}:
                matched_skills.append(skill)

        if not matched_skills:
            profile_match = [skill for skill in [self.normalize_skill(s) for s in (profile or {}).get("skills", []) or []] if skill]
            for skill in profile_match:
                skill_key = skill.lower()
                if skill_key in text:
                    matched_skills.append(self.title_case(skill_key))

        missing_skills = sorted({skill for skill in profile_skills if skill not in {item.lower() for item in matched_skills}})

        experience_level = self._experience_level(cleaned)
        location_match = self._location_match(cleaned)
        embedded_relevance = "Low"
        if role_category != "Unrelated":
            embedded_relevance = "High" if any(token in text for token in ["embedded", "firmware", "rtos", "linux", "driver", "microcontroller", "arm", "iot"]) else "Medium"

        base_score = self.calculate_score(cleaned)
        overlap_score = min(len(matched_skills) * 12, 30)
        experience_score = 5 if self.normalize_text((profile or {}).get("experience", "")).lower() in self.normalize_text(experience_level).lower() or (
            "fresher" in self.normalize_text((profile or {}).get("experience", "")).lower() and "fresher" in self.normalize_text(experience_level).lower()
        ) else 0
        score = max(0, min(base_score + overlap_score + experience_score, 100))

        if role_category == "Unrelated":
            score = min(score, 35)
        if not location_match:
            score = max(0, score - 15)

        mismatch_penalty = self._experience_mismatch_penalty(profile, experience_level)
        if mismatch_penalty > 0:
            score = min(score, 60)
        score = max(0, score - mismatch_penalty)

        rejection_reasons = self._determine_rejection_reasons(cleaned, role_category, matched_skills, profile_skills)

        if role_category == "Unrelated":
            rejection_reasons = ["Role is unrelated to embedded, firmware, or ECE work"] + rejection_reasons
        if self._experience_mismatch_penalty(profile, experience_level) > 0:
            rejection_reasons.append("Experience requirement is too senior for the target ECE fresher profile")

        result = {
            "role_category": role_category,
            "matched_skills": matched_skills,
            "missing_skills": [self.title_case(skill) for skill in missing_skills],
            "experience_level": experience_level,
            "location_match": location_match,
            "embedded_relevance": embedded_relevance,
            "match_score": score,
            "rejection_reasons": list(dict.fromkeys(rejection_reasons)),
        }

        ai_enrichment = self._ai_enrich_analysis(cleaned, profile=profile, orchestrator=orchestrator)
        result["ai_enrichment"] = ai_enrichment
        result["combined_analysis"] = {
            "deterministic": {k: v for k, v in result.items() if k not in {"ai_enrichment", "combined_analysis"}},
            "ai": ai_enrichment,
        }
        return result

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    @staticmethod
    def _ai_label_to_score(value) -> float:
        if value is None:
            return 0.0
        normalized = str(value).strip().lower()
        if not normalized:
            return 0.0
        mapping = {
            "high": 1.0,
            "strong": 1.0,
            "excellent": 1.0,
            "medium": 0.6,
            "moderate": 0.6,
            "low": 0.2,
            "weak": 0.2,
            "poor": 0.2,
            "none": 0.0,
            "unknown": 0.0,
            "n/a": 0.0,
            "not applicable": 0.0,
        }
        if normalized in mapping:
            return mapping[normalized]
        try:
            numeric = float(normalized)
            return JobFilter._clamp(numeric, 0.0, 1.0)
        except ValueError:
            return 0.0

    @classmethod
    def _ai_list_score(cls, values) -> float:
        if not values:
            return 0.0
        if isinstance(values, str):
            values = [values]
        safe_values = [cls._ai_label_to_score(value) for value in values if value is not None]
        if not safe_values:
            return 0.0
        return sum(safe_values) / max(len(safe_values), 1)

    @classmethod
    def _compute_ai_adjustment(cls, ai_enrichment: dict) -> float:
        if not isinstance(ai_enrichment, dict) or ai_enrichment.get("status") != "success":
            return 0.0

        role_score = cls._ai_label_to_score(ai_enrichment.get("role_relevance") or ai_enrichment.get("role_category") or ai_enrichment.get("role"))
        skill_score = cls._ai_list_score(ai_enrichment.get("skill_relevance") or ai_enrichment.get("skills") or [])
        experience_score = cls._ai_label_to_score(ai_enrichment.get("experience_suitability") or ai_enrichment.get("experience_relevance") or ai_enrichment.get("experience_fit"))
        candidate_fit = cls._ai_label_to_score(ai_enrichment.get("candidate_suitability") or ai_enrichment.get("candidate_fit") or ai_enrichment.get("ai_candidate_fit"))
        confidence = cls._clamp(float(ai_enrichment.get("confidence") or 0.0), 0.0, 1.0)

        composite = (0.35 * role_score) + (0.25 * skill_score) + (0.20 * experience_score) + (0.20 * candidate_fit)
        raw_adjustment = (composite - 0.5) * (2.0 * cls.AI_RANKING_MAX_ADJUSTMENT) * confidence * cls.AI_RANKING_CONFIDENCE_WEIGHT
        return cls._clamp(raw_adjustment, cls.AI_RANKING_MIN_ADJUSTMENT, cls.AI_RANKING_MAX_ADJUSTMENT)

    def rank_jobs_for_candidate(self, jobs: Iterable[Job], profile: dict = None, orchestrator=None) -> List[dict]:
        candidate = profile or {}
        ranked = []

        role_priority = {
            "Embedded Linux": 30,
            "Embedded C": 22,
            "Firmware": 20,
            "RTOS": 18,
            "IoT": 18,
            "Embedded Software": 18,
            "Embedded Systems": 16,
            "Device Drivers": 17,
            "Electronics": 12,
            "Unrelated": 0,
        }

        for job in jobs:
            if not isinstance(job, Job):
                continue
            analysis = self.analyze_job_intelligence(job, candidate, orchestrator=orchestrator)
            ai_enrichment = analysis.get("ai_enrichment", {})
            deterministic_score = analysis["match_score"]
            role_score = role_priority.get(analysis["role_category"], 0)
            skill_score = min(len(analysis["matched_skills"]) * 8, 30)
            embedded_score = {"High": 12, "Medium": 6, "Low": 0}.get(analysis["embedded_relevance"], 0)
            location_score = 12 if analysis["location_match"] else -18
            missing_penalty = min(len(analysis["missing_skills"]) * 4, 18)

            candidate_exp = self.normalize_text(candidate.get("experience", "")).lower()
            experience_score = 10 if candidate_exp and candidate_exp in self.normalize_text(analysis["experience_level"]).lower() else 0
            if analysis["experience_level"] in {"5+ years", "Experienced"} and "fresher" in candidate_exp:
                experience_score = -25
            if analysis["experience_level"] in {"Trainee", "Internship", "Graduate", "0-1 years", "0-2 years", "1-2 years", "Entry Level"} and "fresher" in candidate_exp:
                experience_score += 6

            ranking_score = deterministic_score + role_score + skill_score + embedded_score + location_score + experience_score - missing_penalty
            ai_adjustment = self._compute_ai_adjustment(ai_enrichment)
            final_score = self._clamp(deterministic_score + ai_adjustment, 0.0, 100.0)
            display_score = deterministic_score

            reasons = []
            if analysis["role_category"] != "Unrelated":
                reasons.append(f"Role match: {analysis['role_category']}")
            if analysis["matched_skills"]:
                reasons.append(f"Matched skills: {', '.join(analysis['matched_skills'][:5])}")
            if analysis["missing_skills"]:
                reasons.append(f"Missing skills: {', '.join(analysis['missing_skills'][:5])}")
            if analysis["experience_level"]:
                reasons.append(f"Experience level: {analysis['experience_level']}")
            if not analysis["location_match"]:
                reasons.append("Location mismatch")
            if analysis["rejection_reasons"]:
                reasons.extend(analysis["rejection_reasons"][:3])

            ai_role_relevance = ai_enrichment.get("role_relevance", "Unknown") if isinstance(ai_enrichment, dict) else "Unknown"
            ai_skill_relevance = ai_enrichment.get("skill_relevance", []) if isinstance(ai_enrichment, dict) else []
            ai_experience_relevance = ai_enrichment.get("experience_suitability", "Unknown") if isinstance(ai_enrichment, dict) else "Unknown"
            ai_candidate_fit = ai_enrichment.get("candidate_suitability", "Unknown") if isinstance(ai_enrichment, dict) else "Unknown"
            ai_confidence = ai_enrichment.get("confidence", 0.0) if isinstance(ai_enrichment, dict) else 0.0
            ai_concerns = ai_enrichment.get("concerns", []) if isinstance(ai_enrichment, dict) else []
            ai_recommendation = ai_enrichment.get("recommendation", "") if isinstance(ai_enrichment, dict) else ""

            ranked.append({
                "rank": 0,
                "deterministic_score": deterministic_score,
                "match_score": ranking_score,
                "final_score": final_score,
                "ai_adjustment": ai_adjustment,
                "role_match": analysis["role_category"],
                "skill_match": len(analysis["matched_skills"]),
                "experience_match": analysis["experience_level"],
                "location_match": analysis["location_match"],
                "embedded_relevance": analysis["embedded_relevance"],
                "matched_skills": analysis["matched_skills"],
                "missing_skills": analysis["missing_skills"],
                "rejection_reasons": analysis["rejection_reasons"],
                "ranking_reasons": list(dict.fromkeys(reasons)),
                "title": getattr(job, "title", ""),
                "company": getattr(job, "company", ""),
                "url": getattr(job, "url", ""),
                "ai_enrichment": ai_enrichment,
                "ai_role_relevance": ai_role_relevance,
                "ai_skill_relevance": ai_skill_relevance,
                "ai_experience_relevance": ai_experience_relevance,
                "ai_candidate_fit": ai_candidate_fit,
                "ai_confidence": ai_confidence,
                "ai_concerns": ai_concerns,
                "ai_recommendation": ai_recommendation,
            })

        ranked.sort(key=lambda item: (
            1 if item["role_match"] == "Unrelated" else 0,
            0 if item["location_match"] else 1,
            -item["match_score"],
            -role_priority.get(item["role_match"], 0),
            item["title"].lower(),
            item["company"].lower(),
            item["url"].lower(),
        ))

        for index, item in enumerate(ranked, start=1):
            item["rank"] = index

        return ranked

    @staticmethod
    def dedupe_key(job: Job):
        normalized = job
        source_job_id = (getattr(normalized, "source_job_id", "") or "").strip()
        url_key = normalized.url.lower().rstrip("/") if getattr(normalized, "url", "") else ""

        if source_job_id:
            return (("source_job_id", source_job_id.lower()),)

        if url_key:
            return (("url", url_key),)

        identity_key = (
            (normalized.title or "").lower().strip(),
            (normalized.company or "").lower().strip(),
            (normalized.location or "").lower().strip(),
            (normalized.experience or "").lower().strip(),
        )
        return (("identity", identity_key),)

    def deduplicate_jobs(self, jobs: Iterable[Job]) -> List[Job]:
        """Canonical deduplication stage.

        JobFilter owns the final uniqueness decision because it runs after normalization and
        can safely compare canonical URLs, provider source_job_id values, and normalized
        title/company identity. SearchManager may still guard against provider-side duplicates,
        but the primary dedupe responsibility remains here so the pipeline uses one consistent
        dedupe rule across all sources.
        """
        seen = set()
        deduped = []

        for job in jobs:
            if not job:
                continue

            normalized = self.normalize_job(job)
            keys = self.dedupe_key(normalized)

            if any(key in seen for key in keys):
                continue

            for key in keys:
                seen.add(key)
            deduped.append(normalized)

        return deduped

    def _find_keyword_hits(self, text: str, keywords: List[str]) -> List[str]:
        hits = []
        for keyword in keywords:
            if keyword in text:
                hits.append(keyword)
        return hits

    def _has_embedded_hardware_context(self, text: str) -> bool:
        embedded_hits = self._find_keyword_hits(text, self.PRIMARY_EMBEDDED_KEYWORDS)
        if "linux kernel" in text and not any(term in text for term in [
            "embedded",
            "firmware",
            "driver",
            "bsp",
            "u-boot",
            "yocto",
            "buildroot",
            "arm",
            "mcu",
            "microcontroller",
            "stm32",
            "esp32",
            "uart",
            "spi",
            "i2c",
            "gpio",
            "iot",
            "rtos",
            "freertos",
            "device driver",
            "kernel driver",
            "linux device driver",
        ]):
            return False
        hardware_hits = self._find_keyword_hits(text, self.HARDWARE_CONTEXT_KEYWORDS)
        return bool(embedded_hits or hardware_hits)

    def _is_generic_unrelated_role(self, text: str) -> bool:
        if not text:
            return False
        if self._has_embedded_hardware_context(text):
            return False
        return any(keyword in text for keyword in self.GENERIC_UNRELATED_KEYWORDS)

    def document_matches_target(self, job: Job) -> bool:
        text = self._job_text(job).lower()
        if not text:
            return False

        primary_hits = self._find_keyword_hits(text, self.PRIMARY_EMBEDDED_KEYWORDS)
        hardware_hits = self._find_keyword_hits(text, self.HARDWARE_CONTEXT_KEYWORDS)
        support_hits = self._find_keyword_hits(text, self.SUPPORTING_KEYWORDS)

        if "linux kernel" in text and not self._has_embedded_hardware_context(text):
            return False

        if primary_hits:
            return True

        if "linux" in text and hardware_hits:
            return True

        if "firmware" in text and ("embedded" in text or "arm" in text or "mcu" in text or "microcontroller" in text or "iot" in text):
            return True

        if ("embedded" in text or "firmware" in text or "rtos" in text or "freertos" in text or "kernel" in text or "driver" in text) and (
            "arm" in text
            or "mcu" in text
            or "microcontroller" in text
            or "stm32" in text
            or "esp32" in text
            or "uart" in text
            or "spi" in text
            or "i2c" in text
            or "gpio" in text
            or "bsp" in text
            or "yocto" in text
            or "u-boot" in text
            or "firmware" in text
            or "driver" in text
            or "embedded" in text
        ):
            return True

        if support_hits and any(token in text for token in ["embedded", "firmware", "driver", "microcontroller", "arm", "iot", "rtos", "freertos", "linux kernel", "bsp", "yocto", "u-boot"]):
            return True

        if self._is_generic_unrelated_role(text):
            return False

        if "linux" in text and "kernel" in text and not hardware_hits:
            return False

        return False

    def is_entry_level_or_intern(self, job: Job) -> bool:
        text = self._job_text(job).lower()
        if not text:
            return False

        for keyword in self.ENTRY_LEVEL_KEYWORDS:
            if keyword in text:
                return True

        return bool(re.search(r"0\s*[-–]\s*[12]\s*\s*years?", text)) or bool(re.search(r"0\s*[-–]?\s*1\s*years?", text))

    def location_allowed(self, job: Job) -> bool:
        if not settings.ENABLE_LOCATION_FILTER:
            return True

        location_text = (job.location or "").lower()
        if not location_text:
            return True

        normalized_location = re.sub(r"\s+", " ", location_text).strip()
        remote_indicators = [
            "remote",
            "home based",
            "home-based",
            "worldwide",
            "global",
        ]
        if any(indicator in normalized_location for indicator in remote_indicators):
            return True

        location_keywords = [keyword.lower() for keyword in settings.LOCATION_KEYWORDS]
        return any(keyword in normalized_location for keyword in location_keywords)

    def calculate_score(self, job: Job) -> int:
        text = self._job_text(job).lower()

        score = 0
        breakdown = {
            "embedded_hits": [],
            "supporting_hits": [],
            "entry_hits": [],
            "location_hit": None,
            "generic_unrelated_hits": [],
        }

        primary_hits = self._find_keyword_hits(text, self.PRIMARY_EMBEDDED_KEYWORDS)
        score += len(primary_hits) * 18
        breakdown["embedded_hits"] = primary_hits

        support_hits = self._find_keyword_hits(text, self.SUPPORTING_KEYWORDS)
        score += len(support_hits) * 6
        breakdown["supporting_hits"] = support_hits

        entry_hits = self._find_keyword_hits(text, self.ENTRY_LEVEL_KEYWORDS)
        if entry_hits:
            score += 15
        elif re.search(r"0\s*[-–]\s*[12]\s*\s*years?", text):
            score += 15
        breakdown["entry_hits"] = entry_hits

        location_keywords = [keyword.lower() for keyword in settings.LOCATION_KEYWORDS]
        for keyword in location_keywords:
            if keyword in text:
                score += 3
                breakdown["location_hit"] = keyword
                break

        if "junior" in text:
            score += 5
        if "graduate" in text:
            score += 5

        generic_hits = [keyword for keyword in self.GENERIC_UNRELATED_KEYWORDS if keyword in text]
        breakdown["generic_unrelated_hits"] = generic_hits
        if generic_hits and not self._has_embedded_hardware_context(text):
            score -= 30

        score = max(0, min(score, 100))
        job.match_breakdown = breakdown
        job.match_score = score
        return score
    def explain_rejection(self, job: Job) -> List[str]:
        reasons = []

        if not self.normalize_text(job.title):
            reasons.append("Missing job title")

        if not self.normalize_text(job.company):
            reasons.append("Missing company name")

        if not self.normalize_url(job.url):
            reasons.append("Missing or invalid URL")

        text = self._job_text(job).lower()

        if not self.document_matches_target(job):
            if self._is_generic_unrelated_role(text):
                reasons.append(
                    "Role appears unrelated to embedded/Linux hardware work"
                )
            else:
                reasons.append(
                    "No strong embedded or hardware-relevant Linux context"
                )

        if settings.REQUIRE_ENTRY_LEVEL and not self.is_entry_level_or_intern(job):
            reasons.append(
                "No fresher/graduate/trainee/intern/junior/entry-level indicator"
            )

        if not self.location_allowed(job):
            reasons.append("Location outside configured allowed keywords")

        return reasons
    def diagnostic_sample(self, job: Job, reasons: List[str]) -> dict:
        text = self._job_text(job).lower()
        return {
            "title": self.normalize_text(job.title),
            "company": self.normalize_text(job.company),
            "location": self.normalize_text(job.location),
            "source": self.normalize_text(job.source),
            "description_available": bool(getattr(job, "description", "")),
            "skills_available": bool((job.skills or [])),
            "experience": self.normalize_text(job.experience),
            "embedded_keyword_matches": self._find_keyword_hits(text, self.PRIMARY_EMBEDDED_KEYWORDS),
            "entry_level_keyword_matches": self._find_keyword_hits(text, self.ENTRY_LEVEL_KEYWORDS),
            "location_matches": [
                keyword for keyword in [kw.lower() for kw in settings.LOCATION_KEYWORDS]
                if keyword in text
            ],
            "rejection_reasons": list(reasons),
        }

    def filter_jobs(self, jobs):
        normalized_jobs = []
        original_jobs = {}
        self.last_summary = {
            "total_jobs": 0,
            "normalized_jobs": 0,
            "duplicates_removed": 0,
            "accepted": 0,
            "rejected": 0,
            "rejection_counts": {},
            "accepted_jobs": [],
            "rejected_samples": [],
        }

        for original_job in jobs:
            if not isinstance(original_job, Job):
                continue

            normalized_job = self.normalize_job(original_job)
            candidate_keys = self.dedupe_key(normalized_job)
            for key in candidate_keys:
                original_jobs[key] = original_job

            if not normalized_job.title or not normalized_job.company:
                normalized_job.rejection_reasons = ["Missing title or company"]
                original_job.rejection_reasons = ["Missing title or company"]
                original_job.match_breakdown = {}
                continue
            if not self.normalize_url(normalized_job.url):
                normalized_job.rejection_reasons = ["Missing or invalid URL"]
                original_job.rejection_reasons = ["Missing or invalid URL"]
                original_job.match_breakdown = {}
                continue

            normalized_jobs.append(normalized_job)

        self.last_summary["total_jobs"] = len(jobs)
        self.last_summary["normalized_jobs"] = len(normalized_jobs)

        deduped_jobs = self.deduplicate_jobs(normalized_jobs)
        duplicates_removed = len(normalized_jobs) - len(deduped_jobs)
        self.last_summary["duplicates_removed"] = duplicates_removed

        accepted = []
        rejected = []
        rejection_counter = Counter()

        for job in deduped_jobs:
            reasons = self.explain_rejection(job)
            job.rejection_reasons = reasons
            job.match_breakdown = getattr(job, "match_breakdown", {})

            key_candidates = self.dedupe_key(job)
            original_job = None
            for key in key_candidates:
                original_job = original_jobs.get(key)
                if original_job is not None:
                    break
            if original_job is not None:
                original_job.rejection_reasons = reasons
                original_job.match_breakdown = job.match_breakdown

            if reasons:
                rejected.append(job)
                if len(self.last_summary["rejected_samples"]) < 10:
                    self.last_summary["rejected_samples"].append(self.diagnostic_sample(job, reasons))
                for reason in reasons:
                    rejection_counter[reason] += 1
                continue

            job.match_score = self.calculate_score(job)
            if original_job is not None:
                original_job.match_score = job.match_score
                original_job.match_breakdown = job.match_breakdown
                original_job.rejection_reasons = []
            accepted.append(job)

        accepted.sort(key=lambda job: job.match_score, reverse=True)
        self.last_summary["accepted"] = len(accepted)
        self.last_summary["rejected"] = len(rejected)
        self.last_summary["rejection_counts"] = dict(rejection_counter.most_common())
        self.last_summary["accepted_jobs"] = [
            {
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "source": job.source,
                "match_score": job.match_score,
            }
            for job in accepted[:10]
        ]

        return accepted
