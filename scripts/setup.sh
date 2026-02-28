#!/usr/bin/env bash
# AutoShorts MVP — Skrypt konfiguracyjny (development)
set -euo pipefail

echo "=== AutoShorts MVP Setup ==="

# 1. Sprawdzenie wymagań
command -v docker >/dev/null 2>&1 || { echo "Docker nie jest zainstalowany!"; exit 1; }
command -v docker compose >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose nie znaleziony!"; exit 1; }

# 2. Kopiowanie .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Utworzono plik .env z szablonu. Uzupełnij klucze API!"
else
    echo ".env już istnieje — pomijam."
fi

# 3. Uruchomienie infrastruktury
echo "Uruchamianie kontenerów..."
docker compose up -d postgres redis minio

echo "Czekam na gotowość bazy danych..."
sleep 5

# 4. Tworzenie bucketu MinIO
echo "Tworzenie bucketu S3..."
docker compose exec -T minio mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null || true
docker compose exec -T minio mc mb local/autoshorts-media --ignore-existing 2>/dev/null || true

# 5. Backend setup
echo "Instalowanie zależności backendu..."
cd backend
pip install -e ".[dev]" 2>/dev/null || pip install -e .
cd ..

# 6. Frontend setup
echo "Instalowanie zależności frontendu..."
cd frontend
npm install
cd ..

echo ""
echo "=== Setup zakończony! ==="
echo ""
echo "Uruchom usługi:"
echo "  docker compose up -d          # wszystkie kontenery"
echo "  cd backend && uvicorn app.main:app --reload  # API"
echo "  cd frontend && npm run dev    # Frontend"
echo ""
echo "Panel:     http://localhost:3000"
echo "API docs:  http://localhost:8000/docs"
echo "MinIO:     http://localhost:9001"
