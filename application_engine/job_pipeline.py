from typing import Dict, Any, List

from resume_engine.ats_optimizer import ATSOptimizer
from resume_engine.latex_generator import LatexResumeGenerator
from ai_engine.job_filter import JobFilter
from database_engine.database import database as default_database
from models.job import Job


class JobPipeline:
    """Utility class implementing a minimal job->resume pipeline.

    This class is intentionally lightweight and does not perform any
    network operations or automatic submissions. It exposes pure helper
    methods that other parts of the application can call when needed.
    """

    def __init__(self, db=default_database):
        self.ats = ATSOptimizer()
        self.generator = None
        self.filter = JobFilter()
        self.db = db

    def extract_jd_keywords(self, job_description: str) -> List[str]:
        return self.ats.extract_keywords(job_description or "")

    def check_eligibility(self, job: Job) -> bool:
        # Use JobFilter rules to determine overall eligibility
        return self.filter.document_matches_target(job) and self.filter.is_entry_level_or_intern(job) and self.filter.location_allowed(job)

    def score_job(self, job: Job) -> int:
        return self.filter.calculate_score(job)

    def generate_resume(self, name: str, email: str, phone: str, github: str, linkedin: str, matched_skills: List[str], job_title: str, company: str) -> str:
        self.generator = LatexResumeGenerator(name=name, email=email, phone=phone, github=github, linkedin=linkedin)
        return self.generator.generate_latex(matched_skills=matched_skills, job_title=job_title, company=company)

    def prepare_application(self, job: Job, resume_latex: str) -> Dict[str, Any]:
        # Minimal application payload. Actual submission is outside scope.
        return {
            "job_url": job.url,
            "job_title": job.title,
            "company": job.company,
            "resume_latex": resume_latex,
            "status": "prepared",
        }

    def record_status(self, job: Job, status: str = "prepared") -> None:
        job.status = status
        # Keep persistence errors observable to the pipeline caller. The
        # caller already isolates individual application-preparation failures.
        if hasattr(self.db, "save_job") and not self.db.save_job(job):
            raise RuntimeError(f"Failed to persist job status for {job.url}")
