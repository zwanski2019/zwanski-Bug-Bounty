#!/bin/bash
# Activate the virtual environment for zwanski-Bug-Bounty
# Usage: source activate.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please run: bash setup.sh"
    return 1
fi

source "$VENV_DIR/bin/activate"
echo "✓ Virtual environment activated"
echo "Run: python3 scripts/zwanski-oauth-mapper.py"
