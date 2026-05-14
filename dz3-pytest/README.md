# ДЗ-3, модуль 3: Юнит-тесты Booking-сервиса (pytest)

Курс: Нетология, «Основы тестирования для разработчиков» (`bhembd-25-otdr-2`).
Сервис: **Booking-сервис** (5 функций). Тесты написаны на pytest, используют
фикстуры, параметризацию и мок-объекты.

## Состав

| Файл | Что внутри |
|------|-----------|
| `booking_service.py` | Реализация 5 функций (`calc_price`, `check_availability`, `apply_promo_code`, `generate_booking_ref`, `send_notification_email`) |
| `conftest.py` | Общие фикстуры: `fake_db`, `fake_promo_repo`, `fake_mailer`, `booking_details` |
| `test_booking_service_polyуnova.py` | Сами тесты, по классу на функцию, ≥4 теста на функцию (2 позитивных + 2 негативных) |
| `requirements.txt` | `pytest>=8.0`, `pytest-mock>=3.10`, `freezegun>=1.4` |

## Запуск

```powershell
# из c:\Users\kpoluianova\Documents\study\
.venv\Scripts\pip.exe install -r vault\projects\netology-testing-2sem\module3-hw-files\requirements.txt
.venv\Scripts\pytest.exe vault\projects\netology-testing-2sem\module3-hw-files\ -v
```

Ожидаемый итог: все тесты зелёные (28 passed).

## Что проверяется

### `calc_price(base_price, discount, count) -> float`
- Позитив: расчёт без скидки, со скидкой 20%/50%, бесплатный билет, нулевое количество, округление до 2 знаков.
- Негатив: отрицательное количество, скидка > 100% и < 0, отрицательная базовая цена — все поднимают `ValueError`.

### `check_availability(event_id, seats_requested, db) -> bool`
- Позитив: мест хватает; запрос ровно на остаток.
- Негатив: мест недостаточно; событие не найдено (`LookupError`); нулевое/отрицательное `seats_requested` (`ValueError`, мок БД не вызывается).

### `apply_promo_code(order_id, promo_code, repo) -> bool`
- Позитив: валидный промокод; бессрочный (без `expires_at`); срок истекает завтра при «замороженном» сегодня (`freezegun`).
- Негатив: промокод не найден, истёкший, исчерпан (`uses_left == 0`).

### `generate_booking_ref(user_id, event_id) -> str`
- Позитив: формат `BOOK-<user>-<event>-<hex8>`, корректные id внутри, уникальность 100 подряд вызовов.
- Негатив (через мок): при замокированном `secrets.token_hex` суффикс предсказуем — два вызова дают одинаковый референс; подмена корректно отражается в результате.

### `send_notification_email(email, booking_details, mailer) -> bool`
- Позитив: успешная отправка, корректное тело и тема письма.
- Негатив: невалидные email (`""`, без `@`, пробелы), сбой SMTP (`ConnectionError` → `False`), отсутствующий `booking_ref` в данных.

## Использованные техники pytest

- `@pytest.fixture` в `conftest.py` — переиспользуемые моки `MagicMock`.
- `@pytest.mark.parametrize` — табличное тестирование (DDT) валидных/невалидных входов.
- `pytest.raises(..., match=...)` — проверка исключений и текста сообщения.
- `pytest-mock` (`mocker.patch`) — патч `secrets.token_hex` в модуле под тестом.
- `freezegun.freeze_time` — детерминированная подмена `datetime.utcnow()` для тестов промокодов.
- `assert_called_once_with`, `assert_not_called`, `call_args.kwargs` — проверка
  взаимодействия с моками (BDD-стиль «behavior verification»).

## Источники из курса

- 3.1 — Принципы юнит-тестирования
- 3.2 — Mock-объекты (`MagicMock`, side_effect, поведение vs. состояние)
- 3.3 — TDD / DDT / DDD (параметризация = DDT)
- 3.4 — Pytest (фикстуры, маркеры, параметризация)
- 3.5 — Практические примеры
