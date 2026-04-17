"""
LLM-based parameter extraction module.
Uses llama-cpp-python for local inference with Qwen2.5-3B-Instruct GGUF.
License: MIT
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from llama_cpp import Llama

from models.schemas import ExtractedParameters, TaskType, ComponentLevel


logger = logging.getLogger(__name__)


class ParameterExtractor:
    """
    Extracts structured parameters from user text using local LLM.
    Uses forced JSON mode for deterministic output.
    """
    
    SYSTEM_PROMPT = """Ты — система извлечения параметров для оценки стоимости разработки справочников и реестров в сфере Reference Data Management и Master Data Management.
Твоя задача — анализировать текстовое описание и извлекать структурированные параметры в формате JSON.

ВАЖНО:
1. Отвечай ТОЛЬКО валидным JSON без markdown, без пояснений, без дополнительного текста.
2. Используй строго указанную схему JSON.
3. Если описание не относится к справочникам/реестрам, установи task_type="unknown".

Доступные значения:
- task_type: manual_registry, external_integration, classification_registry, reference_data, master_data, ui_component, data_migration, documentation
- component: basic_structure, validation_rules, advanced_validation, read_only, sync_basic, sync_advanced, api_integration, simple, complex, hierarchical, standard, with_versioning, with_approval_workflow, basic, with_golden_record, with_matching, grid_view, search_filter, bulk_operations, audit_log, initial_load, transformation, technical, user_guide

Примеры входных данных и ожидаемого вывода:

Пример 1:
Вход: "Нужно разработать ручной справочник ОКАТО с базовыми полями: код и наименование. Планируется около 500 записей."
Выход: {"task_type": "manual_registry", "component": "basic_structure", "registry_name": "ОКАТО", "has_external_integration": false, "has_validation_rules": false, "requires_support": false, "estimated_records": 500, "additional_components": []}

Пример 2:
Вход: "Требуется создать реестр классификации данных со сложными правилами валидации и интеграцией с внешней CRM системой через API. Нужна поддержка и аудит изменений."
Выход: {"task_type": "classification_registry", "component": "complex", "registry_name": "Реестр классификации данных", "has_external_integration": true, "has_validation_rules": true, "requires_support": true, "estimated_records": null, "additional_components": ["audit_log"]}

Пример 3:
Вход: "Разработка мастер-данных контрагентов с золотой записью и функцией сопоставления дубликатов."
Выход: {"task_type": "master_data", "component": "with_golden_record", "registry_name": "Мастер-данные контрагентов", "has_external_integration": false, "has_validation_rules": false, "requires_support": false, "estimated_records": null, "additional_components": ["bulk_operations"]}

Пример 4:
Вход: "Создать интернет-магазин с корзиной и оплатой."
Выход: {"task_type": "unknown", "component": "unknown", "registry_name": "Не применимо", "has_external_integration": false, "has_validation_rules": false, "requires_support": false, "estimated_records": null, "additional_components": []}"""

    def __init__(self, model_path: Path):
        """
        Initialize the parameter extractor with a GGUF model.
        
        Args:
            model_path: Path to the GGUF model file
        """
        self.model_path = model_path
        self.llm: Optional[Llama] = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the LLM model into memory."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        logger.info(f"Loading model from {self.model_path}...")
        try:
            self.llm = Llama(
                model_path=str(self.model_path),
                n_ctx=2048,
                n_threads=4,
                verbose=False,
            )
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def extract_parameters(self, user_text: str) -> ExtractedParameters:
        """
        Extract structured parameters from user input text.
        
        Args:
            user_text: Raw text description from user
            
        Returns:
            ExtractedParameters object with validated fields
            
        Raises:
            ValueError: If extraction fails or returns invalid JSON
        """
        if self.llm is None:
            raise RuntimeError("LLM model not loaded")
        
        # Construct the prompt
        prompt = f"{self.SYSTEM_PROMPT}\n\nТекущий запрос пользователя:\n{user_text}\n\nИзвлеки параметры в формате JSON:"
        
        try:
            # Run inference with JSON mode
            response = self.llm(
                prompt=prompt,
                max_tokens=512,
                temperature=0.1,  # Low temperature for deterministic output
                top_p=0.9,
                stop=["```", "</code>", "\n\n"],
                echo=False,
            )
            
            logger.info("===================")
            logger.info(response)
            logger.info("===================")
            
            raw_output = response["choices"][0]["text"].strip()
            logger.debug(f"Raw LLM output: {raw_output}")
            
            # Clean up potential markdown artifacts and extra text
            raw_output = self._clean_json_output(raw_output)
            
            logger.debug(f"Cleaned LLM output: {raw_output}")
            
            # Parse JSON
            parsed_data = json.loads(raw_output)
            
            # Handle case where LLM returns a list of objects - take the first one
            if isinstance(parsed_data, list):
                if len(parsed_data) > 0:
                    parsed_data = parsed_data[0]
                else:
                    raise ValueError("LLM returned an empty list instead of a JSON object")
            
            # Validate that we have a dict
            if not isinstance(parsed_data, dict):
                raise ValueError(f"LLM returned unexpected type: {type(parsed_data)}")
            
            # Validate against Pydantic schema
            parameters = ExtractedParameters(**parsed_data)
            
            return parameters
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM: {e}")
            logger.error(f"Raw output was: {raw_output}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error(f"Parameter extraction failed: {e}")
            raise ValueError(f"Parameter extraction failed: {e}")
    
    def _clean_json_output(self, raw_text: str) -> str:
        """
        Clean potential markdown or extra formatting from LLM output.
        
        Args:
            raw_text: Raw text from LLM
            
        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks if present
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        
        raw_text = raw_text.strip()
        
        # Find the first '{' to start extracting JSON
        start_idx = raw_text.find('{')
        if start_idx == -1:
            return raw_text
        
        # Try to find matching closing brace by counting braces
        # This handles cases where there are multiple JSON objects or extra text
        brace_count = 0
        end_idx = -1
        
        for i, char in enumerate(raw_text[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if end_idx != -1:
            raw_text = raw_text[start_idx:end_idx + 1]
        else:
            # Fallback: just take from first '{' to last '}'
            end_idx = raw_text.rfind('}')
            if end_idx != -1 and start_idx < end_idx:
                raw_text = raw_text[start_idx:end_idx + 1]
        
        return raw_text.strip()
