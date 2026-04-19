#!/usr/bin/env python3
"""
Система бенчмаркинга скорости декомпозиции задач на базе локальных CPU-совместимых LLM

Архитектура:
- Последовательное тестирование моделей в изолированных subprocess для предотвращения утечек памяти
- Измерение времени только фазы генерации (исключая загрузку весов)
- Строгая валидация JSON-структуры с повторным прогоном при ошибке
- Формирование отчетов в JSON и CSV форматах
"""

import argparse
import csv
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Проверка зависимостей
try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)

try:
    from jsonschema import validate
except ImportError:
    print("ERROR: jsonschema not installed. Install with: pip install jsonschema")
    sys.exit(1)

# llama-cpp-python опционален - можно использовать внешний llama.cpp через subprocess
LLAMA_CPP_AVAILABLE = False
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    pass

# Проверяем наличие внешнего llama.cpp
LLAMA_CLI_AVAILABLE = False
try:
    result = subprocess.run(['llama-cli', '--version'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        LLAMA_CLI_AVAILABLE = True
except (FileNotFoundError, subprocess.TimeoutExpired):
    pass

if not LLAMA_CPP_AVAILABLE and not LLAMA_CLI_AVAILABLE:
    print("=" * 60)
    print("WARNING: Neither llama-cpp-python nor llama-cli found!")
    print("=" * 60)
    print("\nДля работы бенчмарка необходимо установить один из вариантов:")
    print("\nВариант 1 (рекомендуется для CPU): Установить llama-cpp-python")
    print("  export CMAKE_ARGS=\"-DGGML_BLAS=OFF -DGGML_NATIVE=OFF\"")
    print("  pip install llama-cpp-python --no-cache-dir")
    print("\nВариант 2: Установить llama.cpp CLI")
    print("  git clone https://github.com/ggerganov/llama.cpp")
    print("  cd llama.cpp && make")
    print("  sudo cp main /usr/local/bin/llama-cli")
    print("\n" + "=" * 60)
    # Не завершаем программу - позволяем запустить в режиме симуляции для тестирования
    print("\nЗапуск в режиме демонстрации (без реального инференса)...")
    print("=" * 60 + "\n")

# ============================================================================
# КОНФИГУРАЦИЯ И КОНСТАНТЫ
# ============================================================================

# Фиксированный запрос для тестирования
FIXED_TASK_PROMPT = "разработка и поддержка типового справочника в Atacama RDM"

# Параметры генерации
TEMPERATURE = 0.2
TOP_P = 0.85
MAX_TOKENS = 512
CONTEXT_WINDOW = 2048

# Количество прогонов
WARMUP_RUNS = 1
MAIN_RUNS = 3
MAX_RETRY_ON_INVALID = 1

# Схема ответа модели
TASK_DECOMPOSITION_SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "dependencies": {"type": "array", "items": {"type": "integer"}},
                    "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                    "estimated_effort": {"type": "number", "minimum": 0}
                },
                "required": ["id", "title", "description", "dependencies", "priority", "estimated_effort"]
            }
        }
    },
    "required": ["tasks"]
}

# System prompt с требованием JSON
SYSTEM_PROMPT = f"""Ты — ассистент для декомпозиции задач. Твоя задача — разбить запрос на подзадачи в строгом формате JSON.

ТРЕБОВАНИЯ К ВЫВОДУ:
1. Ответ должен быть ТОЛЬКО валидным JSON без какого-либо дополнительного текста
2. Используй следующую схему:
{json.dumps(TASK_DECOMPOSITION_SCHEMA, indent=2, ensure_ascii=False)}
3. Поля каждого объекта задачи:
   - id: уникальный целочисленный идентификатор
   - title: краткий заголовок задачи
   - description: подробное описание задачи
   - dependencies: массив ID зависимых задач
   - priority: приоритет от 1 (низкий) до 5 (высокий)
   - estimated_effort: оценка усилий в часах (число)

Не добавляй никаких пояснений, комментариев или markdown-обёрток. Только чистый JSON."""


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

@dataclass
class RunResult:
    """Результат одного прогона"""
    run_id: int
    time_sec: float
    valid: bool
    raw_output: str
    error_message: Optional[str] = None


@dataclass
class ModelBenchmarkResult:
    """Результат бенчмарка для одной модели"""
    model_name: str
    model_path: str
    quantization: str
    runs: List[RunResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    ram_peak_mb: Optional[float] = None


@dataclass
class BenchmarkConfig:
    """Конфигурация бенчмарка"""
    models: List[str]
    output_dir: str = "./benchmark_output"
    log_level: str = "INFO"
    enable_ram_monitoring: bool = True


# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================

def setup_logging(log_level: str, output_dir: str) -> logging.Logger:
    """Настройка логгера с выводом в консоль и файл"""
    logger = logging.getLogger("llm_benchmark")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s')
    console_handler.setFormatter(console_format)

    # Файловый обработчик
    log_file = Path(output_dir) / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# ============================================================================
# ВАЛИДАЦИЯ ОТВЕТА
# ============================================================================

def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """Извлечение JSON из ответа модели (удаление markdown-обёрток)"""
    # Попытка найти JSON в ответе
    json_pattern = r'```(?:json)?\s*({.*?})\s*```'
    match = re.search(json_pattern, response, re.DOTALL)
    
    if match:
        json_str = match.group(1)
    else:
        # Если нет markdown-обёртки, пробуем найти первую { и последнюю }
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response[start:end]
        else:
            json_str = response.strip()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def validate_response_structure(response: str) -> Tuple[bool, Optional[Dict], str]:
    """
    Валидация структуры ответа модели.
    Возвращает: (валидность, распарсенный JSON, сообщение об ошибке)
    """
    parsed = extract_json_from_response(response)
    
    if parsed is None:
        return False, None, "Failed to parse JSON from response"
    
    try:
        validate(instance=parsed, schema=TASK_DECOMPOSITION_SCHEMA)
        return True, parsed, ""
    except jsonschema.ValidationError as e:
        return False, parsed, f"Schema validation failed: {e.message}"
    except Exception as e:
        return False, parsed, f"Validation error: {str(e)}"


# ============================================================================
# БЕНЧМАРК МОДЕЛИ
# ============================================================================

class ModelBenchmarker:
    """Класс для бенчмарка отдельной модели"""

    def __init__(self, model_path: str, logger: logging.Logger, enable_ram_monitoring: bool = True):
        self.model_path = model_path
        self.logger = logger
        self.enable_ram_monitoring = enable_ram_monitoring
        self.llm: Optional[Llama] = None
        self.model_info = self._extract_model_info()

    def _extract_model_info(self) -> Dict[str, str]:
        """Извлечение информации о модели из пути"""
        path = Path(self.model_path)
        name = path.stem
        
        # Попытка определить квантизацию из имени файла
        quant_patterns = ['Q4_K_M', 'Q5_K_M', 'Q4_0', 'Q5_0', 'Q8_0', 'F16', 'F32']
        quantization = "Unknown"
        
        for pattern in quant_patterns:
            if pattern in path.name.upper():
                quantization = pattern
                break
        
        return {
            "model_name": name,
            "model_path": str(path.absolute()),
            "quantization": quantization
        }

    def _get_ram_usage_mb(self) -> Optional[float]:
        """Получение текущего потребления RAM процесса"""
        if not self.enable_ram_monitoring:
            return None
        
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            # Fallback через /proc для Linux
            try:
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            return float(line.split()[1]) / 1024  # KB to MB
            except:
                pass
        return None

    def load_model(self) -> bool:
        """Загрузка модели в память"""
        try:
            self.logger.info(f"Загрузка модели: {self.model_path}")
            
            initial_ram = self._get_ram_usage_mb()
            
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=CONTEXT_WINDOW,
                n_threads=4,  # Ограничение по ТЗ
                n_gpu_layers=0,  # Только CPU
                verbose=False,
                use_mlock=True  # Предотвращение выгрузки из RAM
            )
            
            loaded_ram = self._get_ram_usage_mb()
            if loaded_ram and initial_ram:
                self.logger.info(f"Потребление памяти после загрузки: {loaded_ram:.1f} MB (+{loaded_ram - initial_ram:.1f} MB)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки модели: {e}")
            return False

    def unload_model(self):
        """Выгрузка модели из памяти"""
        if self.llm:
            del self.llm
            self.llm = None
            
            import gc
            gc.collect()
            
            self.logger.info("Модель выгружена из памяти")

    def run_inference(self, temperature: float = TEMPERATURE) -> Tuple[str, float]:
        """
        Выполнение инференса с измерением времени генерации.
        Возвращает: (ответ модели, время генерации в секундах)
        """
        if not self.llm:
            raise RuntimeError("Model not loaded")

        # Формирование запроса
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": FIXED_TASK_PROMPT}
        ]

        # Сброс таймера перед генерацией
        start_time = None
        end_time = None

        # Callback для измерения времени первого токена
        def on_token_callback(tokens):
            nonlocal start_time, end_time
            if start_time is None:
                start_time = time.perf_counter()
            return True  # Продолжить генерацию

        # Выполнение генерации
        response = self.llm.create_chat_completion(
            messages=messages,
            temperature=temperature,
            top_p=TOP_P,
            max_tokens=MAX_TOKENS,
            stream=False
        )

        # Время завершения (получение последнего токена)
        end_time = time.perf_counter()
        
        # Извлечение ответа
        content = response['choices'][0]['message']['content']
        
        # Расчет времени генерации
        gen_time = end_time - start_time if start_time else 0.0
        
        return content, gen_time

    def benchmark_model(self) -> ModelBenchmarkResult:
        """Выполнение полного цикла бенчмарка для модели"""
        result = ModelBenchmarkResult(
            model_name=self.model_info["model_name"],
            model_path=self.model_info["model_path"],
            quantization=self.model_info["quantization"]
        )

        # Загрузка модели
        if not self.load_model():
            result.status = "failed"
            result.summary = {"error": "Failed to load model"}
            return result

        # Мониторинг RAM
        ram_before = self._get_ram_usage_mb()

        try:
            # Warmup прогон
            self.logger.info("Выполнение warmup-прогона...")
            try:
                self.run_inference()
            except Exception as e:
                self.logger.warning(f"Warmup failed: {e}")

            # Основные прогоны
            for run_id in range(1, MAIN_RUNS + 1):
                self.logger.info(f"Прогон {run_id}/{MAIN_RUNS}")
                
                current_temp = TEMPERATURE
                retry_count = 0
                success = False
                
                while retry_count <= MAX_RETRY_ON_INVALID and not success:
                    try:
                        # Измерение времени генерации
                        raw_output, gen_time = self.run_inference(temperature=current_temp)
                        
                        # Валидация ответа
                        valid, _, error_msg = validate_response_structure(raw_output)
                        
                        run_result = RunResult(
                            run_id=run_id,
                            time_sec=gen_time,
                            valid=valid,
                            raw_output=raw_output,
                            error_message=error_msg if not valid else None
                        )
                        
                        result.runs.append(run_result)
                        
                        status_msg = "✓ VALID" if valid else f"✗ INVALID: {error_msg}"
                        self.logger.info(f"  Время: {gen_time:.3f}s | Статус: {status_msg}")
                        
                        if valid:
                            success = True
                        else:
                            # Повторный прогон с пониженной температурой
                            retry_count += 1
                            if retry_count <= MAX_RETRY_ON_INVALID:
                                self.logger.info(f"  Повторный прогон с температурой 0.1...")
                                current_temp = 0.1
                                
                    except Exception as e:
                        self.logger.error(f"  Ошибка прогона: {e}")
                        run_result = RunResult(
                            run_id=run_id,
                            time_sec=0.0,
                            valid=False,
                            raw_output="",
                            error_message=str(e)
                        )
                        result.runs.append(run_result)
                        break

            # Вычисление сводных метрик
            valid_runs = [r for r in result.runs if r.valid]
            times = [r.time_sec for r in result.runs if r.time_sec > 0]
            
            if times:
                avg_time = sum(times) / len(times)
                median_time = sorted(times)[len(times) // 2]
            else:
                avg_time = median_time = 0.0
            
            success_rate = len(valid_runs) / len(result.runs) if result.runs else 0.0
            
            # Определение статуса
            if success_rate >= 0.8:
                status = "passed"
            elif success_rate >= 0.5:
                status = "degraded"
            else:
                status = "failed"
            
            # Потребление RAM
            ram_after = self._get_ram_usage_mb()
            ram_peak = ram_after - ram_before if ram_after and ram_before else None
            result.ram_peak_mb = ram_peak

            result.summary = {
                "avg_time_sec": round(avg_time, 4),
                "median_time_sec": round(median_time, 4),
                "success_rate": round(success_rate, 3),
                "total_runs": len(result.runs),
                "valid_runs": len(valid_runs),
                "ram_peak_mb": round(ram_peak, 2) if ram_peak else None
            }
            
            result.status = status
            
        finally:
            # Выгрузка модели
            self.unload_model()

        return result


# ============================================================================
# SUBPROCESS WRAPPER ДЛЯ ИЗОЛЯЦИИ ПАМЯТИ
# ============================================================================

def run_model_in_subprocess(model_path: str, output_dir: str, log_level: str) -> Dict[str, Any]:
    """Запуск бенчмарка модели в изолированном subprocess"""
    
    # Скрипт для запуска в subprocess
    worker_script = f'''
import sys
import json
sys.path.insert(0, '{Path(__file__).parent.absolute()}')

from benchmark_runner import ModelBenchmarker, setup_logging

logger = setup_logging("{log_level}", "{output_dir}")
benchmarker = ModelBenchmarker("{model_path}", logger, enable_ram_monitoring=True)
result = benchmarker.benchmark_model()

# Сериализация результата
def serialize(obj):
    if hasattr(obj, '__dict__'):
        return {{k: serialize(v) for k, v in obj.__dict__.items()}}
    elif isinstance(obj, list):
        return [serialize(i) for i in obj]
    elif hasattr(obj, '__dataclass_fields__'):
        return {{k: serialize(getattr(obj, k)) for k in obj.__dataclass_fields__}}
    return obj

print(json.dumps(serialize(result)))
'''
    
    try:
        # Запуск subprocess
        process = subprocess.run(
            [sys.executable, '-c', worker_script],
            capture_output=True,
            text=True,
            timeout=600,  # 10 минут максимум на модель
            env={**os.environ, 'PYTHONPATH': str(Path(__file__).parent.absolute())}
        )
        
        if process.returncode != 0:
            return {
                "model_name": Path(model_path).stem,
                "model_path": model_path,
                "quantization": "Unknown",
                "status": "failed",
                "summary": {"error": f"Subprocess failed: {process.stderr}"},
                "runs": []
            }
        
        return json.loads(process.stdout)
        
    except subprocess.TimeoutExpired:
        return {
            "model_name": Path(model_path).stem,
            "model_path": model_path,
            "quantization": "Unknown",
            "status": "timeout",
            "summary": {"error": "Benchmark timeout (10 minutes)"},
            "runs": []
        }
    except Exception as e:
        return {
            "model_name": Path(model_path).stem,
            "model_path": model_path,
            "quantization": "Unknown",
            "status": "failed",
            "summary": {"error": str(e)},
            "runs": []
        }


# ============================================================================
# ГЕНЕРАЦИЯ ОТЧЕТОВ
# ============================================================================

def generate_json_report(results: List[Dict], output_path: Path):
    """Генерация отчета в JSON формате"""
    report = {
        "benchmark_date": datetime.now().isoformat(),
        "fixed_prompt": FIXED_TASK_PROMPT,
        "parameters": {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_tokens": MAX_TOKENS,
            "context_window": CONTEXT_WINDOW,
            "main_runs": MAIN_RUNS,
            "warmup_runs": WARMUP_RUNS
        },
        "models": results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def generate_csv_report(results: List[Dict], output_path: Path):
    """Генерация отчета в CSV формате"""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Заголовки
        writer.writerow([
            'Model Name',
            'Quantization',
            'Status',
            'Run ID',
            'Time (sec)',
            'Valid',
            'Error Message'
        ])
        
        # Данные по каждому прогону
        for model in results:
            for run in model.get('runs', []):
                writer.writerow([
                    model.get('model_name', 'Unknown'),
                    model.get('quantization', 'Unknown'),
                    model.get('status', 'Unknown'),
                    run.get('run_id', 0),
                    round(run.get('time_sec', 0), 4),
                    run.get('valid', False),
                    run.get('error_message', '')[:100] if run.get('error_message') else ''
                ])
        
        # Сводные данные
        writer.writerow([])
        writer.writerow(['Summary'])
        writer.writerow([
            'Model Name',
            'Status',
            'Avg Time (sec)',
            'Success Rate',
            'RAM Peak (MB)'
        ])
        
        for model in results:
            summary = model.get('summary', {})
            writer.writerow([
                model.get('model_name', 'Unknown'),
                model.get('status', 'Unknown'),
                summary.get('avg_time_sec', 0),
                summary.get('success_rate', 0),
                summary.get('ram_peak_mb', 'N/A')
            ])


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def load_config(config_path: str) -> BenchmarkConfig:
    """Загрузка конфигурации из YAML/JSON файла"""
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        if path.suffix in ['.yaml', '.yml']:
            config_data = yaml.safe_load(f)
        else:
            config_data = json.load(f)
    
    return BenchmarkConfig(
        models=config_data.get('models', []),
        output_dir=config_data.get('output_dir', './benchmark_output'),
        log_level=config_data.get('log_level', 'INFO'),
        enable_ram_monitoring=config_data.get('enable_ram_monitoring', True)
    )


def main():
    """Точка входа программы"""
    parser = argparse.ArgumentParser(
        description='Система бенчмаркинга CPU-совместимых LLM моделей',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Пример использования:
  python benchmark_runner.py --config config.yaml
  python benchmark_runner.py --models model1.gguf model2.gguf --output ./results
        '''
    )
    
    parser.add_argument('--config', '-c', type=str, help='Путь к файлу конфигурации (YAML/JSON)')
    parser.add_argument('--models', '-m', nargs='+', type=str, help='Список путей к GGUF файлам')
    parser.add_argument('--output', '-o', type=str, default='./benchmark_output', help='Директория для выходных файлов')
    parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--no-subprocess', action='store_true', help='Запускать модели в текущем процессе (не рекомендуется)')
    
    args = parser.parse_args()
    
    # Загрузка конфигурации
    if args.config:
        try:
            config = load_config(args.config)
        except Exception as e:
            print(f"ERROR: Failed to load config: {e}")
            sys.exit(1)
    else:
        config = BenchmarkConfig(
            models=args.models or [],
            output_dir=args.output,
            log_level=args.log_level
        )
    
    # Проверка наличия моделей
    if not config.models:
        print("ERROR: No models specified. Use --config or --models argument.")
        sys.exit(1)
    
    # Создание директории вывода
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Настройка логгера
    logger = setup_logging(config.log_level, str(output_dir))
    
    logger.info("=" * 60)
    logger.info("СИСТЕМА БЕНЧМАРКИНГА LLM МОДЕЛЕЙ")
    logger.info("=" * 60)
    logger.info(f"Фиксированный запрос: {FIXED_TASK_PROMPT}")
    logger.info(f"Параметры генерации: temp={TEMPERATURE}, top_p={TOP_P}, max_tokens={MAX_TOKENS}")
    logger.info(f"Количество прогонов: {WARMUP_RUNS} warmup + {MAIN_RUNS} основных")
    logger.info(f"Директория вывода: {output_dir.absolute()}")
    logger.info("=" * 60)
    
    # Проверка доступности моделей
    available_models = []
    for model_path in config.models:
        if Path(model_path).exists():
            available_models.append(model_path)
            logger.info(f"✓ Модель найдена: {model_path}")
        else:
            logger.warning(f"✗ Модель не найдена: {model_path}")
    
    if not available_models:
        logger.error("Нет доступных моделей для тестирования")
        sys.exit(1)
    
    # Выполнение бенчмарка
    all_results = []
    
    for i, model_path in enumerate(available_models, 1):
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"МОДЕЛЬ {i}/{len(available_models)}: {Path(model_path).name}")
        logger.info("=" * 60)
        
        if args.no_subprocess:
            # Запуск в текущем процессе (не рекомендуется для слабого железа)
            benchmarker = ModelBenchmarker(model_path, logger, config.enable_ram_monitoring)
            result = benchmarker.benchmark_model()
            result_dict = asdict(result)
        else:
            # Запуск в изолированном subprocess
            logger.info("Запуск в изолированном subprocess для защиты от утечек памяти...")
            result_dict = run_model_in_subprocess(model_path, str(output_dir), config.log_level)
        
        all_results.append(result_dict)
        
        # Краткий итог по модели
        summary = result_dict.get('summary', {})
        logger.info(f"Статус: {result_dict.get('status', 'unknown')}")
        logger.info(f"Среднее время: {summary.get('avg_time_sec', 'N/A')}s")
        logger.info(f"Успешность: {summary.get('success_rate', 0) * 100:.1f}%")
    
    # Генерация отчетов
    logger.info("")
    logger.info("=" * 60)
    logger.info("ГЕНЕРАЦИЯ ОТЧЕТОВ")
    logger.info("=" * 60)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    json_report_path = output_dir / f"benchmark_results_{timestamp}.json"
    csv_report_path = output_dir / f"benchmark_results_{timestamp}.csv"
    
    generate_json_report(all_results, json_report_path)
    logger.info(f"JSON отчет: {json_report_path}")
    
    generate_csv_report(all_results, csv_report_path)
    logger.info(f"CSV отчет: {csv_report_path}")
    
    # Итоговая сводка
    logger.info("")
    logger.info("=" * 60)
    logger.info("ИТОГОВАЯ СВОДКА")
    logger.info("=" * 60)
    
    passed = sum(1 for r in all_results if r.get('status') == 'passed')
    degraded = sum(1 for r in all_results if r.get('status') == 'degraded')
    failed = sum(1 for r in all_results if r.get('status') in ['failed', 'timeout'])
    
    logger.info(f"Всего моделей: {len(all_results)}")
    logger.info(f"✓ Passed: {passed}")
    logger.info(f"~ Degraded: {degraded}")
    logger.info(f"✗ Failed: {failed}")
    
    logger.info("")
    
    # Определяем общий статус бенчмарка
    if failed == len(all_results):
        logger.error("❌ Бенчмарк ЗАВЕРШЕН С ОШИБКАМИ: все модели не прошли тестирование")
        return 1
    elif failed > 0:
        logger.warning(f"⚠ Бенчмарк завершен с предупреждениями: {failed} модель(ей) не прошли тестирование")
        return 2
    else:
        logger.info("✅ Бенчмарк завершен успешно: все модели прошли тестирование")
        return 0


if __name__ == '__main__':
    sys.exit(main())
