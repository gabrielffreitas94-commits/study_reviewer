"""Testes de integração específicos para o Side Drawer Interativo do Canvas."""

from tests.integration.test_canvas_side_drawer_and_quick_add import (  # noqa: F401
    client,
    db_engine,
    db_session,
    test_canvas_template_has_side_drawer_and_quick_child_markup,
    test_side_drawer_theory_and_batch_questions_api_workflow,
    test_study_canvas_js_side_drawer_and_quick_add_contracts,
    test_user,
)

__all__ = [
    "client",
    "db_engine",
    "db_session",
    "test_user",
    "test_canvas_template_has_side_drawer_and_quick_child_markup",
    "test_side_drawer_theory_and_batch_questions_api_workflow",
    "test_study_canvas_js_side_drawer_and_quick_add_contracts",
]
