from django.urls import path

from . import views

app_name = "geo"

urlpatterns = [
    path("regions/", views.regions_partial, name="regions"),
    path("cities/", views.cities_partial, name="cities"),
    path("autocomplete/", views.city_autocomplete, name="autocomplete"),
]
