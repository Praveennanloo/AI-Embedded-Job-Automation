import signal
import threading
import time

from rich.console import Console

from config.settings import settings
from database_engine.database import database
from utils.logger import app_logger

from search_engine.search_manager import SearchManager
from ai_engine.job_filter import JobFilter

from search_engine.providers.remoteok_provider import RemoteOKProvider
from search_engine.providers.greenhouse_provider import GreenhouseProvider

console = Console()


def execute_search_cycle():
    database.initialize()

    manager = SearchManager()
    job_filter = JobFilter()

    manager.register_provider(RemoteOKProvider())
    manager.register_provider(GreenhouseProvider())

    app_logger.info("Beginning job search cycle...")
    jobs = manager.search()

    app_logger.info("Applying filters and calculating match scores...")
    accepted_jobs = job_filter.filter_jobs(jobs)
    summary = getattr(job_filter, "last_summary", {})

    app_logger.info(f"Saving {len(accepted_jobs)} filtered jobs to database...")
    for job in accepted_jobs:
        database.save_job(job)

    console.print(f"[green]Application :[/green] {settings.APP_NAME}")
    console.print(f"[green]Version     :[/green] {settings.VERSION}")
    console.print(f"[green]Database    :[/green] {settings.DATABASE_NAME}")
    console.print(f"[green]Interval    :[/green] {settings.SEARCH_INTERVAL_MINUTES} minutes")

    console.print("\n[bold]Provider Retrieval Summary[/bold]")
    for provider_name, count in manager.provider_results.items():
        console.print(f"- {provider_name}: {count} jobs")
    console.print(f"Total normalized jobs: {summary.get('normalized_jobs', 0)}")
    console.print(f"Total duplicates removed: {summary.get('duplicates_removed', 0)}")
    console.print(f"Total jobs accepted: {summary.get('accepted', len(accepted_jobs))}")
    console.print(f"Total jobs rejected: {summary.get('rejected', 0)}")

    rejection_counts = summary.get("rejection_counts", {})
    if rejection_counts:
        console.print("\n[bold]Top Rejection Reasons[/bold]")
        for reason, count in list(rejection_counts.items())[:10]:
            console.print(f"- {reason}: {count}")

    rejected_samples = summary.get("rejected_samples", [])
    if rejected_samples:
        console.print("\n[bold]Representative Rejected Job Samples[/bold]")
        for sample in rejected_samples[:5]:
            console.print(f"- Title: {sample['title']} | Company: {sample['company']} | Location: {sample['location']} | Source: {sample['source']}")
            console.print(f"  Description Available: {sample['description_available']} | Skills Available: {sample['skills_available']} | Experience: {sample['experience']}")
            console.print(f"  Embedded matches: {sample['embedded_keyword_matches']}")
            console.print(f"  Entry-level matches: {sample['entry_level_keyword_matches']}")
            console.print(f"  Location matches: {sample['location_matches']}")
            console.print(f"  Rejection reasons: {sample['rejection_reasons']}")

    console.print(f"\n[bold yellow]Filtered Jobs Found : {len(accepted_jobs)}[/bold yellow]")

    for index, job in enumerate(accepted_jobs[:10], start=1):
        console.rule(f"[cyan]Accepted Job {index}[/cyan]")
        console.print(f"[bold]{job.title}[/bold]")
        console.print(f"Company      : {job.company}")
        console.print(f"Location     : {job.location}")
        console.print(f"Experience   : {job.experience}")
        console.print(f"Source       : {job.source}")
        console.print(f"Match Score  : [bold green]{job.match_score}%[/bold green]")
        console.print(f"Posted Date  : {job.posted_date}")

        if job.skills:
            console.print(f"Skills       : {', '.join(job.skills)}")
        else:
            console.print("Skills       : Not Available")

        console.print(f"URL          : {job.url}")

    app_logger.info("Job search cycle completed successfully.")
    console.print("\n[bold green]System Ready ✓[/bold green]")
    return accepted_jobs, summary, manager


class JobSearchScheduler:
    def __init__(self, interval_minutes=None, sleep_fn=time.sleep, stop_event=None):
        self.interval_minutes = settings.SEARCH_INTERVAL_MINUTES if interval_minutes is None else interval_minutes
        self.interval_seconds = max(int(self.interval_minutes) * 60, 0)
        self.sleep_fn = sleep_fn
        self.stop_event = stop_event or threading.Event()
        self._shutdown_requested = False

    def request_shutdown(self):
        self._shutdown_requested = True
        self.stop_event.set()
        app_logger.info("Scheduler shutdown requested.")

    def _should_stop(self):
        return self._shutdown_requested or self.stop_event.is_set()

    def run(self, cycle_limit=None):
        cycle_count = 0

        while True:
            if self._should_stop():
                app_logger.info("Scheduler stopped before starting next cycle.")
                break

            cycle_count += 1
            app_logger.info(f"Cycle {cycle_count} started. Next run in {self.interval_minutes} minute(s).")
            try:
                execute_search_cycle()
                app_logger.info(f"Cycle {cycle_count} completed successfully.")
            except Exception as exc:
                app_logger.exception(f"Cycle {cycle_count} failed: {exc}")

            if cycle_limit is not None and cycle_count >= cycle_limit:
                app_logger.info(f"Cycle limit reached ({cycle_limit}). Stopping scheduler.")
                break

            if self._should_stop():
                app_logger.info("Scheduler stop requested after cycle completion.")
                break

            next_run_at = time.time() + self.interval_seconds
            app_logger.info(f"Cycle {cycle_count} complete. Next scheduled run at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_run_at))}.")
            self.sleep_fn(self.interval_seconds)

        return cycle_count if cycle_limit is not None else cycle_count


def main():
    app_logger.info("Starting AI Embedded Job Automation...")
    console.rule("[bold cyan]AI Embedded Job Automation[/bold cyan]")

    scheduler = JobSearchScheduler()

    def handle_signal(signum, frame):
        app_logger.info(f"Received termination signal {signum}. Shutting down scheduler.")
        scheduler.request_shutdown()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        scheduler.run()
    except KeyboardInterrupt:
        app_logger.info("Keyboard interrupt received. Shutting down scheduler.")
        scheduler.request_shutdown()

    app_logger.info("Service shutdown complete.")
    console.print("\n[bold green]Scheduler shutdown complete ✓[/bold green]")


if __name__ == "__main__":
    main()
