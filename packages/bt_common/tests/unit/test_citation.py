from bt_common.exceptions import (
    AgentNotFoundError,
    CitationValidationError,
    EMOSConnectionError,
    EMOSError,
    EMOSNotFoundError,
    EMOSValidationError,
    VoiceSessionError,
)


def test_emos_exception_hierarchy() -> None:
    assert issubclass(EMOSConnectionError, EMOSError)
    assert issubclass(EMOSNotFoundError, EMOSError)
    assert issubclass(EMOSValidationError, EMOSError)


def test_domain_exceptions_are_constructible() -> None:
    assert str(AgentNotFoundError("agent missing")) == "agent missing"
    assert str(CitationValidationError("bad citation")) == "bad citation"
    assert str(VoiceSessionError("invalid state")) == "invalid state"
