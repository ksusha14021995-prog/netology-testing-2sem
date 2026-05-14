"""Юнит-тесты Booking-сервиса (ДЗ-3 Нетология, «Основы тестирования»).

На каждую из 5 функций — минимум 2 позитивных и 2 негативных теста.
Используются: @pytest.fixture (общие — в conftest.py), @pytest.mark.parametrize,
unittest.mock.MagicMock + pytest-mock, freezegun для подмены времени.

Запуск:
    .venv\\Scripts\\pytest.exe module3-hw-files/ -v
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time

from booking_service import (
    apply_promo_code,
    calc_price,
    check_availability,
    generate_booking_ref,
    send_notification_email,
)


# ===========================================================================
# 1. calc_price
# ===========================================================================


class TestCalcPrice:
    """Чистая функция: проверяем расчёт, граничные случаи и валидацию входов."""

    # --- Позитивные (4 кейса через параметризацию) ----------------------

    @pytest.mark.parametrize(
        "base, discount, count, expected",
        [
            (100.0, 0.0, 1, 100.0),     # без скидки, 1 билет
            (100.0, 0.2, 5, 400.0),     # 20% скидка, 5 билетов
            (50.0, 0.5, 2, 50.0),       # 50% скидка
            (0.0, 0.0, 10, 0.0),        # бесплатный билет — граничный
        ],
        ids=["no-discount", "20pct-five-tickets", "half-off", "free-tickets"],
    )
    def test_calc_price_valid_inputs(self, base, discount, count, expected):
        assert calc_price(base, discount, count) == expected, (
            f"calc_price({base}, {discount}, {count}) должно быть {expected}"
        )

    def test_calc_price_zero_count_returns_zero(self):
        """Граничный случай: 0 билетов — итоговая цена 0, без исключения."""
        assert calc_price(199.99, 0.1, 0) == 0.0

    def test_calc_price_rounds_to_two_decimals(self):
        """Результат округляется до 2 знаков (для отображения цены)."""
        # 33.33 * 3 * (1 - 0.1) = 89.991 -> 89.99
        assert calc_price(33.33, 0.1, 3) == 89.99

    # --- Негативные ------------------------------------------------------

    @pytest.mark.parametrize(
        "base, discount, count",
        [
            (100.0, 0.0, -1),    # отрицательное количество
            (100.0, 1.5, 1),     # скидка > 100%
            (100.0, -0.1, 1),    # отрицательная скидка
            (-10.0, 0.0, 1),     # отрицательная цена
        ],
        ids=["negative-count", "discount-over-1", "negative-discount", "negative-base"],
    )
    def test_calc_price_invalid_inputs_raise(self, base, discount, count):
        with pytest.raises(ValueError):
            calc_price(base, discount, count)


# ===========================================================================
# 2. check_availability
# ===========================================================================


class TestCheckAvailability:
    """Функция зависит от БД — мокаем её через fake_db (conftest.py)."""

    # --- Позитивные ------------------------------------------------------

    def test_returns_true_when_enough_seats(self, fake_db):
        fake_db.get_remaining_seats.return_value = 10
        assert check_availability(event_id=1, seats_requested=3, db=fake_db) is True
        fake_db.get_remaining_seats.assert_called_once_with(1)

    def test_returns_true_when_exactly_enough_seats(self, fake_db):
        """Граница: запрошено столько же, сколько есть — должно быть True."""
        fake_db.get_remaining_seats.return_value = 5
        assert check_availability(event_id=42, seats_requested=5, db=fake_db) is True

    # --- Негативные ------------------------------------------------------

    def test_returns_false_when_not_enough_seats(self, fake_db):
        fake_db.get_remaining_seats.return_value = 2
        assert check_availability(event_id=1, seats_requested=5, db=fake_db) is False

    def test_raises_lookup_error_when_event_not_found(self, fake_db):
        """БД вернула None -> событие не существует -> LookupError."""
        fake_db.get_remaining_seats.return_value = None
        with pytest.raises(LookupError, match="event 999 not found"):
            check_availability(event_id=999, seats_requested=1, db=fake_db)

    @pytest.mark.parametrize("bad_seats", [0, -1, -100])
    def test_raises_for_non_positive_seats_requested(self, fake_db, bad_seats):
        with pytest.raises(ValueError, match="seats_requested"):
            check_availability(event_id=1, seats_requested=bad_seats, db=fake_db)
        # БД не должна была дёргаться — валидация раньше
        fake_db.get_remaining_seats.assert_not_called()


# ===========================================================================
# 3. apply_promo_code
# ===========================================================================


class TestApplyPromoCode:
    """Зависит от PromoRepo (мок) и текущего времени (freezegun)."""

    # --- Позитивные ------------------------------------------------------

    def test_valid_promo_returns_true(self, fake_promo_repo):
        assert apply_promo_code(order_id=1, promo_code="SAVE10", repo=fake_promo_repo) is True
        fake_promo_repo.get.assert_called_once_with("SAVE10")

    def test_promo_without_expiration_is_accepted(self, fake_promo_repo):
        """Если expires_at == None — промокод бессрочный."""
        fake_promo_repo.get.return_value = {"expires_at": None, "uses_left": 1}
        assert apply_promo_code(1, "FOREVER", fake_promo_repo) is True

    @freeze_time("2026-05-14 12:00:00")
    def test_promo_valid_today_works(self, fake_promo_repo):
        """Замораживаем время — промокод, истекающий завтра, действителен."""
        fake_promo_repo.get.return_value = {
            "expires_at": datetime(2026, 5, 15, 12, 0, 0),
            "uses_left": 3,
        }
        assert apply_promo_code(1, "TODAY", fake_promo_repo) is True

    # --- Негативные ------------------------------------------------------

    def test_unknown_promo_returns_false(self, fake_promo_repo):
        fake_promo_repo.get.return_value = None
        assert apply_promo_code(1, "NOPE", fake_promo_repo) is False

    @freeze_time("2026-05-14 12:00:00")
    def test_expired_promo_returns_false(self, fake_promo_repo):
        fake_promo_repo.get.return_value = {
            "expires_at": datetime(2026, 5, 13, 23, 59, 59),  # вчера
            "uses_left": 10,
        }
        assert apply_promo_code(1, "OLD", fake_promo_repo) is False

    def test_exhausted_promo_returns_false(self, fake_promo_repo):
        fake_promo_repo.get.return_value = {
            "expires_at": datetime.now() + timedelta(days=1),
            "uses_left": 0,
        }
        assert apply_promo_code(1, "USED", fake_promo_repo) is False


# ===========================================================================
# 4. generate_booking_ref
# ===========================================================================


class TestGenerateBookingRef:
    """Генератор уникального идентификатора брони."""

    REF_PATTERN = re.compile(r"^BOOK-\d+-\d+-[0-9a-f]{8}$")

    # --- Позитивные ------------------------------------------------------

    def test_format_matches_spec(self):
        ref = generate_booking_ref(user_id=1, event_id=42)
        assert self.REF_PATTERN.match(ref), (
            f"Референс '{ref}' не соответствует формату BOOK-<user>-<event>-<hex8>"
        )

    def test_contains_user_and_event_ids(self):
        ref = generate_booking_ref(user_id=777, event_id=314)
        assert "BOOK-777-314-" in ref

    def test_subsequent_calls_produce_unique_refs(self):
        """100 вызовов подряд должны дать 100 уникальных значений."""
        refs = {generate_booking_ref(1, 1) for _ in range(100)}
        assert len(refs) == 100, "Референсы должны быть уникальны от вызова к вызову"

    # --- Негативные (через мок генератора случайности) ------------------

    def test_uses_secrets_token_hex_under_the_hood(self, mocker):
        """Подменяем secrets.token_hex и убеждаемся, что результат «склеивается»."""
        mocker.patch("booking_service.secrets.token_hex", return_value="deadbeef")
        ref = generate_booking_ref(user_id=2, event_id=99)
        assert ref == "BOOK-2-99-deadbeef"

    def test_collision_when_random_suffix_is_constant(self, mocker):
        """Если token_hex всегда возвращает одно и то же — рефы повторяются.

        Это негативный сценарий: показываем, что уникальность держится именно
        на secrets, и контракт ломается, если RNG зафиксировать.
        """
        mocker.patch("booking_service.secrets.token_hex", return_value="cafef00d")
        a = generate_booking_ref(5, 5)
        b = generate_booking_ref(5, 5)
        assert a == b, "При замокированном RNG два вызова обязаны дать одинаковый ref"


# ===========================================================================
# 5. send_notification_email
# ===========================================================================


class TestSendNotificationEmail:
    """Внешний mail-сервис мокается через fake_mailer (conftest.py)."""

    # --- Позитивные ------------------------------------------------------

    def test_returns_true_on_successful_send(self, fake_mailer, booking_details):
        result = send_notification_email(
            "user@example.com", booking_details, fake_mailer
        )
        assert result is True
        fake_mailer.send.assert_called_once()
        # Проверяем содержание письма
        kwargs = fake_mailer.send.call_args.kwargs
        assert kwargs["to"] == "user@example.com"
        assert "BOOK-1-42-abcd1234" in kwargs["body"]
        assert kwargs["subject"] == "Бронирование подтверждено"

    def test_returns_false_when_mailer_returns_false(self, fake_mailer, booking_details):
        """Mail-сервис вернул False (отказ доставки) — функция тоже False."""
        fake_mailer.send.return_value = False
        assert send_notification_email(
            "user@example.com", booking_details, fake_mailer
        ) is False

    # --- Негативные ------------------------------------------------------

    @pytest.mark.parametrize("bad_email", ["", "no-at-sign", "  ", "plain.text"])
    def test_invalid_email_raises_value_error(
        self, fake_mailer, booking_details, bad_email
    ):
        with pytest.raises(ValueError, match="invalid email"):
            send_notification_email(bad_email, booking_details, fake_mailer)
        # Mailer не должен быть вызван — валидация раньше
        fake_mailer.send.assert_not_called()

    def test_returns_false_when_mailer_raises_exception(
        self, fake_mailer, booking_details
    ):
        """SMTP-сервер недоступен -> функция должна вернуть False, не падать."""
        fake_mailer.send.side_effect = ConnectionError("SMTP down")
        result = send_notification_email(
            "user@example.com", booking_details, fake_mailer
        )
        assert result is False

    def test_handles_missing_booking_ref_gracefully(self, fake_mailer):
        """Если в booking_details нет booking_ref — отправка всё равно идёт,
        в теле письма появится 'None'. Главное — не падать."""
        result = send_notification_email(
            "user@example.com", {}, fake_mailer
        )
        assert result is True
        body = fake_mailer.send.call_args.kwargs["body"]
        assert "None" in body
