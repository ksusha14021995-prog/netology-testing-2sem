"""Tests for parse_iso_date, validate_tax_number, cap_price, round_money, is_weekend_rate."""
from datetime import datetime

import pytest

from billing.calculator import (
    parse_iso_date,
    validate_tax_number,
    cap_price,
    round_money,
    is_weekend_rate,
)


class TestParseIsoDate:
    def test_full_datetime(self):
        result = parse_iso_date("2025-01-15T10:30:45")
        assert result == datetime(2025, 1, 15, 10, 30, 45)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45

    def test_date_only(self):
        result = parse_iso_date("2025-12-31")
        assert result == datetime(2025, 12, 31, 0, 0, 0)
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 31

    def test_with_microseconds(self):
        result = parse_iso_date("2025-06-15T08:00:00.123456")
        assert result.microsecond == 123456

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_iso_date("not-a-date")

    def test_returns_datetime_type(self):
        result = parse_iso_date("2025-01-01")
        assert isinstance(result, datetime)


class TestValidateTaxNumber:
    def test_valid_lv_12_chars(self):
        # starts with LV AND length 12 → True
        assert validate_tax_number("LV1234567890") is True

    def test_lv_too_short(self):
        # starts with LV but len != 12 → False (pins the `and` operator)
        assert validate_tax_number("LV12345") is False

    def test_lv_too_long(self):
        assert validate_tax_number("LV12345678901") is False

    def test_ee_prefix_correct_length(self):
        # wrong prefix, right length → False (pins the prefix check)
        assert validate_tax_number("EE1234567890") is False

    def test_lv_not_at_start(self):
        # LV present but not at start → False (pins startswith vs in)
        assert validate_tax_number("XXLV12345678") is False

    def test_empty_string(self):
        assert validate_tax_number("") is False

    def test_only_lv(self):
        assert validate_tax_number("LV") is False

    def test_lv_eleven_chars(self):
        # Boundary: 11 chars → False (pins == 12, not >= 12)
        assert validate_tax_number("LV123456789") is False

    @pytest.mark.parametrize(
        "tax_num,expected",
        [
            ("LVABCDEFGHIJ", True),  # 12 chars starting with LV
            ("LV0000000000", True),
            ("LV9999999999", True),
            ("DE1234567890", False),
            ("FR1234567890", False),
            ("LV", False),
            ("LV1", False),
        ],
    )
    def test_parametrized(self, tax_num, expected):
        assert validate_tax_number(tax_num) is expected

    def test_lowercase_lv_fails(self):
        # No .lower() / .upper() — case sensitive
        assert validate_tax_number("lv1234567890") is False


class TestCapPrice:
    def test_price_below_cap(self):
        # price < cap → return price (pins min, not max)
        assert cap_price(3.0, 5.0) == 3.0

    def test_price_above_cap(self):
        # price > cap → return cap (pins min, not max)
        assert cap_price(10.0, 5.0) == 5.0

    def test_price_equals_cap(self):
        assert cap_price(5.0, 5.0) == 5.0

    @pytest.mark.parametrize(
        "price,cap,expected",
        [
            (1.0, 100.0, 1.0),
            (100.0, 1.0, 1.0),
            (50.0, 50.0, 50.0),
            (0.0, 5.0, 0.0),
            (-5.0, 0.0, -5.0),
            (100.5, 100.4, 100.4),
        ],
    )
    def test_parametrized(self, price, cap, expected):
        assert cap_price(price, cap) == expected


class TestRoundMoney:
    def test_default_decimals_is_two(self):
        # No second arg — uses default decimals=2; pins default value
        assert round_money(1.235) == 1.24

    def test_explicit_two_decimals(self):
        # ROUND_HALF_UP: 1.235 → 1.24
        assert round_money(1.235, 2) == 1.24

    def test_zero_decimals_half_up(self):
        # ROUND_HALF_UP: 2.5 → 3 (away from zero, but here both interpretations agree)
        assert round_money(2.5, 0) == 3.0

    def test_one_five_zero_decimals(self):
        # ROUND_HALF_UP: 1.5 → 2
        assert round_money(1.5, 0) == 2.0

    def test_one_decimal(self):
        # 1.25 → 1.3 (half-up)
        assert round_money(1.25, 1) == 1.3

    def test_down_rounds(self):
        # 1.234 → 1.23 (below .5, rounds down)
        assert round_money(1.234, 2) == 1.23

    def test_125_two_decimals(self):
        # 0.125 → 0.13 (half-up)
        assert round_money(0.125, 2) == 0.13

    @pytest.mark.parametrize(
        "value,decimals,expected",
        [
            (1.0, 2, 1.0),
            (0.0, 2, 0.0),
            (100.5, 0, 101.0),
            (3.14159, 2, 3.14),
            (3.14159, 4, 3.1416),
            (10.05, 1, 10.1),  # half-up
        ],
    )
    def test_parametrized(self, value, decimals, expected):
        assert round_money(value, decimals) == expected

    def test_returns_float(self):
        result = round_money(1.0, 2)
        assert isinstance(result, float)


class TestIsWeekendRate:
    def test_monday(self):
        # 2025-01-06 is Monday (weekday=0)
        assert is_weekend_rate(datetime(2025, 1, 6)) is False

    def test_tuesday(self):
        assert is_weekend_rate(datetime(2025, 1, 7)) is False

    def test_wednesday(self):
        assert is_weekend_rate(datetime(2025, 1, 8)) is False

    def test_thursday(self):
        assert is_weekend_rate(datetime(2025, 1, 9)) is False

    def test_friday(self):
        # 2025-01-10 is Friday (weekday=4) — boundary, must NOT be weekend
        # Pins `>= 5` vs `>= 4`
        assert is_weekend_rate(datetime(2025, 1, 10)) is False

    def test_saturday(self):
        # 2025-01-11 is Saturday (weekday=5) — boundary, must BE weekend
        # Pins `>= 5` vs `> 5`
        assert is_weekend_rate(datetime(2025, 1, 11)) is True

    def test_sunday(self):
        # 2025-01-12 is Sunday (weekday=6)
        assert is_weekend_rate(datetime(2025, 1, 12)) is True

    @pytest.mark.parametrize(
        "date,expected",
        [
            (datetime(2025, 5, 30), False),  # Friday
            (datetime(2025, 5, 31), True),  # Saturday
            (datetime(2025, 6, 1), True),  # Sunday
            (datetime(2025, 6, 2), False),  # Monday
            (datetime(2024, 12, 31), False),  # Tuesday
            (datetime(2025, 1, 1), False),  # Wednesday
        ],
    )
    def test_parametrized(self, date, expected):
        assert is_weekend_rate(date) is expected
