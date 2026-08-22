from typing import List, Optional
import inspect

import httpx

from models.job import Job
from config.settings import settings
from utils.logger import app_logger


class SearchManager:

    def __init__(self):
        self.providers = []
        self.provider_results = {}
        self.provider_status = {}
        self.total_jobs_retrieved = 0

    def register_provider(self, provider):
        app_logger.debug(f"Registering provider: {provider.__class__.__name__}")
        self.providers.append(provider)

    def _deduplicate_jobs(self, jobs: List[Job]) -> List[Job]:
        seen = set()
        unique_jobs = []

        for job in jobs:
            if not isinstance(job, Job):
                continue

            url_key = job.url.lower().rstrip("/") if job.url else ""
            identity_key = (
                (job.title or "").lower().strip(),
                (job.company or "").lower().strip(),
                (job.location or "").lower().strip(),
                (job.experience or "").lower().strip(),
            )
            key = url_key or identity_key

            if key in seen:
                continue

            seen.add(key)
            unique_jobs.append(job)

        return unique_jobs

    def search(
        self,
        query: str = "",
        location: str = "",
        limit: Optional[int] = None,
        interactive: bool = False,
    ) -> List[Job]:

        jobs = []
        self.provider_results = {}
        self.provider_status = {}

        for provider in self.providers:

            try:
                app_logger.info(f"Starting search with {provider.__class__.__name__}...")
                parameters = inspect.signature(provider.search).parameters
                kwargs = {}
                if "query" in parameters:
                    kwargs["query"] = query
                if "location" in parameters:
                    kwargs["location"] = location
                if "limit" in parameters:
                    kwargs["limit"] = limit
                if interactive:
                    if "timeout_seconds" in parameters:
                        kwargs["timeout_seconds"] = settings.INTERACTIVE_PROVIDER_TIMEOUT_SECONDS
                    if "max_retries" in parameters:
                        kwargs["max_retries"] = settings.INTERACTIVE_PROVIDER_MAX_RETRIES
                provider_jobs = provider.search(**kwargs)

                if not isinstance(provider_jobs, list):
                    app_logger.warning(f"{provider.__class__.__name__} returned an invalid payload.")
                    self.provider_results[provider.__class__.__name__] = 0
                    self.provider_status[provider.__class__.__name__] = {"status": "malformed", "count": 0, "error": "Provider returned a non-list payload"}
                    continue

                provider_status = getattr(provider, "last_status", None)
                if not isinstance(provider_status, dict):
                    provider_status = {"status": "success", "count": len(provider_jobs), "error": None}
                else:
                    provider_status = dict(provider_status)
                    provider_status["count"] = len(provider_jobs)
                self.provider_results[provider.__class__.__name__] = len(provider_jobs)
                self.provider_status[provider.__class__.__name__] = provider_status
                app_logger.info(f"{provider.__class__.__name__} found {len(provider_jobs)} jobs.")
                jobs.extend(provider_jobs)

            except (httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
                self.provider_results[provider.__class__.__name__] = 0
                self.provider_status[provider.__class__.__name__] = {"status": "failed", "count": 0, "error": str(exc)}
                app_logger.error(f"{provider.__class__.__name__} failed: {exc}")
            except Exception as exc:
                self.provider_results[provider.__class__.__name__] = 0
                self.provider_status[provider.__class__.__name__] = {"status": "failed", "count": 0, "error": str(exc)}
                app_logger.error(f"{provider.__class__.__name__} failed unexpectedly: {exc}")

        self.total_jobs_retrieved = len(jobs)
        # SearchManager keeps a defensive provider-level dedupe for duplicate job payloads
        # returned by the same or multiple providers. The canonical, normalized dedupe is
        # still owned by JobFilter after URL/title/company normalization.
        return self._deduplicate_jobs(jobs)
