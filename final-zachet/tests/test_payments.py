"""Tests for split_payment, compute_refund, loyalty functions."""
import pytest

from billing import loyalty_points_earned
from billing.calculator import (
    split_payment,
    compute_refund,
    apply_loyalty_discount,
    LOYALTY_POINT_RATE,
)


class TestSplitPayment:
    def test_even_split(self):
        # 100 / 4 = 25.0 each, no rounding diff
        result = split_payment(100.0, 4)
        assert result == [25.0, 25.0, 25.0, 25.0]
        assert len(result) == 4
        assert sum(result) == 100.0

    def test_uneven_three_way(self):
        # 10.0 / 3 = 3.333 → 3.33 each, last absorbs +0.01
        result = split_payment(10.0, 3)
        assert result == [3.33, 3.33, 3.34]
        assert len(result) == 3
        assert sum(result) == 10.0

    def test_single_part(self):
        # parts=1 — whole amount in one bucket
        result = split_payment(10.0, 1)
        assert result == [10.0]
        assert len(result) == 1

    def test_zero_parts_raises(self):
        with pytest.raises(ValueError) as exc_info:
            split_payment(10.0, 0)
        assert str(exc_info.value) == "parts must be > 0"

    @pytest.mark.parametrize("parts", [-1, -5, -100])
    def test_negative_parts_raises(self, parts):
        with pytest.raises(ValueError) as exc_info:
            split_payment(10.0, parts)
        assert str(exc_info.value) == "parts must be > 0"

    def test_seven_parts_rounding(self):
        # 100 / 7 = 14.285... → 14.29 each, sum=100.03, diff=-0.03, last=14.26
        result = split_payment(100.0, 7)
        assert len(result) == 7
        assert sum(result) == 100.0
        # Most elements equal the rounded part
        assert result[0] == 14.29
        assert result[5] == 14.29
        # Last element absorbs the diff
        assert result[-1] == 14.26

    def test_last_element_absorbs_diff(self):
        # Verifies the diff goes into amounts[-1], not amounts[0]
        result = split_payment(1.0, 3)
        # 1/3 = 0.333 → 0.33 each, sum=0.99, diff=0.01, last=0.34
        assert result == [0.33, 0.33, 0.34]
        assert result[0] != result[-1]

    def test_two_parts(self):
        # 5.0 / 2 = 2.5 each, no diff
        assert split_payment(5.0, 2) == [2.5, 2.5]

    def test_sum_always_matches_total(self):
        for total, parts in [(100.0, 3), (50.0, 7), (1.0, 9), (12.34, 5)]:
            result = split_payment(total, parts)
            assert len(result) == parts
            assert sum(result) == total


class TestComputeRefund:
    def test_half_refund(self):
        assert compute_refund(200.0, 0.5) == 100.0

    def test_full_refund(self):
        # Boundary: percentage=1 must NOT raise
        assert compute_refund(200.0, 1.0) == 200.0

    def test_zero_refund(self):
        # Boundary: percentage=0 must NOT raise
        assert compute_refund(200.0, 0.0) == 0.0

    @pytest.mark.parametrize("pct", [-0.01, -0.1, -1.0])
    def test_negative_percentage_raises(self, pct):
        with pytest.raises(ValueError) as exc_info:
            compute_refund(200.0, pct)
        assert str(exc_info.value) == "percentage 0..1"

    @pytest.mark.parametrize("pct", [1.01, 1.1, 2.0, 100.0])
    def test_above_one_raises(self, pct):
        with pytest.raises(ValueError) as exc_info:
            compute_refund(200.0, pct)
        assert str(exc_info.value) == "percentage 0..1"

    @pytest.mark.parametrize(
        "paid,pct,expected",
        [
            (100.0, 0.25, 25.0),
            (50.0, 0.1, 5.0),
            (1000.0, 0.75, 750.0),
            (33.33, 0.5, 16.67),  # 16.665 → 16.67 ROUND_HALF_UP
            (10.0, 1.0, 10.0),
            (10.0, 0.0, 0.0),
        ],
    )
    def test_parametrized(self, paid, pct, expected):
        assert compute_refund(paid, pct) == expected


class TestLoyaltyPointsEarned:
    def test_constant_pin(self):
        assert LOYALTY_POINT_RATE == 0.02

    def test_fifty_euros_yields_one_point(self):
        # int(50 * 0.02) = int(1.0) = 1
        assert loyalty_points_earned(50.0) == 1

    def test_below_fifty_yields_zero(self):
        # int(49.99 * 0.02) = int(0.9998) = 0
        assert loyalty_points_earned(49.99) == 0

    def test_199_99_yields_three(self):
        # int(199.99 * 0.02) = int(3.9998) = 3
        assert loyalty_points_earned(199.99) == 3

    def test_100_yields_two(self):
        assert loyalty_points_earned(100.0) == 2

    def test_zero_yields_zero(self):
        assert loyalty_points_earned(0.0) == 0

    def test_one_thousand_yields_twenty(self):
        assert loyalty_points_earned(1000.0) == 20

    @pytest.mark.parametrize(
        "net,expected",
        [
            (25.0, 0),  # 0.5 → 0
            (75.0, 1),  # 1.5 → 1
            (150.0, 3),  # 3.0 → 3
            (5000.0, 100),
        ],
    )
    def test_parametrized(self, net, expected):
        assert loyalty_points_earned(net) == expected

    def test_return_type_is_int(self):
        result = loyalty_points_earned(100.0)
        assert isinstance(result, int)


class TestApplyLoyaltyDiscount:
    def test_basic_discount(self):
        # 500 points * 0.01 = 5.0 discount, 100 - 5 = 95.0
        assert apply_loyalty_discount(100.0, 500) == 95.0

    def test_zero_points(self):
        assert apply_loyalty_discount(100.0, 0) == 100.0

    def test_huge_points_clamps_to_zero(self):
        # 2000 * 0.01 = 20.0 discount, 10 - 20 = -10, clamps to 0
        assert apply_loyalty_discount(10.0, 2000) == 0.0

    def test_exactly_zero_after_discount(self):
        # 100 * 0.01 = 1.0 discount, gross=1.0, 1.0 - 1.0 = 0.0
        assert apply_loyalty_discount(1.0, 100) == 0.0

    def test_partial_discount(self):
        # 200 * 0.01 = 2.0, 10 - 2 = 8.0
        assert apply_loyalty_discount(10.0, 200) == 8.0

    def test_negative_after_clamps(self):
        # 1000 * 0.01 = 10.0, 5 - 10 = -5, clamps to 0
        assert apply_loyalty_discount(5.0, 1000) == 0.0

    @pytest.mark.parametrize(
        "gross,points,expected",
        [
            (50.0, 100, 49.0),
            (50.0, 50, 49.5),
            (20.0, 1500, 5.0),  # discount=15.0, 20-15=5.0
            (20.0, 2500, 0.0),  # discount=25.0, 20-25=-5.0 → clamps to 0.0
            (100.0, 1000, 90.0),  # 1000*0.01=10, 100-10=90
        ],
    )
    def test_parametrized(self, gross, points, expected):
        assert apply_loyalty_discount(gross, points) == expected
