# Нетология — «Основы тестирования для разработчиков» (BHEMBD-25-OTDR-2)

Решения домашних заданий по курсу из магистратуры «Разработка IT-продукта» (МФТИ × Нетология).

**Автор:** Полуянова Ксения
**Курс в LMS:** https://netology.ru/profile/program/bhembd-25-otdr-2/

## Структура

| ДЗ | Тема | Дедлайн | Папка |
|----|------|---------|-------|
| ДЗ-3 | Unit-тестирование на PyTest | 08.03.2026 | [`dz3-pytest/`](dz3-pytest/) |
| ДЗ-4 | Middleware для логирования | 22.03.2026 | [`dz4-logging-middleware/`](dz4-logging-middleware/) |

## Запуск

Все ДЗ написаны под Python 3.13. Создание окружения:

```bash
python -m venv .venv
.venv\Scripts\activate         # Windows
source .venv/bin/activate      # macOS/Linux
```

Зависимости для каждого ДЗ в `requirements.txt` соответствующей подпапки.

## ДЗ-3 — PyTest для Booking-сервиса

5 функций × минимум 2 позитивных + 2 негативных теста = 36 тестов всего.

```bash
cd dz3-pytest
pip install -r requirements.txt
pytest -v
```

Использованные техники: `@pytest.fixture` (общие — в `conftest.py`), `@pytest.mark.parametrize`, `unittest.mock.MagicMock` через `pytest-mock`, `freezegun` для подмены времени.

Подробности: [`dz3-pytest/README.md`](dz3-pytest/README.md).

## ДЗ-4 — Middleware для логирования

Декоратор `@logged(logger_name)`:
- Логирует факт вызова с аргументами (`event=call`, level INFO)
- Логирует успешный результат (`event=ok`, level INFO)
- Перехватывает `ValueError` / `KeyError`, логирует `event=error` с полным traceback (level ERROR) и **пробрасывает исключение дальше** (re-raise)
- Все записи — валидный JSON в одну строку (structured logging, ready for ELK/Loki/Datadog)

```bash
cd dz4-logging-middleware
python demo.py
```

Demo прогоняет happy path и каждое из 5 исключений (ValueError/KeyError в Booking + TaskManager) — выдаёт 9 INFO и 5 ERROR JSON-логов.

Подробности: [`dz4-logging-middleware/README.md`](dz4-logging-middleware/README.md).
