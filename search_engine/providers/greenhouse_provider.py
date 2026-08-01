import httpx

from models.job import Job
from search_engine.providers.base_provider import BaseProvider
from utils.logger import app_logger


class GreenhouseProvider(BaseProvider):

    def search(self):

        jobs = []

        boards = [
            ("Canonical", "https://boards-api.greenhouse.io/v1/boards/canonical/jobs"),
            ("Samsara", "https://boards-api.greenhouse.io/v1/boards/samsara/jobs"),
            ("Flock Safety", "https://boards-api.greenhouse.io/v1/boards/flocksafety/jobs"),
        ]

        for company_name, url in boards:

            try:
                app_logger.debug(f"Fetching Greenhouse jobs for {company_name}...")
                response = httpx.get(url, timeout=20)
                response.raise_for_status()

                data = response.json()
                count = 0

                for item in data.get("jobs", []):

                    title = item.get("title", "")

                    if not any(
                        keyword.lower() in title.lower()
                        for keyword in [
                            "embedded",
                            "firmware",
                            "linux",
                            "c",
                            "driver",
                            "hardware",
                        ]
                    ):
                        continue

                    jobs.append(
                        Job(
                            title=title,
                            company=company_name,
                            location=item.get("location", {}).get("name", "Unknown"),
                            experience="Not Specified",
                            source="Greenhouse",
                            url=item.get("absolute_url", ""),
                            skills=[],
                            posted_date="",
                        )
                    )
                    count += 1
                
                app_logger.debug(f"Found {count} matching jobs for {company_name} on Greenhouse.")

            except Exception as e:
                app_logger.error(f"Greenhouse Error for {company_name}: {e}")

        return jobs
