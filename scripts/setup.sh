#!/bin/bash

# Setup script for Repricing Platform
set -e

echo "🚀 Setting up Repricing Platform..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ .env file created. Please edit it with your configuration."
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p media
mkdir -p staticfiles
mkdir -p ml_models
mkdir -p backups

# Pull and build images
echo "🐳 Building Docker images..."
docker-compose build

# Start services
echo "🔧 Starting services..."
docker-compose up -d db redis

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run migrations
echo "🗄️ Running database migrations..."
docker-compose run --rm web python manage.py migrate

# Collect static files
echo "📦 Collecting static files..."
docker-compose run --rm web python manage.py collectstatic --noinput

# Create superuser (interactive)
echo "👤 Creating superuser..."
echo "Please create a superuser account:"
docker-compose run --rm web python manage.py createsuperuser

# Load demo data (optional)
read -p "🎭 Do you want to load demo data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📊 Loading demo data..."
    docker-compose run --rm web python manage.py loaddata fixtures/demo_data.json 2>/dev/null || echo "⚠️ Demo data not available yet"
fi

# Start all services
echo "🚀 Starting all services..."
docker-compose up -d

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Access the application:"
echo "  - Web Application: http://localhost:8000"
echo "  - Celery Flower: http://localhost:5555"
echo "  - Mailhog: http://localhost:8025"
echo "  - MinIO: http://localhost:9001"
echo ""
echo "📋 Next steps:"
echo "  1. Edit .env file with your API credentials"
echo "  2. Visit http://localhost:8000 to access the application"
echo "  3. Check the logs: docker-compose logs -f"
echo ""
echo "🛑 To stop: docker-compose down"
echo "🔄 To restart: docker-compose restart"
