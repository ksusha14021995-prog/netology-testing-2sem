"""Tests for quantity-based functions: subtotal, booking fee, bulk, total."""
import pytest

from billing import (
    compute_subtotal,
    booking_fee,
    compute_total,
    compute_bulk_total,
)
from billing.calculator import bulk_discount, BOOKING_FEE_PER_TICKET


class TestComputeSubtotal:
    def test_basic(self):
        # 10.0 * 5 = 50.0
        assert compute_subtotal(10.0, 5) == 50.0

    def test_qty_one(self):
        # Boundary: qty=1 must NOT raise
        assert compute_subtotal(7.5, 1) == 7.5

    def test_zero_qty_raises(self):
        with pytest.raises(ValueError) as exc_info:
            compute_subtotal(10.0, 0)
        assert str(exc_info.value) == "qty must be positive"

    @pytest.mark.parametrize("qty", [-1, -10, -100])
    def test_negative_qty_raises(self, qty):
        with pytest.raises(ValueError) as exc_info:
            compute_subtotal(10.0, qty)
        assert str(exc_info.value) == "qty must be positive"

    @pytest.mark.parametrize(
        "unit,qty,expected",
        [
            (1.0, 1, 1.0),
            (2.5, 4, 10.0),
            (3.33, 3, 9.99),
            (99.99, 2, 199.98),
            (0.01, 100, 1.0),
        ],
    )
    def test_parametrized(self, unit, qty, expected):
        assert compute_subtotal(unit, qty) == expected


class TestBookingFee:
    def test_constant_pin(self):
        assert BOOKING_FEE_PER_TICKET == 0.50

    def test_one_ticket(self):
        # 0.50 * 1 = 0.50 — pins BOOKING_FEE_PER_TICKET
        assert booking_fee(1) == 0.5

    def test_four_tickets(self):
        assert booking_fee(4) == 2.0

    def test_zero_qty(self):
        # booking_fee does NOT validate qty
        assert booking_fee(0) == 0.0

    @pytest.mark.parametrize(
        "qty,expected",
        [
            (2, 1.0),
            (3, 1.5),
            (10, 5.0),
            (20, 10.0),
            (100, 50.0),
        ],
    )
    def test_parametrized(self, qty, expected):
        assert booking_fee(qty) == expected


class TestBulkDiscount:
    @pytest.mark.parametrize("qty", [1, 2, 5, 9])
    def test_below_ten_no_discount(self, qty):
        assert bulk_discount(qty) == 0.0

    def test_ten_boundary_gets_eight_percent(self):
        # Pins `qty >= 10` (not `> 10`)
        assert bulk_discount(10) == 0.08

    def test_nineteen_still_eight(self):
        assert bulk_discount(19) == 0.08

    def test_twenty_boundary_gets_fifteen_percent(self):
        # Pins `qty >= 20` (not `> 20`)
        assert bulk_discount(20) == 0.15

    def test_large_qty_gets_fifteen(self):
        assert bulk_discount(100) == 0.15
        assert bulk_discount(1000) == 0.15

    def test_qty_eleven(self):
        assert bulk_discount(11) == 0.08

    def test_qty_twentyone(self):
        assert bulk_discount(21) == 0.15

    def test_zero_and_negative(self):
        # qty < 10 path
        assert bulk_discount(0) == 0.0
        assert bulk_discount(-5) == 0.0


class TestComputeBulkTotal:
    def test_no_discount_below_ten(self):
        # 10.0 * 5 = 50.0 subtotal, no discount, * 1.21 = 60.5
        assert compute_bulk_total(10.0, 5) == 60.5

    def test_ten_pct_discount_tier(self):
        # 10.0 * 10 = 100, * 0.92 = 92, * 1.21 = 111.32
        assert compute_bulk_total(10.0, 10) == 111.32

    def test_fifteen_pct_discount_tier(self):
        # 10.0 * 20 = 200, * 0.85 = 170, * 1.21 = 205.7
        assert compute_bulk_total(10.0, 20) == 205.7

    def test_nineteen_tier(self):
        # 19 → 8% tier
        # 10 * 19 = 190, * 0.92 = 174.8, * 1.21 = 211.508 → 211.51
        assert compute_bulk_total(10.0, 19) == 211.51

    def test_qty_one(self):
        assert compute_bulk_total(10.0, 1) == 12.1

    def test_invalid_qty_raises(self):
        with pytest.raises(ValueError):
            compute_bulk_total(10.0, 0)


class TestComputeTotal:
    def test_no_coupon(self):
        # subtotal=20, fee=1.0, gross=price_with_tax(21)=25.41, no coupon → 25.41
        assert compute_total(10.0, 2, None) == 25.41

    def test_default_no_coupon(self):
        assert compute_total(10.0, 2) == 25.41

    def test_with_sport10(self):
        # 25.41 * 0.9 = 22.869 → 22.87
        assert compute_total(10.0, 2, "SPORT10") == 22.87

    def test_with_newuser5(self):
        # 25.41 * 0.95 = 24.1395 → 24.14
        assert compute_total(10.0, 2, "NEWUSER5") == 24.14

    def test_with_blackfriday(self):
        # 25.41 * 0.75 = 19.0575 → 19.06
        assert compute_total(10.0, 2, "BLACKFRIDAY") == 19.06

    def test_lowercase_coupon(self):
        assert compute_total(10.0, 2, "sport10") == 22.87

    def test_invalid_coupon_no_discount(self):
        assert compute_total(10.0, 2, "BOGUS") == 25.41

    def test_qty_one(self):
        # subtotal=10, fee=0.5, gross=price_with_tax(10.5)=12.705→12.71
        assert compute_total(10.0, 1, None) == 12.71

    def test_invalid_qty_raises(self):
        with pytest.raises(ValueError):
            compute_total(10.0, 0)

    @pytest.mark.parametrize(
        "unit,qty,coupon,expected",
        [
            (5.0, 4, None, 26.62),
            (100.0, 1, "SPORT10", 109.44),
            (50.0, 2, "NEWUSER5", 116.1),
            (1.0, 3, None, 5.45),  # sub=3, fee=1.5, 4.5*1.21=5.445→5.45 (no coupon)
        ],
    )
    def test_parametrized(self, unit, qty, coupon, expected):
        assert compute_total(unit, qty, coupon) == expected
