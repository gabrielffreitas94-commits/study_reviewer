"""Testes de integração específicos para o 1-Click Connected Child Node (+)."""

from tests.integration.test_canvas_side_drawer_and_quick_add import (  # noqa: F401
    client,
    db_engine,
    db_session,
    test_quick_add_child_api_workflow,
    test_user,
)

__all__ = [
    "client",
    "db_engine",
    "db_session",
    "test_user",
    "test_quick_add_child_api_workflow",
]
