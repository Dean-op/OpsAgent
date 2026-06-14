from datetime import datetime, timezone


def test_query_range_builds_prometheus_api_request(monkeypatch):
    from mcp_servers import monitor_server

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "success",
                "data": {
                    "result": [
                        {
                            "metric": {"instance": "localhost:9100"},
                            "values": [[1710000000, "42.5"]],
                        }
                    ]
                },
            }

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, params):
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

    monkeypatch.setattr(monitor_server.httpx, "Client", FakeClient)
    monkeypatch.setattr(monitor_server.config, "prometheus_base_url", "http://prometheus:9090")
    monkeypatch.setattr(monitor_server.config, "prometheus_request_timeout", 7.0)

    start = datetime(2024, 3, 9, 16, 0, tzinfo=timezone.utc)
    end = datetime(2024, 3, 9, 17, 0, tzinfo=timezone.utc)
    result = monitor_server.query_prometheus_range("up", start, end, "60s")

    assert captured["url"] == "http://prometheus:9090/api/v1/query_range"
    assert captured["timeout"] == 7.0
    assert captured["params"]["query"] == "up"
    assert captured["params"]["step"] == "60s"
    assert result["status"] == "success"
