# Multi-stage Dockerfile para Study Reviewer (Twelve-Factor & Dev/Prod Parity)
# Estágio 1: Builder para compilar dependências com uv
FROM ghcr.io/astral-sh/uv:latest AS uv_bin
FROM python:3.13-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copia binário do uv
COPY --from=uv_bin /uv /uvx /bin/

# Copia especificações de dependências
COPY pyproject.toml uv.lock ./

# Instala apenas dependências de produção no ambiente virtual /app/.venv
RUN uv sync --frozen --no-dev --no-install-project

# Estágio 2: Runner final enxuto e seguro
FROM python:3.13-slim AS runner

WORKDIR /app

# Instala dependências de runtime necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root dedicado
RUN useradd -m -u 1000 appuser

# Copia ambiente virtual pré-construído
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copia código-fonte e migrações
COPY src/ /app/src/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh && chown -R appuser:appuser /app

# Executa sob usuário sem privilégios administrativos
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
