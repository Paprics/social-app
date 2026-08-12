from django.urls import path
from search.views import UserSearchView

app_name = "search"

urlpatterns = [
    path("", UserSearchView.as_view(), name="users"),
]
