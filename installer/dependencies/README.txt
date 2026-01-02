# Offline Installers

This folder contains installers for offline installation of Semptify dependencies.

## PostgreSQL 16
- File: postgresql/postgresql-16-windows-x64.exe
- Run this installer first
- Set password to: Semptify2024!
- Keep default port: 5432

## Python 3.12
- File: python/python-3.12.0-amd64.exe
- IMPORTANT: Check "Add Python to PATH" during installation
- Select "Install for all users" recommended

## After Installation
1. Open Command Prompt as Administrator
2. Create the database:
   cd "C:\Program Files\PostgreSQL\16\bin"
   psql -U postgres -c "CREATE DATABASE semptify;"

3. Run Semptify installer:
   Install-Semptify.bat
