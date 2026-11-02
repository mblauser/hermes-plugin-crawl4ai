"""Unit tests for the crawl4ai extract provider (no network, no crawl4ai instance).

Run from the repo root: python -m pytest tests/
Works inside a Hermes checkout or standalone (Hermes' two imports are stubbed if absent).
"""
import asyncio
import importlib.util
import json
import pathlib
import sys
import types

import httpx
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _stub_hermes():
    try:
        import agent.web_search_provider  # noqa: F401
        import tools.url_safety  # noqa: F401
        return
    except Exception:
        pass
    agent = types.ModuleType("agent")
    wsp = types.ModuleType("agent.web_search_provider")
    wsp.WebSearchProvider = type("WebSearchProvider", (), {})
    tools = types.ModuleType("tools")
    safety = types.ModuleType("tools.url_safety")
    safety.is_safe_url = lambda url: True
    sys.modules.update({"agent": agent, "agent.web_search_provider": wsp,
                        "tools": tools, "tools.url_safety": safety})


_stub_hermes()
_spec = importlib.util.spec_from_file_location("crawl4ai_provider", ROOT / "provider.py")
provider = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(provider)


def _crawl_response(status_code=200, success=True, fit="# Title\n\nBody text.", raw="RAW", title="Page Title", error=""):
    return {"success": True, "results": [{
        "url": "https://example.com/page", "status_code": status_code, "success": success,
        "error_message": error, "metadata": {"title": title},
        "markdown": {"raw_markdown": raw, "fit_markdown": fit},
    }]}


def _run(monkeypatch, handler, urls=("https://example.com/page",)):
    seen = []

    def wrapped(request):
        seen.append(request)
        return handler(request)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(provider.httpx, "AsyncClient",
                        lambda **kw: real_client(transport=httpx.MockTransport(wrapped), **kw))
    monkeypatch.setattr(provider, "is_safe_url", lambda url: True)
    monkeypatch.setenv("CRAWL4AI_URL", "http://crawl4ai.test:11235")
    monkeypatch.setenv("CRAWL4AI_API_TOKEN", "test-token")
    monkeypatch.setattr(provider, "_crawl4ai_url", lambda: "http://crawl4ai.test:11235")
    monkeypatch.setattr(provider, "_crawl4ai_token", lambda: "test-token")
    results = asyncio.run(provider.Crawl4aiWebExtractProvider().extract(list(urls)))
    return results, seen


def test_live_page_returns_fit_markdown_and_status(monkeypatch):
    results, seen = _run(monkeypatch, lambda r: httpx.Response(200, json=_crawl_response()))
    assert results == [{
        "url": "https://example.com/page", "title": "Page Title",
        "content": "# Title\n\nBody text.", "raw_content": "# Title\n\nBody text.",
        "metadata": {"status_code": 200},
    }]
    req = seen[0]
    assert req.url.path == "/crawl"
    assert req.headers["Authorization"] == "Bearer test-token"
    body = json.loads(req.content)
    assert body["urls"] == ["https://example.com/page"]
    params = body["crawler_config"]["params"]
    assert params["markdown_generator"]["params"]["content_filter"]["type"] == "PruningContentFilterLXML"


@pytest.mark.parametrize("status", [404, 410, 500, 503])
def test_origin_error_status_is_an_error_not_content(monkeypatch, status):
    # crawl4ai marks these crawls successful and returns the site's error page as markdown
    resp = _crawl_response(status_code=status, success=True, fit="# Page not found", raw="# Page not found")
    results, _ = _run(monkeypatch, lambda r: httpx.Response(200, json=resp))
    assert results[0]["error"] == f"HTTP {status} from origin"
    assert results[0]["content"] == ""


def test_origin_status_wins_over_crawl4ai_failure_message(monkeypatch):
    resp = _crawl_response(status_code=404, success=False, error="Blocked by anti-bot protection: minimal_text")
    results, _ = _run(monkeypatch, lambda r: httpx.Response(200, json=resp))
    assert results[0]["error"] == "HTTP 404 from origin"


def test_redirect_with_content_is_not_an_error(monkeypatch):
    results, _ = _run(monkeypatch, lambda r: httpx.Response(200, json=_crawl_response(status_code=302)))
    assert "error" not in results[0]
    assert results[0]["content"]


def test_crawl_failure_without_status_is_reported(monkeypatch):
    resp = _crawl_response(status_code=None, success=False, error="net::ERR_NAME_NOT_RESOLVED")
    results, _ = _run(monkeypatch, lambda r: httpx.Response(200, json=resp))
    assert results[0]["error"].startswith("Crawl4ai could not fetch the page: net::ERR_NAME_NOT_RESOLVED")


def test_empty_filtered_markdown_falls_back_to_raw(monkeypatch):
    resp = _crawl_response(fit="", raw="Unfiltered page text")
    results, _ = _run(monkeypatch, lambda r: httpx.Response(200, json=resp))
    assert results[0]["content"] == "Unfiltered page text"


def test_title_falls_back_to_first_heading(monkeypatch):
    resp = _crawl_response(title=None, fit="intro\n# Heading From Markdown\ntext")
    results, _ = _run(monkeypatch, lambda r: httpx.Response(200, json=resp))
    assert results[0]["title"] == "Heading From Markdown"


def test_crawl4ai_server_error_is_reported(monkeypatch):
    results, _ = _run(monkeypatch, lambda r: httpx.Response(401, text="Unauthorized"))
    assert results[0]["error"].startswith("Crawl4ai HTTP 401")


def test_unexpected_response_shape_is_an_error(monkeypatch):
    results, _ = _run(monkeypatch, lambda r: httpx.Response(200, json={"detail": "something else"}))
    assert results[0]["error"].startswith("Crawl4ai returned no result")


def test_each_url_is_independent(monkeypatch):
    def handler(request):
        url = json.loads(request.content)["urls"][0]
        return httpx.Response(200, json=_crawl_response(status_code=404 if url.endswith("/gone") else 200))
    results, seen = _run(monkeypatch, handler, urls=("https://example.com/ok", "https://example.com/gone"))
    assert len(seen) == 2
    assert "error" not in results[0]
    assert results[1]["error"] == "HTTP 404 from origin"
