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
        salary="  ₹8-12 LPA  ",
        employment_type=" full-time ",
        remote=True,
        application_url="  https://EXAMPLE.com/apply/abc  ",
        source_job_id="  JOB-123  ",
    )

    normalized = filterer.normalize_job(job)

    assert normalized.title == "Embedded C Engineer"
    assert normalized.company == "Acme Robotics"
    assert normalized.location == "Remote, India"
    assert normalized.experience == "Fresher / Intern"
    assert normalized.url == "https://example.com/jobs/abc"
    assert normalized.skills == ["Embedded C", "Linux"]
    assert normalized.posted_date == "2026-08-01"
    assert normalized.salary == "₹8-12 LPA"
    assert normalized.employment_type == "Full-time"
    assert normalized.remote is True
    assert normalized.application_url == "https://example.com/apply/abc"
    assert normalized.source_job_id == "JOB-123"

    key = filterer.dedupe_key(normalized)
    assert key == (("source_job_id", "job-123"),)


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


def test_linux_kernel_job_without_embedded_context_is_rejected():
    filterer = JobFilter()
    job = Job(
        title="Junior Linux Kernel Engineer - Ubuntu",
        company="Canonical",
        location="Home based - Worldwide",
        experience="Not Specified",
        source="Greenhouse",
        url="https://example.com/junior-linux-kernel",
        skills=[],
        posted_date="2026-08-01",
    )

    filtered = filterer.filter_jobs([job])

    assert filtered == []
    assert any("embedded" in reason.lower() or "hardware" in reason.lower() for reason in job.rejection_reasons)


def test_strong_embedded_c_fresher_job_is_accepted():
    filterer = JobFilter()
    job = Job(
        title="Embedded C Firmware Engineer",
        company="Astra Microsystems",
        location="Hyderabad",
        experience="Fresher",
        source="RemoteOK",
        url="https://example.com/embedded-c-fresher",
        skills=["Embedded C", "UART", "SPI", "ARM"],
        posted_date="2026-08-01",
    )

    filtered = filterer.filter_jobs([job])

    assert len(filtered) == 1
    assert filtered[0].match_score >= 50
    assert filtered[0].rejection_reasons == []


def test_embedded_linux_graduate_job_is_accepted():
    filterer = JobFilter()
    job = Job(
        title="Embedded Linux Graduate Engineer",
        company="IoT Robotics",
        location="Bengaluru",
        experience="Graduate Engineer",
        source="Greenhouse",
        url="https://example.com/embedded-linux-graduate",
        skills=["Embedded Linux", "Linux Kernel", "C", "GPIO"],
        posted_date="2026-08-02",
    )

    filtered = filterer.filter_jobs([job])

    assert len(filtered) == 1
    assert filtered[0].title == "Embedded Linux Graduate Engineer"
    assert filtered[0].rejection_reasons == []


def test_firmware_trainee_job_is_accepted():
    filterer = JobFilter()
    job = Job(
        title="Firmware Engineer Trainee",
        company="IoT Labs",
        location="Hyderabad",
        experience="Trainee",
        source="Greenhouse",
        url="https://example.com/firmware-trainee",
        skills=["Firmware", "MCU", "C"],
        posted_date="2026-08-03",
    )

    filtered = filterer.filter_jobs([job])

    assert len(filtered) == 1
    assert filtered[0].title == "Firmware Engineer Trainee"
    assert filtered[0].rejection_reasons == []


def test_rtos_freertos_junior_job_is_accepted():
    filterer = JobFilter()
    job = Job(
        title="RTOS / FreeRTOS Junior Engineer",
        company="Embedded Systems Co",
        location="Pune",
        experience="Junior",
        source="RemoteOK",
        url="https://example.com/rtos-junior",
        skills=["FreeRTOS", "STM32", "C", "UART"],
        posted_date="2026-08-04",
    )

    filtered = filterer.filter_jobs([job])

    assert len(filtered) == 1
    assert filtered[0].match_score >= 45
    assert filtered[0].rejection_reasons == []


def test_generic_software_graduate_job_is_rejected():
    filterer = JobFilter()
    job = Job(
        title="Graduate Software Engineer",
        company="CloudWorks",
        location="Remote",
        experience="Graduate",
        source="RemoteOK",
        url="https://example.com/software-graduate",
        skills=["Python", "Django"],
        posted_date="2026-08-05",
    )

    filtered = filterer.filter_jobs([job])

    assert filtered == []
    assert job.rejection_reasons


def test_generic_linux_administrator_is_rejected():
    filterer = JobFilter()
    job = Job(
        title="Junior Linux Administrator",
        company="OpsWorks",
        location="Remote",
        experience="Junior",
        source="RemoteOK",
        url="https://example.com/linux-admin",
        skills=["Linux", "Bash", "Docker"],
        posted_date="2026-08-06",
    )

    filtered = filterer.filter_jobs([job])

    assert filtered == []
    assert any("linux" in reason.lower() or "embedded" in reason.lower() for reason in job.rejection_reasons)


def test_unrelated_junior_job_is_rejected():
    filterer = JobFilter()
    job = Job(
        title="Junior Sales Executive",
        company="MarketForge",
        location="Hyderabad",
        experience="Junior",
        source="RemoteOK",
        url="https://example.com/sales-junior",
        skills=["Sales", "CRM"],
        posted_date="2026-08-07",
    )

    filtered = filterer.filter_jobs([job])

    assert filtered == []
    assert job.rejection_reasons


def test_missing_or_null_fields_are_handled():
    filterer = JobFilter()
    job = Job(
        title=None,
        company="",
        location=None,
        experience="Junior",
        source="RemoteOK",
        url="",
        skills=None,
        posted_date="",
    )

    filtered = filterer.filter_jobs([job])

    assert filtered == []
    assert job.rejection_reasons


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


def test_embedded_role_title_patterns_are_recognized():
    filterer = JobFilter()
    profile = {"skills": ["C", "Embedded C", "Linux", "GPIO", "ARM"], "experience": "fresher"}

    titles = [
        "Embedded Software Engineer",
        "Embedded Linux Engineer",
        "Firmware Engineer",
        "Embedded C Engineer",
        "IoT Engineer",
        "Device Driver Engineer",
        "Linux Engineer",
        "RTOS Engineer",
        "Graduate Engineer Trainee",
        "Embedded Systems Trainee",
        "Firmware Trainee",
        "Software Engineer - Embedded",
        "Embedded Intern",
        "Embedded Internship",
        "Any Embedded Fresher Role",
    ]

    for title in titles:
        job = Job(
            title=title,
            company="Target Systems",
            location="Remote, India",
            experience="Fresher" if "Intern" not in title and "Internship" not in title else "Internship",
            source="RemoteOK",
            url=f"https://example.com/{title.lower().replace(' ', '-')}",
            skills=["C", "Linux", "Embedded C", "GPIO"],
            posted_date="2026-08-01",
            description="Develop embedded software for Linux-based hardware, firmware, device drivers, and microcontrollers.",
        )
        analysis = filterer.analyze_job_intelligence(job, profile)
        assert analysis["role_category"] != "Unrelated", title
        assert analysis["match_score"] > 0, title


def test_candidate_specific_ranking():
    filterer = JobFilter()
    profile = {"skills": ["C", "Embedded C", "Linux", "GPIO", "ARM"], "experience": "fresher", "remote": True}

    perfect_match = Job(
        title="Embedded Linux Engineer",
        company="Acme Semiconductor",
        location="Remote, India",
        experience="0-1 years",
        source="RemoteOK",
        url="https://example.com/perfect-linux",
        skills=["Embedded Linux", "C", "Linux", "ARM", "GPIO"],
        posted_date="2026-08-01",
        description="Build embedded Linux applications, kernel drivers, and BSPs for ARM boards.",
    )
    strong_firmware = Job(
        title="Firmware Engineer",
        company="CoreIoT",
        location="Hyderabad",
        experience="Graduate",
        source="Greenhouse",
        url="https://example.com/firmware",
        skills=["C", "Firmware", "GPIO", "RTOS"],
        posted_date="2026-08-02",
        description="Firmware for microcontrollers and embedded devices using RTOS and C.",
    )
    missing_skills = Job(
        title="Embedded Software Engineer",
        company="ChipWorks",
        location="Pune",
        experience="Internship",
        source="RemoteOK",
        url="https://example.com/embedded-software",
        skills=["C"],
        posted_date="2026-08-03",
        description="Write embedded C for microcontrollers and hardware prototypes.",
    )
    experienced_only = Job(
        title="Senior Embedded Linux Engineer",
        company="Bespoke Devices",
        location="Remote",
        experience="5+ years",
        source="Greenhouse",
        url="https://example.com/senior-linux",
        skills=["Linux", "C", "ARM"],
        posted_date="2026-08-04",
        description="Senior Linux and device driver development for embedded platforms.",
    )
    unrelated = Job(
        title="Frontend Developer",
        company="WebWorks",
        location="Remote",
        experience="Experienced",
        source="RemoteOK",
        url="https://example.com/frontend",
        skills=["React", "Node", "CSS"],
        posted_date="2026-08-05",
        description="Build web dashboards and cloud interfaces.",
    )
    location_mismatch = Job(
        title="Embedded C Engineer",
        company="Edge Labs",
        location="Berlin",
        experience="Fresher",
        source="RemoteOK",
        url="https://example.com/berlin",
        skills=["C", "Embedded C", "UART", "GPIO"],
        posted_date="2026-08-06",
        description="Embedded C programming for microcontrollers and peripheral control.",
    )

    ranked = filterer.rank_jobs_for_candidate([perfect_match, strong_firmware, missing_skills, experienced_only, unrelated, location_mismatch], profile)
    assert ranked[0]["title"] == "Embedded Linux Engineer"
    assert ranked[0]["match_score"] >= ranked[1]["match_score"]
    assert ranked[0]["role_match"] == "Embedded Linux"
    assert ranked[0]["location_match"] is True
    assert ranked[1]["role_match"] in {"Firmware", "Embedded Systems", "Embedded Software"}
    assert ranked[-1]["role_match"] == "Unrelated"
    assert all(item["rank"] == index + 1 for index, item in enumerate(ranked))
    assert "ranking_reasons" in ranked[0]
    assert "matched_skills" in ranked[0]
    assert "missing_skills" in ranked[0]

    assert ranked[3]["experience_match"] in {"5+ years", "Experienced"}
    assert ranked[4]["location_match"] is False
    assert ranked[-1]["role_match"] == "Unrelated"
    assert ranked[-1]["match_score"] <= 35

    equal_jobs = [
        Job(title="Embedded C Engineer", company="A", location="Remote", experience="Fresher", source="S", url="https://example.com/a", skills=["C", "Embedded C"], posted_date="2026-08-01"),
        Job(title="Embedded C Engineer", company="A", location="Remote", experience="Fresher", source="S", url="https://example.com/b", skills=["C", "Embedded C"], posted_date="2026-08-02"),
    ]
    equal_ranked = filterer.rank_jobs_for_candidate(equal_jobs, profile)
    assert equal_ranked[0]["rank"] == 1
    assert equal_ranked[1]["rank"] == 2
    assert equal_ranked[0]["match_score"] == equal_ranked[1]["match_score"]


def test_block_2c_embedded_job_intelligence():
    filterer = JobFilter()
    profile = {"skills": ["C", "Embedded C", "Linux", "GPIO", "ARM"], "experience": "fresher"}

    linux_job = Job(
        title="Embedded Linux Engineer",
        company="Acme Semiconductor",
        location="Remote, India",
        experience="0-1 years",
        source="RemoteOK",
        url="https://example.com/linux",
        skills=["C", "Linux", "Embedded Linux", "ARM", "Make"],
        posted_date="2026-08-01",
        description="Develop Linux drivers and BSP for ARM boards. Work with Yocto, U-Boot, and embedded Linux on SoCs.",
    )
    linux_analysis = filterer.analyze_job_intelligence(linux_job, profile)
    assert linux_analysis["role_category"] == "Embedded Linux"
    assert "Linux" in " ".join(linux_analysis["matched_skills"]) or "Embedded Linux" in " ".join(linux_analysis["matched_skills"])
    assert linux_analysis["experience_level"] == "0-1 years"
    assert linux_analysis["embedded_relevance"] in {"High", "Medium"}
    assert linux_analysis["match_score"] > 0
    assert linux_analysis["location_match"] is True

    firmware_job = Job(
        title="Firmware Engineer",
        company="CoreIoT",
        location="Hyderabad",
        experience="Graduate",
        source="Greenhouse",
        url="https://example.com/firmware",
        skills=["C", "RTOS", "GPIO", "SPI"],
        posted_date="2026-08-02",
        description="Firmware for microcontrollers and embedded hardware with event-driven design.",
    )
    firmware = filterer.analyze_job_intelligence(firmware_job, profile)
    assert firmware["role_category"] in {"Firmware", "Embedded Systems", "Embedded Software"}
    assert "RTOS" in " ".join(firmware["matched_skills"]) or "C" in " ".join(firmware["matched_skills"])

    iot_job = Job(
        title="IoT Engineer Trainee",
        company="Smart Grid Labs",
        location="Bengaluru",
        experience="Trainee",
        source="RemoteOK",
        url="https://example.com/iot",
        skills=["Python", "C", "IoT", "GPIO"],
        posted_date="2026-08-03",
        description="Build IoT prototypes using microcontrollers and sensor nodes.",
    )
    iot = filterer.analyze_job_intelligence(iot_job, profile)
    assert iot["role_category"] == "IoT"
    assert iot["experience_level"] == "Trainee"

    unrelated_job = Job(
        title="Frontend Developer",
        company="WebWorks",
        location="Remote",
        experience="Experienced",
        source="RemoteOK",
        url="https://example.com/frontend",
        skills=["React", "Node", "CSS"],
        posted_date="2026-08-04",
        description="Build cloud-first web interfaces and dashboards.",
    )
    unrelated = filterer.analyze_job_intelligence(unrelated_job, profile)
    assert unrelated["role_category"] == "Unrelated"
    assert unrelated["embedded_relevance"] == "Low"
    assert unrelated["match_score"] <= 35
    assert any("unrelated" in reason.lower() for reason in unrelated["rejection_reasons"])

    experienced_only = Job(
        title="Senior Embedded Linux Engineer",
        company="ChipForge",
        location="Remote",
        experience="5+ years",
        source="Greenhouse",
        url="https://example.com/senior-linux",
        skills=["C", "Linux", "Kernel", "ARM"],
        posted_date="2026-08-05",
        description="Senior Linux kernel and device driver engineer for embedded systems.",
    )
    senior = filterer.analyze_job_intelligence(experienced_only, profile)
    assert senior["experience_level"] in {"Experienced", "5+ years"}
    assert senior["embedded_relevance"] in {"High", "Medium"}
    assert senior["match_score"] <= 60

    missing_skills_job = Job(
        title="Embedded C Engineer",
        company="IDK Labs",
        location="Remote, India",
        experience="Fresher",
        source="RemoteOK",
        url="https://example.com/missing",
        skills=["C"],
        posted_date="2026-08-06",
        description="Write embedded C for microcontrollers. Work with GPIO and timers.",
    )
    missing = filterer.analyze_job_intelligence(missing_skills_job, profile)
    assert "C" in " ".join(missing["matched_skills"])
    assert len(missing["missing_skills"]) >= 1
    assert missing["match_score"] >= 20

    repeated = filterer.analyze_job_intelligence(linux_job, profile)
    repeated_again = filterer.analyze_job_intelligence(linux_job, profile)
    assert repeated == repeated_again

    embedded_c_job = Job(
        title="Embedded C Engineer (Graduate)",
        company="IoT Forge",
        location="Pune",
        experience="Graduate",
        source="Greenhouse",
        url="https://example.com/embedded-c",
        skills=["Embedded C", "C", "UART", "SPI"],
        posted_date="2026-08-07",
        description="Develop embedded C for microcontrollers and peripherals with UART, SPI and GPIO interfaces.",
    )
    embedded_c = filterer.analyze_job_intelligence(embedded_c_job, profile)
    assert embedded_c["role_category"] in {"Embedded C", "Embedded Software"}
    assert "Embedded C" in " ".join(embedded_c["matched_skills"])
    assert embedded_c["match_score"] > 40

    assert "role_category" in linux_analysis
    assert "matched_skills" in linux_analysis
    assert "missing_skills" in linux_analysis
    assert "experience_level" in linux_analysis
    assert "location_match" in linux_analysis
    assert "embedded_relevance" in linux_analysis
    assert "match_score" in linux_analysis
    assert "rejection_reasons" in linux_analysis

def test_scheduler_uses_configured_interval_minutes():
    from app import JobSearchScheduler

    scheduler = JobSearchScheduler(interval_minutes=2)

    assert scheduler.interval_minutes == 2
    assert scheduler.interval_seconds == 120


def test_scheduler_runs_multiple_cycles_successfully(monkeypatch):
    import app

    calls = []

    def fake_cycle():
        calls.append("cycle")
        return [], {}, None

    monkeypatch.setattr(app, "execute_search_cycle", fake_cycle)
    scheduler = app.JobSearchScheduler(interval_minutes=0, sleep_fn=lambda seconds: None)

    completed_cycles = scheduler.run(cycle_limit=2)

    assert completed_cycles == 2
    assert len(calls) == 2


def test_scheduler_recovers_after_cycle_failure(monkeypatch):
    import app

    calls = []

    def fake_cycle():
        calls.append("cycle")
        if len(calls) == 1:
            raise RuntimeError("temporary provider outage")
        return [], {}, None

    monkeypatch.setattr(app, "execute_search_cycle", fake_cycle)
    scheduler = app.JobSearchScheduler(interval_minutes=0, sleep_fn=lambda seconds: None)

    completed_cycles = scheduler.run(cycle_limit=2)

    assert completed_cycles == 2
    assert len(calls) == 2


def test_scheduler_graceful_shutdown_stops_cleanly(monkeypatch):
    import threading
    import app

    calls = []

    def fake_cycle():
        calls.append("cycle")
        return [], {}, None

    stop_event = threading.Event()
    stop_event.set()
    monkeypatch.setattr(app, "execute_search_cycle", fake_cycle)
    scheduler = app.JobSearchScheduler(interval_minutes=1, sleep_fn=lambda seconds: None, stop_event=stop_event)

    completed_cycles = scheduler.run(cycle_limit=10)

    assert completed_cycles == 0
    assert calls == []
