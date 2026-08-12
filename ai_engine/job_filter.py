import re
from collections import Counter
from typing import Iterable, List
from urllib.parse import urlparse

from config.settings import settings
from models.job import Job


class JobFilter:

    PRIMARY_EMBEDDED_KEYWORDS = [
        "embedded",
        "embedded c",
        "embedded linux",
        "embedded software",
        "firmware",
        "device driver",
        "driver development",
        "rtos",
        "freertos",
        "linux kernel",
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
        "electronics",
        "ece",
    ]

    SUPPORTING_KEYWORDS = [
        "c",
        "c++",
        "linux",
        "embedded c",
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
            skills=normalized_skills,
            posted_date=self.normalize_text(job.posted_date),
            status=job.status,
            match_score=job.match_score,
            rejection_reasons=list(getattr(job, "rejection_reasons", []) or []),
            match_breakdown=dict(getattr(job, "match_breakdown", {}) or {}),
        )
        return normalized

    def deduplicate_jobs(self, jobs: Iterable[Job]) -> List[Job]:
        seen = set()
        deduped = []

        for job in jobs:
            if not job:
                continue

            normalized = self.normalize_job(job)
            url_key = normalized.url.lower().rstrip("/") if normalized.url else ""
            identity_key = (
                normalized.title.lower(),
                normalized.company.lower(),
                normalized.location.lower(),
                normalized.experience.lower(),
            )
            key = url_key or identity_key

            if key in seen:
                continue

            seen.add(key)
            deduped.append(normalized)

        return deduped

    def _find_keyword_hits(self, text: str, keywords: List[str]) -> List[str]:
        hits = []
        for keyword in keywords:
            if keyword in text:
                hits.append(keyword)
        return hits

    def document_matches_target(self, job: Job) -> bool:
        text = self._job_text(job).lower()

        primary_hits = self._find_keyword_hits(text, self.PRIMARY_EMBEDDED_KEYWORDS)
        if primary_hits:
            return True

        if ("embedded" in text or "firmware" in text or "rtos" in text or "arm" in text or "linux" in text or "driver" in text or "mcu" in text or "microcontroller" in text or "iot" in text) and (
            "c" in text or "c++" in text or "linux" in text or "firmware" in text or "rtos" in text or "arm" in text or "microcontroller" in text or "iot" in text
        ):
            return True

        support_hits = self._find_keyword_hits(text, self.SUPPORTING_KEYWORDS)
        if support_hits and any(token in text for token in ["embedded", "firmware", "linux", "driver", "microcontroller", "arm", "iot", "rtos"]):
            return True

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
        }

        primary_hits = self._find_keyword_hits(text, self.PRIMARY_EMBEDDED_KEYWORDS)
        for keyword in primary_hits:
            score += 12
        breakdown["embedded_hits"] = primary_hits

        support_hits = self._find_keyword_hits(text, self.SUPPORTING_KEYWORDS)
        for keyword in support_hits:
            score += 4
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

        score = min(score, 100)
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
        if not self.document_matches_target(job):
            reasons.append("No embedded firmware/RTOS/Linux/IoT or MCU keyword match")
        if not self.is_entry_level_or_intern(job):
            reasons.append("No fresher/graduate/trainee/intern/junior/entry-level indicator")
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
            key = (
                normalized_job.url.lower().rstrip("/") if normalized_job.url else "",
                (normalized_job.title or "").lower().strip(),
                (normalized_job.company or "").lower().strip(),
            )
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

            key = (
                job.url.lower().rstrip("/"),
                job.title.lower().strip(),
                job.company.lower().strip(),
            )
            original_job = original_jobs.get(key)
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
