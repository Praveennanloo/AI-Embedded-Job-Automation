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
            url TEXT UNIQUE,
            skills TEXT,
            match_score INTEGER DEFAULT 0,
            status TEXT,
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

        try:
            cur.execute("""
            INSERT INTO jobs
            (
                title,
                company,
                location,
                experience,
                source,
                url,
                skills,
                match_score,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                job.url,
                skills_str,
                job.match_score,
                job.status
            ))
            conn.commit()
            app_logger.debug(f"Saved job: {job.title} from {job.source}")
        except sqlite3.Error as e:
            app_logger.error(f"Database Error while saving job {job.url}: {e}")
        finally:
            conn.close()


database = Database()
