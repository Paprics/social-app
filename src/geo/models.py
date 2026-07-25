from django.db import models
from django.utils.translation import get_language

SUPPORTED_LANGUAGES = ["en", "uk", "ru"]


class GeoBase(models.Model):
    """Абстрактная база для всех гео-моделей."""

    geoname_id = models.IntegerField(unique=True, db_index=True)
    name_en = models.CharField(max_length=200)
    name_uk = models.CharField(max_length=200, blank=True)
    name_ru = models.CharField(max_length=200, blank=True)

    class Meta:
        abstract = True

    def get_name(self, lang=None):
        """Возвращает название на нужном языке с fallback на английский."""
        if lang is None:
            lang = (get_language() or "en")[:2]
        if lang not in SUPPORTED_LANGUAGES:
            lang = "en"
        return getattr(self, f"name_{lang}", None) or self.name_en

    def __str__(self):
        return self.name_en


class Country(GeoBase):
    code2 = models.CharField(
        max_length=2, unique=True, db_index=True, verbose_name="ISO 3166-1 alpha-2"
    )
    code3 = models.CharField(
        max_length=3, blank=True, verbose_name="ISO 3166-1 alpha-3"
    )
    continent = models.CharField(max_length=2, blank=True)
    phone_code = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"
        ordering = ["name_en"]

    def __str__(self):
        return f"{self.code2} — {self.name_en}"


class Region(GeoBase):
    """Область / штат / регион."""

    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="regions"
    )
    geoname_code = models.CharField(max_length=20, blank=True, db_index=True)

    class Meta:
        verbose_name = "Region"
        verbose_name_plural = "Regions"
        ordering = ["name_en"]
        unique_together = [("country", "geoname_code")]

    def __str__(self):
        return f"{self.name_en} ({self.country.code2})"


class City(GeoBase):
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="cities"
    )
    region = models.ForeignKey(
        Region, on_delete=models.SET_NULL, null=True, blank=True, related_name="cities"
    )
    population = models.IntegerField(default=0, db_index=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    feature_code = models.CharField(max_length=10, blank=True)

    class Meta:
        verbose_name = "City"
        verbose_name_plural = "Cities"
        ordering = ["-population", "name_en"]
        indexes = [
            models.Index(fields=["country", "-population"]),
            models.Index(fields=["region", "-population"]),
            # Для автокомплита по каждому языку
            models.Index(fields=["name_en"]),
            models.Index(fields=["name_uk"]),
            models.Index(fields=["name_ru"]),
        ]

    def __str__(self):
        region_str = f", {self.region.name_en}" if self.region else ""
        return f"{self.name_en}{region_str}, {self.country.code2}"
