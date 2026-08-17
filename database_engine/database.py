import sqlite3
from pathlib import Path
from utils.logger import app_logger


class Database:
    def __init__(self):
        self.database = Path("database/jobs.db")
        self.database.parent.mkdir(exist_ok=True)

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

        # Create indexes for faster searching and filtering
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_url ON jobs(url);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_status ON jobs(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_match_score ON jobs(match_score);")

        conn.commit()
        conn.close()
        app_logger.info("Database initialized successfully.")

    def save_job(self, job):
        conn = self.connect()
        cur = conn.cursor()

        skills_str = ", ".join(job.skills) if job.skills else ""
        rejection_str = ", ".join(job.rejection_reasons) if getattr(job, "rejection_reasons", None) else ""
        remote_val = 1 if getattr(job, "remote", False) else 0

        try:
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
            app_logger.debug(f"Saved job: {job.title} from {job.source}")
        except sqlite3.Error as e:
            app_logger.error(f"Database Error while saving job {job.url}: {e}")
        finally:
            conn.close()

    def save_jobs(self, jobs):
        """Save multiple Job objects using the existing save_job logic.

        Accepts any iterable of Job objects. Handles empty iterables safely.
        """
        if not jobs:
            return 0

        count = 0
        for job in jobs:
            try:
                self.save_job(job)
                count += 1
            except Exception as exc:
                app_logger.error(f"Failed to save job {getattr(job, 'url', '<unknown>')}: {exc}")
                # continue saving remaining jobs
                continue

        return count


database = Database()
