# Geo App — географический справочник

Модуль `geo` хранит локальный справочник стран, регионов и населённых пунктов на основе открытых данных [GeoNames](https://www.geonames.org/).

После импорта сайт работает только со своей PostgreSQL через Django ORM. GeoNames API в рантайме не используется.

---

## 1. Что хранит модуль

Основная структура:

```text
Country
    └── Region
            └── City
```

- `Country` — страна.
- `Region` — административный регион первого уровня (`admin1` в GeoNames).
- `City` — населённый пункт, прошедший фильтр приложения.

Для названий используются поля:

```text
name_en
name_uk
name_ru
```

Импорт переводов поддерживает только `en`, `uk`, `ru`, потому что именно эти поля существуют в моделях.

---

## 2. Исходные данные

Все данные берутся из GeoNames:

<https://download.geonames.org/export/dump/>

Файлы должны находиться в:

```text
src/geo/data/
```

### Общие файлы

| Файл | Назначение |
|---|---|
| `countryInfo.txt` | страны и ISO-коды |
| `admin1CodesASCII.txt` | регионы первого административного уровня |
| `alternateNamesV2.txt` | английские, украинские и русские названия |

Скачать:

- <https://download.geonames.org/export/dump/countryInfo.txt>
- <https://download.geonames.org/export/dump/admin1CodesASCII.txt>
- <https://download.geonames.org/export/dump/alternateNamesV2.zip>

`alternateNamesV2.txt` получается после распаковки `alternateNamesV2.zip`.

Если `alternateNamesV2.txt` отсутствует, импорт продолжится, но часть локализованных названий будет пустой.

### Файлы населённых пунктов

Для каждой страны нужен отдельный dump:

```text
UA.txt
RU.txt
PL.txt
CZ.txt
DE.txt
...
```

Файл страны скачивается как:

```text
https://download.geonames.org/export/dump/XX.zip
```

Например:

```text
UA.zip -> UA.txt
PL.zip -> PL.txt
```

Текущий набор:

```text
src/geo/data/
├── countryInfo.txt
├── admin1CodesASCII.txt
├── alternateNamesV2.txt
├── UA.txt
├── RU.txt
├── PL.txt
├── CZ.txt
└── DE.txt
```

---

## 3. Команда импорта

Management command находится здесь:

```text
src/geo/management/commands/import_geo.py
```

Из корня проекта:

```bash
python src/manage.py import_geo --help
```

Полный импорт текущих стран:

```bash
python src/manage.py import_geo \
    --country UA RU PL CZ DE
```

По умолчанию выполняются три этапа:

```text
Country -> Region -> City
```

---

## 4. Фильтрация населённых пунктов

GeoNames содержит огромное количество городов, посёлков, сёл и других populated places. В `City` импортируется только нужная приложению часть.

Сначала рассматриваются только объекты:

```text
feature_class = P
```

Далее применяется `feature_code`.

### Административные центры

Эти типы импортируются **всегда**, независимо от `population`:

| Код | Значение |
|---|---|
| `PPLC` | столица государства |
| `PPLA` | административный центр 1-го уровня |
| `PPLA2` | административный центр 2-го уровня |
| `PPLA3` | административный центр 3-го уровня |
| `PPLG` | административно значимый центр / seat of government |

Например:

```text
PPLA2 + population=0 -> импортируется
```

Это сделано специально: отсутствующее или неточное население в GeoNames не должно ломать административный каркас страны.

### Обычные населённые пункты `PPL`

Для `PPL` действует фильтр по населению.

Порог по умолчанию:

```text
MIN_POPULATION = 2500
```

Примеры:

```text
PPL + 50000 -> импортируется
PPL + 2500  -> импортируется
PPL + 2499  -> пропускается
PPL + 0     -> пропускается
```

### Остальные коды

Остальные `feature_code` не импортируются.

Итоговая логика:

```text
feature_class != P
    -> пропустить

PPLC / PPLA / PPLA2 / PPLA3 / PPLG
    -> импортировать всегда

PPL
    -> импортировать при population >= 2500

остальные feature_code
    -> пропустить
```

Правило одинаково для всех стран. Специальной логики для Украины, Германии, Польши и т. д. нет.

---

## 5. `--min-population`

Порог для обычных `PPL` можно изменить при запуске:

```bash
python src/manage.py import_geo \
    --country UA \
    --min-population 5000
```

Важно: этот параметр влияет **только на `PPL`**.

Административные центры:

```text
PPLC
PPLA
PPLA2
PPLA3
PPLG
```

по-прежнему импортируются независимо от населения.

---

## 6. Как работает импорт

При полном запуске команда выполняет следующий flow.

### 1. Проверяет параметры

- ISO-коды приводятся к верхнему регистру.
- Код страны должен состоять из двух букв.
- Дубликаты кодов удаляются.
- `--min-population` не может быть отрицательным.
- Для импорта `cities` или `all` обязательно нужен `--country`.

### 2. Определяет нужные `geoname_id`

До чтения большого `alternateNamesV2.txt` команда собирает ID только тех объектов, которые реально будут участвовать в текущем импорте.

Для городов сюда попадают только населённые пункты, уже прошедшие фильтр.

### 3. Загружает переводы

Из `alternateNamesV2.txt` выбираются только:

```text
en
uk
ru
```

и только для нужных `geoname_id`.

Если для одного языка есть несколько вариантов названия, предпочтение отдаётся более подходящему актуальному варианту; исторические и разговорные названия имеют меньший приоритет.

### 4. Импортирует страны

`Country` читается из:

```text
countryInfo.txt
```

**Важно:** `--country` не ограничивает таблицу `Country`.

Например:

```bash
python src/manage.py import_geo --country UA PL
```

при полном импорте всё равно обрабатывает все страны из `countryInfo.txt`.

`--country` ограничивает только `Region` и `City`.

### 5. Импортирует регионы

`Region` читается из:

```text
admin1CodesASCII.txt
```

Для указанных стран импортируются соответствующие `admin1`-регионы.

### 6. Импортирует населённые пункты

Для каждой страны используется её `XX.txt`.

Регион определяется по сочетанию:

```text
country_code + admin1_code
```

После фильтрации записи сохраняются в `City`.

---

## 7. Режимы запуска

### Полный импорт

```bash
python src/manage.py import_geo --country UA
```

То же самое:

```bash
python src/manage.py import_geo \
    --type all \
    --country UA
```

### Только страны

```bash
python src/manage.py import_geo --type countries
```

`--country` не требуется.

### Только регионы

```bash
python src/manage.py import_geo \
    --type regions \
    --country UA PL
```

Если запустить `--type regions` без `--country`, команда будет рассматривать регионы всех стран. В обычной эксплуатации лучше явно указывать нужные страны.

### Только населённые пункты

```bash
python src/manage.py import_geo \
    --type cities \
    --country UA PL
```

`Country` и `Region` к этому моменту уже должны существовать.

---

## 8. Добавление новой страны

Например, нужно добавить Словакию (`SK`).

1. Скачать:

```text
https://download.geonames.org/export/dump/SK.zip
```

2. Распаковать `SK.txt`.

3. Положить:

```text
src/geo/data/SK.txt
```

4. Выполнить:

```bash
python src/manage.py import_geo --country SK
```

Изменять Python-код для новой страны не требуется: правила фильтрации едины для всех стран.

---

## 9. Повторный импорт и `--update`

Главный идентификатор сущностей:

```text
geoname_id
```

### Без `--update`

```bash
python src/manage.py import_geo --country UA
```

Логика:

```text
записи нет -> создать
запись есть -> пропустить
```

Это подходящий режим для добавления новой страны или недостающих данных.

### С `--update`

```bash
python src/manage.py import_geo \
    --country UA \
    --update
```

Логика:

```text
записи нет -> создать
запись есть -> обновить
```

`--update` работает для:

```text
Country
Region
City
```

У `City` обновляются названия, регион, население, координаты, `feature_code` и связанные поля.

---

## 10. Обновление данных GeoNames

Для обновления справочника:

1. скачать свежие GeoNames dumps;
2. заменить локальные файлы в `src/geo/data/`;
3. выполнить импорт с `--update`.

Например:

```bash
python src/manage.py import_geo \
    --country UA RU PL CZ DE \
    --update
```

Команда создаёт и обновляет данные, но **не удаляет автоматически** старые записи.

Например, если раньше использовался порог `2500`, а затем его изменить на `10000`, старые `PPL` с населением 2500–9999 сами из БД не исчезнут.

Для удаления данных нужна отдельная операция очистки.

---

## 11. Статистика

После каждого этапа команда выводит:

```text
создано
обновлено
пропущено
некорректных строк
```

Для `City` дополнительно:

```text
отфильтровано
```

Пример:

```text
UA: создано 812, обновлено 0, пропущено 0,
отфильтровано 31000, некорректных строк 0.
```

Счётчики отражают фактически обработанные записи.

При `--verbosity 2` дополнительно выводится прогресс сканирования большого `alternateNamesV2.txt`:

```bash
python src/manage.py import_geo \
    --country UA \
    --verbosity 2
```

---

## 12. Проверка после импорта

Количество регионов и населённых пунктов:

```bash
python src/manage.py shell -c "
from geo.models import Country, Region, City

for code in ['UA', 'RU', 'PL', 'CZ', 'DE']:
    country = Country.objects.filter(code2=code).first()
    if not country:
        print(code, 'COUNTRY NOT FOUND')
        continue

    print(
        code,
        'regions=', Region.objects.filter(country=country).count(),
        'cities=', City.objects.filter(country=country).count(),
    )
"
```

Проверка переводов:

```bash
python src/manage.py shell -c "
from geo.models import Country

for country in Country.objects.filter(
    code2__in=['UA', 'RU', 'PL', 'CZ', 'DE']
).order_by('code2'):
    print(
        country.code2,
        '|',
        country.name_en,
        '|',
        country.name_uk,
        '|',
        country.name_ru,
    )
"
```

---

## 13. Импорт в production через SSH-туннель

Команда работает через обычный Django ORM, поэтому локальный `import_geo` можно запускать против удалённой production-БД.

Для проектной конфигурации `remote_server`:

```bash
DJANGO_SETTINGS_MODULE=_config.settings.remote_server \
python src/manage.py import_geo \
    --country UA RU PL CZ DE
```

Flow:

```text
локальные GeoNames-файлы
        ↓
локальный import_geo
        ↓
Django ORM
        ↓
SSH tunnel
        ↓
production PostgreSQL
```

Это позволяет не копировать большие GeoNames-файлы на сервер.

Перед запуском необходимо проверить SSH-туннель и убедиться, что `remote_server` подключён именно к нужной БД.

**Любой такой импорт изменяет реальную production-базу.**

---

## 14. Важные особенности

### `City` — это не буквально только города

Название модели историческое.

GeoNames `PPL` означает обычный populated place и не гарантирует юридический статус «город». Поэтому `City` фактически содержит значимые населённые пункты, отобранные правилами приложения.

### `population=0`

```text
административный центр + population=0 -> импорт
обычный PPL + population=0            -> пропуск
```

### Изменение фильтра не чистит БД

Новый запуск влияет на создаваемые и обновляемые записи, но не удаляет объекты, которые были импортированы по старым правилам.

### Новая страна не требует нового кода

Если GeoNames предоставляет `XX.txt`, обычно достаточно добавить файл и ISO-код в `--country`.

---

## 15. `.gitignore`

GeoNames dumps не должны храниться в Git:

```gitignore
# GeoNames source data
src/geo/data/*.txt
src/geo/data/*.zip
```

---

## Краткий набор команд

Полный импорт:

```bash
python src/manage.py import_geo \
    --country UA RU PL CZ DE
```

Обновление:

```bash
python src/manage.py import_geo \
    --country UA RU PL CZ DE \
    --update
```

Другой порог для `PPL`:

```bash
python src/manage.py import_geo \
    --country UA RU PL CZ DE \
    --min-population 5000
```

Только `City`:

```bash
python src/manage.py import_geo \
    --type cities \
    --country UA RU PL CZ DE
```

Production через `remote_server`:

```bash
DJANGO_SETTINGS_MODULE=_config.settings.remote_server \
python src/manage.py import_geo \
    --country UA RU PL CZ DE
```
