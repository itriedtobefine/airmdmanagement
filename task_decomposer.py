#!/usr/bin/env python3
"""
Task Decomposition Application using Local LLM
Author: AI Assistant
Date: 2026
License: MIT

This application takes a text task description and decomposes it into subtasks using a local LLM.
The output is in CSV format to save tokens and provide clearer results faster.
"""

import os
import sys
import csv
import json
import argparse
from typing import List, Dict, Any
from llama_cpp import Llama


class TaskDecomposer:
    """
    A class to decompose tasks into subtasks using a local LLM.
    """
    
    def __init__(self, model_path: str):
        """
        Initialize the TaskDecomposer with a local LLM model.
        
        Args:
            model_path (str): Path to the local GGUF model file
        """
        self.model_path = model_path
        self.llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=4,
            verbose=False
        )
    
    def _generate_prompt(self, task_description: str) -> str:
        """
        Generate a prompt for the LLM to decompose the task.
        
        Args:
            task_description (str): The original task description
            
        Returns:
            str: Formatted prompt for the LLM
        """
        prompt = f"""Decompose the following task into subtasks. Format your response as a structured list with each subtask containing an ID, title, description, and priority.

Task: {task_description}

Provide the subtasks in this format:
ID|Title|Description|Priority
Where priority can be 'high', 'medium', or 'low'.

Example:
1|Define Requirements|Formalize business requirements, user stories, constraints, and success metrics|high
2|Choose Architecture|Design system architecture based on open-source stack|high
3|Develop Components|Implement basic services like authentication, catalog, cart|high
4|Write Documentation|Create technical documentation and user guides|medium
5|Security Review|Conduct security audit and compliance checks|high
6|Testing|Perform functional and integration testing|high
7|Deployment|Set up production infrastructure and deploy|high
8|Support|Monitor SLA and handle incidents|medium"""
        
        return prompt
    
    def decompose_task(self, task_description: str) -> List[Dict[str, Any]]:
        """
        Decompose a task into subtasks using the local LLM.
        
        Args:
            task_description (str): The task to decompose
            
        Returns:
            List[Dict[str, Any]]: List of subtasks with id, title, description, and priority
        """
        prompt = self._generate_prompt(task_description)
        
        output = self.llm(
            prompt,
            max_tokens=1024,
            stop=["\n\n", "Task:", "Example:"],
            temperature=0.1
        )
        
        response_text = output['choices'][0]['text']
        
        subtasks = []
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if '|' in line and not line.lower().startswith('id|'):
                parts = line.split('|')
                if len(parts) >= 4:
                    try:
                        subtask_id = int(parts[0].strip())
                        title = parts[1].strip()
                        description = parts[2].strip()
                        priority = parts[3].strip().lower()
                        
                        if priority not in ['high', 'medium', 'low']:
                            priority = 'medium'
                            
                        subtasks.append({
                            'id': subtask_id,
                            'title': title,
                            'description': description,
                            'priority': priority
                        })
                    except ValueError:
                        continue
        
        return subtasks
    
    def process_task(self, task_description: str) -> Dict[str, Any]:
        """
        Process a task and return the full decomposition result.
        
        Args:
            task_description (str): The original task description
            
        Returns:
            Dict[str, Any]: Complete result with original task and subtasks
        """
        subtasks = self.decompose_task(task_description)
        
        return {
            "original_task": task_description,
            "subtasks": subtasks
        }


def save_to_csv(result: Dict[str, Any], output_file: str) -> None:
    """
    Save the decomposition result to a CSV file.
    
    Args:
        result (Dict[str, Any]): The result dictionary from process_task
        output_file (str): Path to the output CSV file
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['original_task', 'id', 'title', 'description', 'priority']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for subtask in result['subtasks']:
            row = {
                'original_task': result['original_task'],
                'id': subtask['id'],
                'title': subtask['title'],
                'description': subtask['description'],
                'priority': subtask['priority']
            }
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Task Decomposition Application")
    parser.add_argument("task", help="The task description to decompose")
    parser.add_argument("--model-path", default="./models/qwen2.5-0.5b-instruct-q4_k_m.gguf",
                        help="Path to the local GGUF model file")
    parser.add_argument("--output", "-o", default="decomposition.csv",
                        help="Output CSV file path")
    parser.add_argument("--format", choices=['csv', 'json'], default='csv',
                        help="Output format (default: csv)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.model_path):
        print(f"Error: Model file not found at {args.model_path}")
        print("Please download the model first using download_model.py")
        sys.exit(1)
    
    try:
        decomposer = TaskDecomposer(model_path=args.model_path)
    except Exception as e:
        print(f"Error initializing the model: {e}")
        sys.exit(1)
    
    print(f"Processing task: {args.task}")
    result = decomposer.process_task(args.task)
    
    if args.format == 'json':
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
    else:
        if args.output:
            save_to_csv(result, args.output)
            print(f"Results saved to {args.output}")
        else:
            fieldnames = ['original_task', 'id', 'title', 'description', 'priority']
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            for subtask in result['subtasks']:
                row = {
                    'original_task': result['original_task'],
                    'id': subtask['id'],
                    'title': subtask['title'],
                    'description': subtask['description'],
                    'priority': subtask['priority']
                }
                writer.writerow(row)


if __name__ == "__main__":
    main()
