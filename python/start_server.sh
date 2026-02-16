#!/bin/bash

cd "$(dirname "$0")"

echo "Starting Free Range Chess Training Server..."
echo ""
echo "Make sure you have installed dependencies:"
echo "  pip install -r requirements.txt"
echo ""

python server.py 8000
