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
        headers = {"User-Agent": "Mozilla/5.0"}
        max_attempts = settings.PROVIDER_MAX_RETRIES + 1

        for attempt in range(1, max_attempts + 1):
            try:
                response = httpx.get(
                    self.API_URL,
                    headers=headers,
                    timeout=settings.PROVIDER_TIMEOUT_SECONDS,
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
                    return []

                if status in {429, 500, 502, 503, 504} and attempt <= settings.PROVIDER_MAX_RETRIES:
                    delay = self._backoff_delay(attempt)
                    app_logger.warning(
                        f"Provider RemoteOK attempt {attempt}/{max_attempts} failed with {failure_type}; retrying in {delay}s."
                    )
                    time.sleep(delay)
                    continue

                app_logger.error(
                    f"Provider RemoteOK final failure after {attempt} attempt(s): {failure_type}."
                )
                return []
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.ConnectTimeout) as exc:
                failure_type = exc.__class__.__name__

                if attempt <= settings.PROVIDER_MAX_RETRIES:
                    delay = self._backoff_delay(attempt)
                    app_logger.warning(
                        f"Provider RemoteOK attempt {attempt}/{max_attempts} failed with {failure_type}; retrying in {delay}s."
                    )
                    time.sleep(delay)
                    continue

                app_logger.error(
                    f"Provider RemoteOK final failure after {attempt} attempt(s): {failure_type}: {exc}"
                )
                return []
            except ValueError as exc:
                app_logger.error(f"Provider RemoteOK final failure: invalid JSON payload: {exc}")
                return []
            except Exception as exc:
                app_logger.error(
                    f"Provider RemoteOK final failure after {attempt} attempt(s): unexpected error: {exc}"
                )
                return []

        try:
            for item in data:
                if not isinstance(item, dict):
                    continue

                title = item.get("position") or item.get("title")
                if not title:
                    continue

                company = item.get("company", "Unknown")
                location = item.get("location", "Remote")
                url = item.get("url", "")
                tags = item.get("tags", [])
                date = item.get("date", "")

                jobs.append(
                    Job(
                        title=title,
                        company=company,
                        location=location,
                        experience="Not Specified",
                        source="RemoteOK",
                        url=url,
                        skills=tags,
                        posted_date=date,
                    )
                )
        except (TypeError, ValueError) as exc:
            app_logger.error(f"Provider RemoteOK failed while parsing results: {exc}")
            return []

        return jobs
