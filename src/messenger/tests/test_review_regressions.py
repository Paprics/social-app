import pytest

from messenger.models import Message, Participant
from messenger.models.dialog import Dialog, DialogType
from messenger.selectors.dialog import get_private_dialog, get_user_dialogs
from messenger.services.dialog import DialogService
from messenger.services.message import MessageService


@pytest.fixture
def users(django_user_model):
    user_a = django_user_model.objects.create_user(
        username="messenger_user_a",
        password="test-password",
    )
    user_b = django_user_model.objects.create_user(
        username="messenger_user_b",
        password="test-password",
    )
    user_c = django_user_model.objects.create_user(
        username="messenger_user_c",
        password="test-password",
    )

    return user_a, user_b, user_c


@pytest.mark.django_db
def test_message_visible_queryset_is_valid(users):
    """
    Message.objects.visible() не должен обращаться
    к несуществующим полям модели.
    """
    user_a, user_b, _ = users

    dialog = DialogService.create_dialog([user_a, user_b])

    message = Message.objects.create(
        dialog=dialog,
        sender=user_a,
        text="hello",
    )

    messages = list(Message.objects.visible())

    assert message in messages


@pytest.mark.django_db
def test_dialog_unread_count_counts_only_messages_after_last_read(users):
    """
    unread_count должен учитывать только входящие сообщения,
    появившиеся после last_read_message.
    """
    user_a, user_b, _ = users

    dialog = DialogService.create_dialog([user_a, user_b])

    first_message = MessageService.create_message(
        dialog=dialog,
        sender=user_b,
        text="first",
    )

    second_message = MessageService.create_message(
        dialog=dialog,
        sender=user_b,
        text="second",
    )

    participant = Participant.objects.get(
        dialog=dialog,
        user=user_a,
    )

    participant.last_read_message = first_message
    participant.save(update_fields=["last_read_message"])

    dialog_from_list = get_user_dialogs(user_a).get(
        pk=dialog.pk,
    )

    assert dialog_from_list.unread_count == 1
    assert second_message.id > first_message.id


@pytest.mark.django_db
def test_get_private_dialog_does_not_return_group_dialog(users):
    """
    Selector приватного диалога не должен случайно
    возвращать групповой чат с теми же пользователями.
    """
    user_a, user_b, user_c = users

    group_dialog = Dialog.objects.create(
        dialog_type=DialogType.GROUP,
        title="Test group",
    )

    Participant.objects.bulk_create(
        [
            Participant(dialog=group_dialog, user=user_a),
            Participant(dialog=group_dialog, user=user_b),
            Participant(dialog=group_dialog, user=user_c),
        ]
    )

    dialog = get_private_dialog(user_a, user_b)

    assert dialog is None
