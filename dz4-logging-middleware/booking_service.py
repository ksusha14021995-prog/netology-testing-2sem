"""Booking service — original homework source, instrumented with @logged."""
import datetime

from middleware import logged

# Упрощенная «база» мероприятий
EVENTS_DB = {
    1: {"title": "Football Match", "available_seats": 10, "date": datetime.date(2025, 7, 1)},
    2: {"title": "Basketball Playoffs", "available_seats": 5, "date": datetime.date(2025, 7, 2)},
    3: {"title": "Tennis Open", "available_seats": 3, "date": datetime.date(2025, 7, 3)},
}

# Упрощенная «база» бронирований (хранилище в памяти)
BOOKINGS_DB: dict[str, dict] = {}


@logged("booking")
def create_booking(event_id: int, user_id: int) -> dict:
    """
    Создает бронь на мероприятие event_id для пользователя user_id.
    Возвращает словарь с данными о брони или выбрасывает ValueError при ошибках.
    """
    if event_id not in EVENTS_DB:
        raise ValueError(f"Event with id={event_id} does not exist.")

    event_info = EVENTS_DB[event_id]
    if event_info["available_seats"] <= 0:
        raise ValueError("No available seats.")

    event_info["available_seats"] -= 1

    booking_id = f"{int(datetime.datetime.now().timestamp())}_{user_id}"

    BOOKING_DATA = {
        "booking_id": booking_id,
        "event_id": event_id,
        "user_id": user_id,
        "title": event_info["title"],
        "date": event_info["date"],
        "created_at": datetime.datetime.now(),
    }
    BOOKINGS_DB[booking_id] = BOOKING_DATA
    return BOOKING_DATA


@logged("booking")
def get_booking(booking_id: str) -> dict:
    """
    Возвращает данные о конкретной брони по booking_id.
    Поднимает KeyError, если брони нет.
    """
    return BOOKINGS_DB[booking_id]


if __name__ == "__main__":
    booking = create_booking(event_id=1, user_id=101)
    print("Created booking:", booking)

    retrieved = get_booking(booking["booking_id"])
    print("Retrieved booking:", retrieved)
