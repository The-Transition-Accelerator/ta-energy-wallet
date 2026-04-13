class InputParameterTableError(ValueError):
    """Raised when an input parameter table is malformed or fails validation."""


class InputParameterJoinError(ValueError):
    """Raised when input parameter tables cannot be matched to expanded archetypes."""
