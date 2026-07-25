from django.contrib import admin
from django.utils.html import format_html

from .models import City, Country, Region


class RegionInline(admin.TabularInline):
    model = Region
    extra = 0
    fields = ("geoname_id", "geoname_code", "name_en", "name_uk", "name_ru")
    show_change_link = True


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        "flag",
        "code2",
        "code3",
        "name_en",
        "name_uk",
        "name_ru",
        "continent",
        "region_count",
        "city_count",
    )
    list_filter = ("continent",)
    search_fields = ("code2", "code3", "name_en", "name_uk", "name_ru")
    ordering = ("code2",)
    inlines = [RegionInline]
    readonly_fields = ("region_count", "city_count")

    @admin.display(description="")
    def flag(self, obj):
        # Флаг через emoji: код страны → региональный индикатор unicode
        flag = "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in obj.code2.upper())
        return format_html('<span style="font-size:1.4em">{}</span>', flag)

    @admin.display(description="Regions")
    def region_count(self, obj):
        return obj.regions.count()

    @admin.display(description="Cities")
    def city_count(self, obj):
        return obj.cities.count()


class CityInline(admin.TabularInline):
    model = City
    extra = 0
    fields = ("geoname_id", "name_en", "name_uk", "name_ru", "population")
    show_change_link = True
    ordering = ("-population",)

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-population")[:20]


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = (
        "name_en",
        "name_uk",
        "name_ru",
        "geoname_code",
        "country",
        "city_count",
    )
    list_filter = ("country",)
    search_fields = ("name_en", "name_uk", "name_ru", "geoname_code")
    raw_id_fields = ("country",)
    inlines = [CityInline]

    @admin.display(description="Cities")
    def city_count(self, obj):
        return obj.cities.count()


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = (
        "name_en",
        "name_uk",
        "name_ru",
        "region",
        "country",
        "population",
        "feature_code",
    )
    list_filter = ("country", "feature_code")
    search_fields = ("name_en", "name_uk", "name_ru")
    raw_id_fields = ("country", "region")
    ordering = ("-population",)
    list_per_page = 50

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "geoname_id",
                    "feature_code",
                    "country",
                    "region",
                    "population",
                )
            },
        ),
        ("Names", {"fields": ("name_en", "name_uk", "name_ru")}),
        (
            "Coordinates",
            {"fields": ("latitude", "longitude"), "classes": ("collapse",)},
        ),
    )
