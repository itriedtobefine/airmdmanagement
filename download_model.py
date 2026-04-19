#!/usr/bin/env python3
"""
Скрипт для скачивания GGUF модели TinyLlama-1.1B Chat v1.0 Q2_K
Модель: tinyllama-1.1b-chat-v1.0.Q2_K.gguf (~461 MB)
Источник: TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF на HuggingFace

ПРИМЕЧАНИЕ: Для данной песочницы с 454MB свободного места,
эта модель слишком велика. Используйте модель меньшего размера.
"""

import os
import urllib.request
import sys

# Используем модель которая помещается в доступное место
MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q2_k.gguf"
MODEL_DIR = "models"
MODEL_FILENAME = "qwen2.5-0.5b-instruct-q2_k.gguf"

def download_model():
    """Скачивает модель в локальную директорию models/"""
    
    # Создаем директорию для моделей если не существует
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
        print(f"Создана директория: {MODEL_DIR}")
    
    model_path = os.path.join(MODEL_DIR, MODEL_FILENAME)
    
    # Проверяем есть ли уже модель
    if os.path.exists(model_path):
        file_size = os.path.getsize(model_path)
        print(f"Модель уже существует: {model_path}")
        print(f"Размер: {file_size / (1024*1024):.2f} MB")
        return model_path
    
    print(f"Начинаю загрузку модели...")
    print(f"URL: {MODEL_URL}")
    print(f"Путь сохранения: {model_path}")
    
    try:
        # Скачиваем с прогресс-баром
        def report_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, (downloaded / total_size) * 100)
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"\rЗагружено: {mb_downloaded:.2f}/{mb_total:.2f} MB ({percent:.1f}%)", end='')
        
        urllib.request.urlretrieve(MODEL_URL, model_path, reporthook=report_progress)
        print()  # Новая строка после прогресса
        
        # Проверяем размер файла
        file_size = os.path.getsize(model_path)
        print(f"\nМодель успешно загружена!")
        print(f"Путь: {model_path}")
        print(f"Размер: {file_size / (1024*1024):.2f} MB")
        
        return model_path
        
    except Exception as e:
        print(f"\nОшибка при загрузке: {e}")
        # Очищаем частично загруженный файл
        if os.path.exists(model_path):
            os.remove(model_path)
        sys.exit(1)

if __name__ == "__main__":
    model_path = download_model()
    print(f"\nГотово! Модель доступна по пути: {os.path.abspath(model_path)}")
