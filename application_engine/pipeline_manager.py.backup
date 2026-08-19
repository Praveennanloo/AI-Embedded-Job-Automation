from typing import List, Dict, Any, Optional
import logging

from search_engine.search_manager import SearchManager
from ai_engine.job_filter import JobFilter
from application_engine.job_pipeline import JobPipeline
from database_engine.database import database as default_database
from models.job import Job
from utils.logger import app_logger


class PipelineManager:
    """Orchestrates the end-to-end job pipeline:
    Search -> Normalize -> Filter -> Eligibility -> Score -> Shortlist
    -> ATS analysis -> Tailored resume -> Application record
    """

    def __init__(self, db=default_database, search_manager: Optional[SearchManager] = None):
        # Allow injection of an externally-initialized SearchManager
        self.search_manager = search_manager if search_manager is not None else SearchManager()
        self.filter = JobFilter()
        self.pipeline = JobPipeline(db=db)
        self.db = db

    def run_pipeline(self, limit: int = 50, shortlist_size: int = 10, resume_owner: Optional[Dict[str, str]] = None, generate_applications: bool = False) -> Dict[str, Any]:
        # 1. Collect jobs
        raw_jobs: List[Job] = []
        try:
            raw_jobs = self.search_manager.search()
        except Exception as exc:
            app_logger.error(f"Search failed: {exc}")

        if getattr(self.search_manager, "provider_results", None):
            total_found = sum(int(v) for v in self.search_manager.provider_results.values() if isinstance(v, (int, float)))
        else:
            total_found = len(raw_jobs)

        # apply limit
        if limit and isinstance(limit, int) and limit > 0:
            raw_jobs = raw_jobs[:limit]

        # 2-3. Normalize, dedupe and filter (returns accepted jobs)
        accepted = self.filter.filter_jobs(raw_jobs)

        # 4-5. Eligibility and scoring (filter.calculate_score already set scores)
        eligible = []
        for job in accepted:
            try:
                if self.pipeline.check_eligibility(job):
                    # `filter_jobs` already calculates a `match_score`. Only score if missing.
                    if getattr(job, "match_score", None) in (None, 0):
                        job.match_score = self.pipeline.score_job(job)
                    eligible.append(job)
                else:
                    job.rejection_reasons = getattr(job, "rejection_reasons", []) + ["Not eligible by pipeline checks"]
            except Exception as exc:
                app_logger.error(f"Eligibility check failed for {getattr(job,'url', job)}: {exc}")

        # 6. Shortlist top N
        eligible.sort(key=lambda j: getattr(j, "match_score", 0), reverse=True)
        shortlisted = eligible[:shortlist_size]

        prepared_applications = []

        # 7. Pipeline finalization: extract JD keywords and optionally prepare applications
        for job in shortlisted:
            try:
                keywords = self.pipeline.extract_jd_keywords(getattr(job, "description", "") or "")

                if resume_owner:
                    try:
                        resume_latex = self.pipeline.generate_resume(
                            name=resume_owner.get("name", ""),
                            email=resume_owner.get("email", ""),
                            phone=resume_owner.get("phone", ""),
                            github=resume_owner.get("github", ""),
                            linkedin=resume_owner.get("linkedin", ""),
                            matched_skills=job.skills or keywords,
                            job_title=job.title,
                            company=job.company,
                        )
                        application = self.pipeline.prepare_application(job, resume_latex)
                        # record status and persist
                        self.pipeline.record_status(job, status=application.get("status", "prepared"))
                        prepared_applications.append({
                            "job": {
                                "title": job.title,
                                "company": job.company,
                                "url": job.url,
                                "match_score": job.match_score,
                            },
                            "application": application,
                            "keywords": keywords,
                        })
                    except Exception as exc:
                        app_logger.error(f"Failed preparing application for {getattr(job,'url', job)}: {exc}")
                else:
                    # Still gather basic job payload info for the caller
                    prepared_applications.append({
                        "job": {
                            "title": job.title,
                            "company": job.company,
                            "url": job.url,
                            "match_score": job.match_score,
                        },
                        "keywords": keywords,
                    })
            except Exception as exc:
                app_logger.error(f"Pipeline finalization failed for {getattr(job,'url', job)}: {exc}")


        # persist shortlisted jobs in DB if batch save available
        persisted_count = 0
        try:
            if hasattr(self.db, "save_jobs"):
                try:
                    persisted_count = int(self.db.save_jobs(shortlisted) or 0)
                except Exception:
                    # fall back to per-job save
                    persisted_count = 0
                    for j in shortlisted:
                        try:
                            if hasattr(self.db, "save_job"):
                                self.db.save_job(j)
                                persisted_count += 1
                        except Exception:
                            app_logger.exception("Failed saving job")
            else:
                for j in shortlisted:
                    try:
                        if hasattr(self.db, "save_job"):
                            self.db.save_job(j)
                            persisted_count += 1
                    except Exception:
                        app_logger.exception("Failed saving job")
        except Exception:
            app_logger.exception("Batch save_jobs failed")

        # Build structured result expected by Block 1B while preserving previous fields
        result = {
            "total_found": total_found,
            "total_eligible": len(eligible),
            # rejected = found - accepted
            "total_rejected": max(0, total_found - len(accepted)),
            "shortlisted_jobs": [p.get("job") for p in prepared_applications],
            "persisted_count": persisted_count,

            # Backwards-compatible fields
            "limited_to": len(raw_jobs),
            "accepted_count": len(accepted),
            "eligible_count": len(eligible),
            "shortlisted_count": len(shortlisted),
            "prepared_applications": prepared_applications,
        }

        return result


__all__ = ["PipelineManager"]
