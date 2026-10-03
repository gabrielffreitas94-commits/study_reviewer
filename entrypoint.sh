#!/bin/sh
set -e

echo "==> Compilando CSS estático com Tailwind..."
if command -v tailwindcss >/dev/null 2>&1; then
    tailwindcss -i /app/src/adapters/web/static/css/input.css -o /app/src/adapters/web/static/css/tailwind.css --minify
fi

echo "==> Executando migrações do banco com Alembic..."
alembic upgrade head

echo "==> Iniciando aplicação..."
exec "$@"
