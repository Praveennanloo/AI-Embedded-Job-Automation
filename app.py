import time
import logging
import threading
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dataclasses import asdict

from search_engine.search_manager import SearchManager
from ai_engine.job_filter import JobFilter
from application_engine.pipeline_manager import PipelineManager
from database_engine.database import Database
from resume_engine.ats_optimizer import ATSOptimizer
from resume_engine.latex_generator import LatexResumeGenerator

from config.settings import settings

SEARCH_INTERVAL = settings.SEARCH_INTERVAL_MINUTES

logger = logging.getLogger(__name__)

# Initialize engines
search_manager = SearchManager()
def _register_providers_once(manager: SearchManager):
    """Register production providers in a controlled way, avoiding duplicates."""
    existing = {p.__class__.__name__ for p in manager.providers}

    # Register RemoteOKProvider if not already present. Import lazily so a
    # missing dependency or import-time error won't crash the app on startup.
    if "RemoteOKProvider" not in existing:
        try:
            from search_engine.providers.remoteok_provider import RemoteOKProvider

            try:
                manager.register_provider(RemoteOKProvider())
            except Exception as exc:
                logger.error(f"Failed to initialize RemoteOKProvider: {exc}")
        except ImportError as imp_exc:
            logger.error(f"RemoteOKProvider import failed: {imp_exc}")
        except Exception as exc:
            logger.error(f"Unexpected error importing RemoteOKProvider: {exc}")

    # Register GreenhouseProvider if not already present. Import lazily.
    if "GreenhouseProvider" not in existing:
        try:
            from search_engine.providers.greenhouse_provider import GreenhouseProvider

            try:
                manager.register_provider(GreenhouseProvider())
            except Exception as exc:
                logger.error(f"Failed to initialize GreenhouseProvider: {exc}")
        except ImportError as imp_exc:
            logger.error(f"GreenhouseProvider import failed: {imp_exc}")
        except Exception as exc:
            logger.error(f"Unexpected error importing GreenhouseProvider: {exc}")


# Perform registration at module import time in a controlled way
_register_providers_once(search_manager)
job_filter = JobFilter()
db_engine = Database()

# Create pipeline manager after database engine is available
pipeline_manager = PipelineManager(db=db_engine)


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


def execute_search_cycle(
    query: str = "Embedded Firmware Engineer",
    location: str = "",
    limit: int = 20,
    candidate_profile: Optional[dict] = None,
    interactive: bool = False,
):
    """Executes a single job search, filtering, and persistence cycle.

    Uses SearchManager.search() to aggregate provider results, then applies
    a simple `limit` slice before filtering and persistence.
    """
    try:
        # Use a PipelineManager instance tied to the current db_engine to execute the full pipeline
        pm = PipelineManager(db=db_engine)
        # Ensure PipelineManager uses the application's SearchManager (allows tests to monkeypatch app.search_manager)
        pm.search_manager = search_manager
        result = pm.run_pipeline(
            query=query,
            location=location,
            limit=limit,
            shortlist_size=limit,
            candidate_profile=candidate_profile,
            interactive=interactive,
        )
        # PipelineManager persists shortlisted jobs; return accepted list for API
        # For backward compatibility, return the shortlisted Job objects if available
        shortlisted = result.get("jobs", [])

        logger.info(f"Pipeline run complete. Found: {result.get('total_found')}, Shortlisted: {result.get('shortlisted_count')}")
        return shortlisted, result, None
    except Exception as e:
        logger.error(f"Error executing search cycle: {e}")
        raise


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


scheduler = JobSearchScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize durable state before serving requests and stop the worker cleanly."""
    db_engine.initialize()
    if settings.SCHEDULER_ENABLED:
        scheduler.start()
    try:
        yield
    finally:
        scheduler.stop()


app = FastAPI(
    title="AI Embedded Job Automation API",
    description="Backend service for fetching, filtering, and optimizing embedded systems job applications.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    location: str = Query("", max_length=120),
    limit: int = Query(20, ge=1, le=100),
    candidate_skills: List[str] = Query(default=[]),
    candidate_experience: str = Query("", max_length=120),
):
    try:
        profile = {"skills": candidate_skills, "experience": candidate_experience} if (candidate_skills or candidate_experience) else None
        results, pipeline_result, _ = execute_search_cycle(
            query=search_query,
            location=location,
            limit=limit,
            candidate_profile=profile,
            interactive=True,
        )
        provider_status = pipeline_result.get("provider_status", {})
        if provider_status and not any(item.get("status") in {"success", "partial"} for item in provider_status.values()):
            raise HTTPException(503, detail={"message": "All live job providers failed", "providers": provider_status})
        successful = [item for item in provider_status.values() if item.get("status") in {"success", "partial"}]
        failed = [item for item in provider_status.values() if item.get("status") not in {"success", "partial"}]
        response_status = "partial_success" if successful and failed else "success"
        result_state = "matches" if results else "zero_matches"
        return {
            "status": response_status,
            "result_state": result_state,
            "query": search_query,
            "location": location,
            "total_found": pipeline_result.get("total_found", 0),
            "total_returned": len(results),
            "accepted_count": pipeline_result.get("accepted_count", 0),
            "rejected_count": pipeline_result.get("total_rejected", 0),
            "persisted_count": pipeline_result.get("persisted_count", 0),
            "persistence_errors": pipeline_result.get("persistence_errors", []),
            "providers": provider_status,
            "jobs": results
        }
    except HTTPException:
        raise
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
