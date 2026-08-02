"""Exceptions raised by the provider layer."""


class ProviderError(Exception):
    """Base class for all provider-layer errors."""


class ProviderConfigError(ProviderError):
    """A provider is misconfigured (e.g. missing credentials)."""


class ProviderAPIError(ProviderError):
    """A provider's underlying backend call failed."""
