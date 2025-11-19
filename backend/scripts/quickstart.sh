#!/bin/bash

# XOXO Backend Quick Start Script
# This script helps you get started quickly with the backend

set -e

echo "=========================================="
echo "XOXO Backend Quick Start"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo ".env file created. You may want to review and update it."
else
    echo ".env file already exists."
fi

echo ""
echo "Starting services with Docker Compose..."
docker-compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 5

echo ""
echo "Services started successfully!"
echo ""
echo "=========================================="
echo "Access Points:"
echo "=========================================="
echo "API:              http://localhost:8000"
echo "API Docs:         http://localhost:8000/docs"
echo "Health Check:     http://localhost:8000/api/v1/health"
echo ""
echo "=========================================="
echo "Useful Commands:"
echo "=========================================="
echo "View logs:        docker-compose logs -f"
echo "Stop services:    docker-compose down"
echo "Restart:          docker-compose restart"
echo "Run migrations:   docker-compose exec app alembic upgrade head"
echo "Run tests:        docker-compose exec app pytest"
echo ""
echo "=========================================="
