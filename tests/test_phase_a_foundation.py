import asyncio
import sqlite3

import app
from database_engine.database import Database
from models.job import Job


def _job() -> Job:
    return Job(
        title="Embedded Firmware Engineer",
        company="Example",
        location="Bengaluru, India",
        experience="Fresher",
        source="test",
        url="https://example.test/jobs/1",
        skills=["Embedded C"],
        posted_date="2026-08-21",
    )


def test_clean_database_initialization_uses_current_schema(tmp_path):
    db = Database(tmp_path / "clean.db")
    db.initialize()

    with sqlite3.connect(db.database) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
        version = conn.execute("PRAGMA user_version").fetchone()[0]

    assert {"source_job_id", "remote", "description", "posted_date", "score"} <= columns
    assert version == db.SCHEMA_VERSION


def test_legacy_schema_is_migrated_with_backup(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE jobs (id INTEGER PRIMARY KEY, title TEXT, url TEXT UNIQUE, match_score INTEGER, status TEXT)"
        )
        conn.execute("INSERT INTO jobs (title, url) VALUES ('Existing role', 'https://example.test/existing')")

    db = Database(path)
    db.initialize()

    assert path.with_suffix(".db.pre_migration.bak").exists()
    with sqlite3.connect(path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
        existing = conn.execute("SELECT title FROM jobs WHERE url = ?", ("https://example.test/existing",)).fetchone()
    assert "description" in columns
    assert existing == ("Existing role",)


def test_failed_save_is_not_counted_as_persisted(tmp_path, monkeypatch):
    db = Database(tmp_path / "jobs.db")
    db.initialize()
    monkeypatch.setattr(db, "connect", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("disk unavailable")))

    assert db.save_jobs([_job()]) == 0
    assert db.last_save_errors


def test_lifespan_initializes_database_and_stops_scheduler(monkeypatch):
    events = []

    class FakeDatabase:
        def initialize(self):
            events.append("initialize")

    class FakeScheduler:
        def start(self):
            events.append("start")

        def stop(self):
            events.append("stop")

    monkeypatch.setattr(app, "db_engine", FakeDatabase())
    monkeypatch.setattr(app, "scheduler", FakeScheduler())

    async def exercise_lifespan():
        async with app.lifespan(app.app):
            assert events[:2] == ["initialize", "start"]

    asyncio.run(exercise_lifespan())
    assert events == ["initialize", "start", "stop"]
