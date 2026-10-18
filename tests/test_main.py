"""End-to-end main.main() runs with every external dependency faked."""

import json
import sys

import pytest

from conftest import FakeResponse, rss_xml

FEED = "http://feeds.test/a"
HOOK = "http://hooks.test/w"


@pytest.fixture
def env(workdir, fake_http, fake_openai, named_logger_clean, monkeypatch):
    (workdir / ".env").write_text(
        f"OPENAI_API_KEY=test-key\nRSS_FEEDS={FEED}\nFILTER_PROMPT=disasters\n"
        f"FILTER_MODEL=gpt-4o-mini\nGROUP_MODEL=gpt-4o-mini\nSUMMARIZE_MODEL=gpt-4o-mini\n"
        f"SLACK_WEBHOOK_URL={HOOK}\n"
    )
    fake_http.add(HOOK, FakeResponse(200, "ok"))

    def filter_handler(kw):
        user = kw["messages"][1]["content"]
        if "ERR" in user:
            return RuntimeError("api down")
        return "Yes" if "KEEP" in user else "No"

    def handler(kw):
        if "response_format" in kw:
            return "not json"  # exercises the fallback grouping path
        if "max_completion_tokens" in kw and "<article>" in kw["messages"][1]["content"]:
            return filter_handler(kw)
        return "Summary text."

    fake_openai.handler = handler
    monkeypatch.setattr(sys, "argv", ["main.py", "--output", "slack"])

    def set_feed(entries):
        fake_http.add(FEED, FakeResponse(200, rss_xml(entries)))

    return set_feed


def run_main():
    # Imported lazily: web_dashboard runs os.makedirs("data") at import time,
    # which must land in the temp cwd, not the repo.
    import main as main_mod

    main_mod.main()


def history_links(workdir):
    p = workdir / "data" / "article_history.json"
    return set(json.loads(p.read_text())["articles"]) if p.exists() else set()


def slack_posts(fake_http):
    return [c for c in fake_http.calls if c[0] == "POST"]


def u(n):
    return f"http://x.test/{n}"


def test_main_slack_success_marks_delivered_and_rejected(env, workdir, fake_http):
    env([("KEEP one", u(1), "s"), ("KEEP two", u(2), "s"), ("drop three", u(3), "s")])
    run_main()
    assert len(slack_posts(fake_http)) == 1
    assert history_links(workdir) == {u(1), u(2), u(3)}


def test_main_slack_failure_leaves_filtered_unmarked_but_records_rejected(env, workdir, fake_http):
    env([("KEEP one", u(1), "s"), ("drop two", u(2), "s")])
    fake_http.add(HOOK, FakeResponse(500, "err"))
    run_main()
    assert history_links(workdir) == {u(2)}


def test_main_slack_failure_then_retry_delivers_the_same_article(env, workdir, fake_http):
    env([("KEEP one", u(1), "s")])
    fake_http.add(HOOK, FakeResponse(500, "err"))
    run_main()
    fake_http.add(HOOK, FakeResponse(200, "ok"))
    run_main()
    assert len(slack_posts(fake_http)) == 2
    assert history_links(workdir) == {u(1)}


def test_main_errored_articles_are_never_recorded(env, workdir, fake_http):
    env([("KEEP one", u(1), "s"), ("ERR two", u(2), "s"), ("drop three", u(3), "s")])
    run_main()
    assert history_links(workdir) == {u(1), u(3)}


def test_main_all_rejected_sends_nothing_and_records_rejections(env, workdir, fake_http):
    env([("drop one", u(1), "s")])
    run_main()
    assert slack_posts(fake_http) == []
    assert history_links(workdir) == {u(1)}


def test_main_second_run_skips_already_published(env, workdir, fake_http, fake_openai):
    env([("KEEP one", u(1), "s")])
    run_main()
    calls_after_first = len(fake_openai.calls)
    run_main()
    assert len(fake_openai.calls) == calls_after_first
    assert len(slack_posts(fake_http)) == 1


def test_main_missing_api_key_returns_without_any_calls(env, workdir, fake_http, fake_openai):
    (workdir / ".env").write_text(f"RSS_FEEDS={FEED}\n")
    run_main()
    assert fake_http.calls == [] and fake_openai.calls == []


def test_main_duplicate_link_one_yes_one_no_then_failed_delivery_is_retried(env, workdir, fake_http):
    env([("KEEP passed copy", u(1), "s"), ("drop rejected copy", u(1), "s")])
    fake_http.add(HOOK, FakeResponse(500, "err"))
    run_main()
    fake_http.add(HOOK, FakeResponse(200, "ok"))
    run_main()
    ok_posts = [c for c in slack_posts(fake_http) if "KEEP passed copy" in json.dumps(c[2]["json"])]
    assert len(ok_posts) == 2  # failed attempt plus the successful retry


def test_main_rejected_link_is_refiltered_when_content_changes(env, workdir, fake_http):
    env([("drop old headline", u(1), "s")])
    run_main()
    env([("KEEP updated headline", u(1), "s")])
    run_main()
    assert len(slack_posts(fake_http)) == 1


def test_main_partial_slack_delivery_marks_only_delivered(env, workdir, fake_http, monkeypatch):
    env([("KEEP one", u(1), "s"), ("KEEP two", u(2), "s")])
    import main as main_mod

    def partial(summary, hook, delivered_links=None):
        delivered_links.add(u(1))
        return False

    monkeypatch.setattr(main_mod, "publish_to_slack", partial)
    main_mod.main()
    assert history_links(workdir) == {u(1)}
