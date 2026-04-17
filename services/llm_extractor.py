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

КРИТИЧЕСКИ ВАЖНО:
1. Отвечай ТОЛЬКО валидным JSON. Никакого текста до или после JSON. Никаких пояснений. Никакого markdown.
2. Используй строго указанную схему JSON.
3. Если описание не относится к справочникам/реестрам, установи task_type="unknown".
4. Для указания количества одинаковых задач ИСПОЛЬЗУЙ поле quantity. Например, если пользователь просит "20 справочников", создай ОДИН элемент с quantity=20, а не 20 отдельных элементов.
5. РАЗДЕЛЯЙ разные типы задач: если пользователь просит "разработать справочники И сделать первичную загрузку", создавай ОТДЕЛЬНЫЕ элементы в массиве registries - один для разработки справочников (с quantity=N), и ОТДЕЛЬНЫЙ элемент для первичной загрузки (с quantity=N).
6. Распознавай типы справочников:
   - "внешний справочник", "справочник с внешним источником", "интеграция с внешним источником" -> task_type="external_integration"
   - "ручной справочник", "типовой ручной справочник", "справочник с ручным заполнением" -> task_type="manual_registry"
   - "реестр классификации" -> task_type="classification_registry"
   - "мастер-данные" -> task_type="master_data"
   - "нормативно-справочная информация" -> task_type="reference_data"
   - "первичная загрузка", "загрузка данных", "импорт данных" -> task_type="data_migration", component="initial_load"
   - "трансформация данных", "очистка данных" -> task_type="data_migration", component="transformation"

Доступные значения:
- task_type: manual_registry, external_integration, classification_registry, reference_data, master_data, ui_component, data_migration, documentation
- component: basic_structure, validation_rules, advanced_validation, read_only, sync_basic, sync_advanced, api_integration, simple, complex, hierarchical, standard, with_versioning, with_approval_workflow, basic, with_golden_record, with_matching, grid_view, search_filter, bulk_operations, audit_log, initial_load, transformation, technical, user_guide

Примеры входных данных и ожидаемого вывода:

Пример 1:
Вход: "Нужно разработать ручной справочник ОКАТО с базовыми полями: код и наименование. Планируется около 500 записей."
Выход: {"registries": [{"task_type": "manual_registry", "component": "basic_structure", "registry_name": "ОКАТО", "has_external_integration": false, "has_validation_rules": false, "estimated_records": 500, "additional_components": [], "quantity": 1}], "requires_support": true}

Пример 2:
Вход: "Мне нужно сделать 2 внешних справочника и 2 типовых ручных справочника"
Выход: {"registries": [{"task_type": "external_integration", "component": "api_integration", "registry_name": "Внешний справочник", "has_external_integration": true, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 2}, {"task_type": "manual_registry", "component": "basic_structure", "registry_name": "Ручной справочник", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 2}], "requires_support": true}

Пример 3:
Вход: "Требуется создать реестр классификации данных со сложными правилами валидации и интеграцией с внешней CRM системой через API. Нужна поддержка и аудит изменений."
Выход: {"registries": [{"task_type": "classification_registry", "component": "complex", "registry_name": "Реестр классификации данных", "has_external_integration": true, "has_validation_rules": true, "estimated_records": null, "additional_components": ["audit_log"], "quantity": 1}], "requires_support": true}

Пример 4:
Вход: "Разработка мастер-данных контрагентов с золотой записью и функцией сопоставления дубликатов."
Выход: {"registries": [{"task_type": "master_data", "component": "with_golden_record", "registry_name": "Мастер-данные контрагентов", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": ["bulk_operations"], "quantity": 1}], "requires_support": true}

Пример 5:
Вход: "Создать интернет-магазин с корзиной и оплатой."
Выход: {"registries": [{"task_type": "unknown", "component": "unknown", "registry_name": "Не применимо", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 1}], "requires_support": false}

Пример 6:
Вход: "Разработай 2 внешних справочника и проведи первичную загрузку данных"
Выход: {"registries": [{"task_type": "external_integration", "component": "api_integration", "registry_name": "Внешний справочник", "has_external_integration": true, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 2}, {"task_type": "data_migration", "component": "initial_load", "registry_name": "Первичная загрузка данных", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 2}], "requires_support": true}

Пример 7:
Вход: "Разработай 2 типовых ручных справочника и сделай первоначальную загрузку данных"
Выход: {"registries": [{"task_type": "manual_registry", "component": "basic_structure", "registry_name": "Ручной справочник", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 2}, {"task_type": "data_migration", "component": "initial_load", "registry_name": "Первоначальная загрузка данных", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 2}], "requires_support": true}

Пример 8:
Вход: "Разработай 20 ручных справочников и сделай первичную загрузку для каждого из них"
Выход: {"registries": [{"task_type": "manual_registry", "component": "basic_structure", "registry_name": "Ручной справочник", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 20}, {"task_type": "data_migration", "component": "initial_load", "registry_name": "Первичная загрузка данных", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 20}], "requires_support": true}"""

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
                max_tokens=2048,  # Increased for multiple registries and complex responses
                temperature=0.1,  # Low temperature for deterministic output
                top_p=0.9,
                stop=["```", "</code>"],  # Removed "\\n\\n" to allow full JSON generation
                echo=False,
            )
            
            logger.info("===================")
            logger.info(response)
            logger.info("===================")
            
            raw_output = response["choices"][0]["text"].strip()
            finish_reason = response["choices"][0].get("finish_reason", "unknown")
            logger.debug(f"Raw LLM output: {raw_output}")
            logger.debug(f"Finish reason: {finish_reason}")
            
            # Check if response was truncated
            if finish_reason == "length":
                logger.warning("LLM response was truncated due to token limit. Attempting to recover partial JSON...")
            
            # Clean up potential markdown artifacts
            raw_output = self._clean_json_output(raw_output)
            
            # Parse JSON
            parsed_data = json.loads(raw_output)
            
            # Validate that we have a dict
            if not isinstance(parsed_data, dict):
                raise ValueError(f"LLM returned unexpected type: {type(parsed_data)}")
            
            # Handle legacy format - convert single object to list format
            if "task_type" in parsed_data and "registries" not in parsed_data:
                # Legacy format detected, convert to new format
                legacy_item = {
                    "task_type": parsed_data.get("task_type", "unknown"),
                    "component": parsed_data.get("component", "basic"),
                    "registry_name": parsed_data.get("registry_name", "Неизвестный справочник"),
                    "has_external_integration": parsed_data.get("has_external_integration", False),
                    "has_validation_rules": parsed_data.get("has_validation_rules", False),
                    "estimated_records": parsed_data.get("estimated_records"),
                    "additional_components": parsed_data.get("additional_components", []),
                    "quantity": parsed_data.get("quantity", 1),
                }
                parsed_data = {
                    "registries": [legacy_item],
                    "requires_support": parsed_data.get("requires_support", True),
                }
            
            # Validate against Pydantic schema
            parameters = ExtractedParameters(**parsed_data)
            
            return parameters
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM: {e}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error(f"Parameter extraction failed: {e}")
            raise ValueError(f"Parameter extraction failed: {e}")
    
    def _clean_json_output(self, raw_text: str) -> str:
        """
        Clean potential markdown or extra formatting from LLM output.
        Uses robust JSON extraction by finding balanced braces.
        Can attempt to repair truncated JSON if needed.
        
        Args:
            raw_text: Raw text from LLM
            
        Returns:
            Cleaned JSON string
            
        Raises:
            ValueError: If no valid JSON can be extracted
        """
        # Remove markdown code blocks if present
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        
        raw_text = raw_text.strip()
        
        # Find the first '{' to start JSON
        start_idx = raw_text.find('{')
        if start_idx == -1:
            logger.error(f"No JSON object found in output: {raw_text[:200]}")
            raise ValueError("No JSON object found in LLM output")
        
        # Extract substring starting from first '{'
        json_candidate = raw_text[start_idx:]
        
        # Find balanced closing brace by counting braces
        brace_count = 0
        bracket_count = 0
        end_idx = -1
        in_string = False
        escape_next = False
        
        for i, char in enumerate(json_candidate):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
        
        if end_idx == -1:
            # JSON might be truncated - try to repair by adding closing brackets/braces
            logger.warning(f"JSON appears truncated. Attempting to repair...")
            
            # Find where it cuts off
            last_complete_pos = 0
            brace_count = 0
            bracket_count = 0
            in_string = False
            escape_next = False
            
            for i, char in enumerate(json_candidate):
                if escape_next:
                    escape_next = False
                    last_complete_pos = i + 1
                    continue
                
                if char == '\\':
                    escape_next = True
                    last_complete_pos = i + 1
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                    if not in_string:
                        last_complete_pos = i + 1
                    continue
                
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            last_complete_pos = i + 1
                    elif char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0 and brace_count == 1:
                            # Inside main object, array closed properly
                            last_complete_pos = i + 1
            
            # Try to close all open structures
            if last_complete_pos > 0 and brace_count > 0:
                # We have unclosed braces - try to close them
                repaired = json_candidate[:last_complete_pos]
                
                # Close any open arrays first
                while bracket_count > 0:
                    repaired += ']'
                    bracket_count -= 1
                
                # Then close braces
                while brace_count > 0:
                    repaired += '}'
                    brace_count -= 1
                
                logger.info(f"Repaired truncated JSON: {repaired[:100]}...")
                
                # Verify it's valid JSON now
                try:
                    json.loads(repaired)
                    return repaired.strip()
                except json.JSONDecodeError:
                    logger.error(f"Repair failed, still invalid JSON")
            
            logger.error(f"Could not find balanced JSON braces in output: {raw_text[:200]}")
            raise ValueError("Could not parse JSON from LLM output - unbalanced braces")
        
        # Extract the balanced JSON
        raw_text = json_candidate[:end_idx + 1].strip()
        
        return raw_text
