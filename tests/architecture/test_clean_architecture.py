"""Testes automatizados de conformidade com a Clean Architecture (ADR-001) e ADRs.

Utiliza a AST (Abstract Syntax Tree) do Python para inspecionar os imports e
garantir programaticamente que a Regra de Dependência nunca seja violada.
"""

import ast
from pathlib import Path

# Bibliotecas e frameworks proibidos no núcleo de domínio (Python puro)
PROHIBITED_DOMAIN_LIBRARIES = {
    "sqlalchemy",
    "fastapi",
    "pydantic",
    "httpx",
    "requests",
    "uvicorn",
    "jinja2",
    "psycopg2",
    "alembic",
}

# Camadas que o domínio jamais pode importar (aponta exclusivamente para dentro)
PROHIBITED_DOMAIN_LAYERS = {
    "src.adapters",
    "src.infrastructure",
    "src.application",
    "adapters",
    "infrastructure",
    "application",
}

# Camadas que a aplicação (use cases) jamais pode importar (inversão de dependência)
PROHIBITED_APPLICATION_LAYERS = {
    "src.adapters",
    "src.infrastructure",
    "adapters",
    "infrastructure",
}

PROHIBITED_APPLICATION_LIBRARIES = {
    "sqlalchemy",
    "fastapi",
    "uvicorn",
    "psycopg2",
    "alembic",
}


def _get_imports(file_path: Path) -> list[tuple[str, int]]:
    """Extrai todos os nomes de módulos importados e a respectiva linha."""
    imports: list[tuple[str, int]] = []
    with open(file_path, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))

    return imports


def test_domain_layer_is_pure_python_and_has_no_external_dependencies() -> None:
    """Garante que a camada de domínio (src/domain/) não possua nenhuma dependência

    de frameworks, ORMs, bibliotecas de IO ou camadas externas (ADR-001).
    """
    domain_dir = Path("src/domain")
    if not domain_dir.exists():
        return

    violations: list[str] = []
    for py_file in domain_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        for imported_module, lineno in _get_imports(py_file):
            root_module = imported_module.split(".")[0]

            # 1. Verifica bibliotecas externas proibidas
            if (
                root_module in PROHIBITED_DOMAIN_LIBRARIES
                or imported_module in PROHIBITED_DOMAIN_LIBRARIES
            ):
                violations.append(
                    f"{py_file.name}:{lineno} importa biblioteca proibida: '{imported_module}'"
                )

            # 2. Verifica camadas externas do projeto
            for prohibited_layer in PROHIBITED_DOMAIN_LAYERS:
                if imported_module == prohibited_layer or imported_module.startswith(
                    prohibited_layer + "."
                ):
                    violations.append(
                        f"{py_file.name}:{lineno} importa camada externa: '{imported_module}'"
                    )

    assert not violations, (
        "Violações da Regra de Dependência (ADR-001) detectadas no domínio:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_application_layer_does_not_import_adapters_or_infrastructure() -> None:
    """Garante que a camada de aplicação (src/application/) não importe adaptadores

    ou infraestrutura concreta, assegurando a Inversão de Dependência (DIP - ADR-001).
    """
    app_dir = Path("src/application")
    if not app_dir.exists():
        return

    violations: list[str] = []
    for py_file in app_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        for imported_module, lineno in _get_imports(py_file):
            root_module = imported_module.split(".")[0]

            # 1. Proibição de ORMs / frameworks concretos
            if root_module in PROHIBITED_APPLICATION_LIBRARIES:
                violations.append(
                    f"{py_file.name}:{lineno} importa infraestrutura: '{imported_module}'"
                )

            # 2. Proibição de camadas de adaptadores ou infraestrutura
            for prohibited_layer in PROHIBITED_APPLICATION_LAYERS:
                if imported_module == prohibited_layer or imported_module.startswith(
                    prohibited_layer + "."
                ):
                    violations.append(
                        f"{py_file.name}:{lineno} importa adaptador concreto: '{imported_module}'"
                    )

    assert not violations, (
        "Violações de Inversão de Dependência (ADR-001) detectadas na aplicação:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_all_adrs_follow_nygard_standard() -> None:
    """Garante que todos os documentos ADR em docs/adrs/ sigam a estrutura padrão

    com Status, Contexto, Decisão e Consequências.
    """
    adrs_dir = Path("docs/adrs")
    if not adrs_dir.exists():
        return

    adr_files = list(adrs_dir.glob("ADR-*.md"))
    assert adr_files, "Nenhum arquivo ADR encontrado em docs/adrs/"

    for adr_file in adr_files:
        content = adr_file.read_text(encoding="utf-8")
        assert "* **Status:**" in content, f"{adr_file.name} deve conter o campo '* **Status:**'"
        assert "## 1. Contexto" in content, f"{adr_file.name} deve conter a seção '## 1. Contexto'"
        assert "## 2. Decisão" in content, f"{adr_file.name} deve conter a seção '## 2. Decisão'"
        assert "## 3. Consequências" in content, (
            f"{adr_file.name} deve conter a seção '## 3. Consequências'"
        )
