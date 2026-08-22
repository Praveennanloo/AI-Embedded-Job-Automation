import random
import time

import httpx

from config.settings import settings
from models.job import Job
from search_engine.providers.base_provider import BaseProvider
from utils.logger import app_logger


class RemoteOKProvider(BaseProvider):

    API_URL = "https://remoteok.com/api"

    @staticmethod
    def _clean_text(value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @staticmethod
    def _coalesce(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned
            elif isinstance(value, (int, float)):
                return str(value)
            else:
                cleaned = str(value).strip()
                if cleaned:
                    return cleaned
        return ""

    @staticmethod
    def _safe_list(value):
        if not value:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return [str(value).strip()]

    @staticmethod
    def _backoff_delay(attempt: int) -> float:
        base_delay = min(
            settings.PROVIDER_BASE_DELAY_SECONDS * (2 ** max(attempt - 1, 0)),
            settings.PROVIDER_MAX_DELAY_SECONDS,
        )
        jitter = random.uniform(0.0, min(base_delay * 0.5, 1.0))
        return round(base_delay + jitter, 3)

    @staticmethod
    def _describe_http_failure(status_code):
        if status_code == 429:
            return "HTTP 429 rate limit"
        if status_code in {500, 502, 503, 504}:
            return f"HTTP {status_code} server error"
        return f"HTTP {status_code}"

    def search(
        self,
        query: str = "",
        location: str = "",
        limit: int | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ):

        self.last_status = {"status": "failed", "count": 0, "error": None}
        jobs = []
        headers = {"User-Agent": "Mozilla/5.0"}
        timeout_seconds = settings.PROVIDER_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        max_retries = settings.PROVIDER_MAX_RETRIES if max_retries is None else max_retries
        max_attempts = max_retries + 1

        for attempt in range(1, max_attempts + 1):
            try:
                response = httpx.get(
                    self.API_URL,
                    headers=headers,
                    timeout=timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
                break
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else "unknown"
                failure_type = self._describe_http_failure(status) if isinstance(status, int) else f"HTTP {status}"

                if status in {400, 401, 403, 404}:
                    app_logger.error(
                        f"Provider RemoteOK final failure: {failure_type}; permanent 4xx error, not retrying."
                    )
                    self.last_status["error"] = failure_type
                    return []

                if status in {429, 500, 502, 503, 504} and attempt <= max_retries:
                    delay = self._backoff_delay(attempt)
                    app_logger.warning(
                        f"Provider RemoteOK attempt {attempt}/{max_attempts} failed with {failure_type}; retrying in {delay}s."
                    )
                    time.sleep(delay)
                    continue

                app_logger.error(
                    f"Provider RemoteOK final failure after {attempt} attempt(s): {failure_type}."
                )
                self.last_status["error"] = failure_type
                return []
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.ConnectTimeout) as exc:
                failure_type = exc.__class__.__name__

                if attempt <= max_retries:
                    delay = self._backoff_delay(attempt)
                    app_logger.warning(
                        f"Provider RemoteOK attempt {attempt}/{max_attempts} failed with {failure_type}; retrying in {delay}s."
                    )
                    time.sleep(delay)
                    continue

                app_logger.error(
                    f"Provider RemoteOK final failure after {attempt} attempt(s): {failure_type}: {exc}"
                )
                self.last_status["error"] = f"{failure_type}: {exc}"
                return []
            except ValueError as exc:
                app_logger.error(f"Provider RemoteOK final failure: invalid JSON payload: {exc}")
                self.last_status["status"] = "malformed"
                self.last_status["error"] = str(exc)
                return []
            except Exception as exc:
                app_logger.error(
                    f"Provider RemoteOK final failure after {attempt} attempt(s): unexpected error: {exc}"
                )
                self.last_status["error"] = str(exc)
                return []

        try:
            for item in data:
                if not isinstance(item, dict):
                    continue

                title = self._coalesce(item.get("position"), item.get("title"))
                if not title:
                    continue

                company = self._coalesce(item.get("company"), "Unknown")
                location = self._coalesce(item.get("location"), "Remote")
                url = self._coalesce(item.get("url"), item.get("application_url"), "")
                tags = self._safe_list(item.get("tags"))
                date = self._coalesce(item.get("date"), item.get("posted_date"), "")
                description = self._coalesce(item.get("description"), item.get("content"), item.get("snippet"), "")
                salary = self._coalesce(item.get("salary"), item.get("salary_range"), item.get("compensation"), "")
                job_type = self._coalesce(item.get("job_type"), item.get("type"), "")
                employment_type = self._coalesce(item.get("employment_type"), item.get("employment"), "")
                application_url = self._coalesce(item.get("application_url"), url, "")
                source_job_id = self._coalesce(item.get("id"), item.get("source_job_id"), "")
                remote = bool(item.get("remote")) or "remote" in location.lower()

                jobs.append(
                    Job(
                        title=title,
                        company=company,
                        location=location,
                        experience=self._coalesce(item.get("experience"), "Not Specified"),
                        source="RemoteOK",
                        url=url,
                        skills=tags,
                        posted_date=date,
                        source_job_id=source_job_id,
                        remote=remote,
                        description=description,
                        salary=salary,
                        job_type=job_type,
                        employment_type=employment_type,
                        application_url=application_url,
                    )
                )
        except (TypeError, ValueError) as exc:
            app_logger.error(f"Provider RemoteOK failed while parsing results: {exc}")
            self.last_status["status"] = "malformed"
            self.last_status["error"] = str(exc)
            return []

        # RemoteOK's public feed has no query parameter. Filter only the real
        # payload locally, using title/tags/description; do not invent jobs.
        if self._query_terms(query):
            matched_jobs = []
            for job in jobs:
                query_match = self.query_match_details(job, query)
                if query_match["matched"]:
                    job.match_breakdown = {
                        **getattr(job, "match_breakdown", {}),
                        "query_match": query_match,
                    }
                    matched_jobs.append(job)
            jobs = matched_jobs
        jobs = [job for job in jobs if self.location_matches(job, location)]
        jobs = jobs[:limit] if limit else jobs
        self.last_status = {"status": "success", "count": len(jobs), "error": None}
        return jobs
