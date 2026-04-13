"""Multi-lookup join logic for input parameter tables.

This module handles the mapping between raw input parameter table columns and the
expanded archetype columns that contain slot-expanded and base/alt variants.

The core problem:
  An input parameter table (e.g. vehicle_costs.csv) has a key column like
  ``vehicle_type`` and value columns like ``vehicle_purchase_cost``.  But the
  expanded archetype table has slot-expanded columns like ``vehicle_1_type``,
  ``vehicle_2_type``, ``alt_vehicle_1_type``, ``alt_vehicle_2_type``.

  The multi-lookup system generates a *plan* of individual lookups that:
    1. Map the raw key ``vehicle_type`` to a specific slot/alt column.
    2. Rename the resulting value columns to include the slot number and
       ``_base`` / ``_alt`` suffix.

Algorithm overview:
  1. For each join column in the input table, detect whether it maps directly
     to an expanded column (passthrough), maps via slot expansion (e.g.
     ``vehicle_type`` -> ``vehicle_1_type``, ``vehicle_2_type``), or maps via
     a simple alt variant (e.g. ``heating_system`` -> ``alt_heating_system``).
  2. If all join columns are direct matches AND the value columns already carry
     ``_base`` / ``_alt`` suffixes, the table is a *passthrough* -- no
     multi-lookup is needed.
  3. Otherwise, generate one ``LookupSpec`` per (slot, suffix) combination.
     Each spec describes how to remap the join columns and rename the value
     columns for a single left-join operation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TechTypeExpansion:
    """Describes how a single input join column expands into slot variants.

    Example: input_col="vehicle_category" with 2 slots produces
      slot_variants=["vehicle_1_category", "vehicle_2_category"]
      alt_variants=["alt_vehicle_1_category", "alt_vehicle_2_category"]

    ``alt_variants`` is a per-slot list aligned with ``slot_variants``.
    Each entry is either the alt column name or ``None`` if that slot has
    no alt counterpart.  For example, if only vehicle slot 1 has an alt
    config but slot 2 does not (because it is always ``none``):

      slot_variants=["vehicle_1_category", "vehicle_2_category"]
      alt_variants=["alt_vehicle_1_category", None]

    When *all* entries are ``None`` (no alt counterparts at all), the plan
    builder uses the base slot columns for alt lookups, because the column
    does not change between baseline and alternative -- only a companion
    column does.
    """

    input_col: str
    slot_variants: list[str]
    alt_variants: list[Optional[str]]


@dataclass(frozen=True)
class LookupSpec:
    """One concrete lookup operation to execute against the merged DataFrame.

    ``join_col_mapping`` maps *input table* column names to the *expanded*
    column names to use for the left-join.

    ``value_col_rename`` maps *input table* value column names to the final
    output column names (with slot number and _base/_alt suffix).

    ``suffix`` is "base" or "alt", indicating which scenario side this lookup
    produces.
    """

    join_col_mapping: dict[str, str]
    value_col_rename: dict[str, str]
    suffix: str


@dataclass(frozen=True)
class LookupPlan:
    """Complete plan for attaching one input parameter table.

    ``table_name`` is the stem of the CSV file (e.g. "vehicle_costs").

    ``direct_join_cols`` are input columns that exist verbatim in the expanded
    table (e.g. ``climate_zone``, ``dwelling_type``).

    ``tech_type_expansions`` describe columns that trigger slot or alt
    expansion.

    ``lookups`` is the ordered list of LookupSpec operations to execute.

    ``is_passthrough`` is True when no multi-lookup expansion is needed: all
    join cols are direct and the value columns already carry _base/_alt
    suffixes.
    """

    table_name: str
    direct_join_cols: list[str]
    tech_type_expansions: list[TechTypeExpansion]
    lookups: list[LookupSpec]
    is_passthrough: bool


# ---------------------------------------------------------------------------
# Slot / alt variant detection helpers
# ---------------------------------------------------------------------------

def _detect_slot_variants(
    input_col: str,
    expanded_columns: set[str],
) -> Optional[TechTypeExpansion]:
    """Detect slot-expanded variants of *input_col* among *expanded_columns*.

    The algorithm splits *input_col* at every ``_`` boundary to find a
    (prefix, suffix) pair such that ``{prefix}_{N}_{suffix}`` exists in
    *expanded_columns* for at least one digit N.

    Example::

        input_col = "vehicle_type"
        prefix candidates: [("vehicle", "type")]
        Matches: "vehicle_1_type", "vehicle_2_type"

    For ``heating_system`` the candidates would be
    ``("heating", "system")``.  If ``heating_1_system`` does not exist in
    *expanded_columns*, no match is found -- which is the correct behaviour
    because ``heating_system`` is a non-slot tech type.

    Returns None if no slot variants are detected.
    """
    parts = input_col.split("_")
    if len(parts) < 2:
        return None

    # Try every possible split point (prefix is parts[:i], suffix is parts[i:])
    for i in range(1, len(parts)):
        prefix = "_".join(parts[:i])
        suffix = "_".join(parts[i:])

        # Gather all matching slot columns
        slot_variants: list[tuple[int, str]] = []
        for col in sorted(expanded_columns):
            # Pattern: {prefix}_{digit(s)}_{suffix}
            pattern = re.compile(
                r"^" + re.escape(prefix) + r"_(\d+)_" + re.escape(suffix) + r"$"
            )
            m = pattern.match(col)
            if m:
                slot_variants.append((int(m.group(1)), col))

        if not slot_variants:
            continue

        # Sort by slot number
        slot_variants.sort(key=lambda x: x[0])
        slot_cols = [col for _, col in slot_variants]

        # Build per-slot alt mapping.  Each entry is the alt column name
        # if it exists, or None if that slot has no alt counterpart.
        # Partial matches are valid (e.g. slot 1 has an alt config but
        # slot 2 is always "none" and has no alt config).
        alt_cols: list[Optional[str]] = []
        for slot_col in slot_cols:
            alt_col = f"alt_{slot_col}"
            if alt_col in expanded_columns:
                alt_cols.append(alt_col)
            else:
                alt_cols.append(None)

        return TechTypeExpansion(
            input_col=input_col,
            slot_variants=slot_cols,
            alt_variants=alt_cols,
        )

    return None


def _detect_alt_variant(
    input_col: str,
    expanded_columns: set[str],
) -> Optional[str]:
    """Check whether ``alt_{input_col}`` exists in *expanded_columns*.

    This handles non-slot technology types like ``heating_system`` where the
    expanded table has both ``heating_system`` and ``alt_heating_system``.

    Returns the alt column name, or None if not found.
    """
    alt_col = f"alt_{input_col}"
    if alt_col in expanded_columns:
        return alt_col
    return None


# ---------------------------------------------------------------------------
# Value-column renaming for slot expansion
# ---------------------------------------------------------------------------

def _rename_value_col_for_slot(
    value_col: str,
    input_key_col: str,
    slot_variant: str,
) -> str:
    """Produce the output column name for a value column under slot expansion.

    Naming convention: insert the slot number after the first word of the
    value column name.

    Examples::

        value_col="vehicle_purchase_cost", slot_variant="vehicle_1_type"
          -> "vehicle_1_purchase_cost"

        value_col="ev_efficiency_factor", slot_variant="vehicle_1_type"
          -> "ev_1_efficiency_factor"

        value_col="ev_pct_charged_home", slot_variant="vehicle_2_type"
          -> "ev_2_pct_charged_home"

    The slot number N is extracted from *slot_variant* (the digit between the
    first and second underscores after prefix).
    """
    # Extract slot number from the slot_variant string
    m = re.search(r"_(\d+)_", slot_variant)
    if not m:
        raise ValueError(
            f"Cannot extract slot number from slot_variant '{slot_variant}'"
        )
    slot_num = m.group(1)

    # Insert slot number after first word of value_col
    idx = value_col.find("_")
    if idx == -1:
        # Single-word value column (unlikely but handle gracefully)
        return f"{value_col}_{slot_num}"

    first_word = value_col[:idx]
    rest = value_col[idx:]  # includes the leading underscore
    return f"{first_word}_{slot_num}{rest}"


# ---------------------------------------------------------------------------
# Plan builder
# ---------------------------------------------------------------------------

def build_lookup_plan(
    table_name: str,
    input_join_cols: list[str],
    input_value_cols: list[str],
    expanded_columns: set[str],
) -> LookupPlan:
    """Build a complete lookup plan for one input parameter table.

    Parameters
    ----------
    table_name : str
        Name of the table (usually the CSV file stem).
    input_join_cols : list[str]
        The join/key columns declared by the input table (e.g. ["vehicle_type",
        "climate_zone"]).
    input_value_cols : list[str]
        The value/parameter columns in the input table (e.g.
        ["vehicle_purchase_cost", "vehicle_assumed_life"]).
    expanded_columns : set[str]
        All column names present in the expanded archetype DataFrame.

    Returns
    -------
    LookupPlan
        A plan describing all lookup operations needed to attach this table.

    Raises
    ------
    ValueError
        If a join column cannot be resolved against the expanded columns.
    """
    direct_join_cols: list[str] = []
    tech_type_expansions: list[TechTypeExpansion] = []

    # Non-slot tech-type columns: columns that are direct matches but also
    # have an alt variant (e.g. heating_system / alt_heating_system)
    non_slot_tech_cols: dict[str, str] = {}  # input_col -> alt_col

    for col in input_join_cols:
        if col in expanded_columns:
            # Direct match -- also check for alt variant
            alt_col = _detect_alt_variant(col, expanded_columns)
            direct_join_cols.append(col)
            if alt_col is not None:
                non_slot_tech_cols[col] = alt_col
        else:
            # Try slot expansion
            expansion = _detect_slot_variants(col, expanded_columns)
            if expansion is not None:
                tech_type_expansions.append(expansion)
            else:
                raise ValueError(
                    f"{table_name}: join column '{col}' cannot be resolved. "
                    f"It is not in expanded_columns and no slot variants were "
                    f"detected."
                )

    # Determine passthrough vs multi-lookup.
    #
    # A table is passthrough (single join, no remapping) when:
    #   - No tech-type join columns were detected (no slot expansion, no alt
    #     variants among join keys).
    #
    # A table needs multi-lookup when it has tech-type join columns AND its
    # value columns do NOT already carry _base/_alt suffixes.
    #
    # Special case: if the table has tech-type join cols but value columns
    # ALREADY have _base/_alt (e.g. a table was authored with explicit
    # suffixes), we still treat it as passthrough since the suffixes indicate
    # the joins are pre-resolved.
    has_tech_types = bool(tech_type_expansions) or bool(non_slot_tech_cols)
    value_cols_have_suffixes = bool(input_value_cols) and all(
        c.endswith("_base") or c.endswith("_alt") for c in input_value_cols
    )
    is_passthrough = (not has_tech_types) or value_cols_have_suffixes

    if is_passthrough:
        # Single passthrough lookup -- no remapping needed
        return LookupPlan(
            table_name=table_name,
            direct_join_cols=direct_join_cols,
            tech_type_expansions=[],
            lookups=[],
            is_passthrough=True,
        )

    # Build multi-lookup specs
    lookups: list[LookupSpec] = []

    # Separate direct join cols into "pure direct" (no tech-type aspect) and
    # "non-slot tech" cols.
    pure_direct_cols = [c for c in direct_join_cols if c not in non_slot_tech_cols]

    if tech_type_expansions:
        # Slot-based expansion: iterate over each expansion's slots.
        #
        # When a table has multiple slot-expanded columns (e.g. vehicle_type
        # and vehicle_category), they must share the same slot structure.
        # The "primary" expansion (the one with alt variants, or the first
        # one if none have alts) drives the slot iteration and value column
        # renaming.  All other expansions are "companion" columns that are
        # mapped alongside the primary for each lookup.
        #
        # For the base lookup, every expansion maps to its base slot variant.
        # For the alt lookup, expansions WITH alt variants map to the alt
        # variant, expansions WITHOUT alt variants map back to the base slot
        # variant (because that column doesn't change between base and alt).

        # Choose the primary expansion: prefer the one with any alt variants
        # (it drives value column renaming), otherwise use the first.
        primary = None
        companions: list[TechTypeExpansion] = []
        for exp in tech_type_expansions:
            has_any_alts = any(a is not None for a in exp.alt_variants)
            if has_any_alts and primary is None:
                primary = exp
            else:
                companions.append(exp)
        if primary is None:
            # No expansion has alt variants -- use the first one as primary
            primary = companions.pop(0)

        num_slots = len(primary.slot_variants)

        for slot_idx in range(num_slots):
            slot_col = primary.slot_variants[slot_idx]

            # Base lookup: map all expansion input keys -> base slot columns
            base_join_mapping: dict[str, str] = {}
            base_join_mapping[primary.input_col] = slot_col
            for comp in companions:
                base_join_mapping[comp.input_col] = comp.slot_variants[slot_idx]
            for dc in pure_direct_cols:
                base_join_mapping[dc] = dc
            # Non-slot tech cols map to themselves for base
            for tc in non_slot_tech_cols:
                base_join_mapping[tc] = tc

            base_value_rename: dict[str, str] = {}
            for vc in input_value_cols:
                renamed = _rename_value_col_for_slot(vc, primary.input_col, slot_col)
                base_value_rename[vc] = f"{renamed}_base"

            lookups.append(LookupSpec(
                join_col_mapping=base_join_mapping,
                value_col_rename=base_value_rename,
                suffix="base",
            ))

            # Alt lookup: map expansion keys -> alt or base slot columns.
            # For each expansion, use the alt variant for this slot if it
            # exists; otherwise fall back to the base slot column (the
            # column value doesn't change between base and alt for that slot).
            alt_join_mapping: dict[str, str] = {}
            if primary.alt_variants[slot_idx] is not None:
                alt_join_mapping[primary.input_col] = primary.alt_variants[slot_idx]
            else:
                alt_join_mapping[primary.input_col] = slot_col  # unchanged
            for comp in companions:
                if comp.alt_variants[slot_idx] is not None:
                    alt_join_mapping[comp.input_col] = comp.alt_variants[slot_idx]
                else:
                    alt_join_mapping[comp.input_col] = comp.slot_variants[slot_idx]
            for dc in pure_direct_cols:
                alt_join_mapping[dc] = dc
            # Non-slot tech cols map to their alt variant
            for tc, alt_tc in non_slot_tech_cols.items():
                alt_join_mapping[tc] = alt_tc

            alt_value_rename: dict[str, str] = {}
            for vc in input_value_cols:
                renamed = _rename_value_col_for_slot(vc, primary.input_col, slot_col)
                alt_value_rename[vc] = f"{renamed}_alt"

            lookups.append(LookupSpec(
                join_col_mapping=alt_join_mapping,
                value_col_rename=alt_value_rename,
                suffix="alt",
            ))

    elif non_slot_tech_cols:
        # Non-slot tech type expansion only (e.g. heating_system with
        # alt_heating_system but no slot numbers).

        # Base lookup
        base_join_mapping = {}
        for dc in pure_direct_cols:
            base_join_mapping[dc] = dc
        for tc in non_slot_tech_cols:
            base_join_mapping[tc] = tc

        base_value_rename = {}
        for vc in input_value_cols:
            base_value_rename[vc] = f"{vc}_base"

        lookups.append(LookupSpec(
            join_col_mapping=base_join_mapping,
            value_col_rename=base_value_rename,
            suffix="base",
        ))

        # Alt lookup
        alt_join_mapping = {}
        for dc in pure_direct_cols:
            alt_join_mapping[dc] = dc
        for tc, alt_tc in non_slot_tech_cols.items():
            alt_join_mapping[tc] = alt_tc

        alt_value_rename = {}
        for vc in input_value_cols:
            alt_value_rename[vc] = f"{vc}_alt"

        lookups.append(LookupSpec(
            join_col_mapping=alt_join_mapping,
            value_col_rename=alt_value_rename,
            suffix="alt",
        ))

    return LookupPlan(
        table_name=table_name,
        direct_join_cols=direct_join_cols,
        tech_type_expansions=tech_type_expansions,
        lookups=lookups,
        is_passthrough=is_passthrough,
    )
