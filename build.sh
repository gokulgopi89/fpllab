#!/bin/bash
set -e

# Use Python 3.10
python -m pip install --upgrade pip setuptools wheel

# Install requirements
pip install -r requirements.txt
