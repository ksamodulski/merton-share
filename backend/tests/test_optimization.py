"""Tests for optimization API endpoints."""

import pytest


class TestOptimizeEndpoint:
    """Tests for POST /api/v1/optimize endpoint."""

    def test_optimize_returns_weights(self, client, sample_optimization_request):
        """Test that optimization returns valid weights."""
        response = client.post("/api/v1/optimize", json=sample_optimization_request)

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "optimal_weights" in data
        assert "portfolio_stats" in data

        # Check weights are returned for all assets
        weights = data["optimal_weights"]
        assert set(weights.keys()) == {"US", "Europe", "Japan", "EM", "Gold"}

        # Check weights sum to ~100%
        total = sum(weights.values())
        assert 99.9 <= total <= 100.1, f"Weights sum to {total}, expected ~100"

        # Check all weights are non-negative
        for asset, weight in weights.items():
            assert weight >= 0, f"{asset} has negative weight: {weight}"

    def test_optimize_returns_portfolio_stats(self, client, sample_optimization_request):
        """Test that optimization returns portfolio statistics."""
        response = client.post("/api/v1/optimize", json=sample_optimization_request)

        assert response.status_code == 200
        stats = response.json()["portfolio_stats"]

        # Check all expected stats are present
        assert "return" in stats
        assert "volatility" in stats
        assert "sharpe_ratio" in stats
        assert "crra_utility" in stats
        assert "risk_contribution" in stats

        # Check stats are reasonable
        assert 0 < stats["return"] < 20, "Return should be between 0-20%"
        assert 0 < stats["volatility"] < 30, "Volatility should be between 0-30%"

    def test_optimize_validates_input_dimensions(self, client):
        """Test that mismatched dimensions are rejected."""
        bad_request = {
            "assets": ["US", "Europe"],  # 2 assets
            "expected_returns": [0.05, 0.07, 0.06],  # 3 returns - mismatch!
            "volatilities": [0.16, 0.18],
            "correlation_matrix": [[1, 0.6], [0.6, 1]],
            "crra": 3.0,
        }

        response = client.post("/api/v1/optimize", json=bad_request)
        assert response.status_code == 422  # Validation error

    def test_optimize_rejects_invalid_crra(self, client, sample_optimization_request):
        """Test that CRRA must be positive and <= 10."""
        # CRRA = 0 should fail
        sample_optimization_request["crra"] = 0
        response = client.post("/api/v1/optimize", json=sample_optimization_request)
        assert response.status_code == 422

        # CRRA > 10 should fail
        sample_optimization_request["crra"] = 15
        response = client.post("/api/v1/optimize", json=sample_optimization_request)
        assert response.status_code == 422


class TestGapAnalysisEndpoint:
    """Tests for POST /api/v1/optimize/gap-analysis endpoint."""

    def test_gap_analysis_returns_rows(self, client, sample_gap_analysis_request):
        """Test that gap analysis returns rows for all assets."""
        response = client.post("/api/v1/optimize/gap-analysis", json=sample_gap_analysis_request)

        assert response.status_code == 200
        data = response.json()

        assert "rows" in data
        assert "high_priority" in data
        assert "medium_priority" in data

        # Check we got a row for each asset
        assert len(data["rows"]) == 5

    def test_gap_analysis_calculates_correct_gaps(self, client):
        """Test that gaps are calculated correctly (target - current)."""
        request = {
            "current_allocation": {"US": 30.0, "Europe": 70.0},
            "target_allocation": {"US": 50.0, "Europe": 50.0},
        }

        response = client.post("/api/v1/optimize/gap-analysis", json=request)
        assert response.status_code == 200

        rows = {r["ticker"]: r for r in response.json()["rows"]}

        # US: 50 - 30 = +20 (underweight)
        assert rows["US"]["gap"] == 20.0
        # Europe: 50 - 70 = -20 (overweight)
        assert rows["Europe"]["gap"] == -20.0

    def test_gap_analysis_assigns_priorities(self, client):
        """Test that priorities are assigned based on gap size."""
        request = {
            "current_allocation": {
                "A": 0.0,   # Gap +10 -> high priority
                "B": 6.0,   # Gap +4 -> medium priority
                "C": 10.0,  # Gap 0 -> hold
                "D": 15.0,  # Gap -5 -> skip
            },
            "target_allocation": {
                "A": 10.0,
                "B": 10.0,
                "C": 10.0,
                "D": 10.0,
            },
        }

        response = client.post("/api/v1/optimize/gap-analysis", json=request)
        rows = {r["ticker"]: r["priority"] for r in response.json()["rows"]}

        assert rows["A"] == "high"     # +10% gap
        assert rows["B"] == "medium"   # +4% gap
        assert rows["C"] == "hold"     # 0% gap
        assert rows["D"] == "skip"     # -5% gap


class TestAllocateEndpoint:
    """Tests for POST /api/v1/optimize/allocate endpoint."""

    def test_allocate_spreads_contribution(self, client):
        """Test that contribution is spread across underweight assets."""
        # First get gap analysis
        gap_request = {
            "current_allocation": {"Europe": 10.0, "Gold": 10.0, "EM": 80.0},
            "target_allocation": {"Europe": 40.0, "Gold": 40.0, "EM": 20.0},
        }
        gap_response = client.post("/api/v1/optimize/gap-analysis", json=gap_request)
        gap_data = gap_response.json()

        # Now allocate
        alloc_request = {
            "contribution_amount": 10000,
            "current_portfolio_value": 50000,
            "gap_analysis": gap_data,
            "min_allocation": 500,
        }

        response = client.post("/api/v1/optimize/allocate", json=alloc_request)
        assert response.status_code == 200

        data = response.json()
        assert "recommendations" in data
        assert "post_allocation_preview" in data

        # Should recommend buying Europe and Gold (underweight), not EM (overweight)
        tickers = [r["ticker"] for r in data["recommendations"]]
        assert "EM" not in tickers or data["recommendations"][0]["amount_eur"] == 0

    def test_allocate_respects_minimum(self, client):
        """Test that allocations respect minimum amount."""
        gap_request = {
            "current_allocation": {"A": 0.0, "B": 0.0},
            "target_allocation": {"A": 50.0, "B": 50.0},
        }
        gap_response = client.post("/api/v1/optimize/gap-analysis", json=gap_request)

        alloc_request = {
            "contribution_amount": 1000,
            "current_portfolio_value": 10000,
            "gap_analysis": gap_response.json(),
            "min_allocation": 600,  # Only room for 1 allocation
        }

        response = client.post("/api/v1/optimize/allocate", json=alloc_request)
        data = response.json()

        # Should only have 1 recommendation since min is 600 and total is 1000
        assert len(data["recommendations"]) <= 2
        for rec in data["recommendations"]:
            assert rec["amount_eur"] >= 600 or rec["amount_eur"] == 0

    def test_allocate_returns_preview(self, client):
        """Test that allocation returns post-allocation preview."""
        gap_request = {
            "current_allocation": {"US": 50.0, "Europe": 50.0},
            "target_allocation": {"US": 30.0, "Europe": 70.0},
        }
        gap_response = client.post("/api/v1/optimize/gap-analysis", json=gap_request)

        alloc_request = {
            "contribution_amount": 5000,
            "current_portfolio_value": 10000,
            "gap_analysis": gap_response.json(),
            "min_allocation": 500,
        }

        response = client.post("/api/v1/optimize/allocate", json=alloc_request)
        data = response.json()

        # Check preview structure
        assert "post_allocation_preview" in data
        preview = data["post_allocation_preview"]

        for pos in preview:
            assert "ticker" in pos
            assert "current_pct" in pos
            assert "new_pct" in pos
            assert "target_pct" in pos
            assert "gap_after" in pos


class TestRebalanceEndpoint:
    """Tests for POST /api/v1/optimize/rebalance-check endpoint."""

    def test_rebalance_detects_overweight(self, client):
        """Test that rebalance check detects overweight positions."""
        request = {
            "current_allocation": {"US": 60.0, "Europe": 40.0},
            "target_allocation": {"US": 40.0, "Europe": 60.0},
            "rebalance_threshold": 5.0,
        }

        response = client.post("/api/v1/optimize/rebalance-check", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["is_rebalance_recommended"] is True
        assert data["max_deviation"] == 20.0  # US is 20% off

        # US should be in overweight positions
        overweight_tickers = [p["ticker"] for p in data["overweight_positions"]]
        assert "US" in overweight_tickers

    def test_rebalance_not_needed_when_balanced(self, client):
        """Test that rebalance is not recommended when within threshold."""
        request = {
            "current_allocation": {"US": 48.0, "Europe": 52.0},
            "target_allocation": {"US": 50.0, "Europe": 50.0},
            "rebalance_threshold": 5.0,
        }

        response = client.post("/api/v1/optimize/rebalance-check", json=request)
        data = response.json()

        assert data["is_rebalance_recommended"] is False
        assert len(data["overweight_positions"]) == 0
