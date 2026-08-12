import httpx

from models.job import Job
from search_engine.providers.base_provider import BaseProvider
from utils.logger import app_logger


class RemoteOKProvider(BaseProvider):

    API_URL = "https://remoteok.com/api"

    def search(self):

        jobs = []

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        try:
            response = httpx.get(
                self.API_URL,
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            app_logger.warning(f"RemoteOK returned HTTP {status}: {exc}")
            return []
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as exc:
            app_logger.warning(f"RemoteOK request failed: {exc}")
            return []

        try:
            data = response.json()
        except ValueError as exc:
            app_logger.warning(f"RemoteOK returned invalid JSON: {exc}")
            return []

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

        return jobs
