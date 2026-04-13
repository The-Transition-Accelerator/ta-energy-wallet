"""Input-set validation orchestrator backed by pipeline validators.

This module intentionally does not duplicate validation rules. It delegates to
the existing Step 1/2/3 loaders, table validators, and join validators, then
maps raised exceptions into a unified list of ``ValidationIssue`` objects.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .alternative_configurations import (
    AlternativeConfigJoinError,
    AlternativeConfigTableError,
    build_expanded_archetype_table,
    discover_alternative_configuration_files,
    load_alternative_configuration_table,
)
from .archetypes import (
    ArchetypeJoinError,
    ArchetypeTableError,
    discover_archetype_files,
    load_all_archetype_tables,
    load_archetype_table,
    merge_archetypes,
)
from .input_parameters import (
    InputParameterJoinError,
    InputParameterTableError,
    build_model_input_table,
    discover_input_parameter_files,
    load_input_parameter_table,
)


Severity = Literal["error", "warning"]
Category = Literal["archetypes", "alternative_configurations", "input_parameters", "cross-step"]


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    category: Category
    file: str
    rule: str
    message: str


def _issue(
    *,
    category: Category,
    file: str,
    rule: str,
    message: str,
    severity: Severity = "error",
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,
        category=category,
        file=file,
        rule=rule,
        message=message,
    )


def _validate_archetypes(inputs_root: Path, tolerance: float) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    archetypes_dir = inputs_root / "archetypes"
    try:
        files = discover_archetype_files(archetypes_dir)
    except ArchetypeTableError as exc:
        return [
            _issue(
                category="archetypes",
                file="archetypes/",
                rule="discovery",
                message=str(exc),
            )
        ]

    for path in files:
        try:
            load_archetype_table(path, tolerance=tolerance)
        except ArchetypeTableError as exc:
            issues.append(
                _issue(
                    category="archetypes",
                    file=path.name,
                    rule="table_validation",
                    message=str(exc),
                )
            )
    return issues


def _validate_alt_configs(inputs_root: Path, tolerance: float) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    alt_dir = inputs_root / "alternative_configurations"
    try:
        files = discover_alternative_configuration_files(alt_dir)
    except AlternativeConfigTableError as exc:
        return [
            _issue(
                category="alternative_configurations",
                file="alternative_configurations/",
                rule="discovery",
                message=str(exc),
            )
        ]

    for path in files:
        try:
            load_alternative_configuration_table(path, tolerance=tolerance)
        except AlternativeConfigTableError as exc:
            issues.append(
                _issue(
                    category="alternative_configurations",
                    file=path.name,
                    rule="table_validation",
                    message=str(exc),
                )
            )
    return issues


def _validate_input_params(
    inputs_root: Path,
    *,
    expanded_columns: set[str] | None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    input_params_dir = inputs_root / "input_parameters"
    try:
        files = discover_input_parameter_files(input_params_dir)
    except InputParameterTableError as exc:
        return [
            _issue(
                category="input_parameters",
                file="input_parameters/",
                rule="discovery",
                message=str(exc),
            )
        ]

    for path in files:
        try:
            load_input_parameter_table(
                path,
                expanded_columns=expanded_columns,
            )
        except InputParameterTableError as exc:
            issues.append(
                _issue(
                    category="input_parameters",
                    file=path.name,
                    rule="table_validation",
                    message=str(exc),
                )
            )
    return issues


def _build_expanded_columns_for_step3(
    inputs_root: Path,
    tolerance: float,
) -> tuple[set[str] | None, ValidationIssue | None]:
    """Build Step 2 expanded column set used by Step 3 spec inference."""
    try:
        tables_list, specs_list = load_all_archetype_tables(
            inputs_root / "archetypes",
            tolerance=tolerance,
        )
        tables = {spec.path.stem: t for t, spec in zip(tables_list, specs_list)}
        specs = {s.path.stem: s for s in specs_list}
        baseline = merge_archetypes(
            tables,
            specs,
            keep_provenance_shares=False,
            tolerance=tolerance,
        )
        expanded = build_expanded_archetype_table(
            baseline,
            inputs_root=inputs_root,
            tolerance=tolerance,
        )
        return set(expanded.columns), None
    except (
        ArchetypeTableError,
        ArchetypeJoinError,
        AlternativeConfigTableError,
        AlternativeConfigJoinError,
    ) as exc:
        return None, _issue(
            category="cross-step",
            file="pipeline",
            rule="step2_failed_for_step3_inference",
            message=(
                "Could not build Step 2 expanded schema required for Step 3 "
                f"table inference: {exc}"
            ),
        )


def _validate_full_pipeline(inputs_root: Path, tolerance: float) -> list[ValidationIssue]:
    """Run Step 1-3 using production pipeline code and collect failures."""
    issues: list[ValidationIssue] = []

    try:
        tables_list, specs_list = load_all_archetype_tables(
            inputs_root / "archetypes",
            tolerance=tolerance,
        )
        tables = {spec.path.stem: t for t, spec in zip(tables_list, specs_list)}
        specs = {s.path.stem: s for s in specs_list}
        baseline = merge_archetypes(
            tables,
            specs,
            keep_provenance_shares=False,
            tolerance=tolerance,
        )
    except (ArchetypeTableError, ArchetypeJoinError) as exc:
        return [
            _issue(
                category="cross-step",
                file="pipeline",
                rule="step1_failed",
                message=str(exc),
            )
        ]

    try:
        # This path runs Step 2 table validators + join/output validators.
        expanded = build_expanded_archetype_table(
            baseline,
            inputs_root=inputs_root,
            tolerance=tolerance,
        )
    except (AlternativeConfigTableError, AlternativeConfigJoinError) as exc:
        return [
            _issue(
                category="cross-step",
                file="pipeline",
                rule="step2_failed",
                message=str(exc),
            )
        ]

    try:
        # This path runs Step 3 table validators + cross-table/final output validation.
        build_model_input_table(
            expanded,
            inputs_root=inputs_root,
        )
    except (InputParameterTableError, InputParameterJoinError) as exc:
        return [
            _issue(
                category="cross-step",
                file="pipeline",
                rule="step3_failed",
                message=str(exc),
            )
        ]

    return issues


def validate_input_set(
    inputs_root: Path,
    *,
    tolerance: float = 1e-3,
    run_pipeline: bool = True,
) -> list[ValidationIssue]:
    """Validate an input set by orchestrating pipeline-native validators."""
    if not inputs_root.is_dir():
        return [
            _issue(
                category="cross-step",
                file=str(inputs_root),
                rule="not_found",
                message=f"Input set directory not found: {inputs_root}",
            )
        ]

    issues: list[ValidationIssue] = []
    issues.extend(_validate_archetypes(inputs_root, tolerance))
    issues.extend(_validate_alt_configs(inputs_root, tolerance))

    expanded_columns, step3_context_issue = _build_expanded_columns_for_step3(
        inputs_root,
        tolerance,
    )
    if step3_context_issue is not None:
        issues.append(step3_context_issue)

    issues.extend(
        _validate_input_params(
            inputs_root,
            expanded_columns=expanded_columns,
        )
    )

    if run_pipeline:
        issues.extend(_validate_full_pipeline(inputs_root, tolerance))

    return issues
