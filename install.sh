#!/bin/bash
# Script to install dependencies for Task Decomposer Application

set -e

echo "=== Installing Task Decomposer Dependencies ==="

# Install llama-cpp-python with pre-built binaries (optimized for minimal space)
echo "Installing llama-cpp-python..."
pip install llama-cpp-python==0.2.60 --prefer-binary --only-binary :all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu/

# Clear pip cache to free up space
echo "Clearing pip cache..."
pip cache purge

# Verify installation
echo "Verifying installation..."
python -c "import llama_cpp; print('llama-cpp-python version:', llama_cpp.__version__); from llama_cpp import Llama; print('Llama class imported successfully')"

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Download the model manually or use --download flag on first run"
echo "2. Run: python task_decomposer.py \"Ваша задача\" --download"
echo ""
echo "Model size: ~400 MB (TinyLlama-1.1B-Chat-v1.0.Q2_K.gguf)"
