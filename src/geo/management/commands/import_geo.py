# src/geo/management/commands/import_geo.py

"""
Импорт географических данных из дампов GeoNames.

Команда наполняет модели Country, Region и City локальными данными GeoNames.
В рантайме внешние API не используются.

Логика отбора населённых пунктов
--------------------------------
GeoNames хранит города, посёлки и сёла в feature class ``P``.

Административно значимые населённые пункты импортируются всегда, даже если
``population`` равен 0 или отсутствует:

    PPLC   — столица государства;
    PPLA   — административный центр 1-го уровня;
    PPLA2  — административный центр 2-го уровня;
    PPLA3  — административный центр 3-го уровня;
    PPLG   — seat of government of a political entity.

Обычные населённые пункты ``PPL`` импортируются только если их население не
меньше ``MIN_POPULATION``. По умолчанию порог равен 2500 жителей.

Остальные populated-place коды (PPLX, PPLL, PPLF, PPLH, PPLQ, PPLW и т.д.)
не импортируются.

Это правило едино для всех стран: административный каркас сохраняется всегда,
а обычные населённые пункты проходят фильтр по населению.

Использование
-------------
    # Только страны
    python manage.py import_geo --type countries

    # Только регионы
    python manage.py import_geo --type regions --country UA PL CZ

    # Только населённые пункты
    python manage.py import_geo --type cities --country UA PL CZ

    # Полный импорт для нескольких стран
    python manage.py import_geo --country UA RU PL CZ DE

    # Изменить порог для обычных PPL
    python manage.py import_geo --country UA --min-population 5000

    # Обновить существующие записи по geoname_id
    python manage.py import_geo --country UA --update

Файлы должны находиться в ``geo/data/``:
    countryInfo.txt
    admin1CodesASCII.txt
    alternateNamesV2.txt
    UA.txt
    PL.txt
    CZ.txt
    RU.txt
    DE.txt
    ...

Важно: ``--country`` ограничивает регионы и населённые пункты. Country по
прежнему импортируется целиком из countryInfo.txt.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from geo.models import City, Country, Region

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Модели имеют только name_en / name_uk / name_ru, поэтому другие языки здесь
# намеренно не поддерживаются.
SUPPORTED_LANGUAGES = {"en", "uk", "ru"}

# Эти населённые пункты имеют административное значение и импортируются всегда.
ADMIN_FEATURE_CODES = {
    "PPLC",  # столица государства
    "PPLA",  # административный центр 1-го уровня
    "PPLA2",  # административный центр 2-го уровня
    "PPLA3",  # административный центр 3-го уровня
    "PPLG",  # seat of government of a political entity
}

# Эти коды проходят дополнительный фильтр по population.
POPULATION_FILTERED_FEATURE_CODES = {
    "PPL",  # обычный city / town / village / populated place
}

MIN_POPULATION = 2500
CITY_BATCH_SIZE = 500

CITY_UPDATE_FIELDS = (
    "country",
    "region",
    "name_en",
    "name_uk",
    "name_ru",
    "population",
    "latitude",
    "longitude",
    "feature_code",
)


@dataclass(slots=True)
class ImportStats:
    """Счётчики одного этапа импорта."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    filtered: int = 0
    malformed: int = 0


@dataclass(frozen=True, slots=True)
class GeoNamesCityRow:
    """Нужные приложению поля одной строки country dump GeoNames."""

    geoname_id: int
    name: str
    ascii_name: str
    latitude: float | None
    longitude: float | None
    feature_class: str
    feature_code: str
    admin1_code: str
    population: int


class Command(BaseCommand):
    """Django management command ``import_geo``."""

    help = "Импортирует страны, регионы и населённые пункты из GeoNames dumps"

    def add_arguments(self, parser):
        """Регистрирует CLI-аргументы management-команды."""
        parser.add_argument(
            "--type",
            choices=("countries", "regions", "cities", "all"),
            default="all",
            help="Что импортировать (default: all)",
        )
        parser.add_argument(
            "--country",
            nargs="+",
            metavar="CODE",
            help="ISO-коды стран для регионов/городов (например: UA PL CZ)",
        )
        parser.add_argument(
            "--min-population",
            type=int,
            default=MIN_POPULATION,
            help=(
                "Минимальное население обычного PPL. Административные центры "
                f"не фильтруются (default: {MIN_POPULATION})"
            ),
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Обновлять существующие записи по geoname_id (default: пропускать)",
        )

    def handle(self, *args, **options):
        """Проверяет параметры и последовательно запускает этапы импорта."""
        import_type = options["type"]
        country_codes = self._normalize_country_codes(options.get("country"))

        self.min_population = options["min_population"]
        self.update = options["update"]
        self.verbosity = options.get("verbosity", 1)

        if self.min_population < 0:
            raise CommandError("--min-population не может быть отрицательным")

        # Проверяем до начала записи в БД. Иначе `--type all` без --country
        # успеет импортировать страны/регионы и только потом упадёт на городах.
        if import_type in {"cities", "all"} and not country_codes:
            raise CommandError("Для импорта населённых пунктов укажите --country " "(например: --country UA PL CZ)")

        if not DATA_DIR.exists():
            raise CommandError(f"Директория {DATA_DIR} не существует. " "Создайте её и положите туда файлы GeoNames.")

        self.stdout.write(f"DATA_DIR: {DATA_DIR}")
        self.stdout.write("Фильтр: PPLC/PPLA/PPLA2/PPLA3/PPLG — всегда; " f"PPL — population >= {self.min_population}.")

        logger.info(
            "GeoNames import started: type=%s countries=%s min_population=%s update=%s",
            import_type,
            country_codes,
            self.min_population,
            self.update,
        )

        # alternateNamesV2.txt очень большой. Сначала собираем geoname_id только
        # тех объектов, которые реально участвуют в текущем запуске, а затем
        # сохраняем в память переводы только для них.
        target_ids = self._collect_target_geoname_ids(import_type, country_codes)
        alt_names = self._load_alternate_names(target_ids)

        if import_type in {"countries", "all"}:
            self._import_countries(alt_names)

        if import_type in {"regions", "all"}:
            self._import_regions(country_codes, alt_names)

        if import_type in {"cities", "all"}:
            self._import_cities(country_codes, alt_names)

        logger.info("GeoNames import finished")
        self.stdout.write(self.style.SUCCESS("Импорт завершён."))

    # ------------------------------------------------------------------
    # Подготовка и переводы
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_country_codes(country_codes: list[str] | None) -> list[str] | None:
        """Нормализует ISO-коды, проверяет формат и удаляет дубликаты."""
        if not country_codes:
            return None

        result: list[str] = []
        seen: set[str] = set()

        for raw_code in country_codes:
            code = raw_code.strip().upper()
            if len(code) != 2 or not code.isalpha():
                raise CommandError(
                    f"Некорректный код страны {raw_code!r}. " "Ожидается двухбуквенный ISO-код, например UA."
                )
            if code not in seen:
                result.append(code)
                seen.add(code)

        return result

    def _collect_target_geoname_ids(
        self,
        import_type: str,
        country_codes: list[str] | None,
    ) -> set[int]:
        """Собирает geoname_id объектов, для которых нужны переводы."""
        target_ids: set[int] = set()

        if import_type in {"countries", "all"}:
            target_ids.update(self._collect_country_ids())

        if import_type in {"regions", "all"}:
            target_ids.update(self._collect_region_ids(country_codes))

        if import_type in {"cities", "all"}:
            assert country_codes is not None  # проверено в handle()
            for country_code in country_codes:
                target_ids.update(self._collect_city_ids(country_code))

        self.stdout.write(f"Объектов для загрузки переводов: {len(target_ids)}")
        return target_ids

    def _collect_country_ids(self) -> set[int]:
        """Читает geoname_id стран из countryInfo.txt."""
        path = self._require_file("countryInfo.txt")
        result: set[int] = set()

        with path.open(encoding="utf-8") as file:
            for line in file:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 17:
                    continue
                try:
                    result.add(int(parts[16]))
                except ValueError:
                    continue

        return result

    def _collect_region_ids(self, country_codes: list[str] | None) -> set[int]:
        """Читает geoname_id admin1-регионов выбранных стран."""
        path = self._require_file("admin1CodesASCII.txt")
        allowed = set(country_codes) if country_codes else None
        result: set[int] = set()

        with path.open(encoding="utf-8") as file:
            for row in csv.reader(file, delimiter="\t"):
                if len(row) < 4:
                    continue
                country_code = row[0].split(".", 1)[0]
                if allowed and country_code not in allowed:
                    continue
                try:
                    result.add(int(row[3]))
                except ValueError:
                    continue

        return result

    def _collect_city_ids(self, country_code: str) -> set[int]:
        """Читает geoname_id городов, которые пройдут текущий фильтр."""
        path = DATA_DIR / f"{country_code}.txt"
        if not path.exists():
            return set()

        result: set[int] = set()
        with path.open(encoding="utf-8") as file:
            for row in csv.reader(file, delimiter="\t"):
                city = self._parse_city_row(row)
                if city and self._should_import_city(city):
                    result.add(city.geoname_id)
        return result

    def _load_alternate_names(
        self,
        target_ids: set[int],
    ) -> dict[int, dict[str, str]]:
        """
        Загружает en/uk/ru из alternateNamesV2.txt только для target_ids.

        Для нескольких вариантов одного языка выбирается актуальное preferred
        name. Исторические и colloquial-названия имеют меньший приоритет.
        """
        if not target_ids:
            return {}

        path = DATA_DIR / "alternateNamesV2.txt"
        if not path.exists():
            message = f"Файл {path} не найден — переводы не будут загружены."
            logger.warning(message)
            self.stdout.write(self.style.WARNING(message))
            return {}

        self.stdout.write("Загружаю переводы из alternateNamesV2.txt...")

        names: dict[int, dict[str, str]] = {}
        priorities: dict[tuple[int, str], tuple[int, int, int, int]] = {}
        scanned = 0
        replacements = 0

        with path.open(encoding="utf-8") as file:
            for row in csv.reader(file, delimiter="\t"):
                scanned += 1
                if self.verbosity >= 2 and scanned % 1_000_000 == 0:
                    self.stdout.write(f"  Просканировано {scanned:,} alternate names...")

                if len(row) < 4:
                    continue

                lang = row[2].strip().lower()
                if lang not in SUPPORTED_LANGUAGES:
                    continue

                try:
                    geoname_id = int(row[1])
                except ValueError:
                    continue

                if geoname_id not in target_ids:
                    continue

                name = row[3].strip()
                if not name:
                    continue

                key = (geoname_id, lang)
                priority = self._alternate_name_priority(row)
                old_priority = priorities.get(key)
                if old_priority is not None and priority <= old_priority:
                    continue

                if old_priority is not None:
                    replacements += 1

                names.setdefault(geoname_id, {})[lang] = name
                priorities[key] = priority

        selected = sum(len(value) for value in names.values())
        self.stdout.write(
            f"  Загружено {selected} переводов для {len(names)} объектов "
            f"(замен более приоритетным вариантом: {replacements})."
        )
        return names

    @staticmethod
    def _alternate_name_priority(row: list[str]) -> tuple[int, int, int, int]:
        """Оценивает вариант имени по флагам alternateNamesV2."""
        preferred = len(row) > 4 and row[4] == "1"
        short = len(row) > 5 and row[5] == "1"
        colloquial = len(row) > 6 and row[6] == "1"
        historic = len(row) > 7 and row[7] == "1"

        # Для справочника важнее актуальное официальное имя. При прочих равных
        # короткое название удобнее длинной формальной формы.
        return (
            int(not historic),
            int(preferred),
            int(not colloquial),
            int(short),
        )

    # ------------------------------------------------------------------
    # Страны
    # ------------------------------------------------------------------

    def _import_countries(self, alt_names: dict[int, dict[str, str]]) -> None:
        """Импортирует все страны из countryInfo.txt."""
        path = self._require_file("countryInfo.txt")
        stats = ImportStats()
        self.stdout.write("Импортирую страны...")

        with path.open(encoding="utf-8") as file:
            for line in file:
                if line.startswith("#") or not line.strip():
                    continue

                parts = line.rstrip("\n").split("\t")
                if len(parts) < 17:
                    stats.malformed += 1
                    continue

                try:
                    geoname_id = int(parts[16])
                except ValueError:
                    stats.malformed += 1
                    continue

                code2 = parts[0].strip().upper()
                if not code2:
                    stats.malformed += 1
                    continue

                translations = alt_names.get(geoname_id, {})
                defaults = {
                    "code2": code2,
                    "code3": parts[1].strip(),
                    "continent": parts[8].strip() if len(parts) > 8 else "",
                    "phone_code": parts[12].strip() if len(parts) > 12 else "",
                    "name_en": translations.get("en", parts[4].strip() or code2),
                    "name_uk": translations.get("uk", ""),
                    "name_ru": translations.get("ru", ""),
                }

                obj, created = Country.objects.get_or_create(
                    geoname_id=geoname_id,
                    defaults=defaults,
                )
                self._finish_single_object(obj, created, defaults, stats)

        self._print_stats("Страны", stats)

    # ------------------------------------------------------------------
    # Регионы
    # ------------------------------------------------------------------

    def _import_regions(
        self,
        country_codes: list[str] | None,
        alt_names: dict[int, dict[str, str]],
    ) -> None:
        """Импортирует admin1-регионы выбранных стран."""
        path = self._require_file("admin1CodesASCII.txt")
        countries = {country.code2: country for country in Country.objects.all()}
        if not countries:
            raise CommandError("Сначала импортируйте страны: --type countries")

        allowed = set(country_codes) if country_codes else None
        stats = ImportStats()
        self.stdout.write("Импортирую регионы...")

        with path.open(encoding="utf-8") as file:
            for row in csv.reader(file, delimiter="\t"):
                if len(row) < 4:
                    stats.malformed += 1
                    continue

                code_full = row[0].strip()
                country_code = code_full.split(".", 1)[0]
                if allowed and country_code not in allowed:
                    continue

                country = countries.get(country_code)
                if country is None:
                    stats.skipped += 1
                    continue

                try:
                    geoname_id = int(row[3])
                except ValueError:
                    stats.malformed += 1
                    continue

                translations = alt_names.get(geoname_id, {})
                defaults = {
                    "country": country,
                    "geoname_code": code_full,
                    "name_en": translations.get("en", row[1].strip()),
                    "name_uk": translations.get("uk", ""),
                    "name_ru": translations.get("ru", ""),
                }

                obj, created = Region.objects.get_or_create(
                    geoname_id=geoname_id,
                    defaults=defaults,
                )
                self._finish_single_object(obj, created, defaults, stats)

        self._print_stats("Регионы", stats)

    # ------------------------------------------------------------------
    # Населённые пункты
    # ------------------------------------------------------------------

    def _import_cities(
        self,
        country_codes: list[str] | None,
        alt_names: dict[int, dict[str, str]],
    ) -> None:
        """Импортирует населённые пункты явно указанных стран."""
        if not country_codes:
            raise CommandError("Для импорта городов требуется --country")

        countries = {country.code2: country for country in Country.objects.all()}
        regions = {region.geoname_code: region for region in Region.objects.all()}

        for country_code in country_codes:
            self._import_cities_for_country(
                country_code=country_code,
                countries=countries,
                regions=regions,
                alt_names=alt_names,
            )

    def _import_cities_for_country(
        self,
        *,
        country_code: str,
        countries: dict[str, Country],
        regions: dict[str, Region],
        alt_names: dict[int, dict[str, str]],
    ) -> None:
        """Импортирует один GeoNames country dump ``XX.txt`` батчами."""
        path = DATA_DIR / f"{country_code}.txt"
        if not path.exists():
            message = f"Файл {path} не найден — {country_code} пропущена."
            logger.warning(message)
            self.stdout.write(self.style.WARNING(message))
            return

        country = countries.get(country_code)
        if country is None:
            message = f"Страна {country_code} отсутствует в Country — импорт городов пропущен."
            logger.warning(message)
            self.stdout.write(self.style.WARNING(message))
            return

        stats = ImportStats()
        batch: list[City] = []
        self.stdout.write(f"Импортирую населённые пункты для {country_code}...")

        with path.open(encoding="utf-8") as file:
            for row in csv.reader(file, delimiter="\t"):
                city = self._parse_city_row(row)
                if city is None:
                    stats.malformed += 1
                    continue

                if not self._should_import_city(city):
                    stats.filtered += 1
                    continue

                region_key = f"{country_code}.{city.admin1_code}" if city.admin1_code else None
                region = regions.get(region_key) if region_key else None
                translations = alt_names.get(city.geoname_id, {})
                fallback_en = city.ascii_name or city.name

                batch.append(
                    City(
                        geoname_id=city.geoname_id,
                        country=country,
                        region=region,
                        name_en=translations.get("en", fallback_en),
                        name_uk=translations.get("uk", ""),
                        name_ru=translations.get("ru", ""),
                        population=city.population,
                        latitude=city.latitude,
                        longitude=city.longitude,
                        feature_code=city.feature_code,
                    )
                )

                if len(batch) >= CITY_BATCH_SIZE:
                    self._merge_stats(stats, self._flush_city_batch(batch))
                    batch.clear()

        if batch:
            self._merge_stats(stats, self._flush_city_batch(batch))

        self._print_stats(country_code, stats, include_filtered=True)

    def _should_import_city(self, city: GeoNamesCityRow) -> bool:
        """
        Возвращает True, если населённый пункт должен попасть в City.

        * feature class должен быть ``P``;
        * PPLC/PPLA/PPLA2/PPLA3/PPLG импортируются всегда;
        * PPL импортируется только при population >= min_population;
        * остальные feature codes отбрасываются.
        """
        if city.feature_class != "P":
            return False

        if city.feature_code in ADMIN_FEATURE_CODES:
            return True

        if city.feature_code in POPULATION_FILTERED_FEATURE_CODES:
            return city.population >= self.min_population

        return False

    @transaction.atomic
    def _flush_city_batch(self, batch: list[City]) -> ImportStats:
        """
        Создаёт/обновляет батч City и возвращает точную статистику.

        В отличие от старого ``bulk_create(ignore_conflicts=True)``, существующие
        geoname_id определяются заранее. Поэтому ``--update`` действительно
        работает для City, а created/skipped больше не являются приблизительными.
        """
        stats = ImportStats()
        geoname_ids = [city.geoname_id for city in batch]
        existing = {city.geoname_id: city for city in City.objects.filter(geoname_id__in=geoname_ids)}

        to_create: list[City] = []
        to_update: list[City] = []

        for incoming in batch:
            current = existing.get(incoming.geoname_id)
            if current is None:
                to_create.append(incoming)
                continue

            if not self.update:
                stats.skipped += 1
                continue

            for field in CITY_UPDATE_FIELDS:
                setattr(current, field, getattr(incoming, field))
            to_update.append(current)

        if to_create:
            City.objects.bulk_create(to_create, batch_size=CITY_BATCH_SIZE)
            stats.created = len(to_create)

        if to_update:
            City.objects.bulk_update(
                to_update,
                fields=CITY_UPDATE_FIELDS,
                batch_size=CITY_BATCH_SIZE,
            )
            stats.updated = len(to_update)

        return stats

    # ------------------------------------------------------------------
    # Парсинг и служебные методы
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_city_row(row: list[str]) -> GeoNamesCityRow | None:
        """Парсит одну строку XX.txt. Некорректная строка возвращает None."""
        if len(row) < 15:
            return None

        try:
            population = int(row[14]) if row[14].strip() else 0
            latitude = float(row[4]) if row[4].strip() else None
            longitude = float(row[5]) if row[5].strip() else None
            geoname_id = int(row[0])
        except ValueError:
            return None

        return GeoNamesCityRow(
            geoname_id=geoname_id,
            name=row[1].strip(),
            ascii_name=row[2].strip(),
            latitude=latitude,
            longitude=longitude,
            feature_class=row[6].strip(),
            feature_code=row[7].strip(),
            admin1_code=row[10].strip(),
            population=population,
        )

    def _finish_single_object(
        self,
        obj,
        created: bool,
        defaults: dict,
        stats: ImportStats,
    ) -> None:
        """Общая логика create/update/skip для Country и Region."""
        if created:
            stats.created += 1
            return

        if not self.update:
            stats.skipped += 1
            return

        for field, value in defaults.items():
            setattr(obj, field, value)
        obj.save()
        stats.updated += 1

    @staticmethod
    def _merge_stats(target: ImportStats, source: ImportStats) -> None:
        """Суммирует два набора статистики."""
        target.created += source.created
        target.updated += source.updated
        target.skipped += source.skipped
        target.filtered += source.filtered
        target.malformed += source.malformed

    def _print_stats(
        self,
        label: str,
        stats: ImportStats,
        *,
        include_filtered: bool = False,
    ) -> None:
        """Выводит итог этапа в stdout и logger."""
        parts = [
            f"создано {stats.created}",
            f"обновлено {stats.updated}",
            f"пропущено {stats.skipped}",
        ]
        if include_filtered:
            parts.append(f"отфильтровано {stats.filtered}")
        parts.append(f"некорректных строк {stats.malformed}")

        message = f"{label}: " + ", ".join(parts) + "."
        logger.info(message)
        self.stdout.write(self.style.SUCCESS(message))

    @staticmethod
    def _require_file(filename: str) -> Path:
        """Возвращает обязательный файл из DATA_DIR или бросает CommandError."""
        path = DATA_DIR / filename
        if not path.exists():
            raise CommandError(f"Файл {path} не найден.")
        return path
