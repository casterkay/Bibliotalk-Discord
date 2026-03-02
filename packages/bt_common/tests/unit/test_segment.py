import json
import logging

from bt_common.logging import JsonFormatter, set_correlation_id


def test_json_formatter_includes_correlation_id() -> None:
    formatter = JsonFormatter()
    set_correlation_id("cid-123")
    record = logging.LogRecord(
        name="bt_common.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    payload = json.loads(formatter.format(record))
    assert payload["message"] == "hello"
    assert payload["correlation_id"] == "cid-123"
    assert payload["logger"] == "bt_common.test"
