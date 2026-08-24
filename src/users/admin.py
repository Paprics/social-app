from django.contrib import admin

from .models import UserData


@admin.register(UserData)
class UserDataAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "username",
        "data_1",
        "data_2",
    )

    search_fields = (
        "username",
        "user__username",
        "user__email",
    )

    list_select_related = ("user",)

    ordering = ("-id",)

    readonly_fields = (
        "user",
        "username",
        "data_1",
        "data_2",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
