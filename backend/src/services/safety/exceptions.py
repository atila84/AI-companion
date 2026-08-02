"""Exceptions raised by the safety layer.

Deliberately not a `ProviderError` subclass: a safety interception is a
policy decision made about the conversation, not a backend/provider failure.
"""


class SafetyInterventionError(Exception):
    """Raised when `UncensoredSafetyGuard` blocks a request or a reply."""
