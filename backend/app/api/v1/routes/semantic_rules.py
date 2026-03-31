"""API endpoints for semantic rule management - with lazy database loading."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.session import get_db
from app.engine.dataset_generator import AttributeSpec, DatasetGenerator
from app.engine.semantic_rule_engine import (
    SemanticRuleEngine,
    build_deterministic_execution_order,
    filter_rules_by_confidence,
    normalize_conflict_policy,
    sort_rules_by_priority,
    validate_semantic_rules as engine_validate_semantic_rules,
)
from app.engine.semantic_rule_validator import SemanticRuleValidator
from app.services.dataset_repository import DatasetRepository


# ============ PYDANTIC SCHEMAS ============


class SemanticRuleDto(BaseModel):
    """Semantic rule data transfer object."""

    id: str
    type: str
    target: str
    sources: list[str]
    transform: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    priority: int = 1
    constraints: dict[str, Any] | None = None


class SemanticRulesResponseDto(BaseModel):
    """Response containing semantic rules for a dataset."""

    dataset_version_id: uuid.UUID
    rules: list[SemanticRuleDto]
    metadata: dict[str, Any] = Field(default_factory=dict)


class FilterRulesRequestDto(BaseModel):
    """Request to filter rules by confidence."""

    threshold: float = Field(ge=0.0, le=1.0, default=0.7)
    rules: list[SemanticRuleDto] = Field(default_factory=list)


class FilteredRulesResponseDto(BaseModel):
    """Response with filtered and sorted rules."""

    original_count: int
    filtered_count: int
    rules: list[SemanticRuleDto]


class ValidateRulesRequestDto(BaseModel):
    """Request to validate rules against sample data."""

    rules: list[SemanticRuleDto]
    sample_data: list[dict[str, Any]]


class ValidationReportDto(BaseModel):
    """Validation report for semantic rules."""

    validation_score: float
    rules_checked: int
    rules_passed: int
    rules_failed: int
    violations: list[str] = Field(default_factory=list)


class UpsertSemanticRulesRequestDto(BaseModel):
    """Request to upsert semantic rules for a dataset version."""

    rules: list[SemanticRuleDto] = Field(default_factory=list)
    conflict_policy: str = Field(default="priority_wins")


class DryRunRulesRequestDto(BaseModel):
    """Request to run semantic rules in dry-run mode for diagnostics."""

    rules: list[SemanticRuleDto] = Field(default_factory=list)
    conflict_policy: str = Field(default="priority_wins")
    sample_rows: int = Field(default=10, ge=1, le=50)
    seed: int | None = Field(default=None, ge=0)


class DryRunRulesResponseDto(BaseModel):
    """Dry-run response with rule validation, sample output, and diffs."""

    dataset_version_id: uuid.UUID
    sample_rows: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    before: list[dict[str, Any]] = Field(default_factory=list)
    after: list[dict[str, Any]] = Field(default_factory=list)
    changed_cells: list[dict[str, Any]] = Field(default_factory=list)


# ============ ROUTER ============

router = APIRouter(prefix="/rules", tags=["semantic-rules"])


# ============ ENDPOINTS ============


@router.get("/dataset/{dataset_version_id}", response_model=SemanticRulesResponseDto)
async def get_semantic_rules(
    dataset_version_id: uuid.UUID,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SemanticRulesResponseDto:
    """Get semantic rules for a dataset.

    Rules are loaded from dataset_version.config_json.semantic_rules.
    """
    try:
        version = DatasetRepository.get_dataset_version_for_user(
            db=db,
            user_id=current_user.id,
            dataset_version_id=dataset_version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    raw_rules = version.config_json.get("semantic_rules", [])
    if not isinstance(raw_rules, list):
        raw_rules = []
    semantic_settings = version.config_json.get("semantic_rule_settings", {})
    conflict_policy = normalize_conflict_policy(
        (semantic_settings or {}).get("conflict_policy")
    )

    available_columns = [
        attribute.name
        for attribute in DatasetRepository.load_version_attributes(
            db=db,
            dataset_version_id=dataset_version_id,
        )
    ]
    validation = engine_validate_semantic_rules(
        raw_rules,
        available_columns=available_columns,
        conflict_policy=conflict_policy,
    )
    ordered_rules = build_deterministic_execution_order(
        validation["sanitized_rules"],
        conflict_policy=conflict_policy,
    )

    return SemanticRulesResponseDto(
        dataset_version_id=dataset_version_id,
        rules=[SemanticRuleDto.model_validate(rule) for rule in ordered_rules],
        metadata={
            "rule_count": len(ordered_rules),
            "is_valid": bool(validation.get("is_valid", True)),
            "warnings": validation.get("warnings", []),
            "errors": validation.get("errors", []),
            "conflict_policy": conflict_policy,
            "execution_order": [
                str(rule.get("id", "")) for rule in ordered_rules if rule.get("id")
            ],
            "conflict_resolution": validation.get("conflict_resolution", {}),
            "source": "dataset_version.config_json.semantic_rules",
        },
    )


@router.put("/dataset/{dataset_version_id}", response_model=SemanticRulesResponseDto)
async def upsert_semantic_rules(
    dataset_version_id: uuid.UUID,
    request: UpsertSemanticRulesRequestDto,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SemanticRulesResponseDto:
    """Validate and upsert semantic rules for a dataset version."""
    try:
        DatasetRepository.get_dataset_version_for_user(
            db=db,
            user_id=current_user.id,
            dataset_version_id=dataset_version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    available_columns = [
        attribute.name
        for attribute in DatasetRepository.load_version_attributes(
            db=db,
            dataset_version_id=dataset_version_id,
        )
    ]
    conflict_policy = normalize_conflict_policy(request.conflict_policy)
    raw_rules = [rule.model_dump(mode="json") for rule in request.rules]
    validation = engine_validate_semantic_rules(
        raw_rules,
        available_columns=available_columns,
        conflict_policy=conflict_policy,
    )

    if not validation.get("is_valid", False):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Semantic rule validation failed",
                "errors": validation.get("errors", []),
                "warnings": validation.get("warnings", []),
            },
        )

    ordered_rules = build_deterministic_execution_order(
        validation["sanitized_rules"],
        conflict_policy=conflict_policy,
    )
    try:
        version = DatasetRepository.update_dataset_version_semantic_rules(
            db=db,
            user_id=current_user.id,
            dataset_version_id=dataset_version_id,
            semantic_rules=ordered_rules,
            conflict_policy=conflict_policy,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    stored_rules = version.config_json.get("semantic_rules", [])
    if not isinstance(stored_rules, list):
        stored_rules = []

    return SemanticRulesResponseDto(
        dataset_version_id=dataset_version_id,
        rules=[SemanticRuleDto.model_validate(rule) for rule in stored_rules],
        metadata={
            "rule_count": len(stored_rules),
            "is_valid": True,
            "warnings": validation.get("warnings", []),
            "errors": validation.get("errors", []),
            "conflict_policy": conflict_policy,
            "execution_order": [
                str(rule.get("id", "")) for rule in stored_rules if rule.get("id")
            ],
            "conflict_resolution": validation.get("conflict_resolution", {}),
            "updated": True,
        },
    )


@router.post("/filter", response_model=FilteredRulesResponseDto)
async def filter_semantic_rules(
    request: FilterRulesRequestDto,
    current_user: User = Depends(get_current_user),
) -> FilteredRulesResponseDto:
    """Filter semantic rules by confidence threshold."""
    try:
        rules_to_filter = [rule.model_dump(mode="json") for rule in request.rules]

        # Filter by confidence
        filtered = filter_rules_by_confidence(rules_to_filter, request.threshold)

        # Sort by priority
        sorted_rules = sort_rules_by_priority(filtered)

        return FilteredRulesResponseDto(
            original_count=len(rules_to_filter),
            filtered_count=len(sorted_rules),
            rules=[SemanticRuleDto(**rule) for rule in sorted_rules],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error filtering rules: {str(e)}")


@router.post("/validate", response_model=ValidationReportDto)
async def validate_semantic_rules_endpoint(
    request: ValidateRulesRequestDto,
    current_user: User = Depends(get_current_user),
) -> ValidationReportDto:
    """Validate semantic rules against sample data."""
    try:
        import pandas as pd

        df = pd.DataFrame(request.sample_data)
        rules = [rule.dict() for rule in request.rules]

        validator = SemanticRuleValidator()
        report = validator.validate_rules(df, rules)

        return ValidationReportDto(
            validation_score=report.get("validation_score", 0.0),
            rules_checked=report.get("rules_checked", 0),
            rules_passed=report.get("rules_passed", 0),
            rules_failed=report.get("rules_failed", 0),
            violations=report.get("violations", []),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error validating rules: {str(e)}")


@router.post(
    "/dataset/{dataset_version_id}/dry-run", response_model=DryRunRulesResponseDto
)
async def dry_run_semantic_rules(
    dataset_version_id: uuid.UUID,
    request: DryRunRulesRequestDto,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DryRunRulesResponseDto:
    """Validate and simulate semantic rules on deterministic sample rows."""
    try:
        version = DatasetRepository.get_dataset_version_for_user(
            db=db,
            user_id=current_user.id,
            dataset_version_id=dataset_version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    attributes = DatasetRepository.load_version_attributes(
        db=db,
        dataset_version_id=dataset_version_id,
    )
    if not attributes:
        raise HTTPException(
            status_code=400,
            detail="Dataset version has no attributes for dry-run",
        )

    attribute_specs = [
        AttributeSpec(
            name=attribute.name,
            data_type=attribute.data_type.value,
            constraints=attribute.constraints_json,
            distribution=attribute.distribution.value,
            null_percentage=attribute.null_percentage,
        )
        for attribute in attributes
    ]
    available_columns = [attribute.name for attribute in attributes]
    conflict_policy = normalize_conflict_policy(request.conflict_policy)
    validation = engine_validate_semantic_rules(
        rules=[rule.model_dump(mode="json") for rule in request.rules],
        available_columns=available_columns,
        conflict_policy=conflict_policy,
    )

    if not validation.get("is_valid", False):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Semantic rule validation failed",
                "errors": validation.get("errors", []),
                "warnings": validation.get("warnings", []),
                "conflict_policy": conflict_policy,
            },
        )

    ordered_rules = build_deterministic_execution_order(
        validation.get("sanitized_rules", []),
        conflict_policy=conflict_policy,
    )
    generator_seed = request.seed if request.seed is not None else version.seed

    baseline_generator = DatasetGenerator(seed=generator_seed)
    baseline_rows = baseline_generator.generate_preview(
        attributes=attribute_specs,
        semantic_rules=[],
    )[: request.sample_rows]

    simulated_generator = DatasetGenerator(seed=generator_seed)
    simulated_rows = simulated_generator.generate_preview(
        attributes=attribute_specs,
        semantic_rules=ordered_rules,
    )[: request.sample_rows]

    changed_cells: list[dict[str, Any]] = []
    changed_rows = 0
    for row_index, (before_row, after_row) in enumerate(
        zip(baseline_rows, simulated_rows)
    ):
        row_changed = False
        for column in available_columns:
            before_value = before_row.get(column)
            after_value = after_row.get(column)
            if before_value != after_value:
                row_changed = True
                changed_cells.append(
                    {
                        "row": row_index,
                        "column": column,
                        "before": before_value,
                        "after": after_value,
                    }
                )
        if row_changed:
            changed_rows += 1

    return DryRunRulesResponseDto(
        dataset_version_id=dataset_version_id,
        sample_rows=request.sample_rows,
        metadata={
            "is_valid": True,
            "warnings": validation.get("warnings", []),
            "errors": validation.get("errors", []),
            "conflict_policy": conflict_policy,
            "execution_order": [
                str(rule.get("id", "")) for rule in ordered_rules if rule.get("id")
            ],
            "conflict_resolution": validation.get("conflict_resolution", {}),
            "changed_rows": changed_rows,
            "changed_cells": len(changed_cells),
        },
        before=baseline_rows,
        after=simulated_rows,
        changed_cells=changed_cells,
    )


@router.post("/apply", response_model=dict)
async def apply_semantic_rule(
    rule: SemanticRuleDto,
    row_data: dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> dict:
    """Apply a single semantic rule to row data."""
    try:
        rule_dict = rule.model_dump(mode="json")
        validation = engine_validate_semantic_rules(
            [rule_dict],
            available_columns=list(row_data.keys()),
        )
        if not validation.get("is_valid", False):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Semantic rule validation failed",
                    "errors": validation.get("errors", []),
                    "warnings": validation.get("warnings", []),
                },
            )

        result = SemanticRuleEngine.apply_rule(rule_dict, row_data)

        return {
            "success": True,
            "rule_id": rule.id,
            "target": rule.target,
            "result": result,
            "input_row": row_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error applying rule: {str(e)}")
