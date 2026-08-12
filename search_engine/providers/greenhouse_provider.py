import httpx

from models.job import Job
from search_engine.providers.base_provider import BaseProvider
from utils.logger import app_logger


class GreenhouseProvider(BaseProvider):

    BOARDS = [
        ("Canonical", "https://boards-api.greenhouse.io/v1/boards/canonical/jobs"),
        ("Samsara", "https://boards-api.greenhouse.io/v1/boards/samsara/jobs"),
        ("Flock Safety", "https://boards-api.greenhouse.io/v1/boards/flocksafety/jobs"),
    ]

    def search(self):

        jobs = []

        for company_name, url in self.BOARDS:

            try:
                app_logger.debug(f"Fetching Greenhouse jobs for {company_name}...")
                response = httpx.get(url, timeout=20)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code if exc.response is not None else "unknown"
                app_logger.warning(f"Greenhouse {company_name} returned HTTP {status}: {exc}")
                continue
            except (httpx.TimeoutException, httpx.RequestError, ValueError) as exc:
                app_logger.warning(f"Greenhouse {company_name} request failed: {exc}")
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

        return jobs
