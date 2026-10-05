#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=== Khởi chạy Cinema Booking System ==="

# 1. Khởi động PostgreSQL container
if [ "$(docker ps -aq -f name=^cinema-postgres$)" ]; then
    if [ ! "$(docker ps -q -f name=^cinema-postgres$)" ]; then
        echo "--> Khởi động cinema-postgres..."
        docker start cinema-postgres >/dev/null
    else
        echo "--> cinema-postgres đã đang chạy."
    fi
else
    echo "--> Tạo mới và chạy cinema-postgres..."
    docker run -d \
        --name cinema-postgres \
        --restart unless-stopped \
        -e POSTGRES_DB=cinema \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=postgres \
        -p 5432:5432 \
        -v cinema_postgres_data:/var/lib/postgresql/data \
        postgres:16-alpine >/dev/null
fi

# Chờ database sẵn sàng
echo "--> Chờ PostgreSQL sẵn sàng..."
until docker exec cinema-postgres pg_isready -U postgres -d cinema >/dev/null 2>&1; do
    sleep 1
done

# 2. Khởi động Backend API container
if [ "$(docker ps -aq -f name=^cinema-api$)" ]; then
    if [ ! "$(docker ps -q -f name=^cinema-api$)" ]; then
        echo "--> Khởi động cinema-api..."
        docker start cinema-api >/dev/null
    else
        echo "--> cinema-api đã đang chạy."
    fi
else
    echo "--> Build và chạy cinema-api..."
    if [ ! "$(docker images -q cinema-api:latest)" ]; then
        docker build -t cinema-api .
    fi
    docker run -d \
        --name cinema-api \
        --restart unless-stopped \
        --network host \
        -e DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/cinema \
        -e CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 \
        cinema-api >/dev/null
fi

# Nạp dữ liệu demo vào database
echo "--> Đảm bảo dữ liệu demo sẵn sàng..."
docker cp "$PROJECT_ROOT/scripts/seed.py" cinema-api:/app/scripts/seed.py >/dev/null 2>&1 || true
docker exec cinema-api python scripts/seed.py >/dev/null 2>&1 || true

# 3. Build và khởi động Frontend
echo "--> Biên dịch Frontend (build dist)..."
docker run --rm \
    -v "$PROJECT_ROOT/frontend:/app" \
    -w /app \
    node:20-alpine npm run build >/dev/null

if [ "$(docker ps -aq -f name=^cinema-frontend$)" ]; then
    echo "--> Khởi động lại cinema-frontend để cập nhật bản build mới..."
    docker restart cinema-frontend >/dev/null
else
    echo "--> Tạo mới và chạy cinema-frontend..."
    docker run -d \
        --name cinema-frontend \
        --restart unless-stopped \
        -p 5173:5173 \
        -v "$PROJECT_ROOT/frontend/dist:/usr/share/nginx/html:ro" \
        -v "$PROJECT_ROOT/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
        nginx:alpine >/dev/null
fi

echo ""
echo " Hệ thống đã sẵn sàng!"
echo "   - Frontend:    http://localhost:5173"
echo "   - API Docs:    http://localhost:8000/docs"
echo "   - ReDoc:       http://localhost:8000/redoc"
