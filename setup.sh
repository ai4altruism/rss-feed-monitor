#!/bin/bash

# RSS Feed Monitor Setup Script

# Create necessary directories
mkdir -p data logs src/templates

# Copy HTML template for web dashboard if the directory exists
if [ -d "templates" ]; then
    cp -v templates/dashboard.html src/templates/
else
    echo "Warning: templates directory not found, dashboard.html wasn't copied"
    echo "Please manually copy dashboard.html to src/templates/ after setup"
fi

# Check if .env file exists, if not, create from example
if [ ! -f .env ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env file with your settings"
else
    echo ".env file already exists, skipping..."
fi

# Check for existing virtual environment
if [ -d ".venv" ]; then
    echo "Found existing virtual environment (.venv)."
    read -p "Do you want to use the existing .venv environment? (y/n): " use_existing_venv
    
    if [[ $use_existing_venv == "y" || $use_existing_venv == "Y" ]]; then
        echo "Using existing virtual environment..."
        source .venv/bin/activate
        
        echo "Installing/updating dependencies..."
        pip install -r requirements.txt
        
        echo "Dependencies installed successfully!"
    else
        read -p "Do you want to create a new virtual environment? (y/n): " create_new_venv
        if [[ $create_new_venv == "y" || $create_new_venv == "Y" ]]; then
            echo "Creating a new virtual environment might conflict with the existing one."
            echo "Please remove or rename the existing .venv directory first."
        fi
    fi
else
    # Ask if user wants to install Python dependencies locally
    read -p "No existing virtual environment found. Create one? (y/n): " install_deps
    if [[ $install_deps == "y" || $install_deps == "Y" ]]; then
        echo "Creating virtual environment..."
        python -m venv .venv
        
        echo "Activating virtual environment..."
        source .venv/bin/activate
        
        echo "Installing dependencies..."
        pip install -r requirements.txt
        
        echo "Dependencies installed successfully!"
    fi
fi

# Ask if user wants to build Docker image
read -p "Do you want to build the Docker image? (y/n): " build_docker
if [[ $build_docker == "y" || $build_docker == "Y" ]]; then
    # Check if Docker is installed
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        echo "Building Docker image..."
        docker-compose build
        
        echo "Docker image built successfully!"
    else
        echo "Docker or docker-compose not found. Please install Docker and docker-compose first."
    fi
fi

echo ""
echo "Setup completed!"
echo "To run using Python: python src/main.py"
echo "To run using Docker: docker-compose up -d"
echo ""
echo "Don't forget to edit the .env file with your API keys and preferences."