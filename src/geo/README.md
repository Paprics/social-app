# Geo App — справочник стран, регионов и городов

Этот модуль реализует географический справочник на основе открытых данных
[GeoNames](https://www.geonames.org/) — бесплатной базы всех населённых пунктов
мира с переводами названий на десятки языков.

---

## Принцип работы

Данные хранятся в трёх таблицах Django:

```
Country (252 записи — все страны мира)
    └── Region (области / штаты / провинции)
            └── City (города и населённые пункты)
```

Все три модели имеют поля `name_en`, `name_uk`, `name_ru` — названия на
разных языках. В шаблонах используется метод `get_name()`, который автоматически
возвращает нужный язык в зависимости от текущей локали Django.

Данные импортируются **один раз** management-командой `import_geo` из дампов
GeoNames. После импорта сайт работает полностью автономно — никаких внешних
API-запросов в рантайме нет.

---

## Откуда брать файлы

Все файлы доступны бесплатно: https://download.geonames.org/export/dump/

Файлы **не хранятся в репозитории** (добавлены в `.gitignore`) — их нужно
скачивать вручную на каждом окружении (dev, prod).

### Справочные файлы (нужны всегда, для любой страны)

| Файл | Ссылка | Описание | Размер |
|---|---|---|---|
| `countryInfo.txt` | [ссылка](https://download.geonames.org/export/dump/countryInfo.txt) | 252 страны мира с кодами ISO | ~25 KB |
| `admin1CodesASCII.txt` | [ссылка](https://download.geonames.org/export/dump/admin1CodesASCII.txt) | Регионы/области всех стран | ~120 KB |
| `alternateNamesV2.txt` | из [alternateNamesV2.zip](https://download.geonames.org/export/dump/alternateNamesV2.zip) | Переводы всех названий (ru, uk, en, pl, ...) | ~400 MB распакованный |

`alternateNamesV2.zip` — самый большой файл (~120 MB zip, ~400 MB txt).
Скачай, распакуй, положи `alternateNamesV2.txt` в эту папку.
Без него импорт пройдёт, но названия на uk/ru не подтянутся.

### Файлы населённых пунктов (по одному на страну)

| Файл | Ссылка | Страна |
|---|---|---|
| `UA.txt` | из [UA.zip](https://download.geonames.org/export/dump/UA.zip) | Украина |
| `PL.txt` | из [PL.zip](https://download.geonames.org/export/dump/PL.zip) | Польша |
| `CZ.txt` | из [CZ.zip](https://download.geonames.org/export/dump/CZ.zip) | Чехия |
| `RU.txt` | из [RU.zip](https://download.geonames.org/export/dump/RU.zip) | Россия |
| `DE.txt` | из [DE.zip](https://download.geonames.org/export/dump/DE.zip) | Германия |

Полный список стран: https://download.geonames.org/export/dump/ (файлы вида `XX.zip`)

---

## Первоначальная установка (с нуля)

### Шаг 1 — Скачать файлы в эту папку

```
geo/data/
├── countryInfo.txt          # скачать напрямую
├── admin1CodesASCII.txt     # скачать напрямую
├── alternateNamesV2.txt     # распаковать из alternateNamesV2.zip
└── UA.txt                   # распаковать из UA.zip
```

### Шаг 2 — Применить миграции (если ещё не сделано)

```bash
python manage.py makemigrations geo
python manage.py migrate
```

### Шаг 3 — Запустить импорт

```bash
# Всё для Украины одной командой:
python manage.py import_geo --country UA
```

Эта команда последовательно выполнит четыре этапа:
1. Загрузит переводы из `alternateNamesV2.txt`
2. Импортирует все 252 страны из `countryInfo.txt`
3. Импортирует регионы UA из `admin1CodesASCII.txt`
4. Импортирует города UA из `UA.txt`

Ожидаемый результат:
```
Страны: создано 252
Регионы: создано 27        # все области Украины
UA: создано ~32500 записей # все населённые пункты
```

---

## Добавление новой страны (пример: Польша)

Когда страны уже импортированы и нужно добавить ещё одну:

**1. Скачать файл страны:**
```
geo/data/PL.txt   ← распаковать из PL.zip
```

**2. Запустить импорт только для Польши:**
```bash
python manage.py import_geo --country PL
```

Страны (252) уже есть в БД — команда их пропустит (`пропущено 252`).
Регионы и города PL будут добавлены.

**Или сразу несколько стран:**
```bash
# Скачать UA.zip, PL.zip, CZ.zip → распаковать в geo/data/
python manage.py import_geo --country UA PL CZ
```

---

## Справочник всех команд

```bash
# Только страны (252 записи, без регионов и городов)
python manage.py import_geo --type countries

# Только регионы для Украины
python manage.py import_geo --type regions --country UA

# Только города для Украины
python manage.py import_geo --type cities --country UA

# Всё сразу для одной страны
python manage.py import_geo --country UA

# Всё сразу для нескольких стран
python manage.py import_geo --country UA PL CZ RU

# Только крупные города (от 10 000 жителей) — меньше записей, быстрее
python manage.py import_geo --country UA --min-population 10000

# Обновить существующие записи (по умолчанию пропускает дубликаты)
python manage.py import_geo --country UA --update

# Импорт с конкретными языками переводов
python manage.py import_geo --country UA --languages en uk ru pl
```

---

## Обновление данных

GeoNames обновляется регулярно. Обновление данных в БД:

```bash
# Скачать свежие файлы (заменить старые в geo/data/)
# Затем запустить с флагом --update:
python manage.py import_geo --country UA --update
```

Флаг `--update` перезаписывает существующие записи по `geoname_id`.
Без него — существующие записи пропускаются (быстрее, но не обновляет изменения).

---

## Структура файлов GeoNames (для понимания)

**`countryInfo.txt`** — TSV, 18 колонок:
```
ISO  ISO3  ISO-Numeric  fips  Country  Capital  Area  Population  Continent  ...  geonameid  neighbours
UA   UKR   804          UP    Ukraine  Kyiv     ...   40000000    EU         ...  690791     RU,BY,PL,...
```

**`admin1CodesASCII.txt`** — TSV, 4 колонки:
```
UA.01   Crimea              Crimea          ...  geonameid
UA.26   Kyiv City           Kyiv City       ...  703448
```

**`UA.txt`** — главный дамп, TSV, 19 колонок:
```
geonameid  name   asciiname  ...  feature_class  feature_code  country_code  admin1_code  population  ...
703448     Kyiv   Kyiv       ...  P              PPLC          UA            26           2797553     ...
```
Импортируются только строки с `feature_class = P` (populated place).

**`alternateNamesV2.txt`** — TSV, переводы:
```
alt_id  geoname_id  lang  alternate_name  ...
12345   703448      uk    Київ
12346   703448      ru    Киев
12347   703448      en    Kyiv
```

---

## .gitignore

Добавь в корневой `.gitignore` проекта:

```gitignore
# GeoNames data files (скачиваются вручную, не хранятся в репо)
geo/data/*.txt
geo/data/*.zip
```

---

## Проверка после импорта

```bash
python manage.py shell -c "
from geo.models import Country, Region, City
print('Стран:', Country.objects.count())
print('Регионов UA:', Region.objects.filter(country__code2='UA').count())
print('Городов UA:', City.objects.filter(country__code2='UA').count())
ua = Country.objects.get(code2='UA')
print('Украина EN:', ua.name_en)
print('Украина UK:', ua.name_uk)
print('Украина RU:', ua.name_ru)
kyiv = City.objects.filter(name_en='Kyiv').first()
if kyiv:
    print('Киев:', kyiv.name_en, '/', kyiv.name_uk, '/', kyiv.name_ru)
"
```

Ожидаемый вывод:
```
Стран: 252
Регионов UA: 27
Городов UA: ~32500
Украина EN: Ukraine
Украина UK: Україна
Украина RU: Украина
Киев: Kyiv / Київ / Киев
```

Визуальный контроль — админка: `/admin/geo/`