"""Shared fakes and fixtures. No test may touch the network or a real API."""

import logging
import os
import sys
from types import SimpleNamespace

import pytest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")


def make_response(content, finish_reason="stop", refusal=None, usage=None):
    msg = SimpleNamespace(content=content, refusal=refusal)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=msg, finish_reason=finish_reason)],
        usage=usage or SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


class FakeOpenAI:
    """Stand-in for openai.OpenAI.

    Configure through the class attributes (the `fake_openai` fixture resets
    them per test):
      handler  - callable(kwargs) -> content str | None | Exception | response
      queue    - list of scripted items consumed in order when no handler
    Items may be a string/None content, an Exception (raised), or a ready
    response object. Every call's kwargs are appended to `calls`.
    """

    handler = None
    queue = []
    calls = []
    default = "No"

    def __init__(self, *args, **kwargs):
        self.init_kwargs = kwargs
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        type(self).calls.append(kw)
        if type(self).handler is not None:
            item = type(self).handler(kw)
        elif type(self).queue:
            item = type(self).queue.pop(0)
        else:
            item = type(self).default
        if isinstance(item, Exception):
            raise item
        if hasattr(item, "choices"):
            return item
        return make_response(item)

    @classmethod
    def reset(cls):
        cls.handler = None
        cls.queue = []
        cls.calls = []
        cls.default = "No"


@pytest.fixture
def fake_openai(monkeypatch):
    import llm_filter
    import summarizer

    FakeOpenAI.reset()
    monkeypatch.setattr(llm_filter, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(summarizer, "OpenAI", FakeOpenAI)
    yield FakeOpenAI
    FakeOpenAI.reset()


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Empty cwd with data/ present, so relative history/cache paths stay in tmp."""
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def history_file(workdir):
    return str(workdir / "data" / "article_history.json")


@pytest.fixture
def cache_file(workdir):
    return str(workdir / "data" / "cache.json")


class FakeHTTP:
    """Fake for requests.get / requests.post. Routes keyed by exact URL.

    A route value is a FakeResponse, an Exception (raised), or a callable
    (url, kwargs) -> either. Unrouted URLs raise, so nothing leaks out.
    """

    def __init__(self):
        self.routes = {}
        self.calls = []

    def add(self, url, response):
        self.routes[url] = response

    def _dispatch(self, method, url, **kw):
        self.calls.append((method, url, kw))
        if url not in self.routes:
            raise AssertionError(f"unrouted fake HTTP request: {method} {url}")
        item = self.routes[url]
        if callable(item):
            item = item(url, kw)
        if isinstance(item, Exception):
            raise item
        return item

    def get(self, url, **kw):
        return self._dispatch("GET", url, **kw)

    def post(self, url, **kw):
        return self._dispatch("POST", url, **kw)


class FakeResponse:
    def __init__(self, status_code=200, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


@pytest.fixture
def fake_http(monkeypatch):
    import requests

    fake = FakeHTTP()
    monkeypatch.setattr(requests, "get", fake.get)
    monkeypatch.setattr(requests, "post", fake.post)
    return fake


@pytest.fixture
def named_logger_clean():
    """Remove handlers setup_logger() adds so tests don't leak into each other."""
    logger = logging.getLogger("RSSFeedMonitor")
    before = list(logger.handlers)
    yield logger
    for h in list(logger.handlers):
        if h not in before:
            logger.removeHandler(h)
            h.close()


RSS_TEMPLATE = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>t</title>
{items}
</channel></rss>"""


def rss_xml(entries):
    items = "".join(
        f"<item><title>{t}</title><link>{l}</link><description>{s}</description></item>"
        for t, l, s in entries
    )
    return RSS_TEMPLATE.format(items=items)


def check_snapshot(name, text):
    """Compare text with tests/snapshots/<name>.txt; UPDATE_SNAPSHOTS=1 rewrites."""
    path = os.path.join(SNAPSHOT_DIR, name + ".txt")
    if os.environ.get("UPDATE_SNAPSHOTS") or not os.path.exists(path):
        with open(path, "w") as f:
            f.write(text)
        if not os.environ.get("UPDATE_SNAPSHOTS"):
            pytest.fail(f"snapshot {name} did not exist; created it, re-run")
        return
    with open(path) as f:
        assert text == f.read()
