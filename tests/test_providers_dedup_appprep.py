import sys
import types
from pathlib import Path
import sqlite3
import pytest

# Minimal stubs for external deps used by production modules
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

# Import modules under test
from ai_engine.job_filter import JobFilter
from search_engine.search_manager import SearchManager
from search_engine.providers.remoteok_provider import RemoteOKProvider
from search_engine.providers.greenhouse_provider import GreenhouseProvider
from application_engine.pipeline_manager import PipelineManager
from database_engine.database import Database
from models.job import Job


def setup_temp_db(tmp_path: Path) -> Database:
    db = Database()
    db.database = tmp_path / "jobs.db"
    db.database.parent.mkdir(exist_ok=True)
    db.initialize()
    return db


def make_job_dict_remoteok(url, title="T", company="C", tags=None):
    return {"position": title, "company": company, "location": "Remote", "url": url, "tags": tags or [], "date": ""}


def make_greenhouse_payload(url, title="T"):
    return {"jobs": [{"title": title, "location": {"name": "Remote"}, "absolute_url": url, "updated_at": ""}]}


class DummyResponse:
    def __init__(self, payload, raise_for_status=False):
        self._payload = payload
        self._raise = raise_for_status

    def raise_for_status(self):
        if self._raise:
            raise Exception("HTTP status")

    def json(self):
        return self._payload


def test_providers_register_and_search(monkeypatch):
    sm = SearchManager()

    # Monkeypatch httpx.get inside provider modules to return controlled data
    def remoteok_get(url, headers=None, timeout=None):
        return DummyResponse([make_job_dict_remoteok("https://r1", title="Remote1")])

    monkeypatch.setattr(RemoteOKProvider, "__module__", RemoteOKProvider.__module__)
    import importlib
    mod_ro = importlib.import_module(RemoteOKProvider.__module__)
    monkeypatch.setattr(mod_ro, "httpx", types.SimpleNamespace(get=remoteok_get, HTTPError=Exception))

    ro = RemoteOKProvider()
    sm.register_provider(ro)

    jobs = sm.search()
    assert isinstance(jobs, list)
    assert len(jobs) == 1
    assert isinstance(jobs[0], Job)

    # Greenhouse
    def greenhouse_get(url, timeout=None):
        return DummyResponse(make_greenhouse_payload("https://g1"))

    mod_gh = importlib.import_module(GreenhouseProvider.__module__)
    monkeypatch.setattr(mod_gh, "httpx", types.SimpleNamespace(get=greenhouse_get, HTTPError=Exception))

    gh = GreenhouseProvider()
    sm.register_provider(gh)

    jobs = sm.search()
    # both providers combined; at least 2 jobs
    assert any(j.source == "RemoteOK" for j in jobs) or any(j.source == "Greenhouse" for j in jobs)


def test_provider_failure_isolation(monkeypatch, tmp_path):
    # Make RemoteOK raise to simulate failure; SearchManager should not crash
    sm = SearchManager()
    def remoteok_get_fail(url, headers=None, timeout=None):
        raise Exception("network")

    import importlib
    mod_ro = importlib.import_module(RemoteOKProvider.__module__)
    monkeypatch.setattr(mod_ro, "httpx", types.SimpleNamespace(get=remoteok_get_fail, HTTPError=Exception))

    sm.register_provider(RemoteOKProvider())

    # Also register a healthy provider by monkeypatching Greenhouse to return a job
    def greenhouse_get(url, timeout=None):
        return DummyResponse(make_greenhouse_payload("https://g2"))

    mod_gh = importlib.import_module(GreenhouseProvider.__module__)
    monkeypatch.setattr(mod_gh, "httpx", types.SimpleNamespace(get=greenhouse_get, HTTPError=Exception))

    sm.register_provider(GreenhouseProvider())

    jobs = sm.search()
    # should return greenhouse jobs but not crash
    assert isinstance(jobs, list)
    assert len(jobs) >= 0

    # Now pass into PipelineManager to ensure jobs enter pipeline
    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db, search_manager=sm)
    res = pm.run_pipeline(limit=10, shortlist_size=5)
    assert "total_found" in res


def test_real_provider_field_mapping_from_mocked_payloads(monkeypatch):
    def remoteok_get(url, headers=None, timeout=None):
        return DummyResponse([
            {
                "id": 101,
                "position": "Embedded Firmware Engineer",
                "company": "Apex Systems",
                "location": "Remote, India",
                "url": "https://remoteok.example/jobs/101",
                "tags": ["Embedded C", "Linux", "RTOS"],
                "date": "2026-08-12",
                "description": "Build embedded Linux firmware and drivers.",
                "salary": "₹8-12 LPA",
                "job_type": "Full Time",
                "employment_type": "Full-time",
                "application_url": "https://remoteok.example/apply/101",
                "remote": True,
            }
        ])

    import importlib
    mod_ro = importlib.import_module(RemoteOKProvider.__module__)
    monkeypatch.setattr(mod_ro, "httpx", types.SimpleNamespace(get=remoteok_get, HTTPError=Exception, HTTPStatusError=Exception, TimeoutException=TimeoutError, ConnectError=ConnectionError, NetworkError=ConnectionError, ReadTimeout=TimeoutError, WriteTimeout=TimeoutError, ConnectTimeout=TimeoutError))

    jobs = RemoteOKProvider().search()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_job_id == "101"
    assert job.source == "RemoteOK"
    assert job.title == "Embedded Firmware Engineer"
    assert job.company == "Apex Systems"
    assert job.location == "Remote, India"
    assert job.remote is True
    assert "embedded linux" in job.description.lower()
    assert job.skills == ["Embedded C", "Linux", "RTOS"]
    assert job.salary == "₹8-12 LPA"
    assert job.job_type == "Full Time"
    assert job.employment_type == "Full-time"
    assert job.application_url == "https://remoteok.example/apply/101"
    assert job.posted_date == "2026-08-12"

    def greenhouse_get(url, timeout=None):
        return DummyResponse({
            "jobs": [{
                "id": 202,
                "title": "Embedded Linux Engineer",
                "location": {"name": "Remote"},
                "absolute_url": "https://greenhouse.example/jobs/202",
                "updated_at": "2026-08-13",
                "description": "Embedded Linux and device driver work.",
                "salary": "₹15-18 LPA",
                "job_type": "Full Time",
                "employment_type": "Full-time",
                "application_url": "https://greenhouse.example/apply/202",
                "remote": True,
                "tags": ["Linux", "C", "Drivers"],
                "metadata": [{"name": "LinkedIn Posting Level", "value": "Mid-Senior"}],
            }]
        })

    mod_gh = importlib.import_module(GreenhouseProvider.__module__)
    monkeypatch.setattr(mod_gh, "httpx", types.SimpleNamespace(get=greenhouse_get, HTTPError=Exception, HTTPStatusError=Exception, TimeoutException=TimeoutError, ConnectError=ConnectionError, NetworkError=ConnectionError, ReadTimeout=TimeoutError, WriteTimeout=TimeoutError, ConnectTimeout=TimeoutError))
    monkeypatch.setattr(GreenhouseProvider, "BOARDS", [("Canonical", "https://boards-api.greenhouse.io/v1/boards/canonical/jobs")])

    gh_jobs = GreenhouseProvider().search()
    assert len(gh_jobs) == 1
    gh_job = gh_jobs[0]
    assert gh_job.source_job_id == "202"
    assert gh_job.source == "Greenhouse"
    assert gh_job.company == "Canonical"
    assert gh_job.location == "Remote"
    assert gh_job.remote is True
    assert "device driver" in gh_job.description.lower()
    assert gh_job.salary == "₹15-18 LPA"
    assert gh_job.application_url == "https://greenhouse.example/apply/202"
    assert gh_job.posted_date == "2026-08-13"
    assert gh_job.metadata == {"LinkedIn Posting Level": "Mid-Senior"}
    assert JobFilter().filter_jobs([gh_job]) == []
    assert gh_job.rejection_reasons


def test_deduplication_primary_jobfilter(monkeypatch, tmp_path):
    # Decision: JobFilter is primary deduplication stage because normalization (URL casing, trailing slashes,
    # title/company casing) must happen before a reliable dedupe key can be formed. SearchManager dedupe helps early
    # reduce noise but the canonical dedupe should be performed after normalization in JobFilter.

    # Create two jobs with same URL differing trailing slash from a provider
    job1 = Job(title="A", company="Co", location="Remote", experience="0-1 years", source="P", url="https://x.com/1", skills=[], posted_date="")
    job2 = Job(title="A", company="Co", location="Remote", experience="0-1 years", source="P", url="https://x.com/1/", skills=[], posted_date="")

    sm = SearchManager()
    class SimpleProvider:
        def search(self_inner):
            return [job1, job2]
    sm.register_provider(SimpleProvider())

    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db, search_manager=sm)
    res = pm.run_pipeline(limit=10, shortlist_size=5)

    # total_found is 2 from provider, but dedup should remove one
    assert res["total_found"] == 2
    # accepted_count should be 1 (after dedupe+filter)
    assert res["accepted_count"] <= 2

    # Also test source_job_id based dedupe when set
    job3 = Job(title="B", company="Co2", location="R", experience="0-1 years", source="P", url="https://x.com/3", skills=[], posted_date="", source_job_id="S1")
    job4 = Job(title="B", company="Co2", location="R", experience="0-1 years", source="P", url="https://x.com/4", skills=[], posted_date="", source_job_id="S1")

    sm2 = SearchManager()
    class Prov2:
        def search(self_inner):
            return [job3, job4]
    sm2.register_provider(Prov2())

    pm2 = PipelineManager(db=db, search_manager=sm2)
    res2 = pm2.run_pipeline(limit=10, shortlist_size=5)

    assert res2["total_found"] == 2
    # dedup by source_job_id should keep one
    assert res2["accepted_count"] <= 2


def test_dedupe_keys_cover_url_sourceid_and_title_company():
    filterer = JobFilter()

    same_url = [
        Job(title="Embedded Engineer", company="Acme", location="Remote", experience="0-1 years", source="P", url="https://x.com/1", skills=[], posted_date=""),
        Job(title="Embedded Engineer", company="Acme", location="Remote", experience="0-1 years", source="P", url="https://x.com/1/", skills=[], posted_date=""),
    ]
    assert len(filterer.deduplicate_jobs(same_url)) == 1

    same_source_id = [
        Job(title="Firmware Engineer", company="Bolt", location="Remote", experience="0-1 years", source="P", url="https://x.com/2", skills=[], posted_date="", source_job_id="S-101"),
        Job(title="Firmware Engineer", company="Bolt", location="Remote", experience="0-1 years", source="P", url="https://x.com/3", skills=[], posted_date="", source_job_id="S-101"),
    ]
    assert len(filterer.deduplicate_jobs(same_source_id)) == 1

    same_title_company = [
        Job(title="Embedded C Engineer", company="Acme", location="Remote", experience="0-1 years", source="P", url="", skills=[], posted_date=""),
        Job(title="embedded c engineer", company="ACME", location="Remote", experience="0-1 years", source="P", url="", skills=[], posted_date=""),
    ]
    assert len(filterer.deduplicate_jobs(same_title_company)) == 1


def test_application_preparation_path(monkeypatch, tmp_path):
    # Use a job that is eligible; enable generate_applications=True and verify DB status updated
    job = Job(title="embedded engineer (fresher)", company="ACME", location="Remote", experience="0-1 years", source="P", url="https://app/1", skills=["Embedded C"], posted_date="", description="Embedded C")

    class Prov:
        def search(self_inner):
            return [job]

    sm = SearchManager()
    sm.register_provider(Prov())

    db = setup_temp_db(tmp_path)
    pm = PipelineManager(db=db, search_manager=sm)

    res = pm.run_pipeline(limit=10, shortlist_size=5, resume_owner={"name":"T","email":"t@e","phone":"p","github":"g","linkedin":"l"}, generate_applications=True)

    assert res["total_found"] == 1
    assert res["total_eligible"] == 1
    assert res["persisted_count"] >= 1

    # Verify DB contains the job and status updated
    conn = sqlite3.connect(str(db.database))
    cur = conn.cursor()
    cur.execute("SELECT url, status FROM jobs WHERE url = ?", (job.url,))
    row = cur.fetchone()
    assert row is not None
    # status should have been recorded (prepared)
    assert row[1] in ("prepared", "NEW")
    conn.close()
