"""API endpoints for semantic rule management - with lazy database loading."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.engine.semantic_rule_engine import (
    SemanticRuleEngine,
    filter_rules_by_confidence,
    sort_rules_by_priority,
)
from app.engine.semantic_rule_validator import SemanticRuleValidator


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


# ============ ROUTER ============

router = APIRouter(prefix="/rules", tags=["semantic-rules"])


# ============ ENDPOINTS ============


@router.get("/dataset/{dataset_version_id}", response_model=SemanticRulesResponseDto)
async def get_semantic_rules(
    dataset_version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
) -> SemanticRulesResponseDto:
    """Get semantic rules for a dataset."""
    try:
        # Lazy import to avoid blocking startup
        from app.db.session import get_db
        from app.engine.profiling.profile_manager import ProfileManager

        db = next(get_db())
        manager = ProfileManager(db)
        profile = manager.get_profile_by_version(dataset_version_id)

        if not profile:
            raise HTTPException(status_code=404, detail="Dataset profile not found")

        return SemanticRulesResponseDto(
            dataset_version_id=dataset_version_id,
            rules=[SemanticRuleDto(**rule) for rule in profile.semantic_rules],
            metadata={
                "rule_count": len(profile.semantic_rules),
                "dataset_name": profile.metadata.get("original_filename", ""),
                "profile_confidence": profile.metadata.get("confidence_score", 0.0),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving rules: {str(e)}")


@router.post("/filter", response_model=FilteredRulesResponseDto)
async def filter_semantic_rules(
    request: FilterRulesRequestDto,
    current_user: User = Depends(get_current_user),
) -> FilteredRulesResponseDto:
    """Filter semantic rules by confidence threshold."""
    try:
        # Without dataset_version_id, just filter empty rules
        rules_to_filter = []

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
        rule_dict = rule.dict()
        result = SemanticRuleEngine.apply_rule(rule_dict, row_data)

        return {
            "success": True,
            "rule_id": rule.id,
            "target": rule.target,
            "result": result,
            "input_row": row_data,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error applying rule: {str(e)}")
