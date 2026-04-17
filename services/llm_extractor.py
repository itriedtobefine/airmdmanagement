"""
LLM-based parameter extraction module.
Uses llama-cpp-python for local inference with Qwen2.5-3B-Instruct GGUF.
License: MIT
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from llama_cpp import Llama

from models.schemas import ExtractedParameters, TaskType, ComponentLevel


logger = logging.getLogger(__name__)


class ParameterExtractor:
    """
    Extracts structured parameters from user text using local LLM.
    Uses forced JSON mode for deterministic output.
    """
    
    SYSTEM_PROMPT = """Ты — система извлечения параметров для оценки стоимости разработки справочников и реестров.
Отвечай ТОЛЬКО валидным JSON без пояснений.

Правила:
1. Каждый справочник — отдельный элемент в массиве registries с quantity=1
2. Если есть "первичная загрузка" — создай ОТДЕЛЬНЫЙ элемент data_migration с таким же quantity как справочников
3. Распознавай: "ручной справочник"=manual_registry, "внешний справочник"=external_integration, "реестр"=classification_registry
4. Для external_integration компонент всегда api_integration
5. Для manual_registry компонент basic_structure

Формат JSON:
{"registries": [{"task_type": "...", "component": "...", "registry_name": "...", "has_external_integration": true/false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 1}], "requires_support": true}

Примеры:
Запрос: "2 ручных справочника"
Ответ: {"registries": [{"task_type": "manual_registry", "component": "basic_structure", "registry_name": "Ручной справочник 1", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 1}, {"task_type": "manual_registry", "component": "basic_structure", "registry_name": "Ручной справочник 2", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 1}], "requires_support": true}

Запрос: "3 внешних справочника с загрузкой данных"
Ответ: {"registries": [{"task_type": "external_integration", "component": "api_integration", "registry_name": "Внешний справочник 1", "has_external_integration": true, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 1}, {"task_type": "external_integration", "component": "api_integration", "registry_name": "Внешний справочник 2", "has_external_integration": true, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 1}, {"task_type": "external_integration", "component": "api_integration", "registry_name": "Внешний справочник 3", "has_external_integration": true, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 1}, {"task_type": "data_migration", "component": "initial_load", "registry_name": "Первичная загрузка данных", "has_external_integration": false, "has_validation_rules": false, "estimated_records": null, "additional_components": [], "quantity": 3}], "requires_support": true}"""

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
                n_ctx=4096,
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
        
        # Construct the prompt with clear instruction at the end
        prompt = f"{self.SYSTEM_PROMPT}\n\nТекущий запрос: {user_text}\n\nОтвет в формате JSON:"
        
        # Try up to 2 times with slightly different parameters
        last_error = None
        for attempt in range(2):
            try:
                # Run inference with JSON mode
                response = self.llm(
                    prompt=prompt,
                    max_tokens=2048,
                    temperature=0.3 if attempt == 1 else 0.2,  # Increase temp on retry
                    top_p=0.9,
                    stop=["```", "</code>", "\n\n"],
                    echo=False,
                )
                
                logger.info("===================")
                logger.info(response)
                logger.info("===================")
                
                raw_output = response["choices"][0]["text"].strip()
                finish_reason = response["choices"][0].get("finish_reason", "unknown")
                logger.debug(f"Raw LLM output: '{raw_output}'")
                logger.debug(f"Finish reason: {finish_reason}")
                
                # Check if we got empty response
                if not raw_output or len(raw_output) < 2:
                    logger.warning(f"Empty or too short response on attempt {attempt + 1}")
                    if attempt == 0:
                        continue  # Retry
                    raise ValueError("LLM returned empty response")
                
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
                
                logger.info(f"Extracted parameters: {parameters}")
                return parameters
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from LLM (attempt {attempt + 1}): {e}")
                last_error = ValueError(f"Failed to parse LLM response as JSON: {e}")
                if attempt == 1:
                    raise last_error
            except Exception as e:
                logger.error(f"Parameter extraction failed (attempt {attempt + 1}): {e}")
                last_error = ValueError(f"Parameter extraction failed: {e}")
                if attempt == 1:
                    raise last_error
        
        # Should not reach here, but just in case
        raise last_error or ValueError("Parameter extraction failed after retries")
    
    def _clean_json_output(self, raw_text: str) -> str:
        """
        Clean potential markdown or extra formatting from LLM output.
        Uses robust JSON extraction by finding balanced braces.
        
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
            
            if char == '\\' and not escape_next:
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
            logger.error(f"Could not find balanced JSON braces in output: {raw_text[:200]}")
            raise ValueError("Could not parse JSON from LLM output - unbalanced braces")
        
        # Extract the balanced JSON
        return json_candidate[:end_idx + 1].strip()
