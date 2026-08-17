from ai_engine.ai_orchestrator import AIConfig, AIOrchestrator, AIProviderRegistry
from ai_engine.job_filter import JobFilter
from models.job import Job


class FakeAIProvider:
    name = "fake"

    def supports(self, task: str) -> bool:
        return True

    def generate(self, request):
        return type("Resp", (), {
            "success": True,
            "payload": {
                "result": {
                    "role_relevance": "High",
                    "embedded_relevance": "High",
                    "skill_relevance": ["C", "Linux", "ARM"],
                    "experience_suitability": "Strong fit",
                    "candidate_suitability": "Strong",
                    "missing_important_skills": ["RTOS"],
                    "positive_matching_factors": ["embedded Linux", "ARM", "GPIO"],
                    "concerns": ["Needs stronger RTOS exposure"],
                    "recommendation": "Good fit for a fresher embedded role.",
                    "confidence": 0.9,
                    "status": "ok",
                }
            },
            "provider": self.name,
            "model": "fake-model",
            "error": None,
            "latency_ms": 15,
        })()


class FakeBrokenProvider:
    name = "broken"

    def supports(self, task: str) -> bool:
        return True

    def generate(self, request):
        return type("Resp", (), {
            "success": True,
            "payload": {"bad": "shape"},
            "provider": self.name,
            "model": "fake-model",
            "error": None,
            "latency_ms": 5,
        })()


class FakeTimeoutProvider:
    name = "timeout"

    def supports(self, task: str) -> bool:
        return True

    def generate(self, request):
        raise TimeoutError("timed out")


class FakeExceptionProvider:
    name = "error"

    def supports(self, task: str) -> bool:
        return True

    def generate(self, request):
        raise RuntimeError("provider crashed")


def test_ai_disabled_uses_deterministic_result():
    filterer = JobFilter()
    job = Job(
        title="Embedded C Engineer",
        company="Edge Labs",
        location="Remote",
        experience="Trainee",
        source="RemoteOK",
        url="https://example.com/edge",
        skills=["C", "Embedded C", "UART", "GPIO"],
        posted_date="2026-08-02",
        description="Embedded C development for microcontrollers and GPIO drivers.",
    )
    profile = {"skills": ["C", "Embedded C", "GPIO"], "experience": "fresher"}

    analysis = filterer.analyze_job_intelligence(job, profile, orchestrator=None)
    assert analysis["role_category"] in {"Embedded C", "Embedded Software"}
    assert "ai_enrichment" in analysis
    assert analysis["ai_enrichment"]["status"] in {"disabled", "fallback"}


def test_ai_enabled_enrichment_added():
    filterer = JobFilter()
    job = Job(
        title="Embedded Linux Engineer",
        company="Acme",
        location="Remote, India",
        experience="0-1 years",
        source="RemoteOK",
        url="https://example.com/embedded-linux",
        skills=["Embedded Linux", "C", "Linux", "ARM", "GPIO"],
        posted_date="2026-08-01",
        description="Build embedded Linux firmware and device drivers for ARM boards.",
    )
    registry = AIProviderRegistry()
    registry.register_provider(FakeAIProvider())
    orchestrator = AIOrchestrator(config=AIConfig(enabled=True, default_provider="fake", required_fields=["result", "status"]), registry=registry)

    analysis = filterer.analyze_job_intelligence(job, {"skills": ["C", "Linux", "ARM"], "experience": "fresher"}, orchestrator=orchestrator)
    assert analysis["ai_enrichment"]["status"] == "success"
    assert analysis["ai_enrichment"]["role_relevance"] == "High"
    assert analysis["ai_enrichment"]["recommendation"]
    assert analysis["match_score"] >= 0


def test_valid_ai_response_accepted():
    registry = AIProviderRegistry()
    registry.register_provider(FakeAIProvider())
    orchestrator = AIOrchestrator(config=AIConfig(enabled=True, default_provider="fake", required_fields=["result", "status"]), registry=registry)

    response = orchestrator.run(task="job_description_understanding", payload={"title": "Embedded Engineer"})
    assert response.success is True
    assert response.payload["result"]["role_relevance"] == "High"


def test_malformed_ai_response_falls_back():
    registry = AIProviderRegistry()
    registry.register_provider(FakeBrokenProvider())
    orchestrator = AIOrchestrator(config=AIConfig(enabled=True, default_provider="broken", required_fields=["result", "status"]), registry=registry)

    analysis = orchestrator.run(task="job_description_understanding", payload={"title": "Embedded Engineer"})
    assert analysis.success is False
    assert "Malformed" in analysis.error


def test_provider_timeout_falls_back():
    registry = AIProviderRegistry()
    registry.register_provider(FakeTimeoutProvider())
    orchestrator = AIOrchestrator(config=AIConfig(enabled=True, default_provider="timeout", required_fields=["result", "status"]), registry=registry)

    result = orchestrator.run(task="job_description_understanding", payload={"title": "Embedded Engineer"})
    assert result.success is False
    assert "Timeout" in result.error or "timed out" in result.error.lower()


def test_provider_exception_falls_back():
    registry = AIProviderRegistry()
    registry.register_provider(FakeExceptionProvider())
    orchestrator = AIOrchestrator(config=AIConfig(enabled=True, default_provider="error", required_fields=["result", "status"]), registry=registry)

    result = orchestrator.run(task="job_description_understanding", payload={"title": "Embedded Engineer"})
    assert result.success is False
    assert result.error is not None


def test_deterministic_score_stays_available():
    filterer = JobFilter()
    job = Job(
        title="Firmware Engineer Trainee",
        company="CoreIoT",
        location="Hyderabad",
        experience="Graduate",
        source="Greenhouse",
        url="https://example.com/firmware-trainee",
        skills=["C", "Firmware", "GPIO", "RTOS"],
        posted_date="2026-08-04",
        description="Firmware development for microcontrollers and GPIO/RTOS tasks.",
    )
    analysis = filterer.analyze_job_intelligence(job, {"skills": ["C", "Firmware", "GPIO"], "experience": "fresher"})
    assert analysis["match_score"] >= 0
    assert analysis["role_category"] == "Firmware"


def test_final_result_has_stable_structure():
    filterer = JobFilter()
    job = Job(
        title="Embedded Linux Engineer",
        company="Acme",
        location="Remote",
        experience="0-1 years",
        source="RemoteOK",
        url="https://example.com/a",
        skills=["Embedded Linux", "C", "Linux", "ARM"],
        posted_date="2026-08-05",
        description="Embedded Linux work with Linux drivers, ARM, and BSPs.",
    )
    result = filterer.analyze_job_intelligence(job, {"skills": ["C", "Linux", "ARM"], "experience": "fresher"})
    assert set(result.keys()) >= {"role_category", "matched_skills", "missing_skills", "experience_level", "location_match", "embedded_relevance", "match_score", "rejection_reasons", "ai_enrichment", "combined_analysis"}
    assert isinstance(result["combined_analysis"], dict)
    assert "deterministic" in result["combined_analysis"]
    assert "ai" in result["combined_analysis"]


class StubAIResponse:
    def __init__(self, success=True, payload=None, error="", provider="stub", model="stub-model"):
        self.success = success
        self.payload = payload or {}
        self.error = error
        self.provider = provider
        self.model = model


class StubAIOrchestrator:
    def __init__(self, payload=None, success=True, error=""):
        self.payload = payload or {
            "result": {
                "role_relevance": "High",
                "embedded_relevance": "High",
                "skill_relevance": ["C", "Linux", "ARM"],
                "experience_suitability": "Strong fit",
                "candidate_suitability": "Strong",
                "missing_important_skills": ["RTOS"],
                "positive_matching_factors": ["embedded Linux", "ARM", "GPIO"],
                "concerns": ["Needs stronger RTOS exposure"],
                "recommendation": "Strong candidate for this embedded role.",
                "confidence": 0.9,
                "status": "ok",
            }
        }
        self.success = success
        self.error = error

    def run(self, task, payload):
        return StubAIResponse(success=self.success, payload=self.payload, error=self.error)


class StubWeakAIOrchestrator(StubAIOrchestrator):
    def __init__(self):
        super().__init__(payload={
            "result": {
                "role_relevance": "Low",
                "embedded_relevance": "Low",
                "skill_relevance": ["Python"],
                "experience_suitability": "Weak fit",
                "candidate_suitability": "Low",
                "missing_important_skills": ["C", "RTOS", "ARM"],
                "positive_matching_factors": [],
                "concerns": ["Poor embedded fit"],
                "recommendation": "Not a strong match.",
                "confidence": 0.1,
                "status": "ok",
            }
        })


class StubMalformedAIOrchestrator(StubAIOrchestrator):
    def __init__(self):
        super().__init__(payload={"bad": "shape"})


class StubTimeoutAIOrchestrator(StubAIOrchestrator):
    def __init__(self):
        self.success = False
        self.error = "Timeout: timed out"

    def run(self, task, payload):
        return StubAIResponse(success=False, payload={}, error="Timeout: timed out")


class StubExceptionAIOrchestrator(StubAIOrchestrator):
    def __init__(self):
        self.success = False
        self.error = "provider crashed"

    def run(self, task, payload):
        raise RuntimeError("provider crashed")


def test_ai_ranked_jobs_use_bounded_ai_adjustment_and_preserve_deterministic_baseline():
    filterer = JobFilter()
    profile = {"skills": ["C", "Embedded C", "Linux", "GPIO", "ARM"], "experience": "fresher"}
    strong_job = Job(
        title="Embedded Linux Engineer",
        company="Acme",
        location="Remote",
        experience="0-1 years",
        source="RemoteOK",
        url="https://example.com/strong",
        skills=["C", "Linux", "Embedded Linux", "ARM", "GPIO"],
        posted_date="2026-08-02",
        description="Build embedded Linux systems using Linux, ARM, and device drivers.",
    )
    weak_job = Job(
        title="Frontend Developer",
        company="WebWorks",
        location="Remote",
        experience="Experienced",
        source="RemoteOK",
        url="https://example.com/weak",
        skills=["React", "Node", "CSS"],
        posted_date="2026-08-03",
        description="Build frontend interfaces and cloud services.",
    )

    strong_ranked = filterer.rank_jobs_for_candidate([strong_job, weak_job], profile, orchestrator=StubAIOrchestrator())
    assert strong_ranked[0]["title"] == "Embedded Linux Engineer"
    assert strong_ranked[0]["deterministic_score"] >= 0
    assert strong_ranked[0]["final_score"] >= strong_ranked[0]["deterministic_score"]
    assert strong_ranked[0]["ai_role_relevance"] in {"High", "Strong", "High"}
    assert strong_ranked[0]["ai_confidence"] >= 0.0
    assert strong_ranked[0]["final_score"] <= 100

    weak_ranked = filterer.rank_jobs_for_candidate([strong_job, weak_job], profile, orchestrator=StubWeakAIOrchestrator())
    assert weak_ranked[0]["title"] == "Embedded Linux Engineer"
    assert weak_ranked[1]["ai_candidate_fit"] in {"Low", "Weak"}
    assert weak_ranked[0]["final_score"] >= 0
    assert weak_ranked[1]["final_score"] <= 100

    malformed_ranked = filterer.rank_jobs_for_candidate([strong_job], profile, orchestrator=StubMalformedAIOrchestrator())
    assert malformed_ranked[0]["ai_enrichment"]["status"] in {"fallback", "disabled"}
    assert malformed_ranked[0]["final_score"] <= 100

    timeout_ranked = filterer.rank_jobs_for_candidate([strong_job], profile, orchestrator=StubTimeoutAIOrchestrator())
    assert timeout_ranked[0]["ai_enrichment"]["status"] == "fallback"
    assert timeout_ranked[0]["final_score"] <= 100

    exception_ranked = filterer.rank_jobs_for_candidate([strong_job], profile, orchestrator=StubExceptionAIOrchestrator())
    assert exception_ranked[0]["ai_enrichment"]["status"] == "fallback"
    assert exception_ranked[0]["final_score"] <= 100


def test_ai_rank_jobs_fallback_and_ordering_are_deterministic():
    filterer = JobFilter()
    profile = {"skills": ["C", "Linux", "ARM", "GPIO"], "experience": "fresher"}
    jobs = [
        Job(title="Embedded Linux Engineer", company="Acme", location="Remote", experience="0-1 years", source="RemoteOK", url="https://example.com/a", skills=["Linux", "C", "ARM"], posted_date="2026-08-01", description="Embedded Linux and ARM boards."),
        Job(title="Embedded C Engineer", company="Beta", location="Remote", experience="Fresher", source="RemoteOK", url="https://example.com/b", skills=["C", "Embedded C", "GPIO"], posted_date="2026-08-01", description="Embedded C development for microcontroller tasks."),
        Job(title="Embedded C Engineer", company="Beta", location="Remote", experience="Fresher", source="RemoteOK", url="https://example.com/c", skills=["C", "Embedded C", "GPIO"], posted_date="2026-08-02", description="Embedded C development for microcontroller tasks."),
    ]

    first_pass = filterer.rank_jobs_for_candidate(jobs, profile)
    second_pass = filterer.rank_jobs_for_candidate(list(reversed(jobs)), profile)
    assert [row["title"] for row in first_pass] == [row["title"] for row in second_pass]

    equal_jobs = [
        Job(title="Embedded C Engineer", company="A", location="Remote", experience="Fresher", source="S", url="https://example.com/e1", skills=["C", "Embedded C"], posted_date="2026-08-01"),
        Job(title="Embedded C Engineer", company="A", location="Remote", experience="Fresher", source="S", url="https://example.com/e2", skills=["C", "Embedded C"], posted_date="2026-08-02"),
    ]
    equal_ranked = filterer.rank_jobs_for_candidate(equal_jobs, profile)
    assert equal_ranked[0]["rank"] == 1
    assert equal_ranked[1]["rank"] == 2
    assert equal_ranked[0]["match_score"] == equal_ranked[1]["match_score"]
    assert equal_ranked[0]["title"] == equal_ranked[1]["title"]


def test_ai_rank_jobs_score_boundaries_and_compatibility():
    filterer = JobFilter()
    profile = {"skills": ["C", "Linux", "ARM", "GPIO"], "experience": "fresher"}
    job = Job(
        title="Embedded Linux Engineer",
        company="Acme",
        location="Remote",
        experience="0-1 years",
        source="RemoteOK",
        url="https://example.com/scorebound",
        skills=["C", "Linux", "ARM", "GPIO"],
        posted_date="2026-08-01",
        description="Linux driver and embedded software engineering for ARM-based platforms.",
    )
    ranked = filterer.rank_jobs_for_candidate([job], profile, orchestrator=StubAIOrchestrator())
    assert 0 <= ranked[0]["final_score"] <= 100
    assert ranked[0]["final_score"] >= ranked[0]["deterministic_score"]
    assert ranked[0]["match_score"] >= ranked[0]["deterministic_score"]
    assert "role_match" in ranked[0]
    assert "skill_match" in ranked[0]
    assert "experience_match" in ranked[0]
    assert "location_match" in ranked[0]
    assert "embedded_relevance" in ranked[0]
    assert "matched_skills" in ranked[0]
    assert "missing_skills" in ranked[0]
    assert "rejection_reasons" in ranked[0]
    assert "ai_role_relevance" in ranked[0]
    assert "ai_skill_relevance" in ranked[0]
    assert "ai_experience_relevance" in ranked[0]
    assert "ai_candidate_fit" in ranked[0]
    assert "ai_confidence" in ranked[0]
    assert "ai_concerns" in ranked[0]
    assert "ai_recommendation" in ranked[0]
