from models.job import Job
from search_engine.search_manager import SearchManager
from search_engine.providers.greenhouse_provider import GreenhouseProvider
from search_engine.providers.remoteok_provider import RemoteOKProvider


def _job(url, title="Embedded Firmware Engineer"):
    return Job(title, "Acme", "India", "0-1 years", "test", url, ["Embedded C"], "", description="embedded firmware")


def test_search_manager_propagates_query_location_and_limit():
    seen = {}

    class Provider:
        def search(self, query="", location="", limit=None):
            seen.update(query=query, location=location, limit=limit)
            return [_job("https://example.test/1")]

    manager = SearchManager()
    manager.register_provider(Provider())
    assert len(manager.search("Embedded Linux", "Telangana", 7)) == 1
    assert seen == {"query": "Embedded Linux", "location": "Telangana", "limit": 7}
    assert manager.provider_status["Provider"]["status"] == "success"


def test_interactive_provider_budget_is_passed_to_supported_providers(monkeypatch):
    seen = {}

    class Provider:
        def search(self, query="", location="", limit=None, timeout_seconds=None, max_retries=None):
            seen.update(timeout_seconds=timeout_seconds, max_retries=max_retries)
            return []

    import search_engine.search_manager as module
    monkeypatch.setattr(module.settings, "INTERACTIVE_PROVIDER_TIMEOUT_SECONDS", 4.0)
    monkeypatch.setattr(module.settings, "INTERACTIVE_PROVIDER_MAX_RETRIES", 1)

    manager = SearchManager()
    manager.register_provider(Provider())
    manager.search("Firmware", "India", 10, interactive=True)

    assert seen == {"timeout_seconds": 4.0, "max_retries": 1}


def test_interactive_retry_limit_and_bounded_failure(monkeypatch):
    import search_engine.providers.greenhouse_provider as module

    calls = []

    def get(url, timeout=None):
        calls.append((url, timeout))
        raise module.httpx.ConnectError("offline")

    monkeypatch.setattr(module.httpx, "get", get)
    monkeypatch.setattr(module.settings, "PROVIDER_BASE_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(module.settings, "PROVIDER_MAX_DELAY_SECONDS", 0.0)

    provider = GreenhouseProvider()
    provider.BOARDS = [("Canonical", "https://good")]
    manager = SearchManager()
    manager.register_provider(provider)

    started = __import__("time").perf_counter()
    jobs = manager.search("Firmware", "India", 10, interactive=True)
    elapsed = __import__("time").perf_counter() - started

    assert jobs == []
    assert len(calls) == 2
    assert all(timeout == module.settings.INTERACTIVE_PROVIDER_TIMEOUT_SECONDS for _, timeout in calls)
    assert manager.provider_status["GreenhouseProvider"]["status"] == "failed"
    assert elapsed < 1.0


def test_successful_provider_behavior_unchanged_with_interactive_budget(monkeypatch):
    import search_engine.providers.remoteok_provider as module

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [{
                "id": 1,
                "position": "Junior Firmware Engineer",
                "company": "Acme",
                "location": "India",
                "url": "https://example.test/1",
                "description": "Junior embedded firmware engineering.",
            }]

    seen = []
    monkeypatch.setattr(module.httpx, "get", lambda url, **kwargs: (seen.append(kwargs) or Response()))
    provider = RemoteOKProvider()
    manager = SearchManager()
    manager.register_provider(provider)

    jobs = manager.search("Junior Firmware Engineer", "India", 10, interactive=True)

    assert len(jobs) == 1
    assert jobs[0].title == "Junior Firmware Engineer"
    assert seen == [{
        "headers": {"User-Agent": "Mozilla/5.0"},
        "timeout": module.settings.INTERACTIVE_PROVIDER_TIMEOUT_SECONDS,
    }]


def test_failed_provider_does_not_block_successful_provider():
    class FailedProvider:
        def search(self, **kwargs):
            raise TimeoutError("offline")

    class SuccessfulProvider:
        def search(self, **kwargs):
            return [_job("https://example.test/success")]

    manager = SearchManager()
    manager.register_provider(FailedProvider())
    manager.register_provider(SuccessfulProvider())

    jobs = manager.search("Firmware", "India", 10, interactive=True)

    assert len(jobs) == 1
    assert jobs[0].url == "https://example.test/success"
    assert manager.provider_status["FailedProvider"]["status"] == "failed"
    assert manager.provider_status["SuccessfulProvider"]["status"] == "success"


def test_remoteok_failure_is_not_reported_as_zero_result_success(monkeypatch):
    import search_engine.providers.remoteok_provider as module

    monkeypatch.setattr(module.settings, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(module.httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("offline")))
    manager = SearchManager()
    manager.register_provider(RemoteOKProvider())
    assert manager.search("Embedded", "India", 10) == []
    assert manager.provider_status["RemoteOKProvider"]["status"] == "failed"


def test_greenhouse_keeps_successful_board_when_another_fails(monkeypatch):
    import search_engine.providers.greenhouse_provider as module

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def get(url, timeout=None):
        if "bad" in url:
            raise ConnectionError("board unavailable")
        return Response({"jobs": [{"id": 1, "title": "Embedded Firmware Engineer", "location": {"name": "India"}, "absolute_url": "https://example.test/1"}]})

    monkeypatch.setattr(module.settings, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(module.httpx, "get", get)
    provider = GreenhouseProvider()
    provider.BOARDS = [("Good", "https://good"), ("Bad", "https://bad")]
    manager = SearchManager()
    manager.register_provider(provider)
    jobs = manager.search("Embedded Firmware Engineer", "India", 10)
    assert len(jobs) == 1
    assert manager.provider_status["GreenhouseProvider"]["status"] == "partial"
    assert manager.provider_status["GreenhouseProvider"]["boards"]["Bad"]["status"] == "failed"


def test_provider_location_matching_accepts_existing_worldwide_indicators_for_india(monkeypatch):
    import search_engine.providers.greenhouse_provider as module

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "jobs": [{
                    "id": 2,
                    "title": "Embedded Firmware Engineer",
                    "location": {"name": "Home based - Worldwide"},
                    "absolute_url": "https://example.test/worldwide",
                }]
            }

    monkeypatch.setattr(module.settings, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(module.httpx, "get", lambda *args, **kwargs: Response())
    provider = GreenhouseProvider()
    provider.BOARDS = [("Canonical", "https://good")]

    jobs = provider.search("Embedded Firmware Engineer", "India", 10)

    assert len(jobs) == 1
    assert jobs[0].location == "Home based - Worldwide"


def test_provider_location_matching_keeps_city_substring_behavior(monkeypatch):
    import search_engine.providers.remoteok_provider as module

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [{
                "id": 3,
                "position": "Embedded Firmware Engineer",
                "company": "Acme",
                "location": "Chennai, India",
                "url": "https://example.test/chennai",
            }]

    monkeypatch.setattr(module.settings, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(module.httpx, "get", lambda *args, **kwargs: Response())

    jobs = RemoteOKProvider().search("Embedded Firmware Engineer", "India", 10)

    assert len(jobs) == 1
    assert jobs[0].location == "Chennai, India"


def test_greenhouse_requests_supported_full_content_and_maps_it(monkeypatch):
    import search_engine.providers.greenhouse_provider as module

    seen_urls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "jobs": [{
                    "id": 4,
                    "title": "Embedded Firmware Engineer",
                    "location": {"name": "India"},
                    "absolute_url": "https://example.test/content",
                    "content": "Full embedded firmware job description.",
                    "updated_at": "2026-08-22T00:00:00Z",
                }]
            }

    def get(url, timeout=None):
        seen_urls.append(url)
        return Response()

    monkeypatch.setattr(module.settings, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(module.httpx, "get", get)
    provider = GreenhouseProvider()
    provider.BOARDS = [("Canonical", "https://good")]

    jobs = provider.search("Embedded Firmware Engineer", "India", 10)

    assert seen_urls == ["https://good?content=true"]
    assert len(jobs) == 1
    assert jobs[0].description == "Full embedded firmware job description."


def test_greenhouse_does_not_apply_limit_before_pipeline_filtering(monkeypatch):
    import search_engine.providers.greenhouse_provider as module

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "jobs": [
                    {
                        "id": 10,
                        "title": "Senior Embedded Firmware Engineer",
                        "location": {"name": "India"},
                        "absolute_url": "https://example.test/senior",
                        "description": "Senior embedded firmware engineering.",
                    },
                    {
                        "id": 11,
                        "title": "Graduate Embedded Firmware Engineer",
                        "location": {"name": "India"},
                        "absolute_url": "https://example.test/graduate",
                        "description": "Graduate embedded firmware engineering.",
                    },
                ]
            }

    monkeypatch.setattr(module.settings, "PROVIDER_MAX_RETRIES", 0)
    monkeypatch.setattr(module.httpx, "get", lambda *args, **kwargs: Response())
    provider = GreenhouseProvider()
    provider.BOARDS = [("Canonical", "https://good")]

    jobs = provider.search("Embedded Firmware Engineer", "India", limit=1)

    assert [job.source_job_id for job in jobs] == ["10", "11"]


def test_provider_query_matching_allows_relevant_partial_intent_match():
    job = Job(
        title="Firmware Engineer",
        company="Acme",
        location="India",
        experience="0-1 years",
        source="test",
        url="https://example.test/firmware",
        skills=[],
        posted_date="",
        description="Build embedded device firmware in C.",
    )

    match = RemoteOKProvider.query_match_details(job, "Embedded Firmware Engineer")

    assert match["matched"] is True
    assert match["strength"] in {"exact", "partial_intent"}
    assert set(match["matched_terms"]) >= {"firmware", "engineer"}


def test_provider_query_matching_rejects_generic_partial_match():
    job = Job(
        title="Software Engineer",
        company="Acme",
        location="India",
        experience="0-1 years",
        source="test",
        url="https://example.test/software",
        skills=[],
        posted_date="",
        description="Build backend services and web APIs.",
    )

    match = RemoteOKProvider.query_match_details(job, "Embedded Firmware Engineer")

    assert match["matched"] is False
    assert match["matched_terms"] == ["engineer"]


def test_provider_query_matching_does_not_match_substrings_in_boilerplate():
    job = Job(
        title="Organisational Development Associate",
        company="Acme",
        location="Remote",
        experience="Entry level",
        source="Greenhouse",
        url="https://example.test/hr",
        skills=[],
        posted_date="",
        description="Be embedded inside a team and support engineering development.",
    )

    match = RemoteOKProvider.query_match_details(job, "Embedded Firmware Engineer")

    assert match["matched"] is False
    assert match["matched_terms"] == ["embedded"]


def test_provider_query_matching_requires_junior_intent():
    senior_job = Job(
        title="Staff Firmware Engineer",
        company="Acme",
        location="Remote",
        experience="Not Specified",
        source="test",
        url="https://example.test/staff-firmware",
        skills=[],
        posted_date="",
        description="Build firmware for embedded products.",
    )

    match = RemoteOKProvider.query_match_details(senior_job, "Junior Firmware Engineer")

    assert match["matched"] is False
    assert match["strength"] == "missing_level_intent"
    assert match["missing_level_terms"] == ["junior"]


def test_provider_query_matching_preserves_firmware_partial_behavior():
    job = Job(
        title="Firmware Engineer",
        company="Acme",
        location="India",
        experience="Not Specified",
        source="test",
        url="https://example.test/firmware-engineer",
        skills=[],
        posted_date="",
        description="Build embedded device firmware in C.",
    )

    match = RemoteOKProvider.query_match_details(job, "Firmware Engineer")

    assert match["matched"] is True
    assert set(match["matched_terms"]) == {"firmware", "engineer"}


def test_provider_query_matching_requires_graduate_and_trainee_intent():
    graduate_only_job = Job(
        title="Graduate Engineer",
        company="Acme",
        location="India",
        experience="Not Specified",
        source="test",
        url="https://example.test/graduate-engineer",
        skills=[],
        posted_date="",
        description="Embedded engineering role.",
    )

    match = RemoteOKProvider.query_match_details(
        graduate_only_job,
        "Graduate Engineer Trainee Embedded",
    )

    assert match["matched"] is False
    assert match["strength"] == "missing_level_intent"
    assert match["missing_level_terms"] == ["trainee"]


def test_provider_query_matching_does_not_accept_senior_as_junior():
    senior_job = Job(
        title="Senior Firmware Engineer",
        company="Acme",
        location="Remote",
        experience="Not Specified",
        source="test",
        url="https://example.test/senior-firmware",
        skills=[],
        posted_date="",
        description="Senior-level firmware development for embedded systems.",
    )

    match = RemoteOKProvider.query_match_details(senior_job, "Junior Firmware Engineer")

    assert match["matched"] is False
    assert "junior" in match["missing_level_terms"]
