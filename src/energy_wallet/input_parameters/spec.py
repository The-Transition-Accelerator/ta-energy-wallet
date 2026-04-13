from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class InputParameterTableSpec:
    path: Path
    join_cols: List[str]                # archetype/alt/scenario/year cols used for matching
    input_value_cols: List[str]         # one or more parameter columns
    year_col: Optional[str]             # None or "year"
    direct_join_cols: List[str] = field(default_factory=list)    # cols that exist in expanded table
    tech_type_join_cols: List[str] = field(default_factory=list) # cols that trigger multi-lookup
    is_multi_lookup: bool = False       # True if any tech_type_join_cols
