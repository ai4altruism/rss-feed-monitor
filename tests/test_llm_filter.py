import pytest

from conftest import check_snapshot
from llm_filter import filter_stories


def art(title, summary="s", link=None):
    return {"title": title, "summary": summary, "link": link or f"http://x.test/{title}"}


def run(articles, **kw):
    return filter_stories(articles, "disasters", kw.pop("model", "gpt-4o-mini"), "k", return_errors=True, **kw)


@pytest.mark.parametrize("answer", ["Yes", "yes", " YES. "])
def test_filter_stories_yes_answer_includes_article(fake_openai, answer):
    fake_openai.queue = [answer]
    passed, errored = run([art("a")])
    assert [a["title"] for a in passed] == ["a"] and errored == []


@pytest.mark.parametrize("answer", ["No", "no", "No."])
def test_filter_stories_no_answer_rejects_without_error(fake_openai, answer):
    fake_openai.queue = [answer]
    assert run([art("a")]) == ([], [])


def test_filter_stories_no_answer_mentioning_yesterday_is_rejected(fake_openai):
    fake_openai.queue = ["No, yesterday's storm"]
    passed, errored = run([art("a")])
    assert passed == [] and errored == []


def test_filter_stories_empty_content_is_errored_not_rejected(fake_openai):
    fake_openai.queue = [None]
    passed, errored = run([art("a")])
    assert passed == [] and [a["title"] for a in errored] == ["a"]


def test_filter_stories_whitespace_content_is_errored(fake_openai):
    fake_openai.queue = ["   "]
    assert run([art("a")])[1][0]["title"] == "a"


def test_filter_stories_exception_is_errored_and_others_continue(fake_openai):
    fake_openai.queue = [RuntimeError("boom"), "Yes"]
    passed, errored = run([art("a"), art("b")])
    assert [a["title"] for a in errored] == ["a"]
    assert [a["title"] for a in passed] == ["b"]


def test_filter_stories_without_return_errors_returns_list_only(fake_openai):
    fake_openai.queue = ["Yes"]
    assert filter_stories([art("a")], "p", "gpt-4o-mini", "k") == [art("a")]


@pytest.mark.parametrize(
    "model,verbose,cap",
    [
        ("gpt-5-mini", False, 4000),
        ("gpt-5-mini", True, 4000),
        ("gpt-6-luna", False, 4000),
        ("o3-mini", False, 4000),
        ("gpt-4o-mini", False, 5),
        ("gpt-4o-mini", True, 100),
        ("gpt-3.5-turbo", False, 5),
    ],
)
def test_filter_stories_completion_cap_follows_model_family(fake_openai, model, verbose, cap):
    fake_openai.queue = ["Yes"]
    filter_stories([art("a")], "p", model, "k", verbose=verbose)
    assert fake_openai.calls[0]["max_completion_tokens"] == cap
    assert fake_openai.calls[0]["model"] == model


def test_filter_stories_verbose_decision_pattern_parsed(fake_openai):
    fake_openai.queue = ["Reasoning here.\nDECISION: No", "Because.\nDECISION: Yes"]
    passed = filter_stories([art("a"), art("b")], "p", "gpt-4o-mini", "k", verbose=True)
    assert [a["title"] for a in passed] == ["b"]


def _prompt_snapshot(fake_openai, verbose):
    fake_openai.queue = ["Yes"]
    filter_stories(
        [{"title": "Flood hits Riverton", "summary": "Rain caused a flood.", "link": "http://x.test/1"}],
        "Natural disasters and humanitarian crises",
        "gpt-4o-mini",
        "k",
        verbose=verbose,
    )
    msgs = fake_openai.calls[0]["messages"]
    return "\n=====\n".join(f"[{m['role']}]\n{m['content']}" for m in msgs)


@pytest.mark.snapshot
def test_filter_prompt_snapshot(fake_openai):
    check_snapshot("filter_prompt", _prompt_snapshot(fake_openai, False))


@pytest.mark.snapshot
def test_filter_prompt_verbose_snapshot(fake_openai):
    check_snapshot("filter_prompt_verbose", _prompt_snapshot(fake_openai, True))


@pytest.mark.parametrize("answer, outcome", [
    ("Yes, a major earthquake", "pass"),
    ("YES.", "pass"),
    ("Eyes on the storm: no", "error"),
    ("Maybe", "error"),
])
def test_filter_stories_reads_the_first_word(fake_openai, answer, outcome):
    fake_openai.queue = [answer]
    passed, errored = run([art("a")])
    assert (passed, errored) == {"pass": ([art("a")], []), "error": ([], [art("a")])}[outcome]
