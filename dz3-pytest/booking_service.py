"""Booking-сервис для ДЗ-3 модуля 3 (Нетология, «Основы тестирования для разработчиков»).

5 функций, для которых пишутся юнит-тесты:
  1. calc_price                — чистая функция расчёта цены
  2. check_availability        — обращение к БД (мок)
  3. apply_promo_code          — обращение к репозиторию промокодов (мок) + время (freezegun)
  4. generate_booking_ref      — генерация уникального идентификатора (формат + уникальность)
  5. send_notification_email   — отправка письма через внешний mail-сервис (мок)
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


# === Контракты внешних зависимостей (для мока) =============================


class PromoRepo(Protocol):
    """Репозиторий промокодов — отдаёт словарь с полями
    `expires_at: datetime | None` и `uses_left: int`."""

    def get(self, code: str) -> dict | None: ...


class MailService(Protocol):
    """Сервис отправки писем — возвращает True при успешной доставке."""

    def send(self, to: str, subject: str, body: str) -> bool: ...


class BookingDB(Protocol):
    """База данных бронирований — возвращает остаток мест на событии или None."""

    def get_remaining_seats(self, event_id: int) -> int | None: ...


# === 1. calc_price =========================================================


def calc_price(base_price: float, discount: float, count: int) -> float:
    """Итоговая стоимость count билетов по цене base_price со скидкой discount.

    discount задаётся как доля от единицы (0.2 == 20%).
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    if not (0 <= discount <= 1):
        raise ValueError("discount must be between 0 and 1")
    if base_price < 0:
        raise ValueError("base_price must be >= 0")
    return round(base_price * count * (1 - discount), 2)


# === 2. check_availability =================================================


def check_availability(event_id: int, seats_requested: int, db: BookingDB) -> bool:
    """True, если в БД зарегистрировано не менее seats_requested свободных мест."""
    if seats_requested <= 0:
        raise ValueError("seats_requested must be > 0")
    remaining = db.get_remaining_seats(event_id)
    if remaining is None:
        raise LookupError(f"event {event_id} not found")
    return remaining >= seats_requested


# === 3. apply_promo_code ===================================================


def apply_promo_code(order_id: int, promo_code: str, repo: PromoRepo) -> bool:
    """True, если промокод существует, не истёк и имеет оставшиеся применения."""
    data = repo.get(promo_code)
    if data is None:
        return False
    expires_at = data.get("expires_at")
    if expires_at is not None and expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        return False
    if data.get("uses_left", 0) <= 0:
        return False
    return True


# === 4. generate_booking_ref ===============================================


def generate_booking_ref(user_id: int, event_id: int) -> str:
    """Возвращает уникальный референс брони формата BOOK-<user>-<event>-<hex8>."""
    suffix = secrets.token_hex(4)  # 8 hex-символов
    return f"BOOK-{user_id}-{event_id}-{suffix}"


# === 5. send_notification_email ============================================


def send_notification_email(
    email: str, booking_details: dict, mailer: MailService
) -> bool:
    """Отправляет письмо-подтверждение. False при сбое внешнего сервиса."""
    if "@" not in email:
        raise ValueError("invalid email")
    try:
        return mailer.send(
            to=email,
            subject="Бронирование подтверждено",
            body=f"Ваша бронь {booking_details.get('booking_ref')} подтверждена.",
        )
    except Exception:
        return False
