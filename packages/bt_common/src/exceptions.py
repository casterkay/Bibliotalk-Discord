"""Typed domain exceptions for agent workflows."""


class EMOSError(Exception):
    """Base exception for EMOS-related failures."""


class EMOSConnectionError(EMOSError):
    """Raised when connecting to EMOS fails after retries."""


class EMOSNotFoundError(EMOSError):
    """Raised when EMOS reports requested entity not found."""


class EMOSValidationError(EMOSError):
    """Raised when request data fails EMOS validation."""


class CitationValidationError(Exception):
    """Raised when citation payload is malformed."""


class AgentNotFoundError(Exception):
    """Raised when a requested agent does not exist."""


class VoiceSessionError(Exception):
    """Raised when a voice-session operation is invalid.

    Note: Voice is out of scope for the current MVP, but this exception is kept
    for backwards compatibility with older test suites.
    """
