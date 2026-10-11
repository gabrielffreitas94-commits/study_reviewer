"""Testes para o handler de compatibilidade com AWS Lambda (Mangum)."""

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.main import handler


@pytest.mark.unit
def test_lambda_handler_initialization() -> None:
    """Verifica que o handler Mangum foi instanciado corretamente com o app FastAPI."""
    assert handler is not None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Simula um evento HTTP Payload v2 completo do AWS Lambda Function URL
        event: dict[str, Any] = {
            "version": "2.0",
            "routeKey": "GET /api/v1/health",
            "rawPath": "/api/v1/health",
            "rawQueryString": "",
            "headers": {"accept": "application/json"},
            "requestContext": {
                "http": {
                    "method": "GET",
                    "path": "/api/v1/health",
                    "protocol": "HTTP/1.1",
                    "sourceIp": "127.0.0.1",
                    "userAgent": "pytest-client",
                }
            },
            "isBase64Encoded": False,
        }
        context = MagicMock()
        response = handler(event, context)
        assert "statusCode" in response
    finally:
        loop.close()
