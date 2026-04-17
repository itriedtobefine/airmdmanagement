# Reference Data Management Cost Calculator

## Описание

Локальное веб-приложение для оценки экономической эффективности передачи разработки и поддержки справочника другой команде. Система анализирует текстовое описание проекта, извлекает параметры с помощью локальной LLM (Qwen2.5-3B-Instruct), и рассчитывает стоимость на основе детерминированных таблиц нормативов.

## Архитектура

```
/workspace
├── app.py                      # FastAPI приложение (main entry point)
├── setup_model.py              # Скрипт загрузки модели
├── requirements.txt            # Зависимости Python
├── README.md                   # Документация
├── models/
│   └── schemas.py              # Pydantic модели
├── services/
│   ├── llm_extractor.py        # LLM извлечение параметров
│   └── cost_calculator.py      # Движок расчёта стоимости
├── data/
│   ├── development_effort.csv  # Нормативы времени на разработку
│   ├── support_effort.csv      # Нормативы времени на поддержку
│   └── hourly_rates.csv        # Часовые ставки специалистов
├── templates/
│   └── index.html              # Веб-интерфейс
├── static/                     # Статические файлы
└── models/                     # Директория для GGUF модели
```

## Требования

- Python 3.10+
- Windows/Linux/macOS
- Минимум 8 ГБ RAM (для работы LLM)
- ~5 ГБ свободного места на диске

## Лицензии зависимостей

Все зависимости используют разрешённые лицензии (MIT, Apache 2.0, BSD):
- fastapi: MIT
- uvicorn: BSD
- pandas: BSD
- pydantic: MIT
- llama-cpp-python: MIT
- huggingface-hub: Apache 2.0

## Инструкция по развёртыванию

### Шаг 1: Клонирование репозитория

```bash
git clone <repository-url> rdmc-calculator
cd rdmc-calculator
```

Если вы работаете с существующим репозиторием:

```bash
cd /path/to/existing/repo
git checkout <branch-name>
# или переключение на конкретный коммит
git checkout <commit-hash>
```

### Шаг 2: Создание виртуального окружения (Windows)

```bash
# Откройте PowerShell или Command Prompt
python -m venv venv

# Активация виртуального окружения
# PowerShell:
.\venv\Scripts\Activate.ps1

# Command Prompt:
.\venv\Scripts\activate.bat
```

### Шаг 3: Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Примечание:** Установка `llama-cpp-python` может занять несколько минут, так как требует компиляции C++ расширений.

### Шаг 4: Загрузка модели

```bash
python setup_model.py
```

Скрипт загрузит модель Qwen2.5-3B-Instruct-GGUF (квантование Q4_K_M) из HuggingFace Hub (~2.5 ГБ). Модель сохранится в директорию `/models`.

### Шаг 5: Запуск приложения

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Приложение будет доступно по адресу: http://localhost:8000

## Использование

1. Откройте браузер и перейдите на http://localhost:8000
2. Введите текстовое описание планируемого справочника или реестра
3. Нажмите кнопку "Рассчитать стоимость"
4. Получите результат с детализацией:
   - Стоимость разработки
   - Годовая стоимость поддержки
   - Детализация по компонентам
   - Обоснование результата

### Примеры входных данных

**Пример 1: Простой справочник**
```
Нужно разработать ручной справочник ОКАТО с базовыми полями: код и наименование. Планируется около 500 записей.
```

**Пример 2: Сложный реестр с интеграцией**
```
Требуется создать реестр классификации данных со сложными правилами валидации и интеграцией с внешней CRM системой через API. Нужна поддержка и аудит изменений.
```

**Пример 3: Мастер-данные**
```
Разработка мастер-данных контрагентов с золотой записью и функцией сопоставления дубликатов. Требуется ежегодная поддержка.
```

## API Endpoints

### POST /api/calculate

Расчёт стоимости на основе текстового описания.

**Request:**
```json
{
    "description": "Текстовое описание проекта"
}
```

**Response:**
```json
{
    "success": true,
    "development_total_hours": 25.0,
    "development_total_cost_rub": 87500.0,
    "support_total_hours_per_year": 10.0,
    "support_total_cost_per_year_rub": 20000.0,
    "development_breakdown": [...],
    "support_breakdown": [...],
    "summary": "Справочник: ОКАТО | Тип задачи: manual_registry | ...",
    "registry_name": "ОКАТО",
    "components_included": ["manual_registry:basic_structure"]
}
```

### GET /api/health

Проверка состояния сервиса.

**Response:**
```json
{
    "status": "healthy",
    "model_loaded": true,
    "calculator_ready": true
}
```

## Таблицы данных

### development_effort.csv

Нормативы времени на разработку по типам задач:
- manual_registry: Ручные справочники
- external_integration: Интеграция с внешними источниками
- classification_registry: Реестры классификации
- reference_data: Нормативно-справочная информация
- master_data: Мастер-данные
- ui_component: UI компоненты
- data_migration: Миграция данных
- documentation: Документация

### support_effort.csv

Годовые нормативы поддержки для каждого типа задач.

### hourly_rates.csv

Часовые ставки специалистов (в рублях):
- developer: 3500 ₽/час
- tester: 2500 ₽/час
- analyst: 3000 ₽/час
- admin: 2000 ₽/час
- support: 2000 ₽/час

## Обработка ошибок

### OUT_OF_SCOPE
Запрос не относится к сфере справочников и реестров. Система отклоняет запросы типа "разработка интернет-магазина" с соответствующим сообщением.

### 422 Unprocessable Entity
Ошибка валидации входных данных или ответа от LLM.

### 503 Service Unavailable
Модель не загружена. Необходимо запустить `python setup_model.py`.

## Производительность

- Время инференса LLM: ~5-15 секунд (зависит от CPU)
- Время расчёта: < 100 мс
- Рекомендуемый CPU: 4+ ядра
- Память: 8+ ГБ

## Безопасность

- Локальное развёртывание без доступа в интернет (после загрузки модели)
- Никаких внешних API вызовов
- Все данные обрабатываются локально

## Расширение таблиц

Для добавления новых типов задач отредактируйте CSV файлы в директории `/data`:

```csv
task_type,component,description,effort_hours
my_custom_type,my_component,Описание задачи,15
```

## Troubleshooting

### Ошибка при установке llama-cpp-python

Убедитесь, что установлены build tools:

**Windows:**
```bash
pip install cmake
pip install llama-cpp-python --no-cache-dir
```

**Linux:**
```bash
sudo apt-get install build-essential
pip install llama-cpp-python --no-cache-dir
```

### Модель не загружается

Проверьте наличие файла модели:
```bash
ls models/qwen2.5-3b-instruct-q4_k_m.gguf
```

При необходимости удалите и загрузите заново:
```bash
rm models/qwen2.5-3b-instruct-q4_k_m.gguf
python setup_model.py
```

### Недостаточно памяти

Уменьшите `n_ctx` в `services/llm_extractor.py` с 2048 до 1024.

## Версия

1.0.0

## Контакты

Для вопросов и предложений обратитесь к документации или исходному коду.
