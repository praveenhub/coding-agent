#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing UV package manager..."
    curl -sSf https://astral.sh/uv/install.sh | bash
    # Add uv to PATH for this session if needed
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Upgrade pip using UV
uv pip install --upgrade pip

echo "Installing dependencies..."

# Install dependencies directly
if [ -f "pyproject.toml" ]; then
    echo "Installing dependencies from pyproject.toml..."
    
    # Install main dependencies
    uv pip install anthropic db-dtypes docker fastapi gunicorn google-cloud-aiplatform google-genai \
    googlemaps instructor ipykernel markdown matplotlib notebook numpy pandas python-dotenv \
    python-json-logger pytest-cov ratelimit requests scikit-learn seaborn uvicorn vertexai \
    weasyprint ruff black
    
    # Install dev dependencies
    uv pip install mypy pytest ruff
    
    echo "Dependencies installed successfully"
else
    echo "No pyproject.toml found!"
    exit 1
fi

# Install the project in development mode
echo "Installing project in development mode..."
uv pip install -e .

# Install IPython kernel globally
python -m ipykernel install --user --name=coda --display-name "Coding Agent"
echo "Jupyter kernel 'coda' has been installed."
echo "Project setup complete!"
