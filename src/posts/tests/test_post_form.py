# src/posts/tests/test_post_form.py

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict

from posts.forms import PostForm


def make_uploaded_file():
    """Return a dummy uploaded file for form-level tests."""

    return SimpleUploadedFile(
        "photo.jpg",
        b"test-image-content",
        content_type="image/jpeg",
    )


class TestPostForm:
    def test_text_only_post_is_valid(self):
        form = PostForm(
            data={
                "content": "Hello world",
            }
        )

        assert form.is_valid()

    def test_empty_post_is_invalid(self):
        form = PostForm(
            data={
                "content": "   ",
            }
        )

        assert not form.is_valid()
        assert "__all__" in form.errors

    def test_image_only_post_is_valid(self):
        form = PostForm(
            data={
                "content": "",
            },
            files=MultiValueDict(
                {
                    "photos": [
                        make_uploaded_file(),
                    ],
                }
            ),
        )

        assert form.is_valid()

    def test_text_and_image_post_is_valid(self):
        form = PostForm(
            data={
                "content": "Post with image",
            },
            files=MultiValueDict(
                {
                    "photos": [
                        make_uploaded_file(),
                    ],
                }
            ),
        )

        assert form.is_valid()

    def test_whitespace_content_is_normalized_to_empty_string(self):
        form = PostForm(
            data={
                "content": "   ",
            },
            files=MultiValueDict(
                {
                    "photos": [
                        make_uploaded_file(),
                    ],
                }
            ),
        )

        assert form.is_valid()
        assert form.cleaned_data["content"] == ""
