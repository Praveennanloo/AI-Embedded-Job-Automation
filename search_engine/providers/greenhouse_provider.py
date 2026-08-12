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

                location = item.get("location", {}).get("name") or "Remote"
                url_value = item.get("absolute_url") or item.get("url") or ""
                if not url_value:
                    continue

                jobs.append(
                    Job(
                        title=title,
                        company=company_name,
                        location=location,
                        experience="Not Specified",
                        source="Greenhouse",
                        url=url_value,
                        skills=[],
                        posted_date=item.get("updated_at") or "",
                    )
                )
                count += 1

            app_logger.debug(f"Found {count} matching jobs for {company_name} on Greenhouse.")
            data = None

        return jobs
