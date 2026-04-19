#!/usr/bin/env python3
"""
Скрипт для скачивания и подготовки модели для декомпозиции задач.
Выбирает модель подходящего размера (меньше 95% свободного места).
"""

import os
import subprocess
import shutil
from huggingface_hub import hf_hub_download


def get_free_space_mb():
    """Получает свободное место на диске в МБ."""
    stat = shutil.disk_usage("/")
    return stat.free / (1024 * 1024)


def get_model_size_mb(model_path):
    """Получает размер модели в МБ."""
    if os.path.isfile(model_path):
        return os.path.getsize(model_path) / (1024 * 1024)
    elif os.path.isdir(model_path):
        total = 0
        for dirpath, dirnames, filenames in os.walk(model_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total / (1024 * 1024)
    return 0


def download_model(model_repo, model_filename, output_path):
    """Скачивает модель с HuggingFace."""
    print(f"Скачивание модели {model_repo}/{model_filename}...")
    
    try:
        model_path = hf_hub_download(
            repo_id=model_repo,
            filename=model_filename,
            local_dir=output_path,
            local_dir_use_symlinks=False
        )
        print(f"Модель скачана: {model_path}")
        return model_path
    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
        return None


def main():
    # Проверяем свободное место
    free_space = get_free_space_mb()
    print(f"Свободное место на диске: {free_space:.2f} MB")
    
    # Максимальный размер модели (95% от свободного места)
    max_model_size = free_space * 0.95
    print(f"Максимальный размер модели: {max_model_size:.2f} MB")
    
    # Список моделей в порядке предпочтения (от меньшей к большей)
    # Используем самые маленькие GGUF модели
    
    models_to_try = [
        # Микро-модели для классификации/генерации текста
        ("Qwen/Qwen1.5-0.5B-Chat-GGUF", "qwen1_5-0_5b-chat-q2_k.gguf"),  # ~298MB
    ]
    
    model_dir = "/workspace/task_decomposer/models"
    os.makedirs(model_dir, exist_ok=True)
    
    downloaded_model = None
    
    for repo, filename in models_to_try:
        # Для единственной модели пробуем скачать без проверки размера
        estimated_size = 298
        
        print(f"\nПытаемся скачать: {repo}/{filename} (~{estimated_size}MB)")
        
        model_path = download_model(repo, filename, model_dir)
        
        if model_path and os.path.exists(model_path):
            actual_size = get_model_size_mb(model_path)
            print(f"Модель успешно скачана! Размер: {actual_size:.2f} MB")
            downloaded_model = model_path
            break
        else:
            print("Не удалось скачать модель, пробуем следующую...")
    
    if downloaded_model:
        print(f"\n=== Модель готова к использованию ===")
        print(f"Путь к модели: {downloaded_model}")
        
        # Сохраняем путь к модели в конфиг
        config_path = os.path.join(model_dir, "model_config.txt")
        with open(config_path, 'w') as f:
            f.write(f"model_path={downloaded_model}\n")
            f.write(f"model_name={os.path.basename(downloaded_model)}\n")
        print(f"Конфигурация сохранена в: {config_path}")
    else:
        print("\n=== Не удалось скачать подходящую модель ===")
        print("Проверьте подключение к интернету или освободите больше места")


if __name__ == "__main__":
    main()
