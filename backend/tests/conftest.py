"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_optimization_request():
    """Sample optimization request with realistic data."""
    return {
        "assets": ["US", "Europe", "Japan", "EM", "Gold"],
        "expected_returns": [0.044, 0.101, 0.076, 0.113, 0.05],
        "volatilities": [0.16, 0.18, 0.20, 0.23, 0.15],
        "correlation_matrix": [
            [1.00, 0.85, 0.65, 0.70, 0.05],
            [0.85, 1.00, 0.60, 0.65, 0.10],
            [0.65, 0.60, 1.00, 0.55, 0.05],
            [0.70, 0.65, 0.55, 1.00, 0.15],
            [0.05, 0.10, 0.05, 0.15, 1.00],
        ],
        "crra": 3.5,
    }


@pytest.fixture
def sample_gap_analysis_request():
    """Sample gap analysis request."""
    return {
        "current_allocation": {
            "US": 3.8,
            "Europe": 31.4,
            "Japan": 20.8,
            "EM": 28.8,
            "Gold": 15.2,
        },
        "target_allocation": {
            "US": 0.0,
            "Europe": 50.0,
            "Japan": 0.0,
            "EM": 22.4,
            "Gold": 27.6,
        },
    }
