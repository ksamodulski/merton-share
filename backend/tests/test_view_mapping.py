"""Tests for confidence-weighted blending of institutional and user views."""

import pytest

from app.core.view_mapping import apply_view_adjustments


class TestInstitutionalOnly:
    """Existing behaviour must be preserved when no user views are supplied."""

    def test_high_conf_overweight_full_strength(self):
        result = apply_view_adjustments(
            base_returns={"US": 0.05},
            institutional_views={"US": "overweight"},
            confidence={"US": "high"},
            enabled=True,
        )
        # high-confidence overweight -> full +2%
        assert result["US"].adjusted_return == pytest.approx(0.07)

    def test_low_conf_underweight_attenuated(self):
        result = apply_view_adjustments(
            base_returns={"Europe": 0.07},
            institutional_views={"Europe": "underweight"},
            confidence={"Europe": "low"},
            enabled=True,
        )
        # low-confidence underweight -> -2% * 0.5 = -1%
        assert result["Europe"].adjusted_return == pytest.approx(0.06)

    def test_disabled_returns_base(self):
        result = apply_view_adjustments(
            base_returns={"US": 0.05},
            institutional_views={"US": "overweight"},
            confidence={"US": "high"},
            enabled=False,
        )
        assert result["US"].adjusted_return == pytest.approx(0.05)


class TestUserViewBlending:
    """User views blend with institutional views, weighted by confidence."""

    def test_user_high_conf_overrides_low_conf_institutional(self):
        # Institutional: overweight (low conf, w=0.5). User: underweight (high, w=1.0)
        # blended = (0.5*+0.02 + 1.0*-0.02) / max(1, 1.5) = (0.01 - 0.02)/1.5 = -0.0067
        result = apply_view_adjustments(
            base_returns={"US": 0.05},
            institutional_views={"US": "overweight"},
            confidence={"US": "low"},
            user_views={"US": "underweight"},
            enabled=True,
        )
        assert result["US"].adjustment == pytest.approx((-0.01) / 1.5)
        assert result["US"].adjusted_return < 0.05  # user pulls it negative

    def test_agreeing_views_average_not_stack(self):
        # Both high-conf overweight: blended = (1*0.02 + 1*0.02)/2 = 0.02 (not 0.04)
        result = apply_view_adjustments(
            base_returns={"US": 0.05},
            institutional_views={"US": "overweight"},
            confidence={"US": "high"},
            user_views={"US": "overweight"},
            enabled=True,
        )
        assert result["US"].adjustment == pytest.approx(0.02)
        assert result["US"].adjusted_return == pytest.approx(0.07)

    def test_user_neutral_dampens_institutional(self):
        # Institutional overweight high (w=1), user neutral high (w=1, m=0)
        # blended = (1*0.02 + 1*0)/max(1,2) = 0.01
        result = apply_view_adjustments(
            base_returns={"US": 0.05},
            institutional_views={"US": "overweight"},
            confidence={"US": "high"},
            user_views={"US": "neutral"},
            enabled=True,
        )
        assert result["US"].adjustment == pytest.approx(0.01)

    def test_user_only_view(self):
        # No institutional view, user overweight (default high conf) -> full +2%
        result = apply_view_adjustments(
            base_returns={"Gold": 0.04},
            user_views={"Gold": "overweight"},
            enabled=True,
        )
        assert result["Gold"].adjusted_return == pytest.approx(0.06)

    def test_region_without_user_view_unaffected(self):
        result = apply_view_adjustments(
            base_returns={"US": 0.05, "Japan": 0.06},
            institutional_views={"US": "overweight", "Japan": "overweight"},
            confidence={"US": "high", "Japan": "high"},
            user_views={"US": "underweight"},
            enabled=True,
        )
        # Japan has no user view -> behaves as institutional-only (+2%)
        assert result["Japan"].adjusted_return == pytest.approx(0.08)

    def test_adjustment_clamped_to_bounds(self):
        # Even an extreme blend stays within [-5%, +15%]
        result = apply_view_adjustments(
            base_returns={"US": 0.145},
            institutional_views={"US": "overweight"},
            confidence={"US": "high"},
            user_views={"US": "overweight"},
            enabled=True,
        )
        assert result["US"].adjusted_return <= 0.15
