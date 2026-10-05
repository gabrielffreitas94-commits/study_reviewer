"""Mecanismo de limitação de taxa (Rate Limiting) para proteção contra DoS e abuso."""

import time
from collections import defaultdict

# Armazenamento em memória de timestamps de requisições por chave identificadora
_REQUEST_TIMESTAMPS: dict[str, list[float]] = defaultdict(list)


class RateLimiter:
    """Implementa janela deslizante para controle de taxa de requisições por usuário."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_allowed(self, identifier: str) -> bool:
        """Verifica se o identificador pode executar a requisição dentro da janela temporal."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        timestamps = _REQUEST_TIMESTAMPS[identifier]

        # Purga timestamps expirados
        _REQUEST_TIMESTAMPS[identifier] = [ts for ts in timestamps if ts > cutoff]

        if len(_REQUEST_TIMESTAMPS[identifier]) >= self.max_requests:
            return False

        _REQUEST_TIMESTAMPS[identifier].append(now)
        return True


def reset_rate_limits() -> None:
    """Limpa contadores de rate limiting (utilizado nos testes unitários e de integração)."""
    _REQUEST_TIMESTAMPS.clear()


# Instância global padrão para sincronização de estudo (20 req/min)
study_sync_rate_limiter = RateLimiter(max_requests=20, window_seconds=60)
