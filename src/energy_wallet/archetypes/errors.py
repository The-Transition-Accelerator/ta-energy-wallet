class ArchetypeTableError(ValueError):
    """Raised when an individual archetype table is malformed or fails validation."""


class ArchetypeJoinError(ValueError):
    """Raised when tables cannot be joined consistently (missing conditioning cols, etc.)."""
