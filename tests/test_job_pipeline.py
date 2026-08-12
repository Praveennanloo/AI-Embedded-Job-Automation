import httpx

from ai_engine.job_filter import JobFilter
from models.job import Job
from search_engine.search_manager import SearchManager


class DummyProviderA:
    def search(self):
        raise httpx.TimeoutException("provider timed out")


class DummyProviderB:
    def search(self):
        return [
            Job(
                title="Embedded Linux Engineer",
                company="Acme Robotics",
                location="Hyderabad",
                experience="Fresher",
                source="RealProvider",
                url="https://example.com/job-1",
                skills=["Embedded C", "Linux"],
                posted_date="2026-08-01",
            )
        ]


class DummyProviderC:
    def search(self):
        return [
            Job(
                title="Embedded Linux Engineer",
                company="Acme Robotics",
                location="Hyderabad",
                experience="Fresher",
                source="RealProvider",
                url="https://example.com/job-1",
                skills=["Embedded C", "Linux"],
                posted_date="2026-08-01",
            )
        ]


def test_normalize_job_fields():
    filterer = JobFilter()
    job = Job(
        title="  embedded c engineer  ",
        company="   acme robotics   ",
        location="  remote, india  ",
        experience="  fresher / intern  ",
        source="RemoteOK",
        url="  https://EXAMPLE.com/jobs/abc  ",
        skills=[" embedded c ", " linux ", ""],
        posted_date=" 2026-08-01 ",
    )

    normalized = filterer.normalize_job(job)

    assert normalized.title == "Embedded C Engineer"
    assert normalized.company == "Acme Robotics"
    assert normalized.location == "Remote, India"
    assert normalized.experience == "Fresher / Intern"
    assert normalized.url == "https://example.com/jobs/abc"
    assert normalized.skills == ["Embedded C", "Linux"]
    assert normalized.posted_date == "2026-08-01"


def test_deduplicate_jobs_by_url_and_identity():
    filterer = JobFilter()
    jobs = [
        Job(
            title="Embedded Linux Engineer",
            company="Acme Robotics",
            location="Hyderabad",
            experience="Fresher",
            source="RemoteOK",
            url="https://example.com/job-1",
            skills=["Embedded C", "Linux"],
            posted_date="2026-08-01",
        ),
        Job(
            title="Embedded Linux Engineer",
            company="Acme Robotics",
            location="Hyderabad",
            experience="Fresher",
            source="RemoteOK",
            url="https://example.com/job-1",
            skills=["Embedded C", "Linux"],
            posted_date="2026-08-01",
        ),
        Job(
            title="Embedded Linux Engineer",
            company="Acme Robotics",
            location="Hyderabad",
            experience="Fresher",
            source="RemoteOK",
            url="https://example.com/job-2",
            skills=["Embedded C", "Linux"],
            posted_date="2026-08-01",
        ),
    ]

    deduped = filterer.deduplicate_jobs(jobs)

    assert len(deduped) == 2
    assert {job.url for job in deduped} == {"https://example.com/job-1", "https://example.com/job-2"}


def test_filter_jobs_keeps_embedded_fresher_and_intern_roles():
    filterer = JobFilter()
    jobs = [
        Job(
            title="Embedded Firmware Engineer",
            company="Acme Robotics",
            location="Remote, India",
            experience="Fresher",
            source="RemoteOK",
            url="https://example.com/embedded-firmware",
            skills=["C", "Linux", "RTOS"],
            posted_date="2026-08-01",
        ),
        Job(
            title="Linux Intern",
            company="Beta Labs",
            location="Bengaluru",
            experience="Intern",
            source="Greenhouse",
            url="https://example.com/linux-intern",
            skills=["Linux", "C"],
            posted_date="2026-08-02",
        ),
        Job(
            title="Product Manager",
            company="Gamma",
            location="Remote",
            experience="Senior",
            source="RemoteOK",
            url="https://example.com/product-manager",
            skills=["Strategy"],
            posted_date="2026-08-03",
        ),
    ]

    filtered = filterer.filter_jobs(jobs)

    assert len(filtered) == 2
    assert {job.title for job in filtered} == {"Embedded Firmware Engineer", "Linux Intern"}


def test_search_manager_handles_provider_failures_without_stopping_others():
    manager = SearchManager()
    manager.register_provider(DummyProviderA())
    manager.register_provider(DummyProviderB())
    manager.register_provider(DummyProviderC())

    jobs = manager.search()

    assert len(jobs) == 1
    assert jobs[0].title == "Embedded Linux Engineer"
