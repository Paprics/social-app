from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("", include("chat.urls")),
    path("", include("users.urls")),
    path("", include("accounts.urls")),
    path("", include("cms.urls")),
    path("geo/", include("geo.urls")),
    path("posts/", include("posts.urls")),
    path("messenger/", include("messenger.urls")),
    path("search/", include("search.urls")),
    path("gallery/", include("gallery.urls")),
    path("staff/analytics/", include("analytics.urls", namespace="analytics")),
    path("notifications/", include("notifications.urls")),
)

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
        path("rosetta/", include("rosetta.urls")),
    ]

    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT,
    )

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
