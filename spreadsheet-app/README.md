# Spreadsheet App - Веб-редактор таблиц

Полноценное веб-приложение для работы с таблицами (аналог NextCloud/Excel в Web).

## Возможности

- ✅ Регистрация и аутентификация пользователей (JWT)
- ✅ Создание, редактирование, удаление таблиц
- ✅ Редактирование ячеек с поддержкой формул
- ✅ Поддержка формул: SUM, AVG, MIN, MAX, COUNT, IF
- ✅ История изменений ячеек
- ✅ Сохранение данных в базу данных (SQLite)
- ✅ Современный UI с адаптивным дизайном
- ✅ REST API с документацией (Swagger/OpenAPI)

## Структура проекта

```
spreadsheet-app/
├── backend/
│   ├── main.py              # Точка входа FastAPI
│   ├── database.py          # Конфигурация БД
│   ├── models.py            # SQLAlchemy модели
│   ├── schemas.py           # Pydantic схемы
│   ├── auth.py              # Аутентификация (JWT)
│   ├── requirements.txt     # Python зависимости
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py          # Маршруты авторизации
│   │   └── spreadsheets.py  # Маршруты таблиц
│   └── tests/
│       ├── __init__.py
│       └── test_api.py      # Модульные тесты
└── frontend/
    ├── index.html           # HTML шаблон
    ├── styles.css           # CSS стили
    └── app.js               # JavaScript логика
```

## Развертывание

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd spreadsheet-app/backend
```

### 2. Создание виртуального окружения

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Запуск приложения

```bash
# Из папки backend
python main.py
```

Приложение будет доступно по адресу: http://localhost:8000

### 5. Документация API

После запуска откройте:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Запуск тестов

```bash
cd backend
pip install pytest httpx
pytest tests/ -v
```

## API Endpoints

### Аутентификация
- `POST /api/auth/register` - Регистрация пользователя
- `POST /api/auth/token` - Получение JWT токена
- `GET /api/auth/me` - Информация о текущем пользователе

### Таблицы
- `GET /api/spreadsheets/` - Список таблиц пользователя
- `POST /api/spreadsheets/` - Создание новой таблицы
- `GET /api/spreadsheets/{id}` - Получение таблицы по ID
- `PUT /api/spreadsheets/{id}` - Обновление таблицы
- `DELETE /api/spreadsheets/{id}` - Удаление таблицы
- `PUT /api/spreadsheets/{id}/cells/{address}` - Обновление ячейки
- `GET /api/spreadsheets/{id}/history` - История изменений

## Поддерживаемые формулы

| Функция | Описание | Пример |
|---------|----------|--------|
| SUM | Сумма диапазона | `=SUM(A1:A5)` |
| AVG | Среднее значение | `=AVG(B1:B10)` |
| MIN | Минимальное значение | `=MIN(C1:C20)` |
| MAX | Максимальное значение | `=MAX(D1:D15)` |
| COUNT | Количество значений | `=COUNT(E1:E100)` |
| IF | Условная функция | `=IF(A1>10,"Да","Нет")` |
| Арифметика | Простые выражения | `=A1+B2*2` |

## Технологии

**Backend:**
- FastAPI 0.109+ (Python web framework)
- SQLAlchemy 2.0+ (ORM)
- SQLite (база данных)
- Pydantic 2.5+ (валидация данных)
- python-jose (JWT токены)
- passlib (хеширование паролей)

**Frontend:**
- Vanilla JavaScript (ES6+)
- CSS3 с переменными
- HTML5

## Лицензия

MIT License - см. LICENSE файл (если присутствует)

## Безопасность

⚠️ **Важно:** В production среде необходимо:
1. Заменить `SECRET_KEY` в `auth.py` на безопасный ключ из переменных окружения
2. Настроить CORS для конкретных доменов
3. Использовать HTTPS
4. Рассмотреть использование PostgreSQL вместо SQLite

## Автор

Spreadsheet App © 2026
