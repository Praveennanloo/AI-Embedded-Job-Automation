import os
import time
import logging
import threading
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from search_engine.search_manager import SearchManager
from ai_engine.job_filter import JobFilter
from database_engine.database import Database
from resume_engine.ats_optimizer import ATSOptimizer
from resume_engine.latex_generator import LatexResumeGenerator

# Safe settings import handling
try:
    from config import settings
    SEARCH_INTERVAL = getattr(settings, "SEARCH_INTERVAL_MINUTES", 60)
except ImportError:
    SEARCH_INTERVAL = 60

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Embedded Job Automation API",
    description="Backend service for fetching, filtering, and optimizing embedded systems job applications.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
search_manager = SearchManager()
job_filter = JobFilter()
db_engine = Database()


class ResumeRequest(BaseModel):
    name: str = "Praveen Bolla"
    email: str = "praveen@example.com"
    phone: str = "+91 9876543210"
    github: str = "https://github.com/Praveennanloo"
    linkedin: str = "https://linkedin.com/in/praveen-bolla"
    job_title: str
    company: str
    job_description: str
    user_skills: List[str] = [
        "Embedded C", "C++", "RTOS", "FreeRTOS", "ARM Cortex-M",
        "STM32", "UART", "SPI", "I2C", "Git"
    ]


def execute_search_cycle(query: str = "Embedded Firmware Engineer", limit: int = 20):
    """Executes a single job search, filtering, and persistence cycle."""
    try:
        raw_jobs = search_manager.fetch_all_jobs(query=query, limit=limit)
        filtered_jobs = job_filter.filter_jobs(raw_jobs)
        
        saved_count = 0
        if hasattr(db_engine, "save_jobs"):
            saved_count = db_engine.save_jobs(filtered_jobs)
            
        logger.info(f"Search cycle complete. Fetched: {len(raw_jobs)}, Filtered: {len(filtered_jobs)}, Saved: {saved_count}")
        return filtered_jobs, {"raw": len(raw_jobs), "filtered": len(filtered_jobs)}, None
    except Exception as e:
        logger.error(f"Error executing search cycle: {e}")
        raise e


class JobSearchScheduler:
    """Background scheduler service for periodic job automation cycles."""
    def __init__(self, interval_minutes: int = None, sleep_fn=None, stop_event=None, **kwargs):
        self.interval_minutes = interval_minutes if interval_minutes is not None else SEARCH_INTERVAL
        self.interval_seconds = self.interval_minutes * 60
        self.sleep_fn = sleep_fn or time.sleep
        self.stop_event = stop_event or threading.Event()
        self.thread = None

    def run(self, cycle_limit: Optional[int] = None) -> int:
        completed_cycles = 0
        while not self.stop_event.is_set():
            if cycle_limit is not None and completed_cycles >= cycle_limit:
                break
            
            try:
                execute_search_cycle()
            except Exception as e:
                logger.error(f"Scheduler cycle failed: {e}")
            
            completed_cycles += 1

            if cycle_limit is not None and completed_cycles >= cycle_limit:
                break

            if self.stop_event.is_set():
                break

            self.sleep_fn(self.interval_seconds)

        return completed_cycles

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "AI Embedded Job Automation Engine",
        "version": "1.0.0"
    }


@app.get("/api/jobs")
def get_jobs(
    search_query: str = Query("Embedded Firmware Engineer", alias="query"),
    limit: int = Query(20, ge=1, le=100)
):
    try:
        filtered_jobs, _, _ = execute_search_cycle(query=search_query, limit=limit)
        results = []
        for j in filtered_jobs:
            job_dict = j.to_dict() if hasattr(j, "to_dict") else dict(j)
            results.append(job_dict)
            
        return {
            "status": "success",
            "total_found": len(results),
            "jobs": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-resume")
def generate_tailored_resume(req: ResumeRequest):
    try:
        optimizer = ATSOptimizer()
        jd_keywords = optimizer.extract_keywords(req.job_description)
        ats_result = optimizer.calculate_ats_match(req.user_skills, jd_keywords)

        generator = LatexResumeGenerator(
            name=req.name,
            email=req.email,
            phone=req.phone,
            github=req.github,
            linkedin=req.linkedin
        )

        latex_code = generator.generate_latex(
            matched_skills=ats_result["matched_keywords"],
            job_title=req.job_title,
            company=req.company
        )

        return {
            "status": "success",
            "ats_score": ats_result["match_score"],
            "matched_keywords": ats_result["matched_keywords"],
            "missing_keywords": ats_result["missing_keywords"],
            "latex_code": latex_code
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
