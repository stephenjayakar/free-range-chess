#!/bin/bash

cd "$(dirname "$0")"

echo "======================================"
echo "Free Range Chess RL Setup"
echo "======================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

echo "Python version:"
python3 --version
echo ""

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "======================================"
echo "Setup complete!"
echo "======================================"
echo ""
echo "To start the training server:"
echo "  1. Activate the environment: source venv/bin/activate"
echo "  2. Run: python server.py"
echo "  3. Open http://localhost:8000 in your browser"
echo ""
echo "Or use the convenience script:"
echo "  ./start_server.sh"
echo ""
echo "To train via command line:"
echo "  python train_ppo.py --mode train --timesteps 1000000 --n-envs 8"
echo ""
