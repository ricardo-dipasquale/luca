#!/bin/bash
# Test script for LUCA Docker setup

echo "🧪 Testing LUCA Docker Setup"
echo "===================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Please create one from .env.example"
    echo "💡 Copy and edit: cp .env.example .env"
    exit 1
fi

echo "✅ Environment file found"

# Build the LUCA image
echo "🔨 Building LUCA Docker image..."
if docker build -t luca-app .; then
    echo "✅ LUCA image built successfully"
else
    echo "❌ Failed to build LUCA image"
    exit 1
fi

# Check if docker-compose.yml is valid
echo "🔍 Validating docker-compose.yml..."
if docker-compose config > /dev/null 2>&1; then
    echo "✅ Docker Compose configuration is valid"
else
    echo "❌ Docker Compose configuration has errors"
    exit 1
fi

echo ""
echo "🎉 Docker setup test completed successfully!"
echo ""
echo "To start the LUCA application:"
echo "  docker-compose up -d"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f luca"
echo ""
echo "To stop the application:"
echo "  docker-compose down"