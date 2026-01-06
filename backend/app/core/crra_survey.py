"""
CRRA (Coefficient of Relative Risk Aversion) estimation module.

This module provides functions to calculate CRRA from survey responses
and interpret the resulting risk profile.
"""

from typing import Dict, TypedDict


class SurveyResponses(TypedDict):
    """Type definition for survey responses."""

    loss_threshold: float  # 0-100: Max tolerable loss percentage
    risk_percentage: float  # 0-100: Max loss accepted in 50/50 gamble
    stock_allocation: float  # 0-100: Preferred risky asset allocation
    safe_choice: float  # 0-100: Job security probability required


class RiskProfile(TypedDict):
    """Type definition for risk profile interpretation."""

    risk_profile: str
    description: str
    typical_allocation: str
    investor_type: str
    percentile: str


def calculate_crra_from_responses(responses: SurveyResponses) -> float:
    """
    Calculate CRRA based on weighted survey responses.

    Args:
        responses: Dictionary with survey responses

    Returns:
        CRRA value between 1 and 10
    """
    weights = {
        "loss_aversion": 0.3,
        "wealth_gamble": 0.3,
        "portfolio_choice": 0.2,
        "income_risk": 0.2,
    }

    crra_indicators = {
        "loss_aversion": responses["loss_threshold"] / 25,  # Scale 0-100% to 0-4
        "wealth_gamble": (100 - responses["risk_percentage"]) / 25,  # Inverse scale
        "portfolio_choice": (100 - responses["stock_allocation"])
        / 20,  # Convert to 1-5 scale
        "income_risk": responses["safe_choice"] / 20,  # Scale 0-100 to 0-5
    }

    weighted_crra = sum(crra * weights[k] for k, crra in crra_indicators.items())

    # Ensure CRRA is between 1 and 10
    return max(1.0, min(10.0, weighted_crra))


def interpret_crra(crra: float) -> RiskProfile:
    """
    Provide interpretation of CRRA value.

    Args:
        crra: CRRA value (1-10)

    Returns:
        RiskProfile dictionary with interpretation
    """
    if crra < 2:
        return {
            "risk_profile": "Very Aggressive",
            "description": "You're comfortable with significant risk for higher returns",
            "typical_allocation": "80-100% risky assets",
            "investor_type": "Growth/Aggressive Growth investor",
            "percentile": "Top 10% most aggressive investors",
        }
    elif crra < 3:
        return {
            "risk_profile": "Aggressive",
            "description": "You're willing to accept substantial risk for better returns",
            "typical_allocation": "70-80% risky assets",
            "investor_type": "Growth investor",
            "percentile": "Top 25% of aggressive investors",
        }
    elif crra < 4:
        return {
            "risk_profile": "Moderate",
            "description": "You seek balance between risk and security",
            "typical_allocation": "50-70% risky assets",
            "investor_type": "Balanced investor",
            "percentile": "Middle 30% of investors (average risk tolerance)",
        }
    elif crra < 6:
        return {
            "risk_profile": "Conservative",
            "description": "You prioritize security over high returns",
            "typical_allocation": "30-50% risky assets",
            "investor_type": "Income with Growth investor",
            "percentile": "Bottom 25% more conservative investors",
        }
    else:
        return {
            "risk_profile": "Very Conservative",
            "description": "You strongly prefer security and stability",
            "typical_allocation": "10-30% risky assets",
            "investor_type": "Income/Preservation investor",
            "percentile": "Bottom 10% most conservative investors",
        }


def get_crra_scale_description() -> list[Dict]:
    """
    Get description of CRRA scale ranges.

    Returns:
        List of dictionaries describing each CRRA range
    """
    return [
        {
            "range": "1.0-2.0",
            "profile": "Very Aggressive",
            "typical_investor": "Professional traders, very aggressive investors",
        },
        {
            "range": "2.0-3.0",
            "profile": "Aggressive",
            "typical_investor": "Young investors with stable income, growth-focused",
        },
        {
            "range": "3.0-4.0",
            "profile": "Moderate",
            "typical_investor": "Average retail investors, balanced approach",
        },
        {
            "range": "4.0-6.0",
            "profile": "Conservative",
            "typical_investor": "Conservative investors, pre-retirees",
        },
        {
            "range": "6.0+",
            "profile": "Very Conservative",
            "typical_investor": "Very conservative investors, retirees",
        },
    ]
