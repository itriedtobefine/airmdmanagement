#!/usr/bin/env python3
"""
Task Decomposition Application using AI Model

This application uses a local LLM to decompose tasks into subtasks.
It accepts a text input describing a task and outputs a structured JSON
with the original task and a list of subtasks.
"""

import json
import sys
import os
from pathlib import Path

from llama_cpp import Llama


class TaskDecomposer:
    """Class to decompose tasks into subtasks using a local LLM."""
    
    def __init__(self, model_path: str, n_ctx: int = 2048):
        """
        Initialize the TaskDecomposer with a model.
        
        Args:
            model_path: Path to the GGUF model file
            n_ctx: Context window size
        """
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.llm = None
        self._load_model()
    
    def _load_model(self):
        """Load the LLM model."""
        print(f"Loading model from {self.model_path}...", file=sys.stderr)
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_threads=2,
            verbose=False
        )
        print("Model loaded successfully.", file=sys.stderr)
    
    def decompose_task(self, task: str, max_subtasks: int = 10) -> dict:
        """
        Decompose a task into subtasks.
        
        Args:
            task: The task description as text
            max_subtasks: Maximum number of subtasks to generate
            
        Returns:
            Dictionary with original_task and subtasks list
        """
        prompt = self._create_prompt(task, max_subtasks)
        
        response = self.llm(
            prompt,
            max_tokens=2048,
            stop=["</s>", "```json", "```"],
            echo=False,
            temperature=0.3,
            top_p=0.9,
        )
        
        generated_text = response["choices"][0]["text"].strip()
        
        # Try to extract JSON from the response
        result = self._extract_json(generated_text, task)
        
        return result
    
    def _create_prompt(self, task: str, max_subtasks: int) -> str:
        """Create a prompt for the LLM."""
        prompt = f"""Task: {task}

Break this task into {max_subtasks} specific subtasks. Output ONLY valid JSON:

{{"original_task":"{task}","subtasks":[{{"id":1,"title":"First step","description":"What to do first","priority":"high"}},{{"id":2,"title":"Second step","description":"What to do next","priority":"medium"}}]}}

Response:"""
        return prompt
    def _create_prompt(self, task: str, max_subtasks: int) -> str:
        """Create a prompt for the LLM."""
        # Use TinyLlama chat format
        system_msg = "You are a helpful assistant that decomposes tasks into subtasks. Always respond with valid JSON only."
        user_msg = f"""Decompose this task into {max_subtasks} subtasks as JSON:
Task: {task}

Format:
{{"original_task":"{task}","subtasks":[{{"id":1,"title":"name","description":"details","priority":"high"}}]}}"""
        
        prompt = f"<|system|>\n{system_msg}</s>\n<|user|>\n{user_msg}</s>\n<|assistant|>\n"
        return prompt
    
    def _extract_json(self, text: str, original_task: str) -> dict:
        """Extract and parse JSON from the model response."""
        # Try to find JSON in the response
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_str = text[json_start:json_end]
            try:
                result = json.loads(json_str)
                if "original_task" not in result:
                    result["original_task"] = original_task
                return result
            except json.JSONDecodeError:
                pass
        
        # If parsing fails, create a basic structure
        lines = text.strip().split('\n')
        subtasks = []
        
        for i, line in enumerate(lines[:10], 1):
            if line.strip():
                subtasks.append({
                    "id": i,
                    "title": f"Subtask {i}",
                    "description": line.strip(),
                    "priority": "medium"
                })
        
        return {
            "original_task": original_task,
            "subtasks": subtasks if subtasks else [{
                "id": 1,
                "title": "Analyze requirements",
                "description": "Review and understand the task requirements",
                "priority": "high"
            }]
        }


def download_model(model_url: str, model_path: str) -> str:
    """
    Download a model from a URL.
    
    Args:
        model_url: URL to download the model from
        model_path: Local path to save the model
        
    Returns:
        Path to the downloaded model
    """
    import urllib.request
    import shutil
    
    print(f"Downloading model from {model_url}...", file=sys.stderr)
    
    with urllib.request.urlopen(model_url) as response:
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(model_path, 'wb') as out_file:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = (downloaded / total_size) * 100
                    print(f"Download progress: {progress:.1f}%", file=sys.stderr)
    
    print(f"Model downloaded to {model_path}", file=sys.stderr)
    return model_path


def check_disk_space(required_mb: float) -> bool:
    """
    Check if there's enough disk space.
    
    Args:
        required_mb: Required space in megabytes
        
    Returns:
        True if enough space, False otherwise
    """
    stat = os.statvfs('/workspace')
    available_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
    
    # Leave 10% buffer
    safe_required = required_mb * 1.1
    
    print(f"Available space: {available_mb:.1f} MB", file=sys.stderr)
    print(f"Required space (with buffer): {safe_required:.1f} MB", file=sys.stderr)
    
    return available_mb >= safe_required


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Decompose tasks into subtasks using AI'
    )
    parser.add_argument(
        'task',
        nargs='?',
        default=None,
        help='Task description to decompose'
    )
    parser.add_argument(
        '--model', '-m',
        default='models/tinyllama-1.1b-chat-v1.0.Q2_K.gguf',
        help='Path to the GGUF model file'
    )
    parser.add_argument(
        '--download', '-d',
        action='store_true',
        help='Download the model if not present'
    )
    parser.add_argument(
        '--model-url', '-u',
        default='https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q2_K.gguf',
        help='URL to download the model from (default: TinyLlama Q2_K ~400MB for low-space environments)'
    )
    parser.add_argument(
        '--max-subtasks', '-n',
        type=int,
        default=10,
        help='Maximum number of subtasks to generate'
    )
    
    args = parser.parse_args()
    
    # Get task from argument or stdin
    task = args.task
    if not task:
        if sys.stdin.isatty():
            print("Please provide a task:")
            task = input("> ")
        else:
            task = sys.stdin.read().strip()
    
    if not task:
        print("Error: No task provided", file=sys.stderr)
        sys.exit(1)
    
    # Check and download model if needed
    model_path = Path(args.model)
    
    if not model_path.exists():
        if args.download:
            # Check disk space before downloading
            # TinyLlama Q2_K is about 400 MB
            model_size_mb = 410  # Add some buffer
            
            if not check_disk_space(model_size_mb):
                print("Warning: Not enough disk space for the recommended model.", file=sys.stderr)
                print("Attempting to download anyway...", file=sys.stderr)
            
            model_path.parent.mkdir(parents=True, exist_ok=True)
            download_model(args.model_url, str(model_path))
        else:
            print(f"Error: Model not found at {model_path}", file=sys.stderr)
            print("Use --download flag to download the model automatically", file=sys.stderr)
            sys.exit(1)
    
    # Create decomposer and process task
    try:
        decomposer = TaskDecomposer(str(model_path))
        result = decomposer.decompose_task(task, args.max_subtasks)
        
        # Output as JSON
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
