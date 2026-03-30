#!/bin/bash

# ==========================================
# Database initialization script
# ==========================================

set -e

DB_USER=${DB_USER:-music_user}
DB_PASSWORD=${DB_PASSWORD:-music_password}
DB_NAME=${DB_NAME:-music_ai_db}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

echo "========================================="
echo "Database Initialization for AI Music Platform"
echo "========================================="
echo ""
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST:$DB_PORT"
echo ""

# Create database (if using local postgres)
# psql -U postgres -h $DB_HOST -c "CREATE DATABASE $DB_NAME;"

echo "✓ Database configuration ready"
echo ""
echo "Run with Docker Compose:"
echo "  docker-compose up -d"
echo ""
echo "PgAdmin access:"
echo "  http://localhost:5050"
echo "  Email: admin@example.com"
echo "  Password: admin"
echo ""
