import pytest

from summarizer import sanitize_json_string, validate_json


def test_sanitize_json_string_strips_json_fence():
    assert sanitize_json_string('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_sanitize_json_string_strips_bare_fence():
    assert sanitize_json_string('```\n{"a": 1}\n```') == '{"a": 1}'


def test_sanitize_json_string_leaves_unfenced_input_unchanged():
    assert sanitize_json_string('  {"a": 1}  ') == '{"a": 1}'


def test_sanitize_json_string_does_not_touch_interior_quotes():
    raw = '{"a": "he said \\"hi\\" twice"}'
    assert sanitize_json_string(raw) == raw


def test_validate_json_accepts_plain_json():
    assert validate_json('{"topics": []}') == (True, {"topics": []})


def test_validate_json_repairs_fenced_json():
    assert validate_json('```json\n{"topics": []}\n```') == (True, {"topics": []})


def test_validate_json_preserves_interior_quotes():
    ok, parsed = validate_json('{"t": "he said \\"hi\\""}')
    assert ok and parsed["t"] == 'he said "hi"'


@pytest.mark.parametrize("bad", ["not json", '{"a": ', "```json\nnope\n```"])
def test_validate_json_rejects_garbage_with_message(bad):
    ok, msg = validate_json(bad)
    assert ok is False and isinstance(msg, str)
