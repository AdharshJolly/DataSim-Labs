"""API endpoints for semantic rule management - with lazy database loading."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.db.session import get_db
from app.engine.semantic_rule_engine import (
    SemanticRuleEngine,
    build_deterministic_execution_order,
    filter_rules_by_confidence,
    sort_rules_by_priority,
    validate_semantic_rules,
)
from app.engine.semantic_rule_validator import SemanticRuleValidator
from app.services.dataset_service import DatasetService


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
        version = DatasetService.get_dataset_version_for_user(
            db=db,
            user_id=current_user.id,
            dataset_version_id=dataset_version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    raw_rules = version.config_json.get("semantic_rules", [])
    if not isinstance(raw_rules, list):
        raw_rules = []

    available_columns = DatasetService.get_dataset_version_attribute_names(
        db=db,
        dataset_version_id=dataset_version_id,
    )
    validation = validate_semantic_rules(raw_rules, available_columns=available_columns)
    ordered_rules = build_deterministic_execution_order(validation["sanitized_rules"])

    return SemanticRulesResponseDto(
        dataset_version_id=dataset_version_id,
        rules=[SemanticRuleDto.model_validate(rule) for rule in ordered_rules],
        metadata={
            "rule_count": len(ordered_rules),
            "is_valid": bool(validation.get("is_valid", True)),
            "warnings": validation.get("warnings", []),
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
        DatasetService.get_dataset_version_for_user(
            db=db,
            user_id=current_user.id,
            dataset_version_id=dataset_version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    available_columns = DatasetService.get_dataset_version_attribute_names(
        db=db,
        dataset_version_id=dataset_version_id,
    )
    raw_rules = [rule.model_dump(mode="json") for rule in request.rules]
    validation = validate_semantic_rules(raw_rules, available_columns=available_columns)

    if not validation.get("is_valid", False):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Semantic rule validation failed",
                "errors": validation.get("errors", []),
                "warnings": validation.get("warnings", []),
            },
        )

    ordered_rules = build_deterministic_execution_order(validation["sanitized_rules"])
    try:
        version = DatasetService.update_dataset_version_semantic_rules(
            db=db,
            user_id=current_user.id,
            dataset_version_id=dataset_version_id,
            semantic_rules=ordered_rules,
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
            "execution_order": [
                str(rule.get("id", "")) for rule in stored_rules if rule.get("id")
            ],
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
async def validate_semantic_rules(
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


@router.post("/apply", response_model=dict)
async def apply_semantic_rule(
    rule: SemanticRuleDto,
    row_data: dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> dict:
    """Apply a single semantic rule to row data."""
    try:
        rule_dict = rule.model_dump(mode="json")
        validation = validate_semantic_rules(
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
