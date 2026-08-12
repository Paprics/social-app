# `render_image` — Django-компонент рендеринга изображений

`render_image` — пользовательский Django inclusion tag для единообразного отображения изображений. Он объединяет генерацию миниатюр через `easy-thumbnails`, fallback при отсутствии файла, пользовательскую политику размытия, интерактивное раскрытие и повторное скрытие, форму контейнера и общую HTML-разметку.

<a id="contents"></a>
## Содержание

- [Назначение](#purpose)
- [Состав компонента](#structure)
- [Публичный интерфейс](#api)
- [Подключение и базовое использование](#usage)
- [Аргументы](#arguments)
- [Серверный flow](#server-flow)
- [Thumbnail variants](#variants)
- [Fallback-изображение](#fallback)
- [Политика blur и reveal](#blur-policy)
- [HTML-контракт](#html-contract)
- [CSS-состояния](#css-states)
- [JavaScript flow](#javascript)
- [Компактный режим](#compact)
- [Форма компонента](#shape)
- [HTMX и кликабельные контейнеры](#htmx)
- [Архитектурные границы](#architecture)
- [Производительность](#performance)
- [Изменение и расширение](#extension)
- [Ограничения реализации](#limitations)
- [Доступность и локализация](#accessibility)
- [Диагностика](#troubleshooting)
- [Рекомендации по тестированию](#testing)
- [Краткая памятка](#cheatsheet)

<a id="purpose"></a>
## Назначение

Без компонента шаблонам пришлось бы самостоятельно:

- проверять наличие исходного изображения;
- выбирать thumbnail alias;
- получать URL миниатюры;
- подставлять placeholder;
- читать настройку `blur_media`;
- формировать контейнер, `<img>`, overlay и кнопку;
- синхронизировать классы с CSS и JavaScript.

Вместо этой логики используется один вызов:

```django
{% render_image target_user.profile.avatar_photo.image variant="avatar_lg" alt=target_user.username reveal=True %}
```

Компонент не является универсальным обработчиком медиафайлов. Его контракт рассчитан на изображения, поддерживаемые `easy-thumbnails`, и на текущую frontend-разметку blur/reveal.

[К содержанию](#contents)

<a id="structure"></a>
## Состав компонента

| Слой | Файл | Ответственность |
|---|---|---|
| Python | `src/core/templatetags/render_image.py` | Thumbnail, fallback, blur-политика и контекст inclusion-шаблона |
| HTML | `src/core/templates/core/components/media/thumbnail_image.html` | Структура контейнера, изображения, overlay и кнопки |
| CSS | `src/static/css/components/image_blur.css` | Геометрия, blur, overlay, состояния reveal и компактная кнопка |
| JavaScript | `src/static/js/components/image_blur.js` | Переключение `Show` / `Hide` и клиентских состояний |
| Документация | `DOCS/render_image_tag.md` | Контракт и правила сопровождения компонента |

Компонент представляет собой цепочку:

```text
Django template
      ↓
render_image.py
      ↓
thumbnail_image.html
      ↓
image_blur.css + image_blur.js
      ↓
Browser UI
```

Изменения структуры HTML необходимо рассматривать совместно с CSS и JavaScript: эти части связаны классами, соседством элементов и `data`-атрибутами.

[К содержанию](#contents)

<a id="api"></a>
## Публичный интерфейс

Python-сигнатура:

```python
render_image(
    context,
    image,
    *,
    variant="avatar_sm",
    alt="",
    css_class="",
    reveal=False,
    shape=None,
)
```

Шаблонный синтаксис:

```django
{% render_image image variant="avatar_sm" alt="" css_class="" reveal=False shape=None %}
```

`context` в шаблоне не передаётся. Django добавляет его автоматически благодаря `takes_context=True`:

```python
@register.inclusion_tag(
    "core/components/media/thumbnail_image.html",
    takes_context=True,
)
```

Все аргументы после `image` являются keyword-only на уровне Python. В шаблонах их также следует передавать по имени.

### Результат тега

Функция возвращает не HTML-строку, а словарь контекста:

```python
{
    "image_url": image_url,
    "alt": alt,
    "css_class": css_class,
    "should_blur": should_blur,
    "show_reveal": should_blur and reveal,
    "shape": shape,
}
```

Django рендерит с этим словарём `core/components/media/thumbnail_image.html` и вставляет полученную разметку в вызывающий шаблон.

[К содержанию](#contents)

<a id="usage"></a>
## Подключение и базовое использование

Подключить библиотеку:

```django
{% load render_image %}
```

Минимальный вызов:

```django
{% render_image user.profile.avatar_photo.image %}
```

Будет использован alias `avatar_sm`, пустой `alt`, без кнопки reveal и без специальной формы контейнера.

Большой аватар:

```django
{% render_image target_user.profile.avatar_photo.image variant="avatar_lg" alt=target_user.username css_class="aspect-[4/5] w-full object-cover" reveal=True %}
```

Круглый компактный аватар:

```django
{% render_image user.profile.avatar_photo.image variant="avatar_sm" alt=user.username shape="circle" css_class="h-10 w-10 object-cover" %}
```

Миниатюра с компактной кнопкой раскрытия:

```django
{% render_image profile.avatar_photo.image variant="avatar_sm" alt=profile.user.username reveal=True shape="circle" css_class="media-image--compact h-24 w-24 object-cover" %}
```

[К содержанию](#contents)

<a id="arguments"></a>
## Аргументы

| Аргумент | Обязательный | По умолчанию | Назначение |
|---|---:|---:|---|
| `image` | Да | — | Исходное изображение для `easy-thumbnails` |
| `variant` | Нет | `"avatar_sm"` | Имя alias из конфигурации `THUMBNAIL_ALIASES` |
| `alt` | Нет | `""` | Значение HTML-атрибута `alt` |
| `css_class` | Нет | `""` | Дополнительные классы элемента `<img>` |
| `reveal` | Нет | `False` | Разрешает кнопку раскрытия, если blur активен |
| `shape` | Нет | `None` | Добавляет модификатор формы всему контейнеру |

### `image`

Передаётся первым позиционным аргументом:

```django
{% render_image photo.image %}
```

Если значение truthy, вызывается:

```python
get_thumbnailer(image)[variant]
```

Если значение falsy, thumbnail не создаётся и используется fallback.

Тег не получает фотографию из базы и не проверяет право на её просмотр. Вызывающий код должен передать уже выбранный и разрешённый объект.

### `variant`

Имя настроенного thumbnail alias:

```django
variant="avatar_lg"
```

Размер, crop, качество и другие операции определяются конфигурацией `easy-thumbnails`, а не самим тегом.

### `alt`

Передаётся напрямую в `<img alt="...">` с обычным экранированием Django:

```django
alt=target_user.username
```

Для содержательных изображений следует передавать осмысленное описание. Пустой `alt` допустим для декоративных изображений.

### `css_class`

Строка добавляется к обязательному классу `media-image`:

```html
class="media-image {{ css_class }}..."
```

Через неё задаются локальные размеры, `object-cover`, aspect ratio и при необходимости служебный класс `media-image--compact`.

`css_class` применяется только к `<img>`, а не к `.media-container`.

### `reveal`

Разрешает вывести кнопку `Show`, но только когда `should_blur=True`:

```python
show_reveal = should_blur and reveal
```

Сам по себе `reveal=True` не включает blur.

### `shape`

Если значение задано, inclusion-шаблон добавляет:

```django
media-container--{{ shape }}
```

Текущий CSS реализует только `shape="circle"`.

[К содержанию](#contents)

<a id="server-flow"></a>
## Серверный flow

```text
template context + arguments
          ↓
получение request из context
          ↓
проверка request/user/settings.blur_media
          ↓
image существует?
   ├── да → get_thumbnailer(image)[variant] → thumbnail.url
   └── нет → static placeholder URL
          ↓
формирование словаря контекста
          ↓
thumbnail_image.html
          ↓
готовый HTML-компонент
```

Пошагово:

1. Из текущего template context читается `request`.
2. `should_blur` становится `True`, только если есть request, пользователь авторизован и `request.user.settings.blur_media` включён.
3. При наличии `image` создаётся или извлекается миниатюра alias `variant`.
4. При отсутствии `image` формируется URL placeholder через Django `static()`.
5. Вычисляется `show_reveal = should_blur and reveal`.
6. Данные передаются inclusion-шаблону.
7. Шаблон всегда создаёт контейнер и `<img>`, а overlay — только при `show_reveal=True`.

[К содержанию](#contents)

<a id="variants"></a>
## Thumbnail variants

Тег не хранит размеры изображений. Он принимает семантическое имя alias:

```django
variant="avatar_sm"
```

Соответствующая конфигурация `THUMBNAIL_ALIASES` определяет:

- итоговый размер;
- crop;
- качество;
- способ масштабирования;
- другие параметры, поддерживаемые `easy-thumbnails`.

Имена желательно выбирать по назначению:

```text
avatar_xs
avatar_sm
avatar_md
avatar_lg
photo_preview
photo_card
```

Так реальные размеры можно менять централизованно, не переименовывая вызовы в шаблонах.

### Что происходит при вызове

```python
thumbnail = get_thumbnailer(image)[variant]
image_url = thumbnail.url
```

`easy-thumbnails` создаёт производный файл, не заменяя оригинал. Повторное обращение к той же комбинации исходника и настроек обычно использует уже созданную миниатюру.

### Неизвестный alias

`render_image` не проверяет и не перехватывает ошибку неизвестного `variant`. Поэтому имя должно существовать в текущей конфигурации. Опечатка может привести к исключению во время рендеринга страницы.

[К содержанию](#contents)

<a id="fallback"></a>
## Fallback-изображение

Если `image` имеет ложное значение, используется:

```python
static("images/placeholders/default-avatar.svg")
```

Ожидаемый ресурс:

```text
src/static/images/placeholders/default-avatar.svg
```

Для fallback:

- `easy-thumbnails` не вызывается;
- применяется тот же inclusion-шаблон;
- сохраняются `alt`, `css_class`, `shape` и blur-политика;
- placeholder может оказаться заблюренным, поскольку `should_blur` не зависит от наличия реального изображения.

Чтобы заменить placeholder без изменения Python-кода, достаточно сохранить новый ресурс по тому же static-пути. Для другого пути необходимо изменить строку в `render_image.py`.

[К содержанию](#contents)

<a id="blur-policy"></a>
## Политика blur и reveal

Blur определяется настройкой текущего авторизованного пользователя:

```python
request.user.settings.blur_media
```

Аргументы `blur` или `should_blur` публичным API не предусмотрены. Шаблон не может вручную отключить blur для отдельного вызова.

`reveal` отвечает за другое решение: разрешено ли в этом конкретном месте показать кнопку ручного переключения.

| `blur_media` | `reveal` | Серверный результат |
|---:|---:|---|
| `False` | `False` | Обычное изображение |
| `False` | `True` | Обычное изображение, без overlay |
| `True` | `False` | Заблюренное изображение без кнопки |
| `True` | `True` | Заблюренное изображение с overlay и кнопкой `Show` |

Для анонимного пользователя `should_blur=False`, даже если в проекте существует иная глобальная политика чувствительного контента. Текущая реализация опирается только на настройки авторизованного пользователя.

Если blur включён, но `reveal=False`, класс `is-blurred` остаётся постоянно, а `pointer-events: none` отключает взаимодействие с самим `<img>`. Это намеренный режим «размыто без возможности раскрытия».

[К содержанию](#contents)

<a id="html-contract"></a>
## HTML-контракт

Базовая разметка:

```html
<div class="media-container">
    <img
        src="..."
        alt="..."
        class="media-image ..."
        loading="lazy"
    >
</div>
```

При активных blur и reveal:

```html
<div class="media-container">
    <img class="media-image is-blurred" ...>

    <div class="media-overlay">
        <button type="button" class="media-reveal-btn" data-media-reveal>
            ...
            <span>Show</span>
        </button>
    </div>
</div>
```

С формой:

```html
<div class="media-container media-container--circle">
```

### Критичные связи

- JavaScript ищет кнопку по `[data-media-reveal]`.
- От кнопки он поднимается к ближайшему `.media-container`.
- В контейнере он ищет `.media-image`.
- Компактный CSS использует соседство `.media-image--compact + .media-overlay`.
- `is-revealed` ставится на контейнер, а `is-blurred` — на изображение.

Произвольное переименование или перестановка этих элементов разорвёт взаимодействие между слоями.

[К содержанию](#contents)

<a id="css-states"></a>
## CSS-состояния

| Селектор | Роль |
|---|---|
| `.media-container` | Контекст позиционирования и обрезка содержимого |
| `.media-container--circle` | Круглая геометрия всего компонента |
| `.media-image` | Базовый блочный responsive-элемент |
| `.media-image.is-blurred` | Blur `18px`, запрет выделения и pointer events |
| `.media-overlay` | Абсолютный затемнённый слой над изображением |
| `.media-container.is-revealed` | Состояние раскрытого изображения |
| `.media-reveal-btn` | Кнопка переключения |
| `.media-image--compact` | Маркер компактной кнопки для небольшой миниатюры |

### Начальное состояние

При blur overlay получает:

- `position: absolute; inset: 0`;
- центрирование кнопки;
- полупрозрачный тёмный фон;
- `backdrop-filter: blur(8px)`.

Само изображение получает `filter: blur(18px)`.

### Состояние после раскрытия

JavaScript добавляет контейнеру `.is-revealed` и снимает с изображения `.is-blurred`.

CSS делает overlay прозрачным и отключает его pointer events, но отдельно возвращает pointer events кнопке. Поэтому изображение становится видимым и доступным, а кнопка `Hide` остаётся кликабельной.

### Переходы

Для изображения настроен переход `filter 0.2s ease`. Для кнопки анимируются фон, граница, тень и нажатие.

[К содержанию](#contents)

<a id="javascript"></a>
## JavaScript flow

Обработчик зарегистрирован на `document`:

```javascript
document.addEventListener("click", ...)
```

При клике:

1. через `event.target.closest("[data-media-reveal]")` определяется кнопка;
2. `preventDefault()` запрещает стандартное действие;
3. `stopPropagation()` не позволяет активировать родительскую ссылку или карточку;
4. находится ближайший `.media-container`;
5. внутри контейнера находится `.media-image`;
6. у контейнера переключается `.is-revealed`;
7. у изображения синхронно переключается `.is-blurred`;
8. обновляются `aria-pressed`, `aria-label` и `title`;
9. исходный HTML кнопки один раз сохраняется в `data-reveal-content`;
10. при раскрытии кнопка заменяется на иконку и текст `Hide`;
11. при повторном скрытии восстанавливается исходный HTML с `Show`.

### Сохранение исходной кнопки

При первом клике:

```javascript
button.dataset.revealContent = button.innerHTML;
```

Это позволяет вернуть исходную серверную разметку и SVG без её повторного конструирования.

Состояние существует только в DOM. Оно не отправляется на сервер и сбрасывается при полном повторном рендеринге компонента.

[К содержанию](#contents)

<a id="compact"></a>
## Компактный режим

Для небольших миниатюр используется класс:

```django
css_class="media-image--compact ..."
```

Он не меняет изображение. Благодаря селектору соседства CSS изменяет расположенную сразу после него кнопку:

```css
.media-image--compact + .media-overlay .media-reveal-btn
```

Результат:

- кнопка `32 × 32 px`;
- текст визуально скрыт, но остаётся в DOM;
- SVG внутри кнопки имеет размер `16 × 16 px`;
- управление остаётся доступным с клавиатуры.

Компактный режим не определяется автоматически по `variant` или CSS-размеру. Его необходимо включать явно.

Если между `<img>` и `.media-overlay` вставить другой элемент, селектор `+` перестанет работать.

[К содержанию](#contents)

<a id="shape"></a>
## Форма компонента

Форма задаётся всему `.media-container`, а не только `<img>`:

```django
shape="circle"
```

Результат:

```html
<div class="media-container media-container--circle">
```

```css
.media-container--circle {
    border-radius: 50%;
}
```

Поскольку контейнер имеет `overflow: hidden`, одна форма применяется одновременно к:

- изображению;
- размытой области;
- overlay;
- состоянию после раскрытия.

`border-radius: 50%` создаёт круг только при квадратной геометрии. Вызывающий шаблон должен задать одинаковые ширину и высоту. Для прямоугольника результатом будет овал.

Необязательно одновременно использовать `shape="circle"` и `rounded-full` на изображении: первый вариант уже обеспечивает форму всего компонента.

[К содержанию](#contents)

<a id="htmx"></a>
## HTMX и кликабельные контейнеры

### Динамически добавленный HTML

Event delegation на `document` позволяет кнопкам работать в компонентах, добавленных через HTMX после загрузки страницы. Повторная инициализация на `htmx:afterSwap` не требуется.

JavaScript-файл должен быть подключён до взаимодействия пользователя, но порядок появления конкретных `.media-container` значения не имеет.

### Внутри ссылки или карточки

Обработчик кнопки вызывает `preventDefault()` и `stopPropagation()`. Поэтому нажатие `Show` / `Hide` не должно активировать родительскую ссылку.

Тем не менее интерактивную кнопку предпочтительно не вкладывать внутрь `<a>`. Более корректная структура — сделать media-компонент и ссылку соседями. Это уменьшает зависимость от JavaScript и сохраняет правильную HTML-семантику.

[К содержанию](#contents)

<a id="architecture"></a>
## Архитектурные границы

`render_image` отвечает за:

```text
разрешённый source image
        ↓
thumbnail variant или fallback
        ↓
политика blur/reveal
        ↓
единая HTML-структура
        ↓
клиентское переключение состояния
```

Компонент не отвечает за:

- выбор фотографии из базы;
- разрешения на просмотр;
- приватность профиля или альбома;
- валидацию загружаемого файла;
- загрузку, удаление или модерацию фотографии;
- определение чувствительности конкретного изображения;
- формирование queryset.

Проверка доступа должна завершиться до вызова тега. Передавать в `render_image` закрытое изображение с расчётом, что blur защитит содержимое, нельзя: blur является UI-эффектом, а не механизмом авторизации.

[К содержанию](#contents)

<a id="performance"></a>
## Производительность

Основное назначение thumbnail — не отдавать большой оригинал там, где интерфейс показывает небольшое изображение.

Правильно выбранный alias уменьшает:

- объём передаваемых данных;
- время загрузки;
- декодирование изображений браузером;
- расход памяти и трафика на страницах со списками.

Особенно важен выбор variant для поиска, друзей, Messenger, галерей и других страниц с множеством изображений.

### Доступ к пользовательским настройкам

Тег читает:

```python
request.user.settings.blur_media
```

В стандартной схеме `request.user` уже загружен authentication middleware, но обращение к `settings` может инициировать запрос к связанной модели, если объект не был закэширован. Это происходит один раз для данного экземпляра пользователя в рамках запроса, а не один раз на каждое изображение после заполнения related-object cache.

Связанный `UserSettings` должен гарантированно существовать для каждого пользователя. Если это обеспечивается сигналом создания, миграцией или сервисом регистрации, этот инвариант необходимо сохранять.

[К содержанию](#contents)

<a id="extension"></a>
## Изменение и расширение

### Добавить thumbnail alias

1. Добавить именованную конфигурацию в `THUMBNAIL_ALIASES`.
2. Выбрать семантическое имя по назначению.
3. Использовать его через `variant="..."`.
4. Проверить генерацию, crop и качество на реальных изображениях.

Сам `render_image.py` при этом менять не требуется.

### Изменить variant по умолчанию

Изменить:

```python
variant="avatar_sm"
```

Это затронет все вызовы, где `variant` не передан явно.

### Изменить fallback

Исправить путь:

```python
static("images/placeholders/default-avatar.svg")
```

Если меняется только содержимое файла при сохранении пути, Python-код изменять не требуется.

### Добавить новую форму

Текущий Python и HTML уже формируют модификатор по шаблону:

```text
media-container--<shape>
```

Для `shape="rounded"` достаточно определить CSS:

```css
.media-container--rounded {
    border-radius: 0.75rem;
}
```

Однако для публичного и предсказуемого API желательно также ввести явный whitelist допустимых значений в Python. Сейчас его нет.

### Изменить blur

Визуальная сила blur задаётся здесь:

```css
.media-image.is-blurred {
    filter: blur(18px);
}
```

Серверную политику включения следует менять в `render_image.py`, а не дублировать условия в вызывающих шаблонах.

### Изменить разметку кнопки

Нужно синхронно проверить:

1. initial HTML в `thumbnail_image.html`;
2. HTML состояния `Hide` в `image_blur.js`;
3. сохранение/восстановление `dataset.revealContent`;
4. CSS для обычного и компактного режимов;
5. accessibility-атрибуты.

[К содержанию](#contents)

<a id="limitations"></a>
## Ограничения реализации

### 1. Неизвестный `variant` не обрабатывается

Ошибка thumbnail alias не превращается в fallback. Она может прервать рендер страницы. Это конфигурационная ошибка разработчика.

### 2. Ошибки генерации thumbnail не перехватываются

Повреждённый файл, проблема хранилища или ошибка обработки также не заменяются placeholder автоматически.

### 3. Предполагается наличие `request.user.settings`

Для авторизованного пользователя без связанного объекта `settings` обращение может вызвать `RelatedObjectDoesNotExist`. Компонент опирается на проектный инвариант «у каждого пользователя есть UserSettings».

### 4. `shape` не валидируется

Любое переданное значение попадёт в имя CSS-класса после стандартного HTML-экранирования Django. Неизвестная форма просто не получит ожидаемых стилей, а строка с пробелами может сформировать лишние классы.

### 5. Fallback подчиняется blur-политике

Placeholder может отображаться размытым и с кнопкой reveal. Если placeholder всегда должен быть видимым, условие `should_blur` потребуется связать с наличием реального `image`.

### 6. Нет индивидуальной чувствительности изображения

Blur зависит только от пользовательской настройки, а не от признака конкретной фотографии. Тег одинаково обрабатывает все переданные изображения.

### 7. `loading="lazy"` применяется всегда

Даже главное изображение первого экрана получает lazy loading. Для LCP-изображений иногда предпочтительнее eager loading или `fetchpriority="high"`, но текущий API не позволяет это настроить.

### 8. Frontend-состояние не сохраняется

После HTMX-замены самого компонента или полной перезагрузки раскрытое изображение снова получает серверное начальное состояние.

### 9. CSS зависит от соседства элементов

Компактный режим перестанет работать, если overlay больше не будет непосредственным соседом `<img>`.

[К содержанию](#contents)

<a id="accessibility"></a>
## Доступность и локализация

### Изображение

`alt` является ответственностью вызывающего шаблона. Компонент не генерирует описание автоматически.

### Кнопка

Начальная кнопка имеет видимый переводимый текст:

```django
{% trans "Show" %}
```

SVG помечен `aria-hidden="true"`, поэтому не дублируется screen reader.

После первого клика JavaScript устанавливает:

```text
aria-pressed="true|false"
aria-label="Hide image|Show image"
title="Hide|Show"
```

Текущее ограничение: значения, формируемые JavaScript, и текст `Hide` жёстко записаны на английском. Они не используют Django i18n. Кроме того, до первого клика в HTML отсутствуют `aria-pressed`, `aria-label` и `title`; доступное имя обеспечивается видимым текстом `Show`.

Для полной локализации следует передать переводы в JavaScript через `data`-атрибуты или использовать JavaScript gettext, а начальные ARIA-атрибуты сформировать в шаблоне.

[К содержанию](#contents)

<a id="troubleshooting"></a>
## Диагностика

### `render_image` не распознан Django

Проверить:

```django
{% load render_image %}
```

и наличие модуля `src/core/templatetags/render_image.py` вместе с `__init__.py`.

### `TemplateDoesNotExist`

Тег ожидает точный template name:

```text
core/components/media/thumbnail_image.html
```

Физический путь должен соответствовать Django template discovery.

### Ошибка при указании `variant`

Проверить точное имя alias в `THUMBNAIL_ALIASES`. Тег не имеет автоматического fallback для неизвестного alias.

### Вместо изображения показывается placeholder

Переданное `image` имеет ложное значение. Проверить значение поля и наличие связанной фотографии до рендеринга.

### Изображение заблюрено без кнопки

Это штатный результат комбинации:

```text
blur_media=True + reveal=False
```

Если раскрытие требуется, передать `reveal=True`.

### `reveal=True`, но кнопки нет

`reveal` не включает blur. Проверить `request`, авторизацию пользователя и `request.user.settings.blur_media`.

### Кнопка есть, но не работает

Проверить:

1. подключение `image_blur.js`;
2. наличие `[data-media-reveal]`;
3. ближайший `.media-container`;
4. наличие `.media-image` внутри него;
5. ошибки JavaScript в консоли.

### Кнопка работает, но состояние выглядит неправильно

Проверить подключение `image_blur.css` и классы `.is-blurred` / `.is-revealed`.

### Компактная кнопка не применяется

Проверить класс `media-image--compact` на `<img>` и непосредственное соседство `.media-overlay`.

### Круглая форма выглядит овальной

Контейнер имеет разные ширину и высоту. `border-radius: 50%` не делает прямоугольник кругом.

### Возникает ошибка `settings`

Проверить существование связанного `UserSettings` для текущего пользователя. Проверка `is_authenticated` защищает только от анонимного пользователя, но не от отсутствующей related-записи.

[К содержанию](#contents)

<a id="testing"></a>
## Рекомендации по тестированию

### Python/inclusion tag

Проверить:

1. изображение создаёт URL указанного alias;
2. default variant равен `avatar_sm`;
3. falsy image возвращает static fallback;
4. анонимный пользователь не получает blur;
5. `blur_media=False` не добавляет blur;
6. `blur_media=True` устанавливает `should_blur=True`;
7. `show_reveal=True` только при одновременных `should_blur` и `reveal`;
8. `alt`, `css_class` и `shape` передаются без потери;
9. неизвестный alias демонстрирует текущий контракт ошибки;
10. отсутствие `UserSettings` обрабатывается согласно выбранному проектному инварианту.

Для unit-тестов вызов `get_thumbnailer` и `static` удобно изолировать mock-объектами.

### HTML

Проверить:

- обязательные `.media-container` и `.media-image`;
- условный `is-blurred`;
- условный overlay;
- `loading="lazy"`;
- модификатор формы;
- экранирование `alt` и пользовательских классов.

### JavaScript

Проверить:

- раскрытие и повторное скрытие;
- синхронность `.is-revealed` и `.is-blurred`;
- обновление ARIA-атрибутов;
- восстановление initial HTML;
- отсутствие перехода по родительской ссылке;
- работу после динамической вставки DOM;
- безопасное завершение при отсутствии контейнера или изображения.

### Визуальная проверка

Проверить обычное, blurred и revealed состояния для:

- большого изображения;
- маленькой миниатюры;
- компактной кнопки;
- круглого контейнера;
- светлой и тёмной фотографии;
- изображения внутри карточки.

[К содержанию](#contents)

<a id="cheatsheet"></a>
## Краткая памятка

```text
Python:       src/core/templatetags/render_image.py
HTML:         src/core/templates/core/components/media/thumbnail_image.html
CSS:          src/static/css/components/image_blur.css
JavaScript:   src/static/js/components/image_blur.js
Документ:     DOCS/render_image_tag.md

Подключение:  {% load render_image %}
Fallback:     images/placeholders/default-avatar.svg
Variant:      avatar_sm
Blur:         request.user.settings.blur_media
Reveal:       should_blur and reveal
Форма:        media-container--<shape>
```

Базовый вызов:

```django
{% render_image image variant="avatar_sm" alt=username %}
```

Интерактивный вызов:

```django
{% render_image image variant="avatar_lg" alt=username reveal=True %}
```

Главное правило сопровождения:

> Python определяет данные и серверную политику, HTML сохраняет структурный контракт, CSS отвечает за состояния, а JavaScript только переключает эти состояния.

[К содержанию](#contents)
