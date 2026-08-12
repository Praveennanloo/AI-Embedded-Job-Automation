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


def test_relevant_embedded_fresher_job_passes():
    filterer = JobFilter()
    job = Job(
        title="Embedded Linux Engineer",
        company="Acme Robotics",
        location="Remote, India",
        experience="Fresher",
        source="RemoteOK",
        url="https://example.com/embedded-linux-fresher",
        skills=["C", "Linux", "Embedded C"],
        posted_date="2026-08-01",
    )

    filtered = filterer.filter_jobs([job])

    assert len(filtered) == 1
    assert filtered[0].title == "Embedded Linux Engineer"
    assert filtered[0].match_score >= 25
    assert filtered[0].rejection_reasons == []


def test_unrelated_software_job_is_rejected():
    filterer = JobFilter()
    job = Job(
        title="Senior Backend Engineer",
        company="CloudWorks",
        location="Bengaluru",
        experience="3-5 Years",
        source="RemoteOK",
        url="https://example.com/backend-engineer",
        skills=["Python", "Django", "Postgres"],
        posted_date="2026-08-01",
    )

    filtered = filterer.filter_jobs([job])

    assert filtered == []
    assert job.rejection_reasons
    assert any("embedded" in reason.lower() for reason in job.rejection_reasons)


def test_missing_skills_and_description_do_not_crash():
    filterer = JobFilter()
    job = Job(
        title="Firmware Engineer Trainee",
        company="IoT Labs",
        location="Hyderabad",
        experience="Trainee",
        source="Greenhouse",
        url="https://example.com/firmware-trainee",
        skills=[],
        posted_date="2026-08-01",
    )

    filtered = filterer.filter_jobs([job])

    assert len(filtered) == 1
    assert filtered[0].title == "Firmware Engineer Trainee"


def test_internship_or_trainee_job_is_recognized():
    filterer = JobFilter()
    jobs = [
        Job(
            title="Embedded Software Intern",
            company="Beta Labs",
            location="Bengaluru",
            experience="Internship",
            source="Greenhouse",
            url="https://example.com/embedded-software-intern",
            skills=["Embedded C", "GPIO"],
            posted_date="2026-08-02",
        ),
        Job(
            title="Robotics Trainee",
            company="Gamma Systems",
            location="Pune",
            experience="Trainee",
            source="RemoteOK",
            url="https://example.com/robotics-trainee",
            skills=["ARM", "RTOS"],
            posted_date="2026-08-03",
        ),
    ]

    filtered = filterer.filter_jobs(jobs)

    assert len(filtered) == 2
    assert {job.title for job in filtered} == {"Embedded Software Intern", "Robotics Trainee"}


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


def test_search_manager_handles_provider_failures_without_stopping_others():
    manager = SearchManager()
    manager.register_provider(DummyProviderA())
    manager.register_provider(DummyProviderB())
    manager.register_provider(DummyProviderC())

    jobs = manager.search()

    assert len(jobs) == 1
    assert jobs[0].title == "Embedded Linux Engineer"


def test_filtering_produces_explainable_rejection_reasons():
    filterer = JobFilter()
    job = Job(
        title="Senior Product Analyst",
        company="Analytic Labs",
        location="Remote",
        experience="Senior",
        source="RemoteOK",
        url="https://example.com/product-analyst",
        skills=["SQL", "Python"],
        posted_date="2026-08-01",
    )

    filtered = filterer.filter_jobs([job])

    assert filtered == []
    assert job.rejection_reasons
    assert any("embedded" in reason.lower() or "entry-level" in reason.lower() for reason in job.rejection_reasons)
