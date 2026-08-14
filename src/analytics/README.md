# analytics — Staff Analytics Dashboard

Самодостаточный Django app для администраторского dashboard.  
Работает без Redis и Celery — все запросы выполняются on-demand к PostgreSQL.

---

## Подключение

### 1. Скопировать папку
```
social-network/src/analytics/
```

### 2. settings/base.py
```python
INSTALLED_APPS = [
    ...
    "django.contrib.humanize",   # если ещё не добавлен
    "analytics",
]
```

### 3. urls.py (корневой)
```python
urlpatterns = [
    ...
    path("staff/analytics/", include("analytics.urls", namespace="analytics")),
]
```

### 4. Доступ
Страница доступна только пользователям с `is_staff=True`.  
URL: `/staff/analytics/`  
Параметры: `?period=30d` (варианты: `24h`, `7d`, `30d`, `90d`, `year`, `all`)

---

## Архитектура

```
analytics/
├── dto/dashboard.py         — frozen dataclasses (Period, StatCard, ...)
├── services/
│   ├── periods.py           — расчёт временных окон и гранулярности
│   └── dashboard.py         — orchestrator всех selectors
├── selectors/
│   ├── users.py             — overview, growth charts
│   ├── demographics.py      — gender, age, looking_for matrix
│   ├── geography.py         — страны, регионы, города
│   ├── activity.py          — online buckets, hourly heatmap
│   ├── media.py             — фото, альбомы, disk storage
│   ├── social.py            — друзья, избранное, блокировки
│   ├── messenger.py         — сообщения, диалоги
│   ├── content.py           — посты, комментарии, визиты
│   ├── funnel.py            — воронка конверсии
│   └── health.py            — качественные показатели БД
├── views/dashboard.py       — AnalyticsDashboardView (staff_member_required)
├── templatetags/
│   └── analytics_tags.py    — |keys, |items, |filesizeformat
└── templates/analytics/
    └── dashboard.html        — всё на одной странице, Chart.js
```

---

## Что показывает

| Блок | Метрики |
|---|---|
| **Overview** | Online, Total users, New, Active, Messages, Posts |
| **Growth** | Line charts регистраций и активных по периоду |
| **Audience** | Gender doughnut, Age histogram, Gender×LookingFor matrix |
| **Geography** | Top countries / regions / cities |
| **Activity** | Online segments, активность по часам суток |
| **Media & Storage** | Фото, альбомы, физический размер диска |
| **Social** | Дружбы, запросы, избранное, блокировки |
| **Messaging** | Сообщения, диалоги, reply rate |
| **Content** | Посты, комментарии, посещения профилей |
| **Funnel** | Регистрация → сообщение → ответ |
| **Health** | Без аватара, без фото, неактивные и т.д. |

---

## Производительность
На больших базах (100k+ users) тяжёлые запросы — `funnel.py` и `health.py`.  
Если нужно — оберни в Django cache (15–60 мин) или добавь индексы:
```python
# Пример быстрого кэша прямо в view
from django.core.cache import cache
data = cache.get_or_set("analytics:30d", lambda: build_dashboard(period), 300)
```
