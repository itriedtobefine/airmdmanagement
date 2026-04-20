# TimeTracker Pro - Task Management with Time and Cost Tracking

## Описание проекта

TimeTracker Pro - это полнофункциональное приложение для управления задачами с возможностью отслеживания времени и расчета стоимости выполненных проектов и задач.

## Архитектура

### Бэкенд (Python/FastAPI)
- REST API с использованием FastAPI
- PostgreSQL база данных
- SQLAlchemy ORM
- Pydantic для валидации данных
- JWT аутентификация

### Фронтенд (React + Vite)
- Современный React с хуками
- Axios для HTTP запросов
- CSS модули для стилизации
- Компонентная архитектура

### База данных
- Пользователи (users)
- Проекты (projects)
- Задачи (tasks)
- Трекинг времени (time_entries)

## Структура проекта

```
/workspace
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── users.py
│   │   ├── projects.py
│   │   ├── tasks.py
│   │   └── time_entries.py
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       │   └── client.js
│       └── components/
│           ├── Projects.jsx
│           ├── Tasks.jsx
│           └── TimeTracker.jsx
├── config.json
├── setup.sh
└── README.md
```

## Развертывание

### Требования
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

### Установка

#### 1. Клонирование репозитория
```bash
git clone <repository_url>
cd timetracker-pro
```

#### 2. Создание виртуального окружения

**Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

#### 3. Установка зависимостей бэкенда
```bash
cd backend
pip install -r requirements.txt
```

#### 4. Установка зависимостей фронтенда
```bash
cd frontend
npm install
```

#### 5. Настройка базы данных
```bash
# Создать базу данных
createdb timetracker_db

# Или через psql
psql -U postgres -c "CREATE DATABASE timetracker_db;"
```

#### 6. Запуск приложения

**Бэкенд:**
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Фронтенд:**
```bash
cd frontend
npm run dev
```

## API Endpoints

### Пользователи
- `POST /api/users/` - Создать пользователя
- `GET /api/users/{user_id}` - Получить пользователя
- `GET /api/users/` - Список всех пользователей

### Проекты
- `POST /api/projects/` - Создать проект
- `GET /api/projects/` - Список проектов
- `GET /api/projects/{project_id}` - Получить проект
- `PUT /api/projects/{project_id}` - Обновить проект
- `DELETE /api/projects/{project_id}` - Удалить проект

### Задачи
- `POST /api/tasks/` - Создать задачу
- `GET /api/tasks/` - Список задач
- `GET /api/tasks/{task_id}` - Получить задачу
- `PUT /api/tasks/{task_id}` - Обновить задачу
- `DELETE /api/tasks/{task_id}` - Удалить задачу

### Трекинг времени
- `POST /api/time-entries/start/` - Начать отслеживание времени
- `POST /api/time-entries/stop/` - Остановить отслеживание времени
- `GET /api/time-entries/` - Список записей времени
- `GET /api/time-entries/project/{project_id}/summary` - Сводка по проекту

## Конфигурация

Файл `config.json` содержит настройки приложения:
- Порт бэкенда
- Порт фронтенда
- Параметры подключения к БД
- Ставки по умолчанию

## Лицензия

MIT License
