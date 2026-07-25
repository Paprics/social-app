# Geo App — эндпоинты (HTMX API)

## Назначение

Эндпоинты geo app — это **не страницы для пользователя** и не REST API.
Это внутренние URL, которые вызывает HTMX на стороне браузера когда
пользователь взаимодействует с формой (выбирает страну, регион, вводит текст).
В ответ сервер возвращает готовый HTML-фрагмент (`<option>` теги или `<li>` список),
который HTMX вставляет в нужное место страницы без перезагрузки.

Открыть в браузере вручную можно, но увидишь просто голые `<option>` без
обёртки — это нормально, они и не предназначены для прямого просмотра.

---

## Подключение в urls.py проекта

```python
# _config/urls.py
urlpatterns = [
    ...
    path('geo/', include('geo.urls', namespace='geo')),
]
```

---

## Список эндпоинтов

### `GET /geo/regions/?country=<id>`

Возвращает список `<option>` регионов для выбранной страны.
Вызывается автоматически когда пользователь меняет значение в `<select name="country">`.

```
/geo/regions/?country=1   →  <option value="1">Вінницька область</option>
                              <option value="2">Волинська область</option>
                              ...
```

### `GET /geo/cities/?region=<id>`

Возвращает список `<option>` городов для выбранного региона.
Вызывается когда пользователь выбрал область.

```
/geo/cities/?region=5   →  <option value="101">Київ</option>
                            <option value="102">Бровари</option>
                            ...
```

### `GET /geo/autocomplete/?q=<текст>&country=<id>`

Возвращает HTML-список `<li>` городов подходящих под введённый текст.
Используется в режиме автокомплита (поиск по вводу вместо каскадных селектов).
Минимум 2 символа для запроса, возвращает до 15 результатов.

```
/geo/autocomplete/?q=Ки&country=1   →  <ul>
                                           <li data-city-id="101">Київ</li>
                                           <li data-city-id="203">Кириківка</li>
                                        </ul>
```

Язык ответа определяется автоматически из текущей локали Django (`request.LANGUAGE_CODE`).
Если интерфейс на украинском — вернёт украинские названия, на русском — русские.

---

## Как это выглядит в шаблоне

```html
<!-- При смене страны — HTMX делает GET /geo/regions/?country=<выбранный id>
     и вставляет результат в #id-region-select -->
<select name="country"
        hx-get="{% url 'geo:regions' %}"
        hx-target="#id-region-select"
        hx-trigger="change">
    ...
</select>

<select id="id-region-select" name="region">
    <!-- Сюда прилетают <option> из /geo/regions/ -->
</select>
```

Готовый пример подключения в форму — см. `geo/templates/geo/partials/location_fields.html`.