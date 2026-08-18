from unittest.mock import patch

import pytest

from django.urls import reverse

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


@pytest.mark.django_db
def test_conversation_without_dialog_renders_new_conversation_page(
    users,
    client,
):
    """
    Страница начала переписки не должна рендерить dialog_detail
    без существующего Dialog/public_id.
    """
    user_a, user_b, _ = users

    client.force_login(user_a)

    response = client.get(
        reverse(
            "messenger:conversation",
            kwargs={
                "user_id": user_b.id,
            },
        )
    )

    assert response.status_code == 200
    assert get_private_dialog(user_a, user_b) is None
    assert response.context["messenger_thread_active"] is True
    assert b'id="conversation-page"' in response.content


@pytest.mark.django_db
def test_conversation_with_existing_dialog_redirects_to_dialog_detail(
    users,
    client,
):
    """Существующая личная переписка открывается через public_id диалога."""
    user_a, user_b, _ = users

    dialog = DialogService.create_dialog(
        [
            user_a,
            user_b,
        ]
    )

    client.force_login(user_a)

    response = client.get(
        reverse(
            "messenger:conversation",
            kwargs={
                "user_id": user_b.id,
            },
        )
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "messenger:dialog_detail",
        kwargs={
            "public_id": dialog.public_id,
        },
    )


@pytest.mark.django_db
def test_deleted_dialog_url_redirects_to_dialog_list(
    users,
    client,
):
    user_a, user_b, _ = users
    dialog = DialogService.create_dialog([user_a, user_b])
    dialog_url = reverse(
        "messenger:dialog_detail",
        kwargs={"public_id": dialog.public_id},
    )

    dialog.delete()
    client.force_login(user_a)

    response = client.get(dialog_url)

    assert response.status_code == 302
    assert response.url == reverse("messenger:dialog_list")


@pytest.mark.django_db
def test_first_conversation_message_notifies_realtime(
    users,
    client,
):
    user_a, user_b, _ = users
    client.force_login(user_a)

    with (
        patch(
            "messenger.services.message.transaction.on_commit",
            side_effect=lambda callback: callback(),
        ),
        patch.object(
            MessageService,
            "notify_message_created",
        ) as notify,
    ):
        response = client.post(
            reverse(
                "messenger:conversation_send",
                kwargs={"user_id": user_b.id},
            ),
            {"text": "first realtime message"},
        )

    assert response.status_code == 204
    notify.assert_called_once()

    message = notify.call_args.kwargs["message"]
    assert message.sender_id == user_a.id
    assert message.dialog.participants.filter(user=user_b).exists()


@pytest.mark.django_db
def test_delete_dialog_schedules_realtime_notification(
    users,
):
    user_a, user_b, _ = users
    dialog = DialogService.create_dialog([user_a, user_b])
    dialog_id = dialog.id

    with (
        patch(
            "messenger.services.dialog.transaction.on_commit",
            side_effect=lambda callback: callback(),
        ),
        patch(
            "messenger.services.dialog.MessengerRealtimeService.notify_dialog_deleted",
        ) as notify,
    ):
        DialogService.delete_dialog(
            dialog=dialog,
            user=user_a,
        )

    assert not Dialog.objects.filter(pk=dialog_id).exists()
    notify.assert_called_once()
    assert notify.call_args.kwargs["dialog_id"] == dialog_id
    assert set(notify.call_args.kwargs["user_ids"]) == {
        user_a.id,
        user_b.id,
    }

@pytest.mark.django_db
def test_delete_non_last_message_keeps_dialog_metadata(users):
    user_a, user_b, _ = users
    dialog = DialogService.create_dialog([user_a, user_b])

    first = MessageService.create_message(
        dialog=dialog,
        sender=user_a,
        text="first",
    )
    second = MessageService.create_message(
        dialog=dialog,
        sender=user_b,
        text="second",
    )

    dialog.refresh_from_db()
    previous_activity_at = dialog.last_activity_at

    MessageService.delete_message(
        message=first,
    )

    dialog.refresh_from_db()

    assert dialog.last_message_id == second.id
    assert dialog.last_activity_at == previous_activity_at


@pytest.mark.django_db
def test_delete_last_message_repoints_dialog_metadata(users):
    user_a, user_b, _ = users
    dialog = DialogService.create_dialog([user_a, user_b])

    first = MessageService.create_message(
        dialog=dialog,
        sender=user_a,
        text="first",
    )
    second = MessageService.create_message(
        dialog=dialog,
        sender=user_b,
        text="second",
    )

    MessageService.delete_message(
        message=second,
    )

    dialog.refresh_from_db()

    assert dialog.last_message_id == first.id
    assert dialog.last_activity_at == first.created_at


@pytest.mark.django_db
def test_delete_read_cursor_message_preserves_unread_count(users):
    reader, sender, _ = users
    dialog = DialogService.create_dialog([reader, sender])

    first = MessageService.create_message(
        dialog=dialog,
        sender=sender,
        text="first",
    )
    second = MessageService.create_message(
        dialog=dialog,
        sender=sender,
        text="second",
    )
    MessageService.create_message(
        dialog=dialog,
        sender=sender,
        text="third",
    )

    participant = Participant.objects.get(
        dialog=dialog,
        user=reader,
    )
    participant.last_read_message = second
    participant.save(
        update_fields=["last_read_message"],
    )

    assert participant.unread_count == 1

    MessageService.delete_message(
        message=second,
    )

    participant.refresh_from_db()

    assert participant.last_read_message_id == first.id
    assert participant.unread_count == 1


@pytest.mark.django_db
def test_delete_only_message_clears_dialog_metadata(users):
    user_a, user_b, _ = users
    dialog = DialogService.create_dialog([user_a, user_b])

    message = MessageService.create_message(
        dialog=dialog,
        sender=user_a,
        text="only",
    )

    MessageService.delete_message(
        message=message,
    )

    dialog.refresh_from_db()

    assert dialog.last_message_id is None
    assert dialog.last_activity_at == dialog.created_at

@pytest.mark.django_db
def test_create_message_schedules_realtime_on_commit(users):
    user_a, user_b, _ = users
    dialog = DialogService.create_dialog([user_a, user_b])

    with patch(
        "messenger.services.message.transaction.on_commit",
    ) as on_commit:
        message = MessageService.create_message(
            dialog=dialog,
            sender=user_a,
            text="scheduled create",
        )

    on_commit.assert_called_once()

    callback = on_commit.call_args.args[0]

    with patch.object(
        MessageService,
        "notify_message_created",
    ) as notify:
        callback()

    notify.assert_called_once_with(
        message=message,
    )


@pytest.mark.django_db
def test_delete_message_schedules_realtime_on_commit(users):
    user_a, user_b, _ = users
    dialog = DialogService.create_dialog([user_a, user_b])

    message = MessageService.create_message(
        dialog=dialog,
        sender=user_a,
        text="scheduled delete",
    )
    dialog_id = dialog.id
    message_id = message.id

    with patch(
        "messenger.services.message.transaction.on_commit",
    ) as on_commit:
        deleted_message_id = MessageService.delete_message(
            message=message,
        )

    assert deleted_message_id == message_id
    on_commit.assert_called_once()

    callback = on_commit.call_args.args[0]

    with patch.object(
        MessageService,
        "notify_message_deleted",
    ) as notify:
        callback()

    notify.assert_called_once_with(
        dialog_id=dialog_id,
        message_id=message_id,
    )

