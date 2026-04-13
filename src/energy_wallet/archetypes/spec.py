from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class ArchetypeTableSpec:
    path: Path
    conditioning_cols: List[str]         # 0+ optional
    new_var_col: str                     # exactly 1 required
    year_col: Optional[str]              # None or "year"
    share_col: str                       # "population_share"
