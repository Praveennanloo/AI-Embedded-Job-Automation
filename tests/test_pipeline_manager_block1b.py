import sqlite3
import sys
import types
from pathlib import Path

# stubs for external deps used by modules under test
if "httpx" not in sys.modules:
    httpx_stub = types.ModuleType("httpx")
    httpx_stub.HTTPError = Exception
    sys.modules["httpx"] = httpx_stub

if "loguru" not in sys.modules:
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
    pydantic_stub.BaseSettings = object
    pydantic_stub.SettingsConfigDict = dict
    sys.modules["pydantic_settings"] = pydantic_stub

import pytest

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


def test_empty_search(tmp_path):
    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db)
    pm.search_manager.search = lambda: []

    res = pm.run_pipeline(limit=10, shortlist_size=5)

    assert res["total_found"] == 0
    assert res["total_eligible"] == 0
    assert res["total_rejected"] == 0
    assert res["persisted_count"] == 0
    assert res["shortlisted_jobs"] == []


def test_provider_failure_isolated(tmp_path):
    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db)

    def fail_search():
        raise RuntimeError("provider error")

    pm.search_manager.search = fail_search

    res = pm.run_pipeline(limit=10, shortlist_size=5)

    assert res["total_found"] == 0
    assert res["total_eligible"] == 0
    assert res["persisted_count"] == 0


def test_irrelevant_job_rejected(tmp_path):
    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db)

    job_bad = make_job(
        title="Frontend Developer",
        company="WebCorp",
        location="Remote",
        experience="3-5 years",
        url="https://example.com/job2",
        skills=["JavaScript", "React"],
        description="Looking for a frontend dev to build SPAs.",
    )

    pm.search_manager.search = lambda: [job_bad]

    res = pm.run_pipeline(limit=10, shortlist_size=5)

    assert res["total_found"] == 1
    assert res["total_eligible"] == 0
    assert res["total_rejected"] >= 1
    assert res["persisted_count"] == 0


def test_eligible_job_scored_and_persisted(tmp_path):
    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db)

    job_good = make_job(
        title="embedded software engineer (fresher)",
        company="Acme",
        location="Remote",
        experience="0-1 years",
        url="https://example.com/job1",
        skills=["C", "Embedded C"],
        description="We build embedded Linux products. Embedded C, RTOS, STM32 required.",
    )

    pm.search_manager.search = lambda: [job_good]

    res = pm.run_pipeline(limit=10, shortlist_size=5)

    assert res["total_found"] == 1
    assert res["total_eligible"] == 1
    assert res["persisted_count"] == 1
    assert len(res["shortlisted_jobs"]) == 1
    job_payload = res["shortlisted_jobs"][0]
    assert isinstance(job_payload["match_score"], int)


def test_sorting_and_top_n(tmp_path):
    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db)

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

    med = make_job(
        title="embedded engineer (fresher)",
        company="M",
        location="Remote",
        experience="0-1 years",
        url="https://example.com/med",
        skills=["Embedded C", "C"],
        description="Embedded C and C",
    )

    pm.search_manager.search = lambda: [low, med, high]

    res = pm.run_pipeline(limit=10, shortlist_size=2)

    assert res["total_eligible"] == 3
    # persisted_count should equal shortlist size (2)
    assert res["persisted_count"] == 2
    shortlisted = res["shortlisted_jobs"]
    assert len(shortlisted) == 2
    scores = [j["match_score"] for j in shortlisted]
    assert scores[0] >= scores[1]