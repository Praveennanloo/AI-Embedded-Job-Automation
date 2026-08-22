import sqlite3
import shutil
from pathlib import Path
from typing import Iterable, List

from config.settings import settings
from utils.logger import app_logger


class Database:
    """SQLite persistence with additive, versioned schema upgrades."""

    SCHEMA_VERSION = 2

    def __init__(self, database_path=None):
        configured_path = database_path or getattr(settings, "DATABASE_PATH", "")
        if not configured_path:
            configured_path = Path("database") / getattr(settings, "DATABASE_NAME", "jobs.db")
        self.database = Path(configured_path)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.last_error = None
        self.last_save_errors: List[str] = []

    def connect(self):
        return sqlite3.connect(self.database)

    def initialize(self):
        app_logger.info("Initializing database...")
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            experience TEXT,
            source TEXT,
            source_job_id TEXT,
            remote INTEGER,
            description TEXT,
            url TEXT UNIQUE,
            skills TEXT,
            salary TEXT,
            job_type TEXT,
            employment_type TEXT,
            application_url TEXT,
            posted_date TEXT,
            score INTEGER DEFAULT 0,
            match_score INTEGER DEFAULT 0,
            status TEXT,
            rejection_reasons TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Existing installations used a smaller jobs table. SQLite only needs
        # additive ALTER TABLE statements for this safe migration, so no job
        # rows are deleted or rewritten.
        expected_columns = {
            "source_job_id": "TEXT",
            "remote": "INTEGER DEFAULT 0",
            "description": "TEXT DEFAULT ''",
            "salary": "TEXT DEFAULT ''",
            "job_type": "TEXT DEFAULT ''",
            "employment_type": "TEXT DEFAULT ''",
            "application_url": "TEXT DEFAULT ''",
            "posted_date": "TEXT DEFAULT ''",
            "score": "INTEGER DEFAULT 0",
            "rejection_reasons": "TEXT DEFAULT ''",
        }
        existing_columns = {row[1] for row in cur.execute("PRAGMA table_info(jobs)")}
        missing_columns = [name for name in expected_columns if name not in existing_columns]
        if missing_columns:
            backup_path = self.database.with_suffix(self.database.suffix + ".pre_migration.bak")
            if self.database.exists() and not backup_path.exists():
                shutil.copy2(self.database, backup_path)
                app_logger.info(f"Backed up pre-migration database to {backup_path}")
            for name in missing_columns:
                cur.execute(f"ALTER TABLE jobs ADD COLUMN {name} {expected_columns[name]}")
            app_logger.info(f"Migrated jobs schema; added: {', '.join(missing_columns)}")

        # Create indexes for faster searching and filtering
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_url ON jobs(url);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_status ON jobs(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_match_score ON jobs(match_score);")
        cur.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

        try:
            conn.commit()
        finally:
            conn.close()
        app_logger.info("Database initialized successfully.")

    def save_job(self, job) -> bool:
        conn = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            skills_str = ", ".join(job.skills) if job.skills else ""
            rejection_str = ", ".join(job.rejection_reasons) if getattr(job, "rejection_reasons", None) else ""
            remote_val = 1 if getattr(job, "remote", False) else 0
            cur.execute("""
            INSERT INTO jobs
            (
                title,
                company,
                location,
                experience,
                source,
                source_job_id,
                remote,
                description,
                url,
                skills,
                salary,
                job_type,
                employment_type,
                application_url,
                posted_date,
                score,
                match_score,
                status,
                rejection_reasons
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                match_score = excluded.match_score,
                status = CASE 
                            WHEN jobs.status = 'NEW' THEN excluded.status 
                            ELSE jobs.status 
                         END
            """, (
                job.title,
                job.company,
                job.location,
                job.experience,
                job.source,
                getattr(job, "source_job_id", ""),
                remote_val,
                getattr(job, "description", ""),
                job.url,
                skills_str,
                getattr(job, "salary", ""),
                getattr(job, "job_type", ""),
                getattr(job, "employment_type", ""),
                getattr(job, "application_url", ""),
                getattr(job, "posted_date", ""),
                getattr(job, "score", 0),
                job.match_score,
                job.status,
                rejection_str
            ))
            conn.commit()
            self.last_error = None
            app_logger.debug(f"Saved job: {job.title} from {job.source}")
            return True
        except sqlite3.Error as e:
            self.last_error = str(e)
            app_logger.error(f"Database Error while saving job {job.url}: {e}")
            return False
        finally:
            if conn is not None:
                conn.close()

    def save_jobs(self, jobs: Iterable) -> int:
        """Save multiple Job objects using the existing save_job logic.

        Accepts any iterable of Job objects. Handles empty iterables safely.
        """
        if not jobs:
            return 0

        self.last_save_errors = []
        count = 0
        for job in jobs:
            try:
                if self.save_job(job):
                    count += 1
                else:
                    message = f"Failed to save job {getattr(job, 'url', '<unknown>')}: {self.last_error}"
                    self.last_save_errors.append(message)
                    app_logger.error(message)
            except Exception as exc:
                message = f"Failed to save job {getattr(job, 'url', '<unknown>')}: {exc}"
                self.last_save_errors.append(message)
                app_logger.error(message)
                # continue saving remaining jobs
                continue

        return count


database = Database()
