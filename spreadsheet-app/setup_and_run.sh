#!/bin/bash
# Скрипт установки и запуска Spreadsheet App
# Использование: ./setup_and_run.sh

set -e

echo "=== Spreadsheet App - Установка и запуск ==="

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.8+"
    exit 1
fi

echo "✓ Python3 найден: $(python3 --version)"

# Переход в директорию backend
cd "$(dirname "$0")/backend"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔌 Активация виртуального окружения..."
source venv/bin/activate

# Обновление pip
echo "⬆️  Обновление pip..."
pip install --upgrade pip

# Установка зависимостей
echo "📥 Установка зависимостей..."
pip install -r requirements.txt

# Установка pytest для тестов (опционально)
pip install pytest httpx

# Создание БД и запуск приложения
echo "🚀 Запуск приложения..."
echo ""
echo "============================================"
echo "Приложение доступно по адресу:"
echo "  http://localhost:8000"
echo ""
echo "API документация:"
echo "  http://localhost:8000/docs"
echo "============================================"
echo ""

python main.py
