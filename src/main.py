"""Ponto de entrada principal da aplicação Study Reviewer."""

import uvicorn
from mangum import Mangum

from src.infrastructure.config import settings
from src.infrastructure.web.app import app

handler = Mangum(app, lifespan="off")

__all__ = ["app", "handler"]

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
