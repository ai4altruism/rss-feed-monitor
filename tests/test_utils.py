import logging

import pytest

from utils import is_reasoning_model, setup_logger


@pytest.mark.parametrize("model", ["gpt-4o-mini", "gpt-4.1-nano", "gpt-3.5-turbo"])
def test_is_reasoning_model_non_reasoning_families_return_false(model):
    assert is_reasoning_model(model) is False


@pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-5.4-nano", "gpt-6-luna", "o3-mini"])
def test_is_reasoning_model_newer_families_return_true(model):
    assert is_reasoning_model(model) is True


def test_setup_logger_writes_named_logger_lines_to_file(workdir, named_logger_clean):
    logger = setup_logger()

    logger.info("named-logger-line")
    for h in logger.handlers:
        h.flush()

    assert "named-logger-line" in (workdir / "logs" / "app.log").read_text()


@pytest.mark.xfail(
    strict=True,
    reason="BUG: only the named logger is configured, so root-level logging.info lines (all modules) are dropped",
)
def test_setup_logger_root_logging_info_reaches_log_file(workdir, named_logger_clean):
    logger = setup_logger()

    logging.info("root-level-line")
    for h in logger.handlers:
        h.flush()

    assert "root-level-line" in (workdir / "logs" / "app.log").read_text()
