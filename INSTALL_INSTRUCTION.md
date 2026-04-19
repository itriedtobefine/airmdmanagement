# Инструкция по установке и проверке llama-cpp-python

## Системные требования
- ОС: Linux x86_64 (также работает на Windows и macOS)
- Python: 3.12+ 
- Свободное место: минимум 100MB

## Шаг 1: Проверка операционной системы и окружения

```bash
uname -a && python --version && pip --version
```

## Шаг 2: Установка библиотеки llama-cpp-python

```bash
pip install llama-cpp-python==0.2.60 --prefer-binary --only-binary :all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu/ 2>&1
```

## Шаг 3: Проверка установки библиотеки

```bash
python -c "import llama_cpp; print('llama-cpp-python version:', llama_cpp.__version__); from llama_cpp import Llama; print('Llama class imported successfully'); import ctypes.util; lib = ctypes.util.find_library('llama'); print('llama library found:', lib)"
```

Ожидаемый вывод:
- `llama-cpp-python version: 0.2.60`
- `Llama class imported successfully`
- `llama library found: None` (это нормально, библиотека встроена в Python модуль)

## Шаг 4: Проверка свободного места

```bash
df -h /workspace && du -sh /workspace
```

## Шаг 5: Очистка кэша pip и временных файлов

```bash
pip cache purge
rm -rf /tmp/*.tmp
```

## Шаг 6: Тестирование с моделью (опционально)

Создайте директорию для моделей:
```bash
mkdir -p /workspace/models
```

Скачайте тестовую модель (20-80 MB):
```bash
cd /workspace/models
curl -L -o test_model.gguf "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v0.3-GGUF/resolve/main/tinyllama-1.1b-chat-v0.3.Q2_K.gguf"
```

Проверьте модель в Python:
```python
from llama_cpp import Llama
llm = Llama(model_path="/workspace/models/test_model.gguf")
output = llm("Q: Hello! A:", max_tokens=32, stop=["Q:", "\n"], echo=True)
print(output)
```

## Шаг 7: Удаление тестовых файлов (после проверки)

```bash
rm -rf /workspace/models
```

## Итоговая команда для быстрой установки и проверки

```bash
# Установка
pip install llama-cpp-python==0.2.60 --prefer-binary --only-binary :all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu/ 2>&1

# Проверка
python -c "import llama_cpp; print('llama-cpp-python version:', llama_cpp.__version__); from llama_cpp import Llama; print('Llama class imported successfully')"

# Очистка
pip cache purge
```

## Зависимости устанавливаемые автоматически:
- typing-extensions>=4.5.0
- numpy>=1.20.0
- diskcache>=5.6.1
- jinja2>=2.11.3
- MarkupSafe>=2.0

## Примечания:
- Библиотека использует CPU версию llama.cpp (без GPU ускорения)
- OpenBLAS warning о L2 cache можно игнорировать
- Для продакшена рекомендуется использовать виртуальное окружение
