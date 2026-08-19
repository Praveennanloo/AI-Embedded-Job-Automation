import random
import time

import httpx

from config.settings import settings
from models.job import Job
from search_engine.providers.base_provider import BaseProvider
from utils.logger import app_logger


class GreenhouseProvider(BaseProvider):

    BOARDS = [
        ("Canonical", "https://boards-api.greenhouse.io/v1/boards/canonical/jobs"),
        ("Samsara", "https://boards-api.greenhouse.io/v1/boards/samsara/jobs"),
    ]

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

    def search(self):

        jobs = []
        max_attempts = settings.PROVIDER_MAX_RETRIES + 1

        for company_name, url in self.BOARDS:
            for attempt in range(1, max_attempts + 1):
                try:
                    app_logger.debug(f"Fetching Greenhouse jobs for {company_name}...")
                    response = httpx.get(url, timeout=settings.PROVIDER_TIMEOUT_SECONDS)
                    response.raise_for_status()
                    data = response.json()
                    break
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code if exc.response is not None else "unknown"
                    failure_type = self._describe_http_failure(status) if isinstance(status, int) else f"HTTP {status}"

                    if status in {400, 401, 403, 404}:
                        app_logger.error(
                            f"Provider Greenhouse {company_name} final failure: {failure_type}; permanent 4xx error, not retrying."
                        )
                        break

                    if status in {429, 500, 502, 503, 504} and attempt <= settings.PROVIDER_MAX_RETRIES:
                        delay = self._backoff_delay(attempt)
                        app_logger.warning(
                            f"Provider Greenhouse {company_name} attempt {attempt}/{max_attempts} failed with {failure_type}; retrying in {delay}s."
                        )
                        time.sleep(delay)
                        continue

                    app_logger.error(
                        f"Provider Greenhouse {company_name} final failure after {attempt} attempt(s): {failure_type}."
                    )
                    break
                except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.ConnectTimeout) as exc:
                    failure_type = exc.__class__.__name__

                    if attempt <= settings.PROVIDER_MAX_RETRIES:
                        delay = self._backoff_delay(attempt)
                        app_logger.warning(
                            f"Provider Greenhouse {company_name} attempt {attempt}/{max_attempts} failed with {failure_type}; retrying in {delay}s."
                        )
                        time.sleep(delay)
                        continue

                    app_logger.error(
                        f"Provider Greenhouse {company_name} final failure after {attempt} attempt(s): {failure_type}: {exc}"
                    )
                    break
                except ValueError as exc:
                    app_logger.error(
                        f"Provider Greenhouse {company_name} final failure: invalid JSON payload: {exc}"
                    )
                    break
                except Exception as exc:
                    app_logger.error(
                        f"Provider Greenhouse {company_name} final failure after {attempt} attempt(s): unexpected error: {exc}"
                    )
                    break
            else:
                continue

            if "data" not in locals():
                continue

            count = 0
            for item in data.get("jobs", []):
                if not isinstance(item, dict):
                    continue

                title = item.get("title") or ""
                if not title:
                    continue

                location = (item.get("location") or {}).get("name") or "Remote"
                url_value = self._coalesce(item.get("absolute_url"), item.get("url"), "")
                if not url_value:
                    continue

                description = self._coalesce(
                    item.get("description"),
                    item.get("content"),
                    item.get("job_description"),
                    "",
                )
                salary = self._coalesce(
                    item.get("salary"),
                    item.get("salary_range"),
                    item.get("compensation"),
                    "",
                )
                job_type = self._coalesce(item.get("job_type"), item.get("type"), "")
                employment_type = self._coalesce(item.get("employment_type"), item.get("employment"), "")
                application_url = self._coalesce(item.get("application_url"), url_value, "")
                source_job_id = self._coalesce(item.get("id"), item.get("source_job_id"), item.get("job_id"), "")
                remote = bool(item.get("remote")) or "remote" in str(location).lower()
                skills = self._safe_list(item.get("tags"))

                jobs.append(
                    Job(
                        title=title,
                        company=company_name,
                        location=location,
                        experience=self._coalesce(item.get("experience"), "Not Specified"),
                        source="Greenhouse",
                        url=url_value,
                        skills=skills,
                        posted_date=self._coalesce(item.get("updated_at"), item.get("posted_date"), ""),
                        source_job_id=source_job_id,
                        remote=remote,
                        description=description,
                        salary=salary,
                        job_type=job_type,
                        employment_type=employment_type,
                        application_url=application_url,
                    )
                )
                count += 1

            app_logger.debug(f"Found {count} matching jobs for {company_name} on Greenhouse.")
            data = None

        return jobs
