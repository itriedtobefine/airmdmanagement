#!/usr/bin/env python3
"""
Основной модуль приложения для декомпозиции задач.
Использует гибридный подход:
1. Эвристические правила и шаблоны для генерации декомпозиции
2. Возможность использования ML-модели при наличии
"""

import json
import re
import os
from typing import Dict, List, Any, Optional
from datetime import datetime


class TaskDecomposer:
    """Класс для декомпозиции задач на подзадачи."""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Инициализация декомпозитора.
        
        Args:
            model_path: Путь к ML-модели (опционально)
        """
        self.model_path = model_path
        self.model = None
        self.template_db = self._load_template_database()
        
        # Если модель указана, пробуем загрузить
        if model_path and os.path.exists(model_path):
            self._load_model(model_path)
    
    def _load_template_database(self) -> Dict[str, List[Dict]]:
        """Загружает базу шаблонов декомпозиции."""
        return {
            "интернет-магазин": [
                {"id": 1, "title": "Определение требований", "description": "Формализация бизнес-требований, пользовательских сценариев, ограничений и метрик успеха. Создание BRD, пользовательских историй, критериев приемки и реестра интеграций.", "priority": "high"},
                {"id": 2, "title": "Выбор архитектуры", "description": "Проектирование системной архитектуры. Выбор паттерна (headless, микросервисы или модульный монолит), БД, кэша, очереди сообщений и CI/CD.", "priority": "high"},
                {"id": 3, "title": "Разработка бэкенда", "description": "Реализация сервисов: аутентификация/авторизация, каталог, корзина, чекаут, платежные шлюзы, логирование, метрики.", "priority": "high"},
                {"id": 4, "title": "Разработка фронтенда", "description": "Создание пользовательского интерфейса: главная страница, каталог товаров, карточка товара, корзина, оформление заказа, личный кабинет.", "priority": "high"},
                {"id": 5, "title": "Интеграция платежей", "description": "Подключение платежного шлюза, реализация обработки платежей, возвратов, вебхуков. Проверка соответствия PCI DSS.", "priority": "high"},
                {"id": 6, "title": "Тестирование", "description": "Проведение функционального, интеграционного, нагрузочного тестирования. Валидация метрик SLA.", "priority": "high"},
                {"id": 7, "title": "Развертывание", "description": "Настройка production-инфраструктуры, миграция данных, zero-downtime деплой, настройка мониторинга.", "priority": "high"},
                {"id": 8, "title": "Поддержка", "description": "Мониторинг SLA, обработка инцидентов, регулярное обновление зависимостей и патчей безопасности.", "priority": "medium"}
            ],
            "справочник": [
                {"id": 1, "title": "Анализ требований", "description": "Изучение документации, определение структуры справочника, атрибутов, связей с другими данными.", "priority": "high"},
                {"id": 2, "title": "Проектирование модели данных", "description": "Разработка логической и физической модели данных. Определение типов данных, ограничений, индексов.", "priority": "high"},
                {"id": 3, "title": "Настройка подключения к источникам", "description": "Конфигурация подключений к источникам данных. Настройка расписаний обновления.", "priority": "medium"},
                {"id": 4, "title": "Разработка правил валидации", "description": "Создание правил проверки качества данных: проверка уникальности, целостности, соответствия форматам.", "priority": "high"},
                {"id": 5, "title": "Загрузка данных", "description": "Реализация процессов загрузки данных из источников. Настройка трансформаций и маппинга полей.", "priority": "high"},
                {"id": 6, "title": "Настройка рабочих процессов", "description": "Создание рабочих процессов утверждения изменений, уведомлений, эскалации.", "priority": "medium"},
                {"id": 7, "title": "Интеграция с потребителями", "description": "Настройка экспорта данных в системы-потребители через API, файлы или шины данных.", "priority": "medium"},
                {"id": 8, "title": "Документирование", "description": "Создание технической документации, инструкций пользователей.", "priority": "low"}
            ],
            "система управления": [
                {"id": 1, "title": "Сбор требований", "description": "Определение функциональных и нефункциональных требований. Анализ бизнес-процессов.", "priority": "high"},
                {"id": 2, "title": "Проектирование архитектуры", "description": "Выбор технологического стека, проектирование базы данных, определение структуры API.", "priority": "high"},
                {"id": 3, "title": "Разработка ядра системы", "description": "Реализация основных моделей данных и бизнес-логики системы.", "priority": "high"},
                {"id": 4, "title": "Система аутентификации", "description": "Регистрация, вход, восстановление пароля, JWT токены, роли и права доступа.", "priority": "high"},
                {"id": 5, "title": "Разработка интерфейса", "description": "Создание пользовательского интерфейса системы. Адаптивный дизайн.", "priority": "high"},
                {"id": 6, "title": "Интеграции", "description": "Подключение внешних систем и сервисов, необходимых для работы.", "priority": "medium"},
                {"id": 7, "title": "Тестирование", "description": "Юнит-тесты, интеграционные тесты, E2E тестирование, исправление багов.", "priority": "high"},
                {"id": 8, "title": "Деплой и мониторинг", "description": "Развертывание на сервере, настройка CI/CD, мониторинг производительности.", "priority": "high"}
            ],
            "чат-бот": [
                {"id": 1, "title": "Анализ сценариев", "description": "Изучение типичных запросов пользователей, определение сценариев диалогов.", "priority": "high"},
                {"id": 2, "title": "Выбор платформы", "description": "Выбор фреймворка для бота, определение каналов коммуникации.", "priority": "high"},
                {"id": 3, "title": "Проектирование диалогов", "description": "Создание сценариев диалогов, интентов, сущностей, контекстов.", "priority": "high"},
                {"id": 4, "title": "Интеграция с базами знаний", "description": "Подключение к базе знаний компании, поиск ответов на вопросы.", "priority": "medium"},
                {"id": 5, "title": "Разработка бота", "description": "Реализация обработки сообщений, управление состояниями диалога.", "priority": "high"},
                {"id": 6, "title": "Обучение модели NLP", "description": "Сбор и разметка данных для обучения, тренировка модели распознавания интентов.", "priority": "high"},
                {"id": 7, "title": "Тестирование", "description": "Тестирование различных сценариев, краш-тесты, проверка граничных случаев.", "priority": "high"},
                {"id": 8, "title": "Развертывание", "description": "Деплой бота, настройка аналитики, мониторинг качества ответов.", "priority": "medium"}
            ],
            "мобильное приложение": [
                {"id": 1, "title": "Исследование и прототипирование", "description": "Анализ конкурентов, создание вайрфреймов, прототипов экранов, тестирование юзабилити.", "priority": "high"},
                {"id": 2, "title": "Разработка дизайна", "description": "Создание визуального дизайна, дизайн-системы, анимаций.", "priority": "high"},
                {"id": 3, "title": "Разработка бэкенда", "description": "API для пользователей, данных, аутентификация, хранение медиа.", "priority": "high"},
                {"id": 4, "title": "Разработка мобильного приложения", "description": "Нативная или кроссплатформенная разработка основных экранов.", "priority": "high"},
                {"id": 5, "title": "Интеграции", "description": "Подключение к внешним сервисам, push-уведомления, аналитика.", "priority": "medium"},
                {"id": 6, "title": "Тестирование", "description": "Функциональное тестирование, тестирование на разных устройствах.", "priority": "high"},
                {"id": 7, "title": "Публикация", "description": "Публикация в App Store и Google Play, ASO.", "priority": "medium"}
            ],
            "api": [
                {"id": 1, "title": "Проектирование API", "description": "Определение endpoints, методов, форматов запросов/ответов, спецификация OpenAPI.", "priority": "high"},
                {"id": 2, "title": "Разработка моделей данных", "description": "Проектирование схемы базы данных, ORM моделей, миграций.", "priority": "high"},
                {"id": 3, "title": "Реализация endpoints", "description": "Разработка обработчиков запросов, бизнес-логики, валидации.", "priority": "high"},
                {"id": 4, "title": "Аутентификация и авторизация", "description": "Реализация JWT/OAuth2, ролевой модели, прав доступа.", "priority": "high"},
                {"id": 5, "title": "Документирование", "description": "Создание документации API, примеров использования, SDK.", "priority": "medium"},
                {"id": 6, "title": "Тестирование", "description": "Юнит-тесты, интеграционные тесты, нагрузочное тестирование.", "priority": "high"},
                {"id": 7, "title": "Развертывание", "description": "Настройка сервера, CI/CD, мониторинг, логирование.", "priority": "high"}
            ],
            "дашборд": [
                {"id": 1, "title": "Анализ требований", "description": "Определение метрик, KPI, источников данных, частоты обновления.", "priority": "high"},
                {"id": 2, "title": "Проектирование визуализации", "description": "Выбор типов графиков, компоновка дашборда, цветовая схема.", "priority": "high"},
                {"id": 3, "title": "Подготовка данных", "description": "Настройка ETL-процессов, агрегация данных, кэширование.", "priority": "high"},
                {"id": 4, "title": "Разработка фронтенда", "description": "Реализация интерактивных графиков, фильтров, экспорта данных.", "priority": "high"},
                {"id": 5, "title": "Интеграция с источниками", "description": "Подключение к базам данных, API, файловым хранилищам.", "priority": "medium"},
                {"id": 6, "title": "Тестирование и оптимизация", "description": "Проверка корректности данных, оптимизация производительности.", "priority": "high"}
            ]
        }
    
    def _load_model(self, model_path: str):
        """Пытается загрузить ML-модель для декомпозиции."""
        try:
            from llama_cpp import Llama
            self.model = Llama(
                model_path=model_path,
                n_ctx=2048,
                n_threads=2,
                verbose=False
            )
            print(f"ML-модель загружена: {model_path}")
        except Exception as e:
            print(f"Не удалось загрузить ML-модель: {e}")
            print("Будет использоваться эвристический метод")
    
    def decompose(self, task_text: str) -> Dict[str, Any]:
        """
        Декомпозирует задачу на подзадачи.
        
        Args:
            task_text: Текст задачи для декомпозиции
            
        Returns:
            Словарь с оригинальной задачей и списком подзадач
        """
        # Очищаем входной текст
        task_text = task_text.strip()
        
        # Пробуем использовать ML-модель если доступна
        if self.model:
            result = self._decompose_with_ml(task_text)
            if result:
                return result
        
        # Используем эвристический метод
        return self._decompose_heuristic(task_text)
    
    def _decompose_with_ml(self, task_text: str) -> Optional[Dict[str, Any]]:
        """Декомпозиция с использованием ML-модели."""
        if not self.model:
            return None
        
        prompt = f"""Декомпозируй следующую задачу на подзадачи. Верни ответ в формате JSON:
{{
  "original_task": "{task_text}",
  "subtasks": [
    {{"id": 1, "title": "...", "description": "...", "priority": "high/medium/low"}},
    ...
  ]
}}

Задача: {task_text}

Ответ:"""
        
        try:
            output = self.model(
                prompt,
                max_tokens=1024,
                temperature=0.3,
                top_p=0.9,
                stop=["\n\n", "```"]
            )
            
            response_text = output['choices'][0]['text'].strip()
            
            # Пытаемся извлечь JSON из ответа
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
        except Exception as e:
            print(f"Ошибка ML-декомпозиции: {e}")
        
        return None
    
    def _decompose_heuristic(self, task_text: str) -> Dict[str, Any]:
        """
        Эвристическая декомпозиция на основе шаблонов и правил.
        """
        task_lower = task_text.lower()
        
        # Определяем тип задачи по ключевым словам
        task_type = self._detect_task_type(task_lower)
        
        # Получаем базовый шаблон
        base_template = self.template_db.get(task_type, self.template_db["система управления"])
        
        # Генерируем подзадачи с адаптацией под конкретную задачу
        subtasks = self._adapt_template(base_template, task_text, task_type)
        
        # Добавляем специфичные подзадачи если обнаружены специальные требования
        special_subtasks = self._detect_special_requirements(task_text)
        if special_subtasks:
            subtasks = self._merge_subtasks(subtasks, special_subtasks)
        
        return {
            "original_task": task_text,
            "subtasks": subtasks
        }
    
    def _detect_task_type(self, task_lower: str) -> str:
        """Определяет тип задачи по ключевым словам."""
        patterns = {
            "интернет-магазин": ["интернет-магазин", "онлайн магазин", "e-commerce", "маркетплейс", "онлайн оплата"],
            "справочник": ["справочник", "классификатор", "окато", "оквэд", "rdm", "mdm", "мастер данные"],
            "чат-бот": ["чат-бот", "бот", "chatbot", "виртуальный помощник"],
            "мобильное приложение": ["мобильное приложение", "ios", "android", "app", "приложение для телефона"],
            "api": ["api", "rest api", "graphql", "микросервис", "веб-сервис"],
            "дашборд": ["дашборд", "панель управления", "dashboard", "визуализация данных", "bi"],
            "система управления": ["система", "платформа", "crm", "erp", "lms", "cms"]
        }
        
        best_match = "система управления"
        max_matches = 0
        
        for task_type, keywords in patterns.items():
            matches = sum(1 for kw in keywords if kw in task_lower)
            if matches > max_matches:
                max_matches = matches
                best_match = task_type
        
        return best_match
    
    def _adapt_template(self, template: List[Dict], task_text: str, task_type: str) -> List[Dict]:
        """Адаптирует шаблон под конкретную задачу."""
        adapted = []
        
        for i, subtask in enumerate(template, 1):
            adapted_subtask = {
                "id": i,
                "title": subtask["title"],
                "description": subtask["description"],
                "priority": subtask["priority"]
            }
            adapted.append(adapted_subtask)
        
        return adapted
    
    def _detect_special_requirements(self, task_text: str) -> Optional[List[Dict]]:
        """Обнаруживает специальные требования и добавляет соответствующие подзадачи."""
        task_lower = task_text.lower()
        special = []
        
        if "онлайн оплата" in task_lower or "платеж" in task_lower:
            special.append({
                "id": 100,
                "title": "Настройка платежной системы",
                "description": "Интеграция с платежными провайдерами, настройка обработки транзакций, обеспечение безопасности платежей.",
                "priority": "high"
            })
        
        if "безопасност" in task_lower:
            special.append({
                "id": 101,
                "title": "Аудит безопасности",
                "description": "Проведение SAST/DAST, аудит зависимостей, пентест, проверка OWASP Top 10.",
                "priority": "high"
            })
        
        if "атаккама" in task_lower or "ataccama" in task_lower:
            special.append({
                "id": 102,
                "title": "Настройка Ataccama RDM",
                "description": "Конфигурация подключения к Ataccama RDM, настройка правил качества данных.",
                "priority": "high"
            })
        
        return special if special else None
    
    def _merge_subtasks(self, base: List[Dict], special: List[Dict]) -> List[Dict]:
        """Объединяет базовые и специальные подзадачи."""
        # Пересчитываем ID
        merged = base.copy()
        for i, subtask in enumerate(special, len(base) + 1):
            subtask["id"] = i
            merged.append(subtask)
        return merged
    
    def to_json(self, result: Dict[str, Any], indent: int = 2) -> str:
        """Конвертирует результат в JSON строку."""
        return json.dumps(result, ensure_ascii=False, indent=indent)


def main():
    """Основная функция приложения."""
    import sys
    
    # Инициализация декомпозитора
    model_path = None
    config_path = "/workspace/task_decomposer/models/model_config.txt"
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            for line in f:
                if line.startswith("model_path="):
                    model_path = line.strip().split("=")[1]
                    break
    
    decomposer = TaskDecomposer(model_path=model_path)
    
    # Если запущено с аргументом - обрабатываем его
    if len(sys.argv) > 1:
        task_text = " ".join(sys.argv[1:])
    else:
        # Интерактивный режим
        print("=== Декомпозитор задач ===")
        print("Введите задачу для декомпозиции (или 'exit' для выхода)")
        
        while True:
            try:
                task_text = input("\nЗадача: ").strip()
                if task_text.lower() in ['exit', 'quit', 'выход']:
                    break
                
                if not task_text:
                    continue
                
                result = decomposer.decompose(task_text)
                print("\n" + "=" * 50)
                print(decomposer.to_json(result))
                print("=" * 50)
                
            except KeyboardInterrupt:
                break
            except EOFError:
                break


if __name__ == "__main__":
    main()
