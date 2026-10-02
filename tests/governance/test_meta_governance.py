"""Testes unitários para as funções auxiliares de governança de segurança AST."""

import ast

from tests.governance.test_security_governance import (
    _check_security_docstring,
    _is_security_marker,
)


def test_is_security_marker_recognizes_marker() -> None:
    """Verifica se _is_security_marker identifica decorator simples e com chamada."""
    code = """
@pytest.mark.security
def test_one():
    pass

@pytest.mark.security(reason="Audit")
def test_two():
    pass

@pytest.mark.unit
def test_three():
    pass
"""
    tree = ast.parse(code)
    func_one = tree.body[0]
    func_two = tree.body[1]
    func_three = tree.body[2]

    assert isinstance(func_one, ast.FunctionDef)
    assert _is_security_marker(func_one.decorator_list[0]) is True

    assert isinstance(func_two, ast.FunctionDef)
    assert _is_security_marker(func_two.decorator_list[0]) is True

    assert isinstance(func_three, ast.FunctionDef)
    assert _is_security_marker(func_three.decorator_list[0]) is False


def test_check_security_docstring_validation() -> None:
    """Valida que docstrings fora do padrão são reprovadas e docstrings completas são aceitas."""
    # Caso 1: Vazia
    assert len(_check_security_docstring(None)) > 0
    assert len(_check_security_docstring("")) > 0

    # Caso 2: Curta
    assert len(_check_security_docstring("Muito curta")) > 0

    # Caso 3: Sem vulnerabilidade prevenida
    doc_sem_vuln = (
        "Garantia de segurança: Assegura que o sistema não permita acessos indevidos com token."
    )
    assert any("vulnerabilidade" in err.lower() for err in _check_security_docstring(doc_sem_vuln))

    # Caso 4: Válida e completa
    doc_valida = """
    Vulnerabilidade prevenida: Impede SQL Injection através do campo de busca de flashcards.
    Garantia de segurança: Assegura que queries parametrizadas sejam sempre utilizadas.
    """
    assert _check_security_docstring(doc_valida) == []
