#!/usr/bin/env bash

echo "=== Đang dừng Cinema Booking System ==="
docker stop cinema-frontend cinema-api cinema-postgres 2>/dev/null || true
echo " Đã dừng tất cả dịch vụ."
