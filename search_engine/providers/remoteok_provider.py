import httpx

from models.job import Job
from search_engine.providers.base_provider import BaseProvider


class RemoteOKProvider(BaseProvider):

    API_URL = "https://remoteok.com/api"

    def search(self):

        jobs = []

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = httpx.get(
            self.API_URL,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

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
                    posted_date=date
                )
            )

        return jobs
