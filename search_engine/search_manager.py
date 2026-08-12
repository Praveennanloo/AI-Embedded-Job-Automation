from typing import List

import httpx

from models.job import Job
from utils.logger import app_logger


class SearchManager:

    def __init__(self):
        self.providers = []

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

    def search(self) -> List[Job]:

        jobs = []

        for provider in self.providers:

            try:
                app_logger.info(f"Starting search with {provider.__class__.__name__}...")
                provider_jobs = provider.search()

                if not isinstance(provider_jobs, list):
                    app_logger.warning(f"{provider.__class__.__name__} returned an invalid payload.")
                    continue

                app_logger.info(f"{provider.__class__.__name__} found {len(provider_jobs)} jobs.")
                jobs.extend(provider_jobs)

            except (httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
                app_logger.error(f"{provider.__class__.__name__} failed: {exc}")
            except Exception as exc:
                app_logger.error(f"{provider.__class__.__name__} failed unexpectedly: {exc}")

        return self._deduplicate_jobs(jobs)
