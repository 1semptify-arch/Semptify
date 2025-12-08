#!/usr/bin/env bash
# Render.com build script for Semptify

set -o errexit  # Exit on error

echo "🚀 Starting Semptify build..."

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/documents data/intake data/laws data/registry
mkdir -p logs uploads security

# Set permissions
chmod -R 755 data logs uploads

echo "✅ Build complete!"
