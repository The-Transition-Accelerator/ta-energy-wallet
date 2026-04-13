class AlternativeConfigTableError(ValueError):
    """Raised when an alternative configuration table is malformed or fails validation."""


class AlternativeConfigJoinError(ValueError):
    """Raised when alternative configuration tables cannot be joined consistently."""
