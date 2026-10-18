# Unit tests

Run from the repo root:

    python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
    .venv/bin/python -m pytest

`pytest.ini` puts `src/` on the path and limits collection to `tests/`.
Nothing here touches the network: `conftest.py` provides `FakeOpenAI`
(patched over `llm_filter.OpenAI` and `summarizer.OpenAI`), `FakeHTTP`
(patched over `requests.get/post`), and `workdir` fixtures that chdir into
a temp directory so `data/` and `logs/` never touch the repo.

Known bugs are pinned with `@pytest.mark.xfail(strict=True, reason="BUG: ...")`.
They fail today and turn into errors (XPASS strict) when the bug is fixed, which
is the cue to delete the marker.

Prompt text for the filter, grouping, and summary calls is snapshotted in
`tests/snapshots/*.txt`. After an intentional prompt edit, regenerate with
`UPDATE_SNAPSHOTS=1 .venv/bin/python -m pytest -m snapshot` and review the diff.
