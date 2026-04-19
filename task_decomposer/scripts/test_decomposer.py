#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы декомпозитора задач.
"""

import json
import sys
sys.path.insert(0, '/workspace/task_decomposer/src')

from decomposer import TaskDecomposer


def test_decomposer():
    """Запускает тесты декомпозитора."""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ДЕКОМПОЗИТОРА ЗАДАЧ")
    print("=" * 60)
    
    decomposer = TaskDecomposer()
    
    # Тестовые кейсы
    test_cases = [
        {
            "input": "Разработай интернет-магазин с онлайн оплатой",
            "expected_subtasks_min": 8,
            "description": "Интернет-магазин"
        },
        {
            "input": "Разработай группу справочников ОКАТО в Ataccama RDM",
            "expected_subtasks_min": 8,
            "description": "Справочник ОКАТО"
        },
        {
            "input": "Создай чат-бота для службы поддержки",
            "expected_subtasks_min": 7,
            "description": "Чат-бот"
        },
        {
            "input": "Разработай мобильное приложение для фитнеса",
            "expected_subtasks_min": 6,
            "description": "Мобильное приложение"
        },
        {
            "input": "Создай API для управления пользователями",
            "expected_subtasks_min": 6,
            "description": "API"
        },
        {
            "input": "Разработай дашборд для аналитики продаж",
            "expected_subtasks_min": 5,
            "description": "Дашборд"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nТест {i}: {test_case['description']}")
        print(f"Вход: {test_case['input']}")
        
        try:
            result = decomposer.decompose(test_case['input'])
            
            # Проверка структуры ответа
            assert 'original_task' in result, "Отсутствует поле 'original_task'"
            assert 'subtasks' in result, "Отсутствует поле 'subtasks'"
            assert isinstance(result['subtasks'], list), "'subtasks' должен быть списком"
            
            # Проверка количества подзадач
            num_subtasks = len(result['subtasks'])
            assert num_subtasks >= test_case['expected_subtasks_min'], \
                f"Ожидалось минимум {test_case['expected_subtasks_min']} подзадач, получено {num_subtasks}"
            
            # Проверка структуры каждой подзадачи
            for subtask in result['subtasks']:
                assert 'id' in subtask, "Отсутствует поле 'id' в подзадаче"
                assert 'title' in subtask, "Отсутствует поле 'title' в подзадаче"
                assert 'description' in subtask, "Отсутствует поле 'description' в подзадаче"
                assert 'priority' in subtask, "Отсутствует поле 'priority' в подзадаче"
                assert subtask['priority'] in ['high', 'medium', 'low'], \
                    f"Некорректный приоритет: {subtask['priority']}"
            
            print(f"✓ PASSED")
            print(f"  Подзадач: {num_subtasks}")
            passed += 1
            
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТЫ: {passed} passed, {failed} failed из {len(test_cases)} тестов")
    print("=" * 60)
    
    return failed == 0


def test_json_output():
    """Проверяет корректность JSON вывода."""
    print("\n\nПРОВЕРКА JSON ВЫВОДА")
    print("=" * 60)
    
    decomposer = TaskDecomposer()
    result = decomposer.decompose("Разработай интернет-магазин с онлайн оплатой")
    
    try:
        json_str = decomposer.to_json(result)
        parsed = json.loads(json_str)
        
        assert parsed == result, "JSON сериализация/десериализация изменила данные"
        print("✓ JSON вывод корректен")
        print(f"\nПример вывода:\n{json_str[:500]}...")
        return True
    except Exception as e:
        print(f"✗ Ошибка JSON: {e}")
        return False


if __name__ == "__main__":
    test1_passed = test_decomposer()
    test2_passed = test_json_output()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        sys.exit(0)
    else:
        print("НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        sys.exit(1)
