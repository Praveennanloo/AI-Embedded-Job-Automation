from unittest.mock import patch

from search_engine.providers.remoteok_provider import RemoteOKProvider


def test_remoteok_provider():
    fake_response = [
        {
            "position": "Embedded Firmware Engineer",
            "company": "Test Company",
            "location": "Remote",
            "url": "https://example.com/job",
            "tags": ["C", "Embedded"],
            "id": "test-1",
        }
    ]

    mock_response = type("MockResponse", (), {
        "status_code": 200,
        "json": lambda self: fake_response,
        "raise_for_status": lambda self: None,
    })()

    with patch(
        "search_engine.providers.remoteok_provider.httpx.get",
        return_value=mock_response,
    ):
        jobs = RemoteOKProvider().search()

    assert isinstance(jobs, list)
    assert len(jobs) == 1
    assert jobs[0].title == "Embedded Firmware Engineer"
