"""CRRA survey API routes."""

from fastapi import APIRouter

from app.core.crra_survey import (
    calculate_crra_from_responses,
    interpret_crra,
    get_crra_scale_description,
)
from app.models.crra import (
    CRRASurveyRequest,
    CRRAResponse,
    CRRAInterpretRequest,
    CRRAScaleResponse,
    CRRAScaleItem,
    RiskProfile,
)

router = APIRouter()


@router.post("/calculate", response_model=CRRAResponse)
async def calculate_crra(request: CRRASurveyRequest) -> CRRAResponse:
    """
    Calculate CRRA from survey responses.

    The survey uses 4 questions to estimate risk tolerance:
    1. Loss threshold: Maximum tolerable loss percentage
    2. Risk percentage: Maximum loss accepted in 50/50 gamble
    3. Stock allocation: Preferred allocation to risky assets
    4. Safe choice: Required job security probability
    """
    responses = {
        "loss_threshold": request.loss_threshold,
        "risk_percentage": request.risk_percentage,
        "stock_allocation": request.stock_allocation,
        "safe_choice": request.safe_choice,
    }

    crra = calculate_crra_from_responses(responses)
    profile_dict = interpret_crra(crra)

    return CRRAResponse(
        crra=round(crra, 2),
        profile=RiskProfile(**profile_dict),
    )


@router.post("/interpret", response_model=CRRAResponse)
async def interpret_crra_value(request: CRRAInterpretRequest) -> CRRAResponse:
    """
    Get interpretation for a specific CRRA value.

    Use this when the user directly inputs their CRRA instead of taking the survey.
    """
    profile_dict = interpret_crra(request.crra)

    return CRRAResponse(
        crra=request.crra,
        profile=RiskProfile(**profile_dict),
    )


@router.get("/scale", response_model=CRRAScaleResponse)
async def get_crra_scale() -> CRRAScaleResponse:
    """
    Get the full CRRA scale description.

    Returns descriptions of each CRRA range and typical investor profiles.
    """
    scale = get_crra_scale_description()
    return CRRAScaleResponse(scale=[CRRAScaleItem(**item) for item in scale])
