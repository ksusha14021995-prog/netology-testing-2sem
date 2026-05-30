"""Tests for currency conversion."""
import pytest

from billing import convert_currency
from billing.calculator import SUPPORTED_CURRENCIES


class TestConvertCurrency:
    def test_eur_identity(self):
        # 100 / 1.0 = 100.0 — pins EUR rate=1.0
        assert convert_currency(100.0, "EUR") == 100.0

    def test_usd_uppercase(self):
        # 100 / 0.92 = 108.695... → 108.70 — pins USD rate
        assert convert_currency(100.0, "USD") == 108.7

    def test_gbp_uppercase(self):
        # 100 / 1.15 = 86.956... → 86.96 — pins GBP rate
        assert convert_currency(100.0, "GBP") == 86.96

    def test_usd_lowercase(self):
        # Pins .upper() call
        assert convert_currency(100.0, "usd") == 108.7

    def test_gbp_mixed_case(self):
        assert convert_currency(100.0, "Gbp") == 86.96

    def test_eur_lowercase(self):
        assert convert_currency(100.0, "eur") == 100.0

    @pytest.mark.parametrize("bad", ["JPY", "AUD", "CHF", "RUB", "XXX", ""])
    def test_unsupported_raises(self, bad):
        with pytest.raises(KeyError) as exc_info:
            convert_currency(100.0, bad)
        # KeyError repr wraps the message in quotes; compare via .args[0] for exact match
        assert exc_info.value.args[0] == f"Unsupported currency {bad.upper()}"

    def test_unsupported_message_includes_code(self):
        with pytest.raises(KeyError) as exc_info:
            convert_currency(100.0, "JPY")
        # The interpolated currency string survives unchanged in the message
        assert exc_info.value.args[0] == "Unsupported currency JPY"

    @pytest.mark.parametrize(
        "amount,to,expected",
        [
            (50.0, "EUR", 50.0),
            (50.0, "USD", 54.35),  # 50/0.92=54.347... → 54.35
            (200.0, "GBP", 173.91),  # 200/1.15=173.913 → 173.91
            (0.0, "USD", 0.0),
            (0.0, "GBP", 0.0),
            (1.0, "USD", 1.09),  # 1/0.92=1.0869 → 1.09
            (10.0, "GBP", 8.7),  # 10/1.15=8.6956 → 8.7
        ],
    )
    def test_parametrized(self, amount, to, expected):
        assert convert_currency(amount, to) == expected

    def test_constants_pinned(self):
        # Pins SUPPORTED_CURRENCIES dict against silent mutations
        assert SUPPORTED_CURRENCIES == {"EUR": 1.0, "USD": 0.92, "GBP": 1.15}
