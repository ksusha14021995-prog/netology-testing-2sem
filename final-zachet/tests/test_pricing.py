"""Tests for tax/coupon/pricing primitives."""
import pytest

from billing import price_with_tax, apply_coupon
from billing.calculator import (
    validate_coupon,
    apply_dynamic_tax,
    tax_breakdown,
    COUPON_CODES,
    SUPPORTED_CURRENCIES,
    TAX_RATE,
)


class TestPriceWithTax:
    def test_hundred_pins_tax_rate(self):
        # 100 * 1.21 == 121.0 — pins TAX_RATE=0.21
        assert price_with_tax(100.0) == 121.0

    def test_zero_returns_zero(self):
        assert price_with_tax(0.0) == 0.0

    def test_one_euro(self):
        assert price_with_tax(1.0) == 1.21

    @pytest.mark.parametrize(
        "net,expected",
        [
            (50.0, 60.5),
            (200.0, 242.0),
            (10.0, 12.1),
            (33.33, 40.33),
            (99.99, 120.99),
        ],
    )
    def test_various_inputs(self, net, expected):
        assert price_with_tax(net) == expected

    @pytest.mark.parametrize("negative", [-0.01, -1.0, -100.0, -0.0001])
    def test_negative_raises(self, negative):
        with pytest.raises(ValueError) as exc_info:
            price_with_tax(negative)
        # Exact-string assertion kills any literal mutation of the message
        assert str(exc_info.value) == "net must be non‑negative"

    def test_negative_zero_boundary_does_not_raise(self):
        # -0.0 is not < 0 in Python, must NOT raise
        result = price_with_tax(-0.0)
        assert result == 0.0

    def test_constant_tax_rate_is_021(self):
        # Direct pin of the module-level constant
        assert TAX_RATE == 0.21


class TestApplyCoupon:
    def test_sport10_uppercase(self):
        assert apply_coupon(100.0, "SPORT10") == 90.0

    def test_newuser5_uppercase(self):
        assert apply_coupon(100.0, "NEWUSER5") == 95.0

    def test_blackfriday_uppercase(self):
        assert apply_coupon(100.0, "BLACKFRIDAY") == 75.0

    def test_sport10_lowercase_still_matches(self):
        # Pins the .upper() call
        assert apply_coupon(100.0, "sport10") == 90.0

    def test_newuser5_mixed_case(self):
        assert apply_coupon(100.0, "NewUser5") == 95.0

    def test_blackfriday_lowercase(self):
        assert apply_coupon(100.0, "blackfriday") == 75.0

    def test_none_coupon(self):
        # None branch — no discount
        assert apply_coupon(100.0, None) == 100.0

    def test_default_arg_is_none(self):
        # Calls with single positional, default coupon=None
        assert apply_coupon(100.0) == 100.0

    def test_empty_string_coupon(self):
        # Empty string — falsy → "" lookup → 0.0 discount
        assert apply_coupon(100.0, "") == 100.0

    def test_unknown_coupon(self):
        assert apply_coupon(100.0, "INVALID") == 100.0

    @pytest.mark.parametrize(
        "gross,code,expected",
        [
            (200.0, "SPORT10", 180.0),
            (50.0, "NEWUSER5", 47.5),
            (40.0, "BLACKFRIDAY", 30.0),
            (123.45, "SPORT10", 111.11),  # 111.105 → 111.11 ROUND_HALF_UP
        ],
    )
    def test_parametrized(self, gross, code, expected):
        assert apply_coupon(gross, code) == expected

    def test_constants_dict_intact(self):
        # Pins COUPON_CODES dict against drop/swap mutants
        assert COUPON_CODES["SPORT10"] == 0.10
        assert COUPON_CODES["NEWUSER5"] == 0.05
        assert COUPON_CODES["BLACKFRIDAY"] == 0.25
        assert len(COUPON_CODES) == 3


class TestValidateCoupon:
    @pytest.mark.parametrize("code", ["SPORT10", "NEWUSER5", "BLACKFRIDAY"])
    def test_valid_uppercase(self, code):
        assert validate_coupon(code) is True

    @pytest.mark.parametrize("code", ["sport10", "newuser5", "blackfriday"])
    def test_valid_lowercase(self, code):
        assert validate_coupon(code) is True

    def test_mixed_case(self):
        assert validate_coupon("Sport10") is True
        assert validate_coupon("BlackFriday") is True

    @pytest.mark.parametrize("code", ["INVALID", "FOO", "SPORT11", "NEWUSER6", "X"])
    def test_invalid_codes(self, code):
        assert validate_coupon(code) is False

    def test_empty_string(self):
        assert validate_coupon("") is False


class TestApplyDynamicTax:
    def test_lv_uppercase(self):
        # Pins 0.21 LV rate
        assert apply_dynamic_tax(100.0, "LV") == 121.0

    def test_lv_lowercase(self):
        # Pins .upper() call
        assert apply_dynamic_tax(100.0, "lv") == 121.0

    def test_lv_mixed(self):
        assert apply_dynamic_tax(100.0, "Lv") == 121.0

    def test_nl_default_branch(self):
        # Pins 0.20 default rate
        assert apply_dynamic_tax(100.0, "NL") == 120.0

    def test_us_default(self):
        assert apply_dynamic_tax(100.0, "US") == 120.0

    def test_de_default_lowercase(self):
        assert apply_dynamic_tax(100.0, "de") == 120.0

    @pytest.mark.parametrize(
        "net,country,expected",
        [
            (50.0, "LV", 60.5),
            (50.0, "DE", 60.0),
            (200.0, "LV", 242.0),
            (200.0, "FR", 240.0),
            (0.0, "LV", 0.0),
            (0.0, "NL", 0.0),
        ],
    )
    def test_parametrized(self, net, country, expected):
        assert apply_dynamic_tax(net, country) == expected


class TestTaxBreakdown:
    def test_hundred(self):
        result = tax_breakdown(100.0)
        # Two asserts kill mutants on either tuple slot
        assert result[0] == 100.0
        assert result[1] == 21.0
        assert result == (100.0, 21.0)

    def test_fifty(self):
        result = tax_breakdown(50.0)
        assert result[0] == 50.0
        assert result[1] == 10.5

    def test_zero(self):
        assert tax_breakdown(0.0) == (0.0, 0.0)

    @pytest.mark.parametrize(
        "net,expected_tax",
        [
            (200.0, 42.0),
            (10.0, 2.1),
            (1.0, 0.21),
            (33.33, 7.0),  # 33.33 * 0.21 = 6.9993 → 7.00
        ],
    )
    def test_tax_values(self, net, expected_tax):
        net_back, tax = tax_breakdown(net)
        assert net_back == net
        assert tax == expected_tax

    def test_returns_tuple_not_list(self):
        result = tax_breakdown(100.0)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestCouponConstantsCurrencyConstants:
    """Pin constant dicts directly so mutmut cannot silently drop entries."""

    def test_currencies_exact_values(self):
        assert SUPPORTED_CURRENCIES["EUR"] == 1.0
        assert SUPPORTED_CURRENCIES["USD"] == 0.92
        assert SUPPORTED_CURRENCIES["GBP"] == 1.15
        assert len(SUPPORTED_CURRENCIES) == 3
