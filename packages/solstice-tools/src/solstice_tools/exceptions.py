"""Custom exceptions for solstice-tools."""


class SolsticeError(Exception):
    """Base exception for all solstice-tools errors."""

    pass


class PoseProcessingError(SolsticeError):
    """Base exception for pose processing errors."""

    pass


class NormalizationError(PoseProcessingError):
    """Raised when pose normalization fails."""

    pass


class InvalidDataError(PoseProcessingError):
    """Raised when input data is invalid or malformed."""

    pass
