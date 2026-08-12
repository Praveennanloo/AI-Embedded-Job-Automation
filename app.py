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

    # Initialize Database
    database.initialize()

    # Create Search Manager
    manager = SearchManager()
    job_filter = JobFilter()

    # Register Providers
    manager.register_provider(RemoteOKProvider())
    manager.register_provider(GreenhouseProvider())

    # Search Jobs
    app_logger.info("Beginning job search cycle...")
    jobs = manager.search()

    # Apply Filter and Scoring
    app_logger.info("Applying filters and calculating match scores...")
    jobs = job_filter.filter_jobs(jobs)

    # Save Jobs into Database
    app_logger.info(f"Saving {len(jobs)} filtered jobs to database...")
    for job in jobs:
        database.save_job(job)

    # Application Information
    console.print(f"[green]Application :[/green] {settings.APP_NAME}")
    console.print(f"[green]Version     :[/green] {settings.VERSION}")
    console.print(f"[green]Database    :[/green] {settings.DATABASE_NAME}")
    console.print(
        f"[green]Interval    :[/green] {settings.SEARCH_INTERVAL_MINUTES} minutes"
    )

    # Show Total Jobs
    console.print(f"\n[bold yellow]Filtered Jobs Found : {len(jobs)}[/bold yellow]")

    # Display Jobs
    for index, job in enumerate(jobs, start=1):

        console.rule(f"[cyan]Job {index}[/cyan]")

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
