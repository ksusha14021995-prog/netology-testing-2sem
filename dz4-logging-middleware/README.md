# ДЗ-4 (модуль 5) — Middleware для логирования

## Файлы

- `middleware.py` — реализация декоратора `@logged(logger_name)` и
  `JsonFormatter` для structured JSON logging.
- `booking_service.py` — исходный сервис из ДЗ, функции обёрнуты
  `@logged("booking")`.
- `task_manager_service.py` — исходный сервис из ДЗ, функции обёрнуты
  `@logged("task_manager")`.
- `demo.py` — запускаемая демонстрация всех веток (успех + ошибки).

## Запуск

```powershell
cd c:\Users\kpoluianova\Documents\study\vault\projects\netology-testing-2sem\module5-hw-files
..\..\..\..\..\.venv\Scripts\python.exe demo.py
```

## Что покажет каждая ветка

| # | Сценарий                                              | Уровни логов            | Исход                                  |
|---|--------------------------------------------------------|-------------------------|----------------------------------------|
| 1 | `create_booking(1, 101)` — корректный                  | INFO `call` → INFO `ok` | Возвращает dict с booking_id           |
| 2 | `get_booking(<valid_id>)`                              | INFO `call` → INFO `ok` | Возвращает данные брони                |
| 3 | `create_booking(999, 101)` — несуществующее event     | INFO `call` → ERROR     | `ValueError` пробрасывается            |
| 4 | `get_booking("nonexistent_id")`                        | INFO `call` → ERROR     | `KeyError` пробрасывается              |
| 5 | `create_task("Демо", …)` — корректный                  | INFO `call` → INFO `ok` | Возвращает dict с task_id              |
| 6 | `complete_task(<valid_id>)`                            | INFO `call` → INFO `ok` | Возвращает dict с completed=True       |
| 7 | `create_task("", …)` — пустое название                 | INFO `call` → ERROR     | `ValueError` пробрасывается            |
| 8 | `create_task("Late", due_date=yesterday)`              | INFO `call` → ERROR     | `ValueError` пробрасывается            |
| 9 | `complete_task(99999)` — несуществующий id             | INFO `call` → ERROR     | `KeyError` пробрасывается              |

Все исключения (3, 4, 7, 8, 9) ловятся в `demo.py` блоками `try/except`, поэтому
процесс завершается с кодом 0. `caught expected: ...` подтверждает, что
исключение действительно вылетело наверх после логирования.

## Структура JSON-лога

Каждая строка stdout — это валидный JSON, который можно скормить ELK / Loki /
любому JSON-aware агрегатору без regex-парсинга:

```json
{
  "ts": "2026-05-14T...Z",
  "level": "INFO",
  "logger": "booking",
  "msg": "call create_booking",
  "function": "create_booking",
  "args": [],
  "kwargs": {"event_id": "1", "user_id": "101"},
  "event": "call"
}
```

Для ERROR добавляется блок `error` с типом, сообщением и traceback'ом.

## Соответствие критериям ДЗ

- [x] Middleware оформлен как декоратор (`@logged`).
- [x] Логируется факт вызова + аргументы (event_id, user_id, booking_id,
      task_id и пр.).
- [x] Логируется результат (успех — `event=ok` с `result_type`/`result_repr`;
      ошибка — `event=error` с типом и traceback'ом).
- [x] `ValueError` и `KeyError` перехватываются, логируются и
      пробрасываются (`raise` без аргументов сохраняет оригинальный
      traceback).
- [x] Применено к `create_booking`, `get_booking`, `create_task`, `complete_task`.
