"""HTTP tests for image attachments in wall posts."""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from gallery.models import Photo, UserAlbum
from posts.models import Post, PostMedia


def make_image_file(
    *,
    name="post-image.png",
    size=(120, 120),
):
    """Create a valid in-memory PNG upload."""

    output = BytesIO()

    Image.new(
        "RGB",
        size,
    ).save(
        output,
        format="PNG",
    )

    output.seek(0)

    return SimpleUploadedFile(
        name,
        output.read(),
        content_type="image/png",
    )


def make_oversized_file(
    *,
    max_size,
    name="oversized.png",
):
    """Create an upload exceeding the configured file-size limit."""

    return SimpleUploadedFile(
        name,
        b"x" * (max_size + 1),
        content_type="image/png",
    )


@pytest.mark.django_db
class TestCreatePostMediaView:
    def test_staff_can_create_text_only_post(
        self,
        client,
        owner,
        staff_user,
    ):
        client.force_login(staff_user)

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "Text only post",
            },
        )

        assert response.status_code == 200

        post = Post.objects.get(
            owner=owner,
            author=staff_user,
        )

        assert post.content == "Text only post"
        assert post.media_items.count() == 0

    def test_staff_can_create_image_only_post(
        self,
        client,
        owner,
        staff_user,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path

        client.force_login(staff_user)

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "",
                "photos": make_image_file(),
            },
        )

        assert response.status_code == 200

        post = Post.objects.get(
            owner=owner,
            author=staff_user,
        )

        assert post.content == ""
        assert post.media_items.count() == 1

    def test_staff_can_create_text_and_image_post(
        self,
        client,
        owner,
        staff_user,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path

        client.force_login(staff_user)

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "Post with photo",
                "photos": make_image_file(),
            },
        )

        assert response.status_code == 200

        post = Post.objects.get(
            owner=owner,
            author=staff_user,
        )

        assert post.content == "Post with photo"
        assert post.media_items.count() == 1

        media = post.media_items.select_related(
            "photo__album",
        ).get()

        assert media.photo.album.user == staff_user
        assert media.photo.album.purpose == UserAlbum.Purpose.POST_PHOTOS

    def test_staff_can_create_post_with_three_images(
        self,
        client,
        owner,
        staff_user,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path

        client.force_login(staff_user)

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "Three photos",
                "photos": [
                    make_image_file(name="first.png"),
                    make_image_file(name="second.png"),
                    make_image_file(name="third.png"),
                ],
            },
        )

        assert response.status_code == 200

        post = Post.objects.get(
            owner=owner,
            author=staff_user,
        )

        media_items = list(
            post.media_items.order_by(
                "position",
                "id",
            )
        )

        assert len(media_items) == 3
        assert [media.position for media in media_items] == [
            0,
            1,
            2,
        ]

    def test_staff_can_create_post_with_ten_images(
        self,
        client,
        owner,
        staff_user,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path
        settings.POST_MAX_IMAGES = 10

        client.force_login(staff_user)

        photos = [
            make_image_file(
                name=f"photo-{index}.png",
            )
            for index in range(10)
        ]

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "Ten photos",
                "photos": photos,
            },
        )

        assert response.status_code == 200

        post = Post.objects.get(
            owner=owner,
            author=staff_user,
        )

        media_items = list(
            post.media_items.order_by(
                "position",
                "id",
            )
        )

        assert len(media_items) == 10
        assert [media.position for media in media_items] == list(range(10))

    def test_more_than_ten_images_returns_400_and_rolls_back(
        self,
        client,
        owner,
        staff_user,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path
        settings.POST_MAX_IMAGES = 10

        client.force_login(staff_user)

        photos = [
            make_image_file(
                name=f"photo-{index}.png",
            )
            for index in range(11)
        ]

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "Too many photos",
                "photos": photos,
            },
        )

        assert response.status_code == 400
        assert response.json()["error"]

        assert not Post.objects.filter(
            owner=owner,
            author=staff_user,
        ).exists()

        assert not PostMedia.objects.exists()

        assert not Photo.objects.filter(
            album__user=staff_user,
            album__purpose=UserAlbum.Purpose.POST_PHOTOS,
        ).exists()

    def test_invalid_image_returns_400_and_rolls_back(
        self,
        client,
        owner,
        staff_user,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path

        client.force_login(staff_user)

        invalid_file = SimpleUploadedFile(
            "broken.jpg",
            b"this-is-not-an-image",
            content_type="image/jpeg",
        )

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "Broken upload",
                "photos": invalid_file,
            },
        )

        assert response.status_code == 400
        assert response.json()["error"]

        assert not Post.objects.filter(
            owner=owner,
            author=staff_user,
        ).exists()

        assert not PostMedia.objects.exists()

        assert not Photo.objects.filter(
            album__user=staff_user,
            album__purpose=UserAlbum.Purpose.POST_PHOTOS,
        ).exists()

    def test_oversized_image_returns_400_and_rolls_back(
        self,
        client,
        owner,
        staff_user,
        settings,
        tmp_path,
    ):
        settings.MEDIA_ROOT = tmp_path
        settings.MAX_PHOTO_FILE_SIZE = 5 * 1024 * 1024

        client.force_login(staff_user)

        oversized_file = make_oversized_file(
            max_size=settings.MAX_PHOTO_FILE_SIZE,
        )

        response = client.post(
            reverse(
                "posts:wall_create",
                kwargs={"user_id": owner.pk},
            ),
            {
                "content": "Oversized photo",
                "photos": oversized_file,
            },
        )

        assert response.status_code == 400
        assert response.json()["error"]

        assert not Post.objects.filter(
            owner=owner,
            author=staff_user,
        ).exists()

        assert not PostMedia.objects.exists()

        assert not Photo.objects.filter(
            album__user=staff_user,
            album__purpose=UserAlbum.Purpose.POST_PHOTOS,
        ).exists()
