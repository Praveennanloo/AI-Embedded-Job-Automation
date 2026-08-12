import re
from typing import Iterable, List
from urllib.parse import urlparse

from models.job import Job


class JobFilter:

    EMBEDDED_KEYWORDS = [
        "embedded",
        "firmware",
        "embedded c",
        "embedded linux",
        "linux",
        "driver",
        "device driver",
        "bsp",
        "rtos",
        "freertos",
        "arm",
        "microcontroller",
        "mcu",
        "iot",
        "esp32",
        "stm32",
        "uart",
        "spi",
        "i2c",
        "electronics",
        "ece",
    ]

    LOCATION_KEYWORDS = [
        "hyderabad",
        "bangalore",
        "bengaluru",
        "chennai",
        "pune",
        "visakhapatnam",
        "vizag",
        "remote",
        "india",
    ]

    EXPERIENCE_KEYWORDS = [
        "fresher",
        "graduate",
        "0 year",
        "0-1",
        "entry",
        "trainee",
        "intern",
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

    def document_matches_target(self, job: Job) -> bool:
        text = " ".join([
            job.title,
            job.company,
            job.location,
            job.experience,
            *job.skills,
        ]).lower()

        return any(keyword in text for keyword in self.EMBEDDED_KEYWORDS)

    def is_entry_level_or_intern(self, job: Job) -> bool:
        text = " ".join([
            job.title,
            job.company,
            job.location,
            job.experience,
            *job.skills,
        ]).lower()

        return any(keyword in text for keyword in self.EXPERIENCE_KEYWORDS)

    def calculate_score(self, job: Job) -> int:
        text = " ".join([
            job.title,
            job.company,
            job.location,
            job.experience,
            *job.skills,
        ]).lower()

        score = 0

        for keyword in self.EMBEDDED_KEYWORDS:
            if keyword in text:
                score += 5

        location = job.location.lower()
        for place in self.LOCATION_KEYWORDS:
            if place in location:
                score += 2

        experience = job.experience.lower()
        for keyword in self.EXPERIENCE_KEYWORDS:
            if keyword in experience:
                score += 3

        if "intern" in text:
            score += 8

        if score > 100:
            score = 100

        return score

    def filter_jobs(self, jobs):
        normalized_jobs = []

        for job in jobs:
            if not isinstance(job, Job):
                continue

            job = self.normalize_job(job)
            if not job.title or not job.company:
                continue
            if not self.normalize_url(job.url):
                continue

            normalized_jobs.append(job)

        deduped_jobs = self.deduplicate_jobs(normalized_jobs)

        matched_jobs = []
        for job in deduped_jobs:
            if not self.document_matches_target(job):
                continue
            if not self.is_entry_level_or_intern(job):
                continue

            job.match_score = self.calculate_score(job)
            if job.match_score >= 15:
                matched_jobs.append(job)

        return matched_jobs
