#!/usr/bin/env python3
"""
Приложение для декомпозиции задач на подзадачи.
Использует комбинацию pattern matching и template-based подхода.
"""

import json
import re
from typing import Dict, List, Any


class TaskDecomposer:
    """Класс для декомпозиции задач на подзадачи."""
    
    def __init__(self):
        # Шаблоны задач и соответствующие им декомпозиции
        self.task_patterns = [
            {
                "pattern": r"(разработай|создай|сделай).*(интернет-магазин|магазин|e-commerce|маркетплейс)",
                "subtasks": [
                    {"id": 1, "title": "Определение требований", "description": "Формализация бизнес-требований, пользовательских сценариев, ограничений и метрик успеха. Создание BRD, пользовательских историй, критериев приемки и реестра интеграций.", "priority": "high"},
                    {"id": 2, "title": "Выбор архитектуры", "description": "Проектирование системной архитектуры. Выбор паттерна (headless, микросервисы или модульный монолит), БД, кэша, очереди сообщений и CI/CD.", "priority": "high"},
                    {"id": 3, "title": "Разработка backend", "description": "Реализация API, аутентификация/авторизация (OAuth2/JWT), каталог, корзина, чекаут, платежные шлюзы.", "priority": "high"},
                    {"id": 4, "title": "Разработка frontend", "description": "Создание UI/UX интерфейса, адаптивная верстка, интеграция с API, управление состоянием.", "priority": "high"},
                    {"id": 5, "title": "Интеграция платежей", "description": "Подключение платежных систем, обработка транзакций, безопасность платежей, PCI DSS compliance.", "priority": "high"},
                    {"id": 6, "title": "Тестирование", "description": "Функциональное, интеграционное, нагрузочное тестирование, валидация метрик SLA.", "priority": "high"},
                    {"id": 7, "title": "Документация", "description": "Специации API (OpenAPI), архитектурные диаграммы, инструкции по развертыванию.", "priority": "medium"},
                    {"id": 8, "title": "Деплой и мониторинг", "description": "Настройка production-инфраструктуры, мониторинг (Prometheus, Grafana), алертинг.", "priority": "high"}
                ]
            },
            {
                "pattern": r"(разработай|создай|сделай).*(справочник|reference data|mdm|rdm|атачма|ataccama)",
                "subtasks": [
                    {"id": 1, "title": "Анализ предметной области", "description": "Изучение структуры ОКАТО, определение атрибутов справочника, связей с другими данными.", "priority": "high"},
                    {"id": 2, "title": "Проектирование модели данных", "description": "Определение сущностей, атрибутов, иерархий, правил валидации для справочника ОКАТО.", "priority": "high"},
                    {"id": 3, "title": "Настройка Ataccama RDM", "description": "Конфигурация среды RDM, создание проекта, настройка подключений к источникам данных.", "priority": "high"},
                    {"id": 4, "title": "Загрузка данных", "description": "Импорт данных ОКАТО из источников, маппинг полей, первичная валидация.", "priority": "high"},
                    {"id": 5, "title": "Настройка правил качества", "description": "Определение rules для валидации данных, дедупликации, проверки целостности иерархии.", "priority": "high"},
                    {"id": 6, "title": "Workflow утверждения", "description": "Настройка процессов stewardship, workflow согласования изменений.", "priority": "medium"},
                    {"id": 7, "title": "Интеграции", "description": "Настройка экспорта данных в целевые системы, API для доступа к справочнику.", "priority": "medium"},
                    {"id": 8, "title": "Документация и обучение", "description": "Документирование модели, инструкций для пользователей, обучение data stewards.", "priority": "medium"}
                ]
            },
            {
                "pattern": r"(разработай|создай|сделай).*(систему управления задачами|task tracker|трекер задач)",
                "subtasks": [
                    {"id": 1, "title": "Анализ требований", "description": "Определение функциональности: создание задач, назначение исполнителей, статусы, дедлайны, уведомления.", "priority": "high"},
                    {"id": 2, "title": "Проектирование БД", "description": "Схема данных: пользователи, проекты, задачи, комментарии, вложения. Выбор PostgreSQL.", "priority": "high"},
                    {"id": 3, "title": "Backend разработка", "description": "REST API, JWT аутентификация, CRUD операции, WebSocket для real-time обновлений.", "priority": "high"},
                    {"id": 4, "title": "Frontend разработка", "description": "React/Vue.js приложение, drag-and-drop канбан, календарь, дашборды.", "priority": "high"},
                    {"id": 5, "title": "Интеграции", "description": "Email уведомления, Slack/Discord боты, экспорт в CSV/PDF.", "priority": "medium"},
                    {"id": 6, "title": "Тестирование и деплой", "description": "Unit/integration тесты, Docker контейнеризация, CI/CD пайплайн.", "priority": "high"}
                ]
            },
            {
                "pattern": r"(разработай|создай|сделай).*(чат-бот|бот|chatbot)",
                "subtasks": [
                    {"id": 1, "title": "Анализ сценариев", "description": "Определение типовых запросов, FAQ, эскалация на оператора.", "priority": "high"},
                    {"id": 2, "title": "Выбор платформы", "description": "Telegram/Discord/WhatsApp API или мультиплатформенное решение.", "priority": "high"},
                    {"id": 3, "title": "NLP движок", "description": "Intent recognition, entity extraction, контекстная память диалога.", "priority": "high"},
                    {"id": 4, "title": "База знаний", "description": "Векторная БД для семантического поиска, RAG архитектура.", "priority": "high"},
                    {"id": 5, "title": "Интеграции", "description": "Ticketing система (Jira/Zendesk), CRM, аналитика.", "priority": "medium"},
                    {"id": 6, "title": "Тестирование", "description": "Диалоговые сценарии, A/B тесты, метрики удовлетворенности.", "priority": "high"}
                ]
            },
            {
                "pattern": r"(разработай|создай|сделай).*(ETL|пайплайн|pipeline|data pipeline)",
                "subtasks": [
                    {"id": 1, "title": "Анализ источников", "description": "Определение форматов данных: CSV, JSON, базы данных. Частота обновления.", "priority": "high"},
                    {"id": 2, "title": "Extract", "description": "Подключение к источникам, incremental load, handling API rate limits.", "priority": "high"},
                    {"id": 3, "title": "Transform", "description": "Очистка данных, нормализация, агрегация, business rules.", "priority": "high"},
                    {"id": 4, "title": "Load", "description": "Загрузка в data warehouse, upsert logic.", "priority": "high"},
                    {"id": 5, "title": "Orchestration", "description": "Airflow DAGs, scheduling, dependencies, error handling.", "priority": "high"},
                    {"id": 6, "title": "Monitoring", "description": "Data quality checks, alerts на failures, lineage tracking.", "priority": "high"}
                ]
            },
            {
                "pattern": r"(разработай|создай|сделай).*(ML|машинное обучение|machine learning|модель)",
                "subtasks": [
                    {"id": 1, "title": "Data preparation", "description": "Feature engineering, train/test split, preprocessing.", "priority": "high"},
                    {"id": 2, "title": "Model training", "description": "Hyperparameter tuning, cross-validation, ensemble methods.", "priority": "high"},
                    {"id": 3, "title": "Model registry", "description": "Versioning, metadata tracking, model comparison.", "priority": "high"},
                    {"id": 4, "title": "Deployment", "description": "Model serving, A/B testing, canary releases.", "priority": "high"},
                    {"id": 5, "title": "Monitoring", "description": "Prediction drift, performance decay, retraining triggers.", "priority": "high"},
                    {"id": 6, "title": "Pipeline orchestration", "description": "MLflow, Kubeflow для автоматизации.", "priority": "medium"}
                ]
            },
            {
                "pattern": r"(разработай|создай|сделай).*(REST API|API|backend)",
                "subtasks": [
                    {"id": 1, "title": "Проектирование API", "description": "OpenAPI спецификация, endpoints, request/response схемы.", "priority": "high"},
                    {"id": 2, "title": "База данных", "description": "Модели данных, выбор СУБД, индексы, миграции.", "priority": "high"},
                    {"id": 3, "title": "Реализация endpoints", "description": "CRUD операции, бизнес-логика, валидация input.", "priority": "high"},
                    {"id": 4, "title": "Безопасность", "description": "Аутентификация, авторизация, rate limiting, защита от атак.", "priority": "high"},
                    {"id": 5, "title": "Документация", "description": "Swagger/OpenAPI документация, примеры использования.", "priority": "medium"},
                    {"id": 6, "title": "Тестирование", "description": "Unit/integration тесты, нагрузочное тестирование.", "priority": "high"}
                ]
            },
            {
                "pattern": r"(разработай|создай|сделай).*(аутентификация|авторизация|auth|IAM)",
                "subtasks": [
                    {"id": 1, "title": "Проектирование", "description": "OAuth2/OIDC flow, роли и permissions, MFA, сессии.", "priority": "high"},
                    {"id": 2, "title": "База данных", "description": "Пользователи, роли, токены, audit log. PostgreSQL.", "priority": "high"},
                    {"id": 3, "title": "Auth сервис", "description": "Регистрация, login, refresh tokens, password reset, MFA.", "priority": "high"},
                    {"id": 4, "title": "Authorization сервис", "description": "RBAC/ABAC, policy engine, middleware для защиты endpoints.", "priority": "high"},
                    {"id": 5, "title": "Безопасность", "description": "Хеширование паролей (bcrypt), rate limiting, brute force protection.", "priority": "high"},
                    {"id": 6, "title": "Интеграции", "description": "Social login (Google, GitHub), SSO, LDAP/Active Directory.", "priority": "medium"}
                ]
            }
        ]
        
        # Общие подзадачи для любых проектов
        self.common_subtasks = [
            {"id": 99, "title": "Планирование", "description": "Оценка сроков, ресурсов, рисков. Составление roadmap.", "priority": "high"},
            {"id": 100, "title": "Документирование", "description": "Техническая документация, инструкции пользователя.", "priority": "medium"}
        ]
    
    def decompose(self, task_text: str) -> Dict[str, Any]:
        """
        Декомпозирует задачу на подзадачи.
        
        Args:
            task_text: Текст задачи для декомпозиции
            
        Returns:
            Словарь с оригинальной задачей и списком подзадач
        """
        task_text_lower = task_text.lower()
        
        # Поиск подходящего шаблона
        matched_subtasks = None
        for pattern_info in self.task_patterns:
            if re.search(pattern_info["pattern"], task_text_lower):
                matched_subtasks = pattern_info["subtasks"].copy()
                break
        
        # Если шаблон не найден, используем универсальную декомпозицию
        if matched_subtasks is None:
            matched_subtasks = self._generate_generic_subtasks(task_text)
        
        # Пересчитываем ID подзадач
        for i, subtask in enumerate(matched_subtasks, 1):
            subtask["id"] = i
        
        return {
            "original_task": task_text,
            "subtasks": matched_subtasks
        }
    
    def _generate_generic_subtasks(self, task_text: str) -> List[Dict[str, Any]]:
        """Генерирует универсальные подзадачи для неизвестного типа задачи."""
        
        # Определяем тип задачи по ключевым словам
        keywords_analysis = self._analyze_keywords(task_text)
        
        generic_subtasks = [
            {
                "id": 1,
                "title": "Анализ требований",
                "description": f"Сбор и формализация требований к системе. Определение функциональных и нефункциональных требований, ограничений, критериев приемки.",
                "priority": "high"
            },
            {
                "id": 2,
                "title": "Проектирование архитектуры",
                "description": f"Выбор технологического стека, проектирование компонентов системы, определение интерфейсов и интеграций.",
                "priority": "high"
            },
            {
                "id": 3,
                "title": "Разработка ядра системы",
                "description": f"Реализация основной бизнес-логики, базовых компонентов и механизмов системы.",
                "priority": "high"
            },
            {
                "id": 4,
                "title": "Разработка интерфейсов",
                "description": f"Создание пользовательских интерфейсов, API для интеграции, документирование контрактов.",
                "priority": "high"
            },
            {
                "id": 5,
                "title": "Интеграции",
                "description": f"Подключение внешних систем, сервисов, настройка обмена данными.",
                "priority": "medium"
            },
            {
                "id": 6,
                "title": "Тестирование",
                "description": f"Функциональное, интеграционное, регрессионное тестирование. Исправление дефектов.",
                "priority": "high"
            },
            {
                "id": 7,
                "title": "Документация",
                "description": f"Создание технической документации, руководств пользователя, инструкций по эксплуатации.",
                "priority": "medium"
            },
            {
                "id": 8,
                "title": "Внедрение и поддержка",
                "description": f"Деплой в production, обучение пользователей, настройка мониторинга, техническая поддержка.",
                "priority": "high"
            }
        ]
        
        return generic_subtasks
    
    def _analyze_keywords(self, text: str) -> Dict[str, bool]:
        """Анализирует текст задачи на наличие ключевых слов."""
        text_lower = text.lower()
        
        return {
            "is_data_project": any(kw in text_lower for kw in ["данные", "data", "etl", "аналитика"]),
            "is_web_project": any(kw in text_lower for kw in ["веб", "web", "сайт", "frontend"]),
            "is_mobile_project": any(kw in text_lower for kw in ["мобильн", "mobile", "ios", "android"]),
            "is_api_project": any(kw in text_lower for kw in ["api", "rest", "graphql", "endpoint"]),
            "is_ml_project": any(kw in text_lower for kw in ["ml", "ai", "нейро", "model", "прогноз"])
        }


def main():
    """Основная функция приложения."""
    import sys
    
    decomposer = TaskDecomposer()
    
    # Если передан аргумент командной строки - используем его
    if len(sys.argv) > 1:
        task_text = " ".join(sys.argv[1:])
    else:
        # Интерактивный режим
        print("=== Приложение для декомпозиции задач ===")
        print("Введите задачу для декомпозиции (или 'exit' для выхода):")
        
        while True:
            try:
                task_text = input("> ").strip()
            except EOFError:
                break
            
            if task_text.lower() in ["exit", "quit", "выход"]:
                break
            
            if not task_text:
                continue
            
            result = decomposer.decompose(task_text)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("\nВведите следующую задачу (или 'exit' для выхода):")
        
        return
    
    # Режим с аргументом
    result = decomposer.decompose(task_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
