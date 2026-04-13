from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class AlternativeConfigTableSpec:
    path: Path
    conditioning_cols: List[str]      # 1+ baseline/alt variables required by Step 2
    new_alt_var_col: str              # exactly one, must begin with "alt_"
    scenario_cols: List[str]          # 0+ scenario dimensions
    year_col: Optional[str]           # None or "year"
    share_col: str                    # "adoption_share" by default
