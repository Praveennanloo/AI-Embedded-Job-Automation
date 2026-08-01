from typing import List

from models.job import Job
from utils.logger import app_logger


class SearchManager:

    def __init__(self):
        self.providers = []

    def register_provider(self, provider):
        app_logger.debug(f"Registering provider: {provider.__class__.__name__}")
        self.providers.append(provider)

    def search(self) -> List[Job]:

        jobs = []

        for provider in self.providers:

            try:
                app_logger.info(f"Starting search with {provider.__class__.__name__}...")
                provider_jobs = provider.search()

                app_logger.info(f"{provider.__class__.__name__} found {len(provider_jobs)} jobs.")

                jobs.extend(provider_jobs)

            except Exception as e:

                app_logger.error(f"{provider.__class__.__name__} failed: {e}")

        return jobs
