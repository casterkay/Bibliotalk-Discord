from uuid import uuid4

from bt_common.logging import JsonFormatter, get_request_logger


def test_get_request_logger_is_idempotent_and_json_formatted() -> None:
    name = f"bt_common.logger.{uuid4()}"
    logger_a = get_request_logger(name)
    logger_b = get_request_logger(name)

    assert logger_a is logger_b
    assert len(logger_a.handlers) == 1
    assert isinstance(logger_a.handlers[0].formatter, JsonFormatter)
