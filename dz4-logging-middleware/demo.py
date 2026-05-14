"""Runnable demo: triggers all logging paths.

Run:
    .venv\\Scripts\\python.exe demo.py

Expected output: a stream of JSON log lines (INFO call / INFO ok for successful
paths, ERROR with traceback for ValueError/KeyError paths) plus
'caught expected: ...' lines for each handled exception. Process exits 0.
"""
from datetime import date, timedelta

from booking_service import create_booking, get_booking
from task_manager_service import complete_task, create_task

if __name__ == "__main__":
    # 1) Booking — успешный путь
    b = create_booking(event_id=1, user_id=101)
    got = get_booking(b["booking_id"])

    # 2) Booking — ValueError (event not found)
    try:
        create_booking(event_id=999, user_id=101)
    except ValueError as e:
        print(f"caught expected: {e}", flush=True)

    # 3) Booking — KeyError (booking not found)
    try:
        get_booking("nonexistent_id")
    except KeyError as e:
        print(f"caught expected: {e}", flush=True)

    # 4) Task — успешный
    t = create_task("Демо", user_id=1, due_date=date.today() + timedelta(days=7))
    complete_task(t["task_id"])

    # 5) Task — ValueError (пустое название)
    try:
        create_task("", user_id=1, due_date=date.today() + timedelta(days=7))
    except ValueError as e:
        print(f"caught expected: {e}", flush=True)

    # 6) Task — ValueError (дата в прошлом)
    try:
        create_task("Late", user_id=1, due_date=date.today() - timedelta(days=1))
    except ValueError as e:
        print(f"caught expected: {e}", flush=True)

    # 7) Task — KeyError (несуществующая задача)
    try:
        complete_task(99999)
    except KeyError as e:
        print(f"caught expected: {e}", flush=True)
