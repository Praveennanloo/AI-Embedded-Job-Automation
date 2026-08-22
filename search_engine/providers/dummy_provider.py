from models.job import Job
from search_engine.providers.base_provider import BaseProvider


class DummyProvider(BaseProvider):

    def search(self, query: str = "", location: str = "", limit: int | None = None):

        jobs = [

            Job(
                title="Graduate Engineer Trainee",
                company="Demo Embedded Pvt Ltd",
                location="Hyderabad",
                experience="0-1 Years",
                source="Dummy Provider",
                url="https://example.com/job1",
                skills=["Embedded C", "Linux", "UART"],
                posted_date="2026-07-31",
            ),

            Job(
                title="Embedded Software Engineer",
                company="Demo IoT Systems",
                location="Bangalore",
                experience="Fresher",
                source="Dummy Provider",
                url="https://example.com/job2",
                skills=["C", "ESP32", "FreeRTOS"],
                posted_date="2026-07-31",
            ),

        ]

        return jobs[:limit] if limit else jobs
