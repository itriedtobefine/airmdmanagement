#!/usr/bin/env python3
"""
Task Decomposition AI Application

This application uses a local LLM (SmolLM2-135M-Instruct) to decompose
text tasks into subtasks and returns the result in JSON format.

Example usage:
    python task_decomposer.py "Разработай интернет-магазин"
"""

import json
import sys
import os
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download
from llama_cpp import Llama


# Configuration
MODEL_REPO_ID = "bartowski/SmolLM2-135M-Instruct-GGUF"
MODEL_FILENAME = "SmolLM2-135M-Instruct-Q2_K.gguf"
MODEL_DIR = Path(__file__).parent / "models"


def check_disk_space(required_size_mb: float) -> bool:
    """Check if there's enough disk space for the model."""
    total, used, free = shutil.disk_usage('/')
    free_mb = free / (1024 * 1024)
    # Model should be at most 60% of free space (leaving 40% buffer)
    max_allowed = free_mb * 0.6
    return required_size_mb <= max_allowed


def get_model_size_mb(repo_id: str, filename: str) -> float:
    """Get model file size in MB from HuggingFace."""
    import requests
    info_url = f'https://huggingface.co/api/models/{repo_id}/tree/main'
    try:
        resp = requests.get(info_url)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                if item.get('type') == 'file' and item['path'] == filename:
                    return item.get('size', 0) / (1024 * 1024)
    except Exception:
        pass
    return 0  # Unknown size


def download_model() -> str:
    """Download the model if not already present."""
    MODEL_DIR.mkdir(exist_ok=True)
    model_path = MODEL_DIR / MODEL_FILENAME
    
    if model_path.exists():
        print(f"Model already exists at {model_path}")
        return str(model_path)
    
    # Check disk space before downloading
    model_size_mb = get_model_size_mb(MODEL_REPO_ID, MODEL_FILENAME)
    if model_size_mb > 0:
        print(f"Model size: {model_size_mb:.1f} MB")
        if not check_disk_space(model_size_mb):
            total, used, free = shutil.disk_usage('/')
            free_mb = free / (1024 * 1024)
            raise RuntimeError(
                f"Insufficient disk space. Required: {model_size_mb:.1f} MB, "
                f"Available (with 40% buffer): {free_mb * 0.6:.1f} MB"
            )
    
    print(f"Downloading model {MODEL_FILENAME} from {MODEL_REPO_ID}...")
    model_path = hf_hub_download(
        repo_id=MODEL_REPO_ID,
        filename=MODEL_FILENAME,
        local_dir=MODEL_DIR,
        local_dir_use_symlinks=False
    )
    print(f"Model downloaded to {model_path}")
    return model_path


def load_model(model_path: str) -> Llama:
    """Load the LLM model."""
    print("Loading model...")
    llm = Llama(
        model_path=model_path,
        n_ctx=2048,  # Context window
        n_threads=2,  # Number of CPU threads
        verbose=False
    )
    print("Model loaded successfully!")
    return llm


def create_prompt(task: str) -> str:
    """Create a prompt for task decomposition."""
    prompt = f"""You are a task decomposition assistant. Your job is to break down complex tasks into smaller, manageable subtasks.

Respond ONLY with a valid JSON object in this exact format:
{{
  "original_task": "the original task description",
  "subtasks": [
    {{
      "id": 1,
      "title": "subtask title",
      "description": "detailed description of what needs to be done",
      "priority": "high"
    }}
  ]
}}

Task to decompose: {task}

JSON response:
"""
    return prompt


def decompose_task(llm: Llama, task: str) -> dict:
    """Decompose a task into subtasks using the LLM."""
    # Use a direct prompt asking for JSON with example
    prompt = f"""Task: {task}

Break this task into 3-5 specific subtasks. Respond in JSON format:

{{
  "original_task": "{task}",
  "subtasks": [
    {{"id": 1, "title": "First step", "description": "What to do first", "priority": "high"}},
    {{"id": 2, "title": "Second step", "description": "What to do second", "priority": "medium"}}
  ]
}}

JSON:"""

    print("Processing task...")
    
    output = llm(
        prompt,
        max_tokens=1024,
        temperature=0.5,
        top_p=0.9,
        stop=["\n\n\n", "Task:", "Break"],
        echo=False
    )
    
    response_text = output['choices'][0]['text'].strip()
    print(f"Raw response: {response_text[:500]}...")
    
    # Try to extract JSON from response
    json_result = extract_json(response_text)
    
    if json_result and 'subtasks' in json_result:
        if 'original_task' not in json_result or not json_result['original_task']:
            json_result['original_task'] = task
        return json_result
    
    # If no valid JSON, try to parse the response and create subtasks
    subtasks = parse_response_to_subtasks(response_text, task)
    
    if subtasks:
        return {
            "original_task": task,
            "subtasks": subtasks
        }
    else:
        # Fallback: create a basic structure
        return {
            "original_task": task,
            "subtasks": [
                {
                    "id": 1,
                    "title": "Analyze requirements",
                    "description": "Understand and document the task requirements",
                    "priority": "high"
                },
                {
                    "id": 2,
                    "title": "Plan implementation",
                    "description": "Create a detailed implementation plan",
                    "priority": "high"
                },
                {
                    "id": 3,
                    "title": "Execute task",
                    "description": "Implement the solution according to the plan",
                    "priority": "medium"
                }
            ]
        }


def parse_response_to_subtasks(response: str, task: str) -> list | None:
    """Parse model response into structured subtasks."""
    import re
    
    # Look for numbered items or bullet points
    lines = response.split('\n')
    subtasks = []
    current_title = None
    current_desc = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for numbered list (1. 2. 3.) or bullet points
        match = re.match(r'^(\d+)[\.\)]\s*(.+)', line)
        if match:
            # Save previous subtask if exists
            if current_title:
                subtasks.append({
                    "id": len(subtasks) + 1,
                    "title": current_title,
                    "description": ' '.join(current_desc).strip(),
                    "priority": "high" if len(subtasks) < 2 else "medium"
                })
            current_title = match.group(2)
            current_desc = []
        elif current_title and (line.startswith('-') or line.startswith('*')):
            current_desc.append(line[1:].strip())
        elif current_title:
            current_desc.append(line)
    
    # Add last subtask
    if current_title:
        subtasks.append({
            "id": len(subtasks) + 1,
            "title": current_title,
            "description": ' '.join(current_desc).strip(),
            "priority": "high" if len(subtasks) < 2 else "medium"
        })
    
    return subtasks if subtasks else None


def extract_json(text: str) -> dict | None:
    """Extract JSON object from text."""
    # Try to find JSON in the text
    start_idx = text.find('{')
    end_idx = text.rfind('}') + 1
    
    if start_idx != -1 and end_idx > start_idx:
        json_str = text[start_idx:end_idx]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Try parsing the entire text as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    return None


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python task_decomposer.py <task_description>")
        print("Example: python task_decomposer.py \"Разработай интернет-магазин\"")
        sys.exit(1)
    
    task = " ".join(sys.argv[1:])
    print(f"Received task: {task}\n")
    
    # Download and load model
    try:
        model_path = download_model()
        llm = load_model(model_path)
        
        # Decompose task
        result = decompose_task(llm, task)
        
        # Output result as formatted JSON
        print("\n" + "="*50)
        print("DECOMPOSITION RESULT:")
        print("="*50)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
