# AI Embedded Job Automation

This project is a FastAPI service that searches live embedded/software jobs, applies the existing location and fresher eligibility rules, persists accepted jobs in SQLite, and can generate a tailored LaTeX resume.

## Architecture

The FastAPI application routes requests through `SearchManager` and the configured providers. `PipelineManager` normalizes, deduplicates, filters, scores, and persists jobs through `Database`. Resume generation uses `ATSOptimizer` and `LatexResumeGenerator`. The optional scheduler can run search cycles in the background.

The currently registered live providers are:

- RemoteOK (`https://remoteok.com/api`)
- Greenhouse boards for Canonical and Samsara

## Ubuntu setup

Prerequisites are Ubuntu with Python 3, `python3-venv`, Git, and network access to install packages and call live providers.

```bash
sudo apt update
sudo apt install -y python3 python3-venv git
```

Clone or open the project, then create and activate the project virtual environment:

```bash
git clone <repository-url>
cd AI-Embedded-Job-Automation-New
python3 -m venv venv
source venv/bin/activate
```

Install the declared runtime dependencies:

```bash
venv/bin/pip install -r requirements.txt
```

## Configuration

Settings are read from environment variables and an optional `.env` file. Unknown `.env` keys are ignored. Existing settings include:

| Setting | Default |
| --- | --- |
| `APP_NAME` | `AI Embedded Job Automation` |
| `VERSION` | `0.1.0` |
| `DEBUG` | `True` |
| `DATABASE_NAME` | `jobs.db` |
| `DATABASE_PATH` | `database/jobs.db` |
| `SEARCH_INTERVAL_MINUTES` | `15` |
| `SCHEDULER_ENABLED` | `True` |
| `PROVIDER_TIMEOUT_SECONDS` | `20.0` |
| `PROVIDER_MAX_RETRIES` | `3` |
| `PROVIDER_BASE_DELAY_SECONDS` | `1.0` |
| `PROVIDER_MAX_DELAY_SECONDS` | `30.0` |
| `ENABLE_LOCATION_FILTER` | `True` |
| `REQUIRE_ENTRY_LEVEL` | `True` |
| `LOCATION_KEYWORDS` | Hyderabad, Bangalore/Bengaluru, Chennai, Pune, Visakhapatnam/Vizag, remote, India |
| `AI_ENABLED` | `False` |
| `AI_PROVIDER` | `openai` |
| `AI_TIMEOUT_SECONDS` | `10.0` |
| `AI_MAX_RETRIES` | `2` |
| `OPENAI_API_KEY` | empty |
| `OPENAI_API_BASE_URL` | `https://api.openai.com/v1` |
| `OPENAI_DEFAULT_MODEL` | `gpt-4o-mini` |

AI is disabled by default. Set only the existing settings needed for the deployment.

## Database behavior

The application initializes SQLite at startup using `DATABASE_PATH`, which defaults to `database/jobs.db`. It creates the `jobs` table and indexes if needed. Existing installations receive additive schema migrations only; missing columns are added without deleting job rows. Before an additive migration, an existing database is backed up as `database/jobs.db.pre_migration.bak` when that backup does not already exist.

## Run the API

Start FastAPI from the project root:

```bash
venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

The scheduler follows `SCHEDULER_ENABLED` and `SEARCH_INTERVAL_MINUTES` while the service is running.

## Test

```bash
venv/bin/pytest -q
```

## API examples

Search live providers for India-located or remote jobs:

```bash
curl -sS "http://127.0.0.1:8000/api/jobs?query=Junior%20Firmware%20Engineer&location=India&limit=10"
```

Generate a resume for a job:

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/generate-resume" \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Junior Firmware Engineer",
    "company": "Example Company",
    "job_description": "Junior embedded firmware engineering using C and Linux.",
    "user_skills": ["C", "Linux", "Embedded C"]
  }'
```

## Live-provider and eligibility behavior

Job searches use real provider data. Provider failures are reported in the API response rather than represented as fabricated jobs; a response can report partial success when only some providers succeed. Accepted results include real provider titles, companies, locations, and URLs.

The existing pipeline applies query matching, location matching, fresher/entry-level filtering, embedded relevance checks, senior-role rejection, deduplication, ranking, and persistence. Explicit senior, staff, lead, manager, director, and related senior roles are rejected for the fresher target. A result is not invented to fill the requested limit.

Coverage depends on the currently configured providers and the jobs they expose at search time. Provider outages, rate limits, changing listings, and limited provider coverage can therefore produce zero or partial results.

## Security

Never commit secrets, API keys, or `.env` credentials. Keep credentials in the runtime environment or an untracked local `.env` file, and do not print them in logs or API requests.
