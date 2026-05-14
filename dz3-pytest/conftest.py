"""Общие фикстуры для тестов Booking-сервиса.

Лежат в conftest.py, чтобы автоматически попадать в любой test_*.py модуль
в этом каталоге.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest


# === Базовые моки внешних зависимостей =====================================


@pytest.fixture
def fake_db() -> MagicMock:
    """Мок БД бронирований. По умолчанию возвращает 10 свободных мест.

    Тест может переопределить return_value/side_effect:
        fake_db.get_remaining_seats.return_value = 0
        fake_db.get_remaining_seats.side_effect = ConnectionError(...)
    """
    db = MagicMock(name="BookingDB")
    db.get_remaining_seats.return_value = 10
    return db


@pytest.fixture
def fake_promo_repo() -> MagicMock:
    """Мок репозитория промокодов. По умолчанию возвращает валидный промокод
    SAVE10 (срок ещё месяц, 5 применений в запасе).
    """
    repo = MagicMock(name="PromoRepo")
    repo.get.return_value = {
        "expires_at": datetime.now() + timedelta(days=30),
        "uses_left": 5,
        "discount": 0.1,
    }
    return repo


@pytest.fixture
def fake_mailer() -> MagicMock:
    """Мок mail-сервиса. По умолчанию имитирует успешную отправку (True)."""
    mailer = MagicMock(name="MailService")
    mailer.send.return_value = True
    return mailer


# === Хелперы =================================================================


@pytest.fixture
def booking_details() -> dict:
    """Типовая структура booking_details, передаваемая в send_notification_email."""
    return {
        "booking_ref": "BOOK-1-42-abcd1234",
        "event_title": "Концерт Pytest Live",
        "seats": 2,
        "total_price": 1800.0,
    }
