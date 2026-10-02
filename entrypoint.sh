#!/bin/sh
set -e

echo "==> Executando migrações do banco com Alembic..."
alembic upgrade head

echo "==> Iniciando aplicação..."
exec "$@"
