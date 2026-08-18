# src/video_chat/services/participant.py

"""Формирование metadata участника случайного видеочата."""

from users.models.profile import Profile


class InvalidChatGender(ValueError):
    """Передан gender, которого нет в Profile.Gender."""


def build_participant_metadata(
    *,
    user,
    chat_gender: str,
    session_id: str,
) -> dict:
    """Собрать identity metadata участника без записи в БД."""

    if chat_gender not in Profile.Gender.values:
        raise InvalidChatGender(chat_gender)

    authenticated_user = None
    username = ""
    profile_gender = ""

    if user is not None and getattr(user, "is_authenticated", False):
        authenticated_user = user
        username = user.get_username()

        profile_gender = (
            Profile.objects.filter(user_id=user.pk)
            .values_list("gender", flat=True)
            .first()
            or ""
        )

    return {
        "session_id": session_id,
        "user_id": authenticated_user.pk if authenticated_user else None,
        "username": username,
        "is_authenticated": authenticated_user is not None,
        "profile_gender": profile_gender,
        "chat_gender": chat_gender,
    }
