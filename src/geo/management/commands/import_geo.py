"""
Импорт гео-данных из GeoNames dumps.

Использование:
    # Импортировать страны (один раз для всех проектов)
    python manage.py import_geo --type countries

    # Импортировать регионы и города для Украины
    python manage.py import_geo --type regions --country UA
    python manage.py import_geo --type cities --country UA

    # Всё сразу для одной страны
    python manage.py import_geo --country UA

    # Несколько стран
    python manage.py import_geo --country UA PL CZ

Файлы (положить в geo/data/):
    geo/data/countryInfo.txt         — скачать с geonames.org/export/dump/countryInfo.txt
    geo/data/admin1CodesASCII.txt    — скачать с geonames.org/export/dump/admin1CodesASCII.txt
    geo/data/alternateNamesV2.txt    — из alternateNamesV2.zip (geonames.org/export/dump/)
    geo/data/UA.txt                  — из UA.zip (geonames.org/export/dump/UA.zip)
    geo/data/PL.txt                  — из PL.zip и т.д.
"""

import csv
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from geo.models import City, Country, Region

logger = logging.getLogger(__name__)

# Директория с input-файлами — живёт прямо в app
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Типы населённых пунктов из GeoNames (P = populated place)
# Только административные центры и значимые города — без сёл и деревень
CITY_FEATURE_CODES = {
    "PPLC",  # столица страны
    "PPLA",  # административный центр 1-го уровня (областной центр)
    "PPLA2",  # административный центр 2-го уровня (районный центр / місто)
    "PPLA3",  # административный центр 3-го уровня
    "PPLG",  # seat of government
    # PPL, PPLF, PPLL, PPLR, PPLS, STLMT — намеренно исключены (сёла, деревни)
}

# Минимальная популяция для импорта.
# 5000 отсекает совсем маленькие посёлки, оставляет районные центры.
# Можно поднять до 10000 если список всё ещё большой.
MIN_POPULATION = 2500


class Command(BaseCommand):
    help = "Импортирует страны, регионы и города из GeoNames dumps в базу данных"

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=["countries", "regions", "cities", "all"],
            default="all",
            help="Что импортировать (default: all)",
        )
        parser.add_argument(
            "--country",
            nargs="+",
            metavar="CODE",
            help="ISO коды стран для импорта регионов/городов (например: UA PL CZ)",
        )
        parser.add_argument(
            "--min-population",
            type=int,
            default=MIN_POPULATION,
            help="Минимальная популяция города (default: 0 — все)",
        )
        parser.add_argument(
            "--languages",
            nargs="+",
            default=["en", "uk", "ru"],
            metavar="LANG",
            help="Языки для импорта переводов (default: en uk ru)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Обновлять существующие записи (default: пропускать)",
        )

    def handle(self, *args, **options):
        import_type = options["type"]
        countries = (
            [c.upper() for c in options["country"]] if options["country"] else None
        )
        self.min_population = options["min_population"]
        self.languages = options["languages"]
        self.update = options["update"]

        self.stdout.write(f"DATA_DIR: {DATA_DIR}")
        if not DATA_DIR.exists():
            raise CommandError(
                f"Директория {DATA_DIR} не существует. "
                f"Создайте её и положите туда файлы из GeoNames."
            )

        # Загружаем переводы один раз — они нужны и для регионов и для городов
        alt_names = {}
        if import_type in ("regions", "cities", "all"):
            alt_names = self._load_alternate_names()

        if import_type in ("countries", "all"):
            self._import_countries(alt_names)

        if import_type in ("regions", "all"):
            self._import_regions(countries, alt_names)

        if import_type in ("cities", "all"):
            self._import_cities(countries, alt_names)

        self.stdout.write(self.style.SUCCESS("Импорт завершён."))

    # ------------------------------------------------------------------
    # Загрузка alternate names
    # ------------------------------------------------------------------

    def _load_alternate_names(self):
        """
        Загружает alternateNamesV2.txt и возвращает словарь:
            {geoname_id: {lang_code: name}}
        Фильтрует только нужные языки.
        """
        path = DATA_DIR / "alternateNamesV2.txt"
        if not path.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Файл {path} не найден — переводы не будут загружены. "
                    f"Скачайте alternateNamesV2.zip с geonames.org/export/dump/"
                )
            )
            return {}

        self.stdout.write("Загружаю переводы из alternateNamesV2.txt...")
        alt_names = {}
        langs_set = set(self.languages)
        count = 0

        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                # alternateNameId, geonameid, isolanguage, alternate name, ...
                if len(row) < 4:
                    continue
                lang = row[2]
                if lang not in langs_set:
                    continue
                try:
                    geoname_id = int(row[1])
                except ValueError:
                    continue
                name = row[3]
                if geoname_id not in alt_names:
                    alt_names[geoname_id] = {}
                # Берём первое встречное название на каждый язык
                if lang not in alt_names[geoname_id]:
                    alt_names[geoname_id][lang] = name
                    count += 1

        self.stdout.write(
            f"  Загружено {count} переводов для {len(alt_names)} объектов."
        )
        return alt_names

    # ------------------------------------------------------------------
    # Страны
    # ------------------------------------------------------------------

    def _import_countries(self, alt_names):
        path = DATA_DIR / "countryInfo.txt"
        if not path.exists():
            raise CommandError(
                f"Файл {path} не найден. "
                f"Скачайте с geonames.org/export/dump/countryInfo.txt"
            )

        self.stdout.write("Импортирую страны...")
        created = updated = skipped = 0

        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.rstrip("\n").split("\t")
                # countryInfo.txt имеет 17-19 колонок в зависимости от строки
                # минимум нужно 17: индексы 0-16, geoname_id = parts[16]
                if len(parts) < 17:
                    continue
                try:
                    geoname_id = int(parts[16].strip())
                except (ValueError, IndexError):
                    continue

                code2 = parts[0].strip()
                if not code2:
                    continue
                translations = alt_names.get(geoname_id, {})

                defaults = {
                    "code2": code2,
                    "code3": parts[1].strip() if len(parts) > 1 else "",
                    "continent": parts[8].strip() if len(parts) > 8 else "",
                    "phone_code": parts[12].strip() if len(parts) > 12 else "",
                    "name_en": translations.get(
                        "en", parts[4].strip() if len(parts) > 4 else code2
                    ),
                    "name_uk": translations.get("uk", ""),
                    "name_ru": translations.get("ru", ""),
                }

                obj, was_created = Country.objects.get_or_create(
                    geoname_id=geoname_id, defaults=defaults
                )
                if was_created:
                    created += 1
                elif self.update:
                    for k, v in defaults.items():
                        setattr(obj, k, v)
                    obj.save()
                    updated += 1
                else:
                    skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Страны: создано {created}, обновлено {updated}, пропущено {skipped}."
            )
        )

    # ------------------------------------------------------------------
    # Регионы (admin1)
    # ------------------------------------------------------------------

    def _import_regions(self, country_codes, alt_names):
        path = DATA_DIR / "admin1CodesASCII.txt"
        if not path.exists():
            raise CommandError(
                f"Файл {path} не найден. "
                f"Скачайте с geonames.org/export/dump/admin1CodesASCII.txt"
            )

        # Индекс стран по code2
        countries_map = {c.code2: c for c in Country.objects.all()}
        if not countries_map:
            raise CommandError("Сначала импортируйте страны: --type countries")

        self.stdout.write("Импортирую регионы...")
        created = updated = skipped = 0

        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) < 4:
                    continue
                # UA.01	Autonomous Republic of Crimea	...	geoname_id
                code_full = row[0]  # UA.01
                country_code = code_full.split(".")[0]

                if country_codes and country_code not in country_codes:
                    continue
                if country_code not in countries_map:
                    continue

                try:
                    geoname_id = int(row[3])
                except (ValueError, IndexError):
                    continue

                translations = alt_names.get(geoname_id, {})
                country = countries_map[country_code]

                defaults = {
                    "country": country,
                    "geoname_code": code_full,
                    "name_en": translations.get("en", row[1].strip()),
                    "name_uk": translations.get("uk", ""),
                    "name_ru": translations.get("ru", ""),
                }

                obj, was_created = Region.objects.get_or_create(
                    geoname_id=geoname_id, defaults=defaults
                )
                if was_created:
                    created += 1
                elif self.update:
                    for k, v in defaults.items():
                        setattr(obj, k, v)
                    obj.save()
                    updated += 1
                else:
                    skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Регионы: создано {created}, обновлено {updated}, пропущено {skipped}."
            )
        )

    # ------------------------------------------------------------------
    # Города
    # ------------------------------------------------------------------

    def _import_cities(self, country_codes, alt_names):
        if not country_codes:
            raise CommandError(
                "Для импорта городов укажите --country (например: --country UA)"
            )

        countries_map = {c.code2: c for c in Country.objects.all()}
        regions_map = {r.geoname_code: r for r in Region.objects.all()}

        for country_code in country_codes:
            self._import_cities_for_country(
                country_code, countries_map, regions_map, alt_names
            )

    def _import_cities_for_country(
        self, country_code, countries_map, regions_map, alt_names
    ):
        path = DATA_DIR / f"{country_code}.txt"
        if not path.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Файл {path} не найден. "
                    f"Скачайте {country_code}.zip с geonames.org/export/dump/"
                )
            )
            return

        if country_code not in countries_map:
            self.stdout.write(
                self.style.WARNING(
                    f"Страна {country_code} не найдена в БД. Сначала импортируйте страны."
                )
            )
            return

        country = countries_map[country_code]
        self.stdout.write(f"Импортирую города для {country_code}...")
        created = updated = skipped = 0

        # GeoNames main dump columns:
        # 0:geonameid 1:name 2:asciiname 3:alternatenames 4:lat 5:lon
        # 6:feature class 7:feature code 8:country code 9:cc2
        # 10:admin1 code 11:admin2 12:admin3 13:admin4
        # 14:population 15:elevation 16:dem 17:timezone 18:modification date

        batch = []
        batch_size = 500

        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if len(row) < 15:
                    continue
                if row[6] != "P":
                    continue  # только populated places
                if row[7] not in CITY_FEATURE_CODES:
                    continue

                try:
                    geoname_id = int(row[0])
                    population = int(row[14]) if row[14] else 0
                    lat = float(row[4]) if row[4] else None
                    lon = float(row[5]) if row[5] else None
                except (ValueError, IndexError):
                    continue

                if population < self.min_population:
                    continue

                # Ищем регион по коду: country_code.admin1_code
                admin1_code = row[10].strip()
                region_key = f"{country_code}.{admin1_code}" if admin1_code else None
                region = regions_map.get(region_key)

                translations = alt_names.get(geoname_id, {})
                name_en = translations.get("en", row[2].strip() or row[1].strip())

                batch.append(
                    City(
                        geoname_id=geoname_id,
                        country=country,
                        region=region,
                        name_en=name_en,
                        name_uk=translations.get("uk", ""),
                        name_ru=translations.get("ru", ""),
                        population=population,
                        latitude=lat,
                        longitude=lon,
                        feature_code=row[7],
                    )
                )

                if len(batch) >= batch_size:
                    created += self._flush_batch(batch)
                    batch = []

            if batch:
                created += self._flush_batch(batch)

        self.stdout.write(
            self.style.SUCCESS(
                f"  {country_code}: создано ~{created * batch_size} записей."
            )
        )

    @transaction.atomic
    def _flush_batch(self, batch):
        """Bulk-insert батча городов, пропуская дубликаты по geoname_id."""
        City.objects.bulk_create(batch, ignore_conflicts=True)
        return 1
