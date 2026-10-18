import json

import pytest

from conftest import check_snapshot
from summarizer import group_and_summarize


def arts(n, prefix="Story"):
    return [{"title": f"{prefix} {i}", "link": f"http://x.test/{prefix}/{i}", "summary": f"Sum {i}"} for i in range(n)]


def grouping(*topics):
    """topics: (name, [article dicts]) -> JSON string the model might return."""
    return json.dumps({"topics": [
        {"topic": n, "articles": [{"title": a["title"], "link": a["link"]} for a in items]}
        for n, items in topics]})


def script(grouping_content, summary="A fine summary."):
    """Handler: grouping calls (response_format present) vs summary calls."""
    def handler(kw):
        if "response_format" in kw:
            return grouping_content(kw) if callable(grouping_content) else grouping_content
        return summary(kw) if callable(summary) else summary
    return handler


def run(articles, fake_openai, handler, gm="gpt-4o-mini", sm="gpt-4o-mini"):
    fake_openai.handler = handler
    return group_and_summarize(articles, gm, sm, "k")


def flat_links(result):
    return [a["link"] for t in result["topics"] for a in t["articles"]]


def test_group_and_summarize_empty_input_makes_no_calls(fake_openai):
    assert group_and_summarize([], "m", "m", "k") == {"topics": []}
    assert fake_openai.calls == []


def test_group_and_summarize_happy_path_groups_and_summarizes(fake_openai):
    a = arts(3)
    out = run(a, fake_openai, script(grouping(("Floods", a[:2]), ("Fire", a[2:]))))
    assert [t["topic"] for t in out["topics"]] == ["Floods", "Fire"]
    assert all(t["summary"] == "A fine summary." for t in out["topics"])
    assert sorted(flat_links(out)) == sorted(x["link"] for x in a)


def test_group_and_summarize_dropped_article_lands_in_additional_stories(fake_openai):
    a = arts(3)
    out = run(a, fake_openai, script(grouping(("Floods", a[:2]))))
    extra = out["topics"][-1]
    assert extra["topic"] == "Additional stories"
    assert [x["link"] for x in extra["articles"]] == [a[2]["link"]]


def test_group_and_summarize_invented_article_is_never_output(fake_openai):
    a = arts(2)
    content = json.dumps({"topics": [{"topic": "T", "articles": [
        {"title": a[0]["title"], "link": a[0]["link"]},
        {"title": "Invented headline", "link": "http://evil.test/x"},
        {"title": a[1]["title"], "link": a[1]["link"]}]}]})
    out = run(a, fake_openai, script(content))
    assert sorted(flat_links(out)) == sorted(x["link"] for x in a)
    assert "http://evil.test/x" not in flat_links(out)


def test_group_and_summarize_topic_of_only_invented_articles_is_dropped(fake_openai):
    a = arts(1)
    content = json.dumps({"topics": [{"topic": "Ghost", "articles": [{"title": "Nope", "link": "http://evil.test/y"}]}]})
    out = run(a, fake_openai, script(content))
    assert [t["topic"] for t in out["topics"]] == ["Additional stories"]


def test_group_and_summarize_corrupt_link_with_exact_title_is_grounded_to_source(fake_openai):
    a = arts(1)
    content = json.dumps({"topics": [{"topic": "T", "articles": [{"title": a[0]["title"], "link": "http://corrupt.test/zzz"}]}]})
    out = run(a, fake_openai, script(content))
    assert [t["topic"] for t in out["topics"]] == ["T"]
    assert flat_links(out) == [a[0]["link"]]


def test_group_and_summarize_whitespace_and_case_variant_title_is_grounded(fake_openai):
    a = arts(1)
    content = json.dumps({"topics": [{"topic": "T", "articles": [{"title": "  STORY   0 ", "link": "bad"}]}]})
    assert flat_links(run(a, fake_openai, script(content))) == [a[0]["link"]]


def test_group_and_summarize_model_repeating_article_places_it_once(fake_openai):
    a = arts(1)
    out = run(a, fake_openai, script(grouping(("A", a), ("B", a))))
    assert flat_links(out) == [a[0]["link"]]


@pytest.mark.parametrize("content", [None, "this is not json", "```json\nstill {not json\n```"])
def test_group_and_summarize_unusable_grouping_falls_back_to_chunk_articles(fake_openai, content):
    a = arts(3)
    out = run(a, fake_openai, script(content))
    assert [t["topic"] for t in out["topics"]] == ["Articles Group 1"]
    assert flat_links(out) == [x["link"] for x in a]


def test_group_and_summarize_grouping_exception_falls_back_to_chunk(fake_openai):
    a = arts(2)
    out = run(a, fake_openai, script(lambda kw: RuntimeError("api down")))
    assert [t["topic"] for t in out["topics"]] == ["Articles Group 1"]
    assert len(flat_links(out)) == 2


def test_group_and_summarize_fenced_valid_json_is_repaired_not_fallback(fake_openai):
    a = arts(2)
    fenced = "```json\n" + grouping(("Floods", a)) + "\n```"
    out = run(a, fake_openai, script(fenced))
    assert [t["topic"] for t in out["topics"]] == ["Floods"]


def test_group_and_summarize_bad_chunk_fallback_contains_exactly_that_chunk(fake_openai):
    a = arts(12)
    state = {"n": 0}

    def grp(kw):
        state["n"] += 1
        return "garbage" if state["n"] == 1 else grouping(("Second", a[10:]))

    out = run(a, fake_openai, script(grp))
    fallback = next(t for t in out["topics"] if t["topic"] == "Articles Group 1")
    assert [x["link"] for x in fallback["articles"]] == [x["link"] for x in a[:10]]
    second = next(t for t in out["topics"] if t["topic"] == "Second")
    assert [x["link"] for x in second["articles"]] == [x["link"] for x in a[10:]]
    assert len(flat_links(out)) == 12


def test_group_and_summarize_summary_exception_uses_placeholder(fake_openai):
    a = arts(2)
    out = run(a, fake_openai, script(grouping(("Floods", a)), summary=lambda kw: RuntimeError("x")))
    assert out["topics"][0]["summary"] == "A collection of 2 articles about Floods."


def test_group_and_summarize_empty_summary_uses_placeholder(fake_openai):
    a = arts(1)
    out = run(a, fake_openai, script(grouping(("Floods", a)), summary=""))
    assert out["topics"][0]["summary"] == "A collection of 1 articles about Floods."


def test_group_and_summarize_summary_cleanup_strips_label_and_newlines(fake_openai):
    a = arts(1)
    out = run(a, fake_openai, script(grouping(("F", a)), summary="Summary: Line one.\n\nLine two."))
    assert out["topics"][0]["summary"] == "Line one. Line two."


@pytest.mark.xfail(strict=True, reason='BUG: empty-summary check runs before the cleanup regex, so a reply of "Summary:" ends as ""')
def test_group_and_summarize_label_only_summary_is_never_empty(fake_openai):
    a = arts(1)
    out = run(a, fake_openai, script(grouping(("F", a)), summary="Summary:"))
    assert out["topics"][0]["summary"].strip() != ""


@pytest.mark.xfail(strict=True, reason="BUG: wrong-shaped grouping JSON raises AttributeError outside any try")
@pytest.mark.parametrize("content", [
    json.dumps({"topics": ["x"]}),
    json.dumps({"topics": [{"topic": "T", "articles": ["t"]}]}),
])
def test_group_and_summarize_wrong_shape_grouping_does_not_raise(fake_openai, content):
    a = arts(2)
    out = run(a, fake_openai, script(content))
    assert sorted(flat_links(out)) == sorted(x["link"] for x in a)


@pytest.mark.xfail(strict=True, reason="BUG: two input articles sharing a link both appear in output (one grounded, one as leftover)")
def test_group_and_summarize_duplicate_link_appears_once(fake_openai):
    a = [{"title": "First", "link": "http://x.test/dup", "summary": "s"},
         {"title": "Second", "link": "http://x.test/dup", "summary": "s"}]
    out = run(a, fake_openai, script(grouping(("T", a))))
    assert flat_links(out).count("http://x.test/dup") == 1


@pytest.mark.parametrize(
    "gm,sm,gcap,scap",
    [("gpt-5-mini", "gpt-6-luna", 16000, 4000), ("gpt-4o-mini", "gpt-4.1-nano", 2000, 400),
     ("gpt-4o-mini", "gpt-5.4-nano", 2000, 4000)],
)
def test_group_and_summarize_caps_follow_model_family(fake_openai, gm, sm, gcap, scap):
    a = arts(1)
    run(a, fake_openai, script(grouping(("T", a))), gm=gm, sm=sm)
    group_call = next(c for c in fake_openai.calls if "response_format" in c)
    summary_call = next(c for c in fake_openai.calls if "response_format" not in c)
    assert group_call["max_completion_tokens"] == gcap and group_call["model"] == gm
    assert summary_call["max_completion_tokens"] == scap and summary_call["model"] == sm
    assert group_call["response_format"] == {"type": "json_object"}


def test_group_and_summarize_summary_prompt_uses_at_most_five_articles(fake_openai):
    a = arts(8)
    run(a, fake_openai, script(grouping(("T", a))))
    prompt = next(c for c in fake_openai.calls if "response_format" not in c)["messages"][1]["content"]
    assert prompt.count("Title: ") == 5


def _fmt(msgs):
    return "\n=====\n".join(f"[{m['role']}]\n{m['content']}" for m in msgs)


@pytest.mark.snapshot
def test_group_and_summarize_prompt_snapshots(fake_openai):
    a = [{"title": "Flood hits Riverton", "link": "http://x.test/1", "summary": "Rain caused a flood."},
         {"title": "Quake near Lakeside", "link": "http://x.test/2", "summary": ""}]
    run(a, fake_openai, script(grouping(("Disasters", a))))
    group_call = next(c for c in fake_openai.calls if "response_format" in c)
    summary_call = next(c for c in fake_openai.calls if "response_format" not in c)
    check_snapshot("group_prompt", _fmt(group_call["messages"]))
    check_snapshot("summarize_prompt", _fmt(summary_call["messages"]))
