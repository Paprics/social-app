import json
import logging
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from users.models import Profile
from gallery.models import Photo, UserAlbum

logger = logging.getLogger(__name__)
User = get_user_model()

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

DEFAULT_SEED_FILE = "dev_data/seed_users.json"
DEFAULT_PHOTOS_ROOT = "dev_data/photos"


class Command(BaseCommand):
    help = "Создаёт тестовых пользователей из dev_data/seed_users.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help=f"Путь к JSON-файлу — абсолютный или относительно корня проекта (по умолчанию: {DEFAULT_SEED_FILE})",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Сбросить флаг seeded у всех записей в JSON (БД не трогает)",
        )

    def handle(self, *args, **options):
        from django.conf import settings

        # BASE_DIR = .../social-network/src — dev_data лежит на уровень выше
        src_dir = Path(settings.BASE_DIR)
        project_root = src_dir.parent

        seed_file = _resolve_path(options["file"], project_root, DEFAULT_SEED_FILE)
        photos_root = project_root / DEFAULT_PHOTOS_ROOT

        self._print_header(seed_file, photos_root, project_root)

        if not seed_file.exists():
            raise CommandError(
                f"Файл не найден: {seed_file}\n" f"  project_root = {project_root}\n" f"  cwd          = {Path.cwd()}"
            )

        with open(seed_file, encoding="utf-8") as f:
            users_data = json.load(f)

        if options["reset"]:
            self._do_reset(seed_file, users_data)
            return

        self._do_seed(seed_file, users_data, photos_root)

    # ─────────────────────────────────────────────
    # Режимы
    # ─────────────────────────────────────────────

    def _do_reset(self, seed_file: Path, users_data: list) -> None:
        count = sum(1 for e in users_data if e.get("seeded"))
        for entry in users_data:
            entry["seeded"] = False
        _write_json(seed_file, users_data)
        self.stdout.write(self.style.WARNING(f"[RESET] Флаг seeded сброшен у {count} записей → {seed_file.name}"))

    def _do_seed(self, seed_file: Path, users_data: list, photos_root: Path) -> None:
        total = len(users_data)
        pending = [e for e in users_data if not e.get("seeded")]
        already = total - len(pending)

        self.stdout.write(f"  Всего в файле : {total}")
        self.stdout.write(f"  Уже создано   : {already}")
        self.stdout.write(f"  К созданию    : {len(pending)}")
        self.stdout.write("")

        if not pending:
            self.stdout.write(self.style.WARNING("Все пользователи уже созданы. Используй --reset для сброса."))
            return

        created_count = 0
        error_count = 0

        for entry in users_data:
            username = entry.get("username", "?")

            if entry.get("seeded"):
                self.stdout.write(f"  {'─'*54}")
                self.stdout.write(f"  [SKIP] @{username} — уже создан")
                continue

            self.stdout.write(f"  {'─'*54}")
            self.stdout.write(f"  → Создаём @{username} ...")

            try:
                with transaction.atomic():
                    user = _create_user(entry, self)
                    profile = _create_profile(user, entry, self)
                    photo_count = _create_photos(user, profile, entry, photos_root, self)

                entry["seeded"] = True
                _write_json(seed_file, users_data)

                self.stdout.write(self.style.SUCCESS(f"  ✓ @{username} создан  pk={user.pk}  фото={photo_count}"))
                created_count += 1

            except Exception as exc:
                logger.exception("seed_users: ошибка при создании %s", username)
                self.stdout.write(self.style.ERROR(f"  ✗ @{username} — ОШИБКА: {exc}"))
                error_count += 1

        self.stdout.write(f"\n  {'═'*54}")
        status = self.style.SUCCESS if error_count == 0 else self.style.WARNING
        self.stdout.write(status(f"  Создано: {created_count}  |  Пропущено: {already}  |  Ошибок: {error_count}"))
        self.stdout.write(f"  {'═'*54}\n")

    # ─────────────────────────────────────────────
    # Вывод шапки
    # ─────────────────────────────────────────────

    def _print_header(self, seed_file: Path, photos_root: Path, project_root: Path) -> None:
        self.stdout.write(f"\n  {'═'*54}")
        self.stdout.write("  seed_users")
        self.stdout.write(f"  {'═'*54}")
        self.stdout.write(f"  project root : {project_root}")
        self.stdout.write(f"  seed file    : {seed_file}")
        self.stdout.write(f"  photos root  : {photos_root}")
        self.stdout.write(f"  {'─'*54}\n")


# ─────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────


def _resolve_path(raw: str | None, project_root: Path, default: str) -> Path:
    """
    Резолвит путь к seed-файлу:
      1. Если не передан — project_root / default
      2. Если абсолютный — берём как есть
      3. Если относительный — пробуем сначала от cwd, затем от project_root
    """
    if raw is None:
        return project_root / default
    p = Path(raw)
    if p.is_absolute():
        return p
    # Относительный: сначала от cwd (при запуске из корня проекта dev_data/... найдётся сразу)
    from_cwd = Path.cwd() / p
    if from_cwd.exists():
        return from_cwd
    # Fallback — от корня проекта
    return project_root / p


def _create_user(entry: dict, cmd: BaseCommand) -> "User":
    username = entry["username"]
    email = entry["email"]

    if User.objects.filter(username=username).exists():
        raise ValueError(f"username '{username}' уже занят в БД")
    if User.objects.filter(email=email).exists():
        raise ValueError(f"email '{email}' уже занят в БД")

    user = User(
        username=username,
        email=email,
        first_name=entry.get("first_name", ""),
        last_name=entry.get("last_name", ""),
        is_active=True,
    )
    user.set_password(entry["password"])
    user.save()
    # UserSettings и UserPremiumFeatures создаются автоматически через post_save сигнал

    cmd.stdout.write(f"      User       pk={user.pk}  username={username}  email={email}")
    return user


def _create_profile(user: "User", entry: dict, cmd: BaseCommand) -> "Profile":
    from geo.models import City, Country, Region

    country = _get_or_none(Country, entry.get("country"), cmd)
    region = _get_or_none(Region, entry.get("region"), cmd)
    city = _get_or_none(City, entry.get("city"), cmd)

    profile = Profile.objects.create(
        user=user,
        bio=entry.get("bio", ""),
        gender=entry.get("gender", ""),
        looking_for=entry.get("looking_for", []),
        birth_date=entry.get("birth_date") or None,
        country=country,
        region=region,
        city=city,
    )

    cmd.stdout.write(
        f"      Profile    pk={profile.pk}  gender={profile.gender or '—'}  "
        f"birth={profile.birth_date or '—'}  "
        f"geo={country or '—'} / {region or '—'} / {city or '—'}"
    )
    return profile


def _create_photos(user: "User", profile: "Profile", entry: dict, photos_root: Path, cmd: BaseCommand) -> int:
    photos_dir_name = entry.get("photos_dir", "").strip()

    if not photos_dir_name:
        cmd.stdout.write("      Photos     photos_dir не указан — пропускаем")
        return 0

    photos_dir = photos_root / photos_dir_name

    if not photos_dir.exists():
        cmd.stdout.write(cmd.style.WARNING(f"      Photos     папка не найдена: {photos_dir}"))
        return 0

    photo_files = sorted(p for p in photos_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)

    if not photo_files:
        cmd.stdout.write(f"      Photos     папка пуста: {photos_dir}")
        return 0

    album = UserAlbum.objects.create(
        user=user,
        title="Photos",
        slug="photos",
        album_type=UserAlbum.AlbumType.PHOTO,
        visibility=UserAlbum.Visibility.PUBLIC,
    )
    cmd.stdout.write(f"      Album      pk={album.pk}  title=Photos  файлов={len(photo_files)}")

    for idx, photo_path in enumerate(photo_files):
        with open(photo_path, "rb") as f:
            file_data = ContentFile(f.read(), name=photo_path.name)

        photo = Photo.objects.create(
            album=album,
            image=file_data,
            title=photo_path.stem,
        )

        is_avatar = idx == 0
        if is_avatar:
            profile.avatar_photo = photo
            profile.save(update_fields=["avatar_photo"])

        tag = " ← avatar" if is_avatar else ""
        cmd.stdout.write(f"        Photo    pk={photo.pk}  {photo_path.name}{tag}")

    return len(photo_files)


def _get_or_none(model_class, pk, cmd: BaseCommand):
    if pk is None:
        return None
    try:
        return model_class.objects.get(pk=pk)
    except model_class.DoesNotExist:
        cmd.stdout.write(cmd.style.WARNING(f"      GEO        {model_class.__name__} pk={pk} не найден → None"))
        return None


def _write_json(path: Path, data: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
