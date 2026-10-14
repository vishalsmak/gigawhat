import json

import pytest
import structlog
from structlog.contextvars import bound_contextvars

from gigawhat.observability.logs import WITHHELD, configure_logging, withhold_content


def test_typed_content_is_withheld_from_a_log_line() -> None:
    event = withhold_content(None, "info", {"event": "x", "question": "Call me on 07700 900461"})

    assert event["question"] == WITHHELD


def test_log_line_is_json_with_the_bound_context(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")

    with bound_contextvars(thread_id="t-1"):
        structlog.get_logger().info("question.received")

    line = json.loads(capsys.readouterr().err)
    assert (line["event"], line["thread_id"], line["level"]) == ("question.received", "t-1", "info")


def test_events_below_the_level_are_not_written(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("WARNING")

    structlog.get_logger().info("workflow.step")

    assert capsys.readouterr().err == ""
