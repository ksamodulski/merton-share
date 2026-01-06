"""Tests for CRRA API endpoints."""

import pytest


class TestCRRACalculateEndpoint:
    """Tests for POST /api/v1/crra/calculate endpoint."""

    def test_calculate_returns_crra(self, client):
        """Test that CRRA calculation returns a valid coefficient."""
        request = {
            "loss_threshold": 20,
            "risk_percentage": 50,
            "stock_allocation": 60,
            "safe_choice": 3,
        }

        response = client.post("/api/v1/crra/calculate", json=request)
        assert response.status_code == 200

        data = response.json()
        assert "crra" in data
        assert "profile" in data

        # CRRA should be a positive number
        assert data["crra"] > 0 and data["crra"] <= 10

    def test_calculate_risk_averse_responses(self, client):
        """Test that risk-averse responses give higher CRRA."""
        risk_averse = {
            "loss_threshold": 10,   # Can't tolerate much loss
            "risk_percentage": 20,  # Low risk tolerance
            "stock_allocation": 30, # Low stock preference
            "safe_choice": 1,       # Most conservative choice
        }

        response = client.post("/api/v1/crra/calculate", json=risk_averse)
        high_crra = response.json()["crra"]

        risk_seeking = {
            "loss_threshold": 40,   # Can tolerate more loss
            "risk_percentage": 80,  # High risk tolerance
            "stock_allocation": 90, # High stock preference
            "safe_choice": 5,       # Most aggressive choice
        }

        response = client.post("/api/v1/crra/calculate", json=risk_seeking)
        low_crra = response.json()["crra"]

        # Risk-averse should have higher CRRA
        assert high_crra > low_crra


class TestCRRAInterpretEndpoint:
    """Tests for POST /api/v1/crra/interpret endpoint."""

    def test_interpret_returns_profile(self, client):
        """Test that CRRA interpretation returns a profile."""
        response = client.post("/api/v1/crra/interpret", json={"crra": 3.5})

        assert response.status_code == 200
        data = response.json()

        assert "crra" in data
        assert "profile" in data
        assert data["crra"] == 3.5

    def test_interpret_different_crra_values(self, client):
        """Test interpretation for different CRRA values."""
        # Low CRRA (risk-seeking)
        response = client.post("/api/v1/crra/interpret", json={"crra": 1.0})
        assert response.status_code == 200

        # Medium CRRA
        response = client.post("/api/v1/crra/interpret", json={"crra": 4.0})
        assert response.status_code == 200

        # High CRRA (risk-averse)
        response = client.post("/api/v1/crra/interpret", json={"crra": 8.0})
        assert response.status_code == 200


class TestCRRAScaleEndpoint:
    """Tests for GET /api/v1/crra/scale endpoint."""

    def test_scale_returns_ranges(self, client):
        """Test that scale endpoint returns CRRA ranges."""
        response = client.get("/api/v1/crra/scale")

        assert response.status_code == 200
        data = response.json()

        assert "scale" in data
        assert len(data["scale"]) > 0

        # Check structure of each scale entry
        for entry in data["scale"]:
            assert "range" in entry
            assert "profile" in entry
            assert "typical_investor" in entry
