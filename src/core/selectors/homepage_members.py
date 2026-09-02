"""Selectors used by the public homepage."""

import random

from django.core.cache import cache

from users.models.profile import Profile

HOMEPAGE_CAROUSEL_CACHE_KEY = "core:homepage-members-carousel:v1"
HOMEPAGE_CAROUSEL_CACHE_TIMEOUT = 15 * 60
HOMEPAGE_CAROUSEL_PROFILES_PER_GENDER = 6

HOMEPAGE_CAROUSEL_GENDERS = (
    Profile.Gender.MALE,
    Profile.Gender.FEMALE,
    Profile.Gender.COUPLE,
    Profile.Gender.NON_BINARY,
)


def _eligible_profiles():
    """Return profiles that may be advertised on the public homepage."""
    return Profile.objects.filter(
        user__is_active=True,
        is_deleted=False,
        is_banned=False,
        avatar_photo__isnull=False,
    )


def _build_random_profile_ids() -> list[int]:
    """Pick up to the configured number of profiles from every gender."""
    buckets = {gender: [] for gender in HOMEPAGE_CAROUSEL_GENDERS}

    for profile_id, gender in _eligible_profiles().values_list("pk", "gender"):
        if gender in buckets:
            buckets[gender].append(profile_id)

    selected_ids: list[int] = []

    for gender in HOMEPAGE_CAROUSEL_GENDERS:
        candidate_ids = buckets[gender]
        selected_ids.extend(
            random.sample(
                candidate_ids,
                k=min(HOMEPAGE_CAROUSEL_PROFILES_PER_GENDER, len(candidate_ids)),
            )
        )

    random.shuffle(selected_ids)
    return selected_ids


def get_homepage_carousel_profiles() -> list[Profile]:
    """Return randomized homepage profiles in stable cached order."""
    profile_ids = cache.get(HOMEPAGE_CAROUSEL_CACHE_KEY)

    if profile_ids is None:
        profile_ids = _build_random_profile_ids()
        cache.set(
            HOMEPAGE_CAROUSEL_CACHE_KEY,
            profile_ids,
            HOMEPAGE_CAROUSEL_CACHE_TIMEOUT,
        )

    if not profile_ids:
        return []

    profiles = (
        _eligible_profiles()
        .filter(pk__in=profile_ids)
        .select_related("user", "avatar_photo")
    )
    profiles_by_id = {profile.pk: profile for profile in profiles}

    return [
        profiles_by_id[profile_id]
        for profile_id in profile_ids
        if profile_id in profiles_by_id
    ]
