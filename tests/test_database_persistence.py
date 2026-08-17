import sqlite3
from pathlib import Path
from database_engine.database import Database
from models.job import Job
import app


def test_save_jobs_multiple(tmp_path):
    db_path = tmp_path / "jobs.db"
    db = Database()
    db.database = db_path
    db.database.parent.mkdir(parents=True, exist_ok=True)
    db.initialize()

    jobs = [
        Job(
            title="Test Job 1",
            company="Acme",
            location="Remote",
            experience="Fresher",
            source="Dummy",
            url="https://example.com/job1",
            skills=["C"],
            posted_date="2026-08-01",
        ),
        Job(
            title="Test Job 2",
            company="Acme",
            location="Remote",
            experience="Fresher",
            source="Dummy",
            url="https://example.com/job2",
            skills=["C++"],
            posted_date="2026-08-01",
        ),
    ]

    saved = db.save_jobs(jobs)
    assert saved == 2

    conn = sqlite3.connect(db.database)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 2


def test_save_jobs_empty(tmp_path):
    db_path = tmp_path / "jobs_empty.db"
    db = Database()
    db.database = db_path
    db.database.parent.mkdir(parents=True, exist_ok=True)
    db.initialize()

    saved = db.save_jobs([])
    assert saved == 0

    conn = sqlite3.connect(db.database)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 0


def test_save_job_single_still_works(tmp_path):
    db_path = tmp_path / "job_single.db"
    db = Database()
    db.database = db_path
    db.database.parent.mkdir(parents=True, exist_ok=True)
    db.initialize()

    job = Job(
        title="Single Job",
        company="Beta",
        location="Hyderabad",
        experience="Fresher",
        source="Dummy",
        url="https://example.com/single",
        skills=["Embedded C"],
        posted_date="2026-08-01",
    )

    db.save_job(job)

    conn = sqlite3.connect(db.database)
    cur = conn.cursor()
    cur.execute("SELECT title, company FROM jobs WHERE url = ?", (job.url,))
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "Single Job"
    assert row[1] == "Beta"


def test_execute_search_cycle_persists(monkeypatch, tmp_path):
    # Prepare a test database and a test job
    db_path = tmp_path / "jobs_app.db"
    test_db = Database()
    test_db.database = db_path
    test_db.database.parent.mkdir(parents=True, exist_ok=True)
    test_db.initialize()

    test_job = Job(
        title="Embedded Linux Graduate Engineer",
        company="Gamma",
        location="Remote, India",
        experience="Graduate Engineer",
        source="Dummy",
        url="https://example.com/pipeline",
        skills=["Embedded Linux", "C"],
        posted_date="2026-08-01",
    )

    # Monkeypatch app.search_manager.search to return our test job
    monkeypatch.setattr(app.search_manager, "search", lambda: [test_job])

    # Monkeypatch app.db_engine to use our test database which now has save_jobs
    monkeypatch.setattr(app, "db_engine", test_db)

    # Run the search cycle which should call db_engine.save_jobs
    filtered_jobs, stats, err = app.execute_search_cycle(query="", limit=10)

    # Verify that the job was persisted
    conn = sqlite3.connect(test_db.database)
    cur = conn.cursor()
    cur.execute("SELECT url FROM jobs WHERE url = ?", (test_job.url,))
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == test_job.url
