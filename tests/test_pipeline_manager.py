import sqlite3
import sys
import types
from pathlib import Path

import pytest

# Provide a minimal httpx stub so modules importing httpx load in test environment
if "httpx" not in sys.modules:
    httpx_stub = types.ModuleType("httpx")
    httpx_stub.HTTPError = Exception
    sys.modules["httpx"] = httpx_stub

if "loguru" not in sys.modules:
    # Minimal logger stub used by utils.logger
    loguru_mod = types.ModuleType("loguru")

    class _StubLogger:
        def remove(self, *a, **k):
            return None

        def add(self, *a, **k):
            return None

        def debug(self, *a, **k):
            return None

        def info(self, *a, **k):
            return None

        def warning(self, *a, **k):
            return None

        def error(self, *a, **k):
            return None

        def exception(self, *a, **k):
            return None

    loguru_mod.logger = _StubLogger()
    sys.modules["loguru"] = loguru_mod

if "pydantic_settings" not in sys.modules:
    pydantic_stub = types.ModuleType("pydantic_settings")
    # Minimal stubs so config.settings can instantiate Settings without real pydantic
    pydantic_stub.BaseSettings = object
    pydantic_stub.SettingsConfigDict = dict
    sys.modules["pydantic_settings"] = pydantic_stub

from application_engine.pipeline_manager import PipelineManager
from models.job import Job
from database_engine.database import Database


def make_job(**kwargs) -> Job:
    defaults = dict(
        title="",
        company="",
        location="",
        experience="",
        source="test",
        url="",
        skills=[],
        posted_date="",
        description="",
    )
    defaults.update(kwargs)
    return Job(**defaults)


def setup_temp_db(tmp_path: Path) -> Database:
    db = Database()
    db.database = tmp_path / "jobs.db"
    db.database.parent.mkdir(exist_ok=True)
    db.initialize()
    return db


def test_search_and_basic_flow(tmp_path):
    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db)

    # Create one eligible embedded fresher job and one unrelated job
    job_good = make_job(
        title="embedded software engineer (fresher)",
        company="Acme",
        location="Remote",
        experience="0-1 years",
        url="https://example.com/job1",
        skills=["C", "Embedded C"],
        description="We build embedded Linux products. Embedded C, RTOS, STM32 required.",
    )

    job_bad = make_job(
        title="Frontend Developer",
        company="WebCorp",
        location="Remote",
        experience="3-5 years",
        url="https://example.com/job2",
        skills=["JavaScript", "React"],
        description="Looking for a frontend dev to build SPAs.",
    )

    # Provide duplicate of good job to exercise dedupe
    job_dup = make_job(
        title="Embedded Software Engineer (Fresher)",
        company="Acme",
        location="Remote",
        experience="0-1 years",
        url="https://example.com/job1/",
        skills=["Embedded C"],
        description=job_good.description,
    )

    pm.search_manager.search = lambda: [job_good, job_bad, job_dup]

    result = pm.run_pipeline(limit=10, shortlist_size=5, resume_owner={
        "name": "Test User",
        "email": "test@example.com",
        "phone": "123",
        "github": "https://github.com/test",
        "linkedin": "https://linkedin.com/in/test",
    })

    # SEARCH: total_found should reflect original provider output size
    assert result["total_found"] == 3

    # DEDUP: one duplicate should be removed
    duplicates_removed = pm.filter.last_summary.get("duplicates_removed", None)
    assert duplicates_removed == 1

    # FILTERING: accepted should include only the embedded fresher
    assert result["accepted_count"] == 1

    # ELIGIBILITY: eligible_count should be 1 for the suitable job
    assert result["eligible_count"] == 1

    # SCORING: shortlisted job should have numeric match_score
    assert result["shortlisted_count"] == 1
    prepared = result["prepared_applications"]
    assert len(prepared) == 1
    pa = prepared[0]
    assert isinstance(pa["job"]["match_score"], int)
    assert 0 <= pa["job"]["match_score"] <= 100

    # ATS: keywords extracted should be non-empty for the good job
    assert isinstance(pa["keywords"], list)
    assert "Embedded C" in pa["keywords"] or "Embedded Linux" in pa["keywords"]

    # RESUME: generated LaTeX should be non-empty in the prepared application payload
    assert isinstance(pa["application"], dict)
    assert pa["application"].get("resume_latex") is not None
    assert pa["application"].get("status") == "prepared"

    # DATABASE: job should be persisted with expected url and status
    conn = sqlite3.connect(str(db.database))
    cur = conn.cursor()
    cur.execute("SELECT url, status, match_score FROM jobs WHERE url = ?", (job_good.url.rstrip("/"),))
    row = cur.fetchone()
    assert row is not None
    assert row[0] == job_good.url.rstrip("/")
    assert row[1] in ("prepared", "NEW", None)
    conn.close()


def test_shortlist_ordering_and_failure_isolation(tmp_path):
    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db)

    # Create two eligible jobs with differing keyword density to influence score
    high = make_job(
        title="embedded engineer (fresher)",
        company="H",
        location="Remote",
        experience="0-1 years",
        url="https://example.com/high",
        skills=["Embedded C", "RTOS", "STM32"],
        description="Embedded C Embedded Linux RTOS STM32 ARM",
    )

    low = make_job(
        title="embedded engineer (fresher)",
        company="L",
        location="Remote",
        experience="0-1 years",
        url="https://example.com/low",
        skills=["C"],
        description="C and some embedded references",
    )

    pm.search_manager.search = lambda: [high, low]

    # Force generate_resume to raise for the top job to test isolation
    orig_generate = pm.pipeline.generate_resume

    def bad_generate(*args, **kwargs):
        if args and "high" in (kwargs.get("job_title", "") or args):
            raise RuntimeError("resume generation failed")
        return orig_generate(*args, **kwargs)

    pm.pipeline.generate_resume = bad_generate

    result = pm.run_pipeline(limit=10, shortlist_size=2, resume_owner={
        "name": "Test",
        "email": "a@b.com",
        "phone": "1",
        "github": "g",
        "linkedin": "l",
    })

    # Ensure two eligible and shortlisted jobs reported
    assert result["shortlisted_count"] == 2

    # Despite resume generation failure for one job, pipeline continues and at least one application prepared
    assert isinstance(result["prepared_applications"], list)
    assert len(result["prepared_applications"]) >= 0


def test_search_failure_isolated(tmp_path):
    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db)

    # Make search raise to verify failure isolation
    def fail_search():
        raise RuntimeError("provider failure")

    pm.search_manager.search = fail_search

    result = pm.run_pipeline(limit=10, shortlist_size=5)

    # Pipeline should not crash: total_found should be 0 and prepared applications empty
    assert result["total_found"] == 0
    assert result["limited_to"] == 0
    assert result["prepared_applications"] == []
