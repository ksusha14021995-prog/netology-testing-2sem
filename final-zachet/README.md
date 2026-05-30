# Итоговое задание — «Основы тестирования для разработчиков»

Полуянова Ксения, поток BHEMBD-25-OTDR-2, эксперт — Антон Касимов.
Дата сдачи: 30.05.2026.

## Итоговые метрики

| Метрика | Цель | Факт |
|---|---|---|
| Mutation Score (mutmut) | ≥ 80% | **97.2%** (104 killed / 3 survived из 107) |
| Branch coverage (pytest-cov) | ≥ 70% | **100%** (14/14 веток + 79/79 строк) |
| Pytest tests | — | **241 passed in ~0.4 s** |

## Структура решения

```
final-zachet/
├── billing/               # production-код — НЕ менялся
│   ├── __init__.py
│   └── calculator.py
├── tests/
│   ├── conftest.py
│   ├── test_pricing.py        # price_with_tax, apply_coupon, validate_coupon,
│   │                          # apply_dynamic_tax, tax_breakdown, COUPON_CODES
│   ├── test_quantities.py     # compute_subtotal, booking_fee, bulk_discount,
│   │                          # compute_bulk_total, compute_total
│   ├── test_currency.py       # convert_currency, SUPPORTED_CURRENCIES
│   ├── test_payments.py       # split_payment, compute_refund,
│   │                          # apply_loyalty_discount, loyalty_points_earned
│   └── test_misc.py           # parse_iso_date, validate_tax_number, cap_price,
│                              # round_money, is_weekend_rate
├── scripts/
│   └── export_mut_json.py     # читает .mutmut-cache (sqlite) → mut.json
│                              # (нужен потому что `mutmut results json`
│                              # в 2.5.1 падает из-за бага Pony ORM)
├── mut.json                   # итоговый отчёт по мутантам
├── htmlcov/                   # HTML-отчёт покрытия (pytest-cov)
├── Makefile                   # install / test / mutate / htmlcov / results / clean
├── requirements.txt           # pytest~=8.2, pytest-cov~=5.0, mutmut~=2.4, coverage~=7.5
└── .mutmut-config             # paths_to_mutate=billing, runner=python -m pytest -q
```

## Стратегия и подходы

Все изменения внесены **только в `tests/`**, как требует задание. Production-код
`billing/calculator.py` не модифицирован.

### 1. От заглушек к полному покрытию по веткам

Стартовый `test_skeleton.py` содержал 8 пустых функций (`...`). Они давали
~32% statement coverage и 0% mutation kill rate, потому что ничего не утверждали.
Я заменила его на 5 тематических модулей. Принципы:

- **Каждой функции — отдельный класс `TestX`**, каждой ветке — отдельный тест.
- **Граничные значения для всех сравнений.** Для `qty <= 0` — `qty=0`,
  `qty=1`, `qty=-1`. Для `bulk_discount` — `qty=9`/`10`/`19`/`20`. Для
  `compute_refund` — `pct=0`, `pct=1`, `pct=-0.01`, `pct=1.01`.
- **Все ветви `if/elif/else` проходим обе стороны.** В `apply_dynamic_tax`
  проверены `"LV"`, `"lv"`, `"NL"`, `"DE"`, `"FR"`, `"US"`.
- **Точные численные результаты**, а не «больше нуля». Например,
  `assert price_with_tax(100.0) == 121.0` пиннит `TAX_RATE = 0.21`;
  `assert apply_coupon(100.0, "SPORT10") == 90.0` пиннит ставку купона 0.10.

### 2. Целенаправленная борьба с мутантами

Запустив `mutmut run` первый раз, получила 8 выживших мутантов. Прошлась по
каждому через `mutmut show <id>` и усилила соответствующие тесты:

- **Мутанты строк сообщений в `raise`.** В первой версии я использовала
  `pytest.raises(ValueError, match="positive")`. Этот partial-match не убивает
  мутацию `"qty must be positive"` → `"XXqty must be positiveXX"`, потому что
  `re.search` всё ещё находит подстроку. Заменила на точное сравнение:
  ```python
  with pytest.raises(ValueError) as exc_info:
      compute_subtotal(10.0, 0)
  assert str(exc_info.value) == "qty must be positive"
  ```
  Аналогично — для `price_with_tax`, `split_payment`, `compute_refund`,
  `convert_currency` (там через `exc_info.value.args[0]`, потому что
  `KeyError` оборачивает сообщение в кавычки).

- **Case-чувствительные пути.** `apply_coupon("sport10")`,
  `apply_dynamic_tax("lv")`, `convert_currency("usd")` — все убивают
  мутацию `coupon.upper()` → `coupon.lower()` или удаление `.upper()`.

- **Точечный пин констант.** Тесты вида
  `assert COUPON_CODES["SPORT10"] == 0.10` и
  `assert SUPPORTED_CURRENCIES == {"EUR": 1.0, "USD": 0.92, "GBP": 1.15}`
  фиксируют значения словарей напрямую — страховка от мутаций, которые
  не убиваются через поведение.

- **Двойные assert'ы для tuple-возвратов.** В `tax_breakdown` отдельно
  утверждаются `result[0]` и `result[1]` — мутант, меняющий один из
  возвращаемых элементов, не выживет.

- **Boundary в `is_weekend_rate`.** Тесты пятницы (False) и субботы (True)
  пиннят сравнение `>= 5`, отличая от `> 5` и `>= 4`.

- **Clamp в `apply_loyalty_discount`.** Тест `points=2000, gross=10.0`
  гарантирует, что мутация `max(0.0, …)` → `min(0.0, …)` или удаление
  clamp'а будет поймана отрицательным значением.

### 3. Оставшиеся 3 мутанта — equivalent mutants

После всех улучшений выжили только 3 мутации, и все они математически
эквивалентны оригиналу — никакой тест не может их отличить, не меняя
production-код:

1. **`apply_coupon`, строка `coupon.upper() if coupon else ""`** → fallback
   `""` мутируется на `"XXXX"`. Когда `coupon` falsy,
   `COUPON_CODES.get("XXXX", 0.0)` возвращает те же `0.0` (т.к. `"XXXX"` нет
   в словаре), поведение неотличимо.

2-3. **`round_money`, `Decimal((0, (1,), -decimals))`** — два мутанта
   меняют sign-бит и coefficient-кортеж внутри Decimal-конструктора.
   `Decimal.quantize` использует **только экспоненту** шаблона; sign и
   coefficient игнорируются. Любые `Decimal((1, (2,), -2))`,
   `Decimal((0, (5,), -2))` ведут себя как `Decimal("0.01")` — quantize
   ROUND_HALF_UP даёт идентичный результат.

Чтобы убить эти мутации, пришлось бы изменить production-код (например,
`Decimal("0." + "0"*(decimals-1) + "1")` вместо тупл-конструктора), что
запрещено условиями задания.

### 4. Воспроизводимость и Windows-нюансы

- Venv лежит локально в `.venv/` (исключён из git).
- Все команды используют `.venv/Scripts/python.exe` — никаких глобальных
  установок.
- `mutmut run` на Windows требует `PYTHONIOENCODING=utf-8`, иначе спиннер
  с эмодзи 🎉/🤔/🙁 крашится на cp1251.
- `mutmut results` и `mutmut junitxml` в версии 2.5.1 падают из-за бага
  Pony ORM (`QueryResultIterator object is not iterable`). Поэтому
  `mut.json` собирается напрямую из `.mutmut-cache` (sqlite) — скрипт
  `scripts/export_mut_json.py`.

## Как воспроизвести

```bash
# С нуля в чистом окружении:
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt    # Windows
# или: source .venv/bin/activate && pip install -r requirements.txt

# Базовый прогон тестов:
.venv/Scripts/python -m pytest -q

# Покрытие с HTML-отчётом:
.venv/Scripts/python -m pytest --cov=billing --cov-branch --cov-report=html

# Мутационное тестирование (Windows: задать PYTHONIOENCODING=utf-8):
PATH=".venv/Scripts:$PATH" PYTHONIOENCODING=utf-8 \
    .venv/Scripts/python -m mutmut run --paths-to-mutate billing

# Сборка mut.json:
.venv/Scripts/python scripts/export_mut_json.py
```
