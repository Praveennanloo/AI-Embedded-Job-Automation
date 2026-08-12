from rich.console import Console

from config.settings import settings
from database_engine.database import database
from utils.logger import app_logger

from search_engine.search_manager import SearchManager
from ai_engine.job_filter import JobFilter

from search_engine.providers.remoteok_provider import RemoteOKProvider
from search_engine.providers.greenhouse_provider import GreenhouseProvider

console = Console()


def main():

    app_logger.info("Starting AI Embedded Job Automation...")
    console.rule("[bold cyan]AI Embedded Job Automation[/bold cyan]")

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


if __name__ == "__main__":
    main()
