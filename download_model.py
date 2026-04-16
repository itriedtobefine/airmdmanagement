"""
Модуль для NLP-обработки текста на основе правил и TF-IDF.
Не требует внешних моделей, работает полностью локально.
"""

import os
import re
import json
from collections import defaultdict

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

# Ключевые слова для классификации типов задач
TASK_KEYWORDS = {
    "manual_reference": ["ручной", "справочник", "типовой", "простой", "НСИ"],
    "manual_reference_advanced": ["ручной", "справочник", "сложный", "правила"],
    "external_integration": ["интеграция", "внешний", "источник", "данных"],
    "external_integration_complex": ["интеграция", "несколько", "множественный", "источник"],
    "registry_simple": ["реестр", "простой", "классификация"],
    "registry_complex": ["реестр", "сложный", "классификация", "правила"],
    "registry_with_workflow": ["реестр", "согласование", "workflow", "процесс"],
    "mdm_full": ["MDM", "мастеринг", "мастер-данные", "полноценный"],
    "rdm_basic": ["RDM", "НСИ", "нормативно-справочный", "базовый"],
    "rdm_advanced": ["НСИ", "иерархия", "версия", "расширенный", "RDM"],
    "api_endpoint": ["API", "эндпоинт", "метод", "REST"],
    "data_migration": ["миграция", "перенос", "данные", "загрузка"],
    "ui_form": ["форма", "ввод", "редактирование", "интерфейс", "UI"],
    "reporting": ["отчет", "отчетность", "статистика", "аналитика"],
    "validation_rules": ["валидация", "правило", "проверка", "контроль"],
    "workflow_approval": ["согласование", "workflow", "утверждение", "маршрут"],
    "versioning": ["версия", "версионирование", "история", "изменение"],
    "hierarchy_management": ["иерархия", "структура", "дерево", "вложенность"],
    "deduplication": ["дедупликация", "дубликат", "уникальность"],
    "audit_log": ["аудит", "лог", "журнал", "трек"]
}

# Слова-триггеры для справочников (достаточно одного совпадения)
REFERENCE_TRIGGER_WORDS = ["справочник", "реестр", "НСИ", "RDM", "MDM", "классификатор", "каталог", "регистр"]

# Ключевые слова для определения поддержки
SUPPORT_KEYWORDS = {
    "support_manual": ["ручной", "справочник", "поддержка"],
    "support_external": ["интеграция", "внешний", "поддержка"],
    "support_registry": ["реестр", "поддержка"],
    "support_mdm": ["MDM", "мастер-данные", "поддержка"],
    "support_rdm": ["RDM", "НСИ", "поддержка"],
    "support_api": ["API", "поддержка"],
    "support_complex": ["сложный", "валидация", "поддержка"]
}

# Стоп-слова (не относятся к справочникам)
OUT_OF_SCOPE_PHRASES = [
    "интернет-магазин", "интернет магазин", "ecommerce", "e-commerce",
    "социальная сеть", "social network",
    "игра", "game", "gaming",
    "мобильное приложение", "mobile app",
    "сайт-визитка", "landing page",
    "CRM", "ERP", "HRM",
    "бухгалтерия", "accounting",
    "чат-бот", "chatbot",
    "биржа", "marketplace",
    "доска объявлений"
]


def load_model():
    """Псевдо-загрузка модели (для совместимости интерфейса)."""
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
    
    # Сохраняем конфигурацию ключевых слов
    config_path = os.path.join(MODEL_DIR, "keywords_config.json")
    config = {
        "task_keywords": TASK_KEYWORDS,
        "support_keywords": SUPPORT_KEYWORDS,
        "out_of_scope": OUT_OF_SCOPE_PHRASES
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    return config


def extract_parameters(text: str) -> dict:
    """Извлекает параметры из текста запроса."""
    text_lower = text.lower()
    
    # Проверка на соответствие целевому сценарию
    for phrase in OUT_OF_SCOPE_PHRASES:
        if phrase.lower() in text_lower:
            return {"error": "out_of_scope"}
    
    # Проверка на наличие триггерных слов справочников
    has_reference_trigger = any(word in text_lower for word in REFERENCE_TRIGGER_WORDS)
    
    detected_tasks = []
    detected_support = []
    
    # Поиск соответствий по ключевым словам
    for task_type, keywords in TASK_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw.lower() in text_lower)
        # Для задач со справочником достаточно 1 совпадения, для остальных - 2
        threshold = 1 if has_reference_trigger else 2
        if match_count >= threshold:
            detected_tasks.append((task_type, match_count))
    
    for support_type, keywords in SUPPORT_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw.lower() in text_lower)
        if match_count >= 1:  # Для поддержки достаточно 1 совпадения
            detected_support.append((support_type, match_count))
    
    # Сортировка по количеству совпадений
    detected_tasks.sort(key=lambda x: x[1], reverse=True)
    detected_support.sort(key=lambda x: x[1], reverse=True)
    
    # Извлечение числовых значений (часы на поддержку)
    hours_pattern = r'(\d+)\s*(?:час|ч\.)'
    hours_matches = re.findall(hours_pattern, text_lower)
    support_hours = int(hours_matches[0]) if hours_matches else None
    
    # Определение технологического стека
    tech_stack = []
    tech_keywords = {
        "Python": ["python", "django", "flask", "fastapi"],
        "Java": ["java", "spring"],
        ".NET": [".net", "c#", "asp.net"],
        "PostgreSQL": ["postgresql", "postgres"],
        "MySQL": ["mysql", "mariadb"],
        "Oracle": ["oracle"],
        "MongoDB": ["mongodb", "mongo"],
        "Redis": ["redis"],
        "Docker": ["docker", "контейнер"],
        "Kubernetes": ["kubernetes", "k8s"]
    }
    
    for tech, keywords in tech_keywords.items():
        if any(kw in text_lower for kw in keywords):
            tech_stack.append(tech)
    
    return {
        "tasks": [t[0] for t in detected_tasks[:5]],  # Топ-5 задач
        "support": [s[0] for s in detected_support[:3]],  # Топ-3 типа поддержки
        "support_hours": support_hours,
        "tech_stack": tech_stack,
        "is_valid": len(detected_tasks) > 0 or has_reference_trigger
    }


if __name__ == "__main__":
    load_model()
    print("NLP module initialized successfully!")
    
    # Тестирование
    test_text = "Разработка справочника ОКАТО с интеграцией получения данных из внешнего источника"
    result = extract_parameters(test_text)
    print(f"Test: {test_text}")
    print(f"Result: {result}")
