from pathlib import Path

from django.core.files.uploadedfile import UploadedFile

from messenger.models import Attachment, Message


class AttachmentService:
    """
    Логика работы с вложениями сообщений.

    Отвечает за:
    - проверку файла;
    - определение типа;
    - создание Attachment.
    """

    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
    }

    VIDEO_EXTENSIONS = {
        ".mp4",
        ".webm",
        ".mov",
    }

    AUDIO_EXTENSIONS = {
        ".mp3",
        ".wav",
        ".ogg",
    }

    @classmethod
    def create_attachment(
        cls,
        *,
        message: Message,
        uploaded_file: UploadedFile,
    ) -> Attachment:
        """
        Создает вложение для сообщения.
        """

        cls.validate_file(uploaded_file)

        attachment_type = cls.detect_type(
            uploaded_file.name
        )

        return Attachment.objects.create(
            message=message,
            file=uploaded_file,
            attachment_type=attachment_type,
            original_name=uploaded_file.name,
            file_size=uploaded_file.size,
            mime_type=uploaded_file.content_type or "",
        )

    @classmethod
    def validate_file(
        cls,
        uploaded_file: UploadedFile,
    ):
        """
        Проверка ограничений файла.
        """

        if uploaded_file.size > cls.MAX_FILE_SIZE:
            raise ValueError(
                "File size exceeds limit"
            )

    @classmethod
    def detect_type(
        cls,
        filename: str,
    ) -> str:
        """
        Определяет тип вложения по расширению.
        """

        extension = Path(
            filename
        ).suffix.lower()

        if extension in cls.IMAGE_EXTENSIONS:
            return Attachment.AttachmentType.IMAGE

        if extension in cls.VIDEO_EXTENSIONS:
            return Attachment.AttachmentType.VIDEO

        if extension in cls.AUDIO_EXTENSIONS:
            return Attachment.AttachmentType.AUDIO

        return Attachment.AttachmentType.FILE