from django.conf import settings
from django.shortcuts import render
from django.utils.translation import get_language

from .models import City, Country, Region


def _lang():
    """Текущий язык интерфейса, 2 символа."""
    return (get_language() or "en")[:2]


def _get_display_name(obj, lang):
    """
    Возвращает название объекта на нужном языке.
    Fallback: en если локализованное поле пустое.
    """
    if lang == "uk":
        return obj.name_uk or obj.name_en
    if lang == "ru":
        return obj.name_ru or obj.name_en
    return obj.name_en


def countries_options(request):
    """Список стран для <select>. Используется при инициализации формы."""
    lang = _lang()
    countries = Country.objects.filter(code2__in=settings.GEO_ALLOWED_COUNTRIES)
    return render(
        request,
        "geo/partials/countries_options.html",
        {
            "countries": countries,
            "lang": lang,
        },
    )


def regions_partial(request):
    """HTMX: возвращает <option> регионов при выборе страны."""
    country_id = request.GET.get("country")
    lang = _lang()
    regions = []
    if country_id:
        qs = Region.objects.filter(country_id=country_id)
        # Сортируем по нужному языку, но только если поле непустое
        if lang == "uk":
            qs = qs.order_by("name_uk", "name_en")
        elif lang == "ru":
            qs = qs.order_by("name_ru", "name_en")
        else:
            qs = qs.order_by("name_en")
        regions = [{"pk": r.pk, "name": _get_display_name(r, lang)} for r in qs]
    return render(
        request,
        "geo/partials/regions_options.html",
        {
            "regions": regions,
            "lang": lang,
        },
    )


def cities_partial(request):
    """HTMX: возвращает <option> городов при выборе региона."""
    region_id = request.GET.get("region")
    lang = _lang()
    cities = []
    if region_id:
        qs = City.objects.filter(region_id=region_id)
        # Для языков с возможными пустыми полями — сортируем по населению,
        # чтобы крупные города шли первыми, и не было "пустого" первого блока
        qs = qs.order_by("-population", "name_en")
        cities = [{"pk": c.pk, "name": _get_display_name(c, lang)} for c in qs]
    return render(
        request,
        "geo/partials/cities_options.html",
        {
            "cities": cities,
            "lang": lang,
        },
    )


def city_autocomplete(request):
    """
    HTMX autocomplete: поиск города по вводу.
    Минимум 2 символа для запроса, возвращает до 15 результатов.
    """
    q = request.GET.get("q", "").strip()
    country_id = request.GET.get("country", "")
    lang = _lang()

    cities = []
    if len(q) >= 2:
        # Ищем по полю текущего языка, если пустое — по английскому
        if lang == "uk":
            from django.db.models import Q

            qs = City.objects.filter(Q(name_uk__icontains=q) | Q(name_en__icontains=q))
        elif lang == "ru":
            from django.db.models import Q

            qs = City.objects.filter(Q(name_ru__icontains=q) | Q(name_en__icontains=q))
        else:
            qs = City.objects.filter(name_en__icontains=q)

        if country_id:
            qs = qs.filter(country_id=country_id)

        qs = qs.select_related("region").order_by("-population")[:15]
        cities = [
            {
                "pk": c.pk,
                "name": _get_display_name(c, lang),
                "region_name": _get_display_name(c.region, lang) if c.region else "",
            }
            for c in qs
        ]

    return render(
        request,
        "geo/partials/autocomplete_results.html",
        {
            "cities": cities,
            "lang": lang,
            "q": q,
        },
    )
