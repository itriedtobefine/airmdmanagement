#!/usr/bin/env python3
"""
Скрипт для тестирования локальной GGUF модели с использованием llama-cpp-python
Модель: TinyGemma3 Q8_0 (~45 MB)
"""

import os
from llama_cpp import Llama

MODEL_PATH = "models/tinygemma3-Q8_0.gguf"

def test_model():
    """Тестирует загруженную модель простым запросом"""
    
    # Проверяем наличие файла модели
    if not os.path.exists(MODEL_PATH):
        print(f"Ошибка: Модель не найдена по пути {MODEL_PATH}")
        print("Запустите сначала download_model.py для загрузки модели")
        return False
    
    file_size = os.path.getsize(MODEL_PATH)
    print(f"Найден файл модели: {MODEL_PATH}")
    print(f"Размер: {file_size / (1024*1024):.2f} MB")
    print()
    
    try:
        print("Загружаю модель в память...")
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=512,  # Контекст окна
            n_threads=2,  # Количество потоков CPU
            verbose=False
        )
        print("Модель успешно загружена!")
        print()
        
        # Тестовый запрос
        prompt = "Привет! Как дела?"
        print(f"Тестовый запрос: {prompt}")
        print("-" * 50)
        
        output = llm(
            prompt,
            max_tokens=100,
            stop=["\n", "</s>"],
            echo=False
        )
        
        response = output['choices'][0]['text']
        print(f"Ответ модели: {response.strip()}")
        print("-" * 50)
        print()
        print("Тестирование завершено успешно!")
        return True
        
    except Exception as e:
        print(f"Ошибка при тестировании модели: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_model()
    exit(0 if success else 1)
