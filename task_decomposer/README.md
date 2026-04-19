# Task Decomposer - Приложение для декомпозиции задач

Приложение использует ИИ-модель (или эвристические методы) для декомпозиции текстовых задач на подзадачи.

## Структура проекта

```
task_decomposer/
├── data/                    # Обучающие данные
│   └── training_data.json   # Датасет для обучения модели
├── models/                  # ML-модели
│   └── model_config.txt     # Конфигурация модели (создается автоматически)
├── scripts/                 # Скрипты
│   ├── generate_dataset.py  # Генератор обучающих данных
│   └── download_model.py    # Скрипт скачивания модели
├── src/                     # Исходный код
│   └── decomposer.py        # Основной модуль декомпозиции
└── README.md                # Этот файл
```

## Установка

### 1. Установка зависимостей

```bash
# Установка llama-cpp-python с оптимизированными бинарниками
pip install llama-cpp-python==0.2.60 --prefer-binary --only-binary :all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu/

# Дополнительные библиотеки
pip install huggingface_hub requests tqdm
```

### 2. Проверка установки

```bash
python -c "import llama_cpp; print('llama-cpp-python version:', llama_cpp.__version__)"
```

### 3. Скачивание модели (опционально)

```bash
cd task_decomposer
python scripts/download_model.py
```

**Важно:** Модель скачивается только если есть достаточно свободного места (модель занимает ~300MB). Если места недостаточно, приложение будет работать в эвристическом режиме без ML-модели.

### 4. Генерация обучающих данных (опционально)

```bash
python scripts/generate_dataset.py
```

## Использование

### Интерактивный режим

```bash
python src/decomposer.py
```

### Обработка задачи из командной строки

```bash
python src/decomposer.py "Разработай интернет-магазин с онлайн оплатой"
```

### Использование в коде Python

```python
from src.decomposer import TaskDecomposer
import json

# Инициализация декомпозитора
decomposer = TaskDecomposer(model_path="/path/to/model.gguf")  # или None для эвристического режима

# Декомпозиция задачи
result = decomposer.decompose("Разработай группу справочников ОКАТО в Ataccama RDM")

# Вывод результата
print(json.dumps(result, ensure_ascii=False, indent=2))
```

## Формат ответа

Приложение возвращает JSON следующего формата:

```json
{
  "original_task": "Текст исходной задачи",
  "subtasks": [
    {
      "id": 1,
      "title": "Название подзадачи",
      "description": "Подробное описание подзадачи",
      "priority": "high|medium|low"
    },
    ...
  ]
}
```

## Примеры работы

### Вход: "Разработай интернет-магазин с онлайн оплатой"

Выход:
```json
{
  "original_task": "Разработай интернет-магазин с онлайн оплатой",
  "subtasks": [
    {"id": 1, "title": "Определение требований", "description": "...", "priority": "high"},
    {"id": 2, "title": "Выбор архитектуры", "description": "...", "priority": "high"},
    {"id": 3, "title": "Разработка бэкенда", "description": "...", "priority": "high"},
    {"id": 4, "title": "Разработка фронтенда", "description": "...", "priority": "high"},
    {"id": 5, "title": "Интеграция платежей", "description": "...", "priority": "high"},
    {"id": 6, "title": "Тестирование", "description": "...", "priority": "high"},
    {"id": 7, "title": "Развертывание", "description": "...", "priority": "high"},
    {"id": 8, "title": "Поддержка", "description": "...", "priority": "medium"}
  ]
}
```

### Вход: "Разработай группу справочников ОКАТО в Ataccama RDM"

Выход:
```json
{
  "original_task": "Разработай группу справочников ОКАТО в Ataccama RDM",
  "subtasks": [
    {"id": 1, "title": "Анализ требований", "description": "...", "priority": "high"},
    {"id": 2, "title": "Проектирование модели данных", "description": "...", "priority": "high"},
    ...
    {"id": 9, "title": "Настройка Ataccama RDM", "description": "...", "priority": "high"}
  ]
}
```

## Режимы работы

### 1. Эвристический режим (по умолчанию)

Использует базу шаблонов и правил для декомпозиции задач:
- Распознавание типа задачи по ключевым словам
- Применение соответствующего шаблона декомпозиции
- Добавление специальных подзадач при обнаружении специфичных требований

### 2. ML-режим (при наличии модели)

Использует языковую модель для генерации декомпозиции:
- Загружается квантованная GGUF модель (Qwen 0.5B)
- Модель генерирует декомпозицию на основе промпта
- Результат парсится и валидируется

## Поддерживаемые типы задач

- Интернет-магазины и e-commerce
- Справочники и классификаторы (ОКАТО, ОКВЭД и т.д.)
- Системы управления (CRM, ERP, LMS, CMS)
- Чат-боты и виртуальные помощники
- Мобильные приложения
- API и микросервисы
- Дашборды и системы визуализации

## Тестирование

```bash
cd task_decomposer

# Запуск тестов
python -c "
from src.decomposer import TaskDecomposer
import json

decomposer = TaskDecomposer()

test_cases = [
    'Разработай интернет-магазин с онлайн оплатой',
    'Разработай группу справочников ОКАТО в Ataccama RDM',
    'Создай чат-бота для службы поддержки',
    'Разработай мобильное приложение для фитнеса'
]

for task in test_cases:
    result = decomposer.decompose(task)
    print(f'Задача: {task}')
    print(f'Подзадач: {len(result[\"subtasks\"])}')
    print()
"
```

## Требования к ресурсам

- **Минимальные:** Работает в эвристическом режиме без ML-модели
- **Рекомендуемые:** 300+ MB свободного места для загрузки модели Qwen 0.5B

## Лицензия

MIT
