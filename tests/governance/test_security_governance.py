"""Meta-teste de Governança de Segurança via AST (Abstract Syntax Tree).

Garante que todos os testes marcados com @pytest.mark.security contenham
uma docstring explicativa obrigatória contendo a vulnerabilidade prevenida
e a garantia de segurança do sistema.
"""

import ast
from pathlib import Path


def _is_security_marker(decorator: ast.expr) -> bool:
    """Verifica se o decorator é @pytest.mark.security."""
    # Caso 1: @pytest.mark.security
    if isinstance(decorator, ast.Attribute):
        if decorator.attr == "security":
            if isinstance(decorator.value, ast.Attribute) and decorator.value.attr == "mark":
                return True
    # Caso 2: @pytest.mark.security(...) com argumentos
    elif isinstance(decorator, ast.Call):
        return _is_security_marker(decorator.func)
    return False


def _check_security_docstring(docstring: str | None) -> list[str]:
    """Valida se a docstring atende aos requisitos mínimos de governança."""
    errors = []
    if not docstring or len(docstring.strip()) < 30:
        errors.append("Docstring ausente ou com menos de 30 caracteres.")
        return errors

    lower_doc = docstring.lower()
    if "vulnerabilidade" not in lower_doc:
        errors.append("Docstring deve explicitar a seção 'Vulnerabilidade prevenida:'.")

    if "garantia" not in lower_doc and "segurança" not in lower_doc:
        errors.append("Docstring deve explicitar a seção 'Garantia de segurança:'.")

    return errors


def test_all_security_tests_have_mandatory_docstrings() -> None:
    """Inspeciona todos os arquivos de teste do repositório em busca de funções

    decoradas com @pytest.mark.security e assegura que todas possuem a
    docstring de segurança com justificativa técnica e garantia.
    """
    tests_dir = Path(__file__).resolve().parent.parent
    violations = []

    for test_file in tests_dir.rglob("test_*.py"):
        # Ignora arquivos de governança para evitar auto-referência recursiva
        if "governance" in test_file.parts:
            continue

        with open(test_file, encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read(), filename=str(test_file))
            except SyntaxError as e:
                violations.append(f"Erro de sintaxe em {test_file.name}: {e}")
                continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_security_marker = any(_is_security_marker(dec) for dec in node.decorator_list)
                if has_security_marker:
                    docstring = ast.get_docstring(node)
                    doc_errors = _check_security_docstring(docstring)
                    if doc_errors:
                        error_msg = "; ".join(doc_errors)
                        violations.append(
                            f"{test_file.name}:{node.lineno} -> {node.name}(): {error_msg}"
                        )

    assert not violations, (
        f"Foram encontradas {len(violations)} violações na governança de testes de segurança:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
