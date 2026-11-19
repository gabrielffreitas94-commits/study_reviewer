"""Meta-testes de conformidade offline e licenciamento do repositório."""

import ast
import json
from pathlib import Path

FORBIDDEN_WEB_PATTERNS = (
    "unpkg.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "cdn.jsdelivr.net",
    "cdn.tailwindcss.com",
    "generativelanguage.googleapis.com",
    "accounts.google.com",
    "oauth2.googleapis.com",
)

FORBIDDEN_PYTHON_MODULES = (
    "boto3",
    "mangum",
    "moto",
    "google_client",
    "gemini_adapters",
)


def test_mit_license_and_public_package_metadata() -> None:
    """Garante presença da licença MIT na raiz e metadados públicos em package.json."""
    license_path = Path("LICENSE")
    assert license_path.is_file(), "Arquivo LICENSE não encontrado na raiz do repositório."
    assert "MIT License" in license_path.read_text(encoding="utf-8")

    pkg_data = json.loads(Path("package.json").read_text(encoding="utf-8"))
    assert pkg_data.get("private") is False, "package.json deve declarar private=false."
    assert pkg_data.get("license") == "MIT", "package.json deve declarar license=MIT."

    all_deps = {
        **pkg_data.get("dependencies", {}),
        **pkg_data.get("devDependencies", {}),
    }
    neon_deps = [name for name in all_deps if name.startswith("@neon/")]
    assert not neon_deps, f"Dependências @neon/* proibidas encontradas: {neon_deps}"


def test_local_htmx_and_no_external_cdn_or_cloud_urls_in_web() -> None:
    """Garante HTMX local e ausência de CDNs/APIs externas em templates HTML e JS."""
    htmx_path = Path("src/adapters/web/static/js/htmx.min.js")
    assert htmx_path.is_file(), "htmx.min.js local não encontrado em static/js/."
    assert htmx_path.stat().st_size > 10_000, "htmx.min.js parece vazio ou corrompido."

    web_root = Path("src/adapters/web")
    violations: list[str] = []

    for asset_file in list(web_root.rglob("*.html")) + list(web_root.rglob("*.js")):
        content = asset_file.read_text(encoding="utf-8").lower()
        for pattern in FORBIDDEN_WEB_PATTERNS:
            if pattern in content:
                violations.append(f"{asset_file.as_posix()} contém referência externa '{pattern}'")

    assert not violations, "Referências externas proibidas encontradas:\n" + "\n".join(
        f"  - {v}" for v in violations
    )


def test_src_has_no_cloud_or_ai_adapter_imports() -> None:
    """Garante via AST que nenhum arquivo em src/ importe módulos cloud, OAuth ou IA externa."""
    src_root = Path("src")
    violations: list[str] = []

    for py_file in src_root.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            else:
                continue

            for mod in modules:
                for forbidden in FORBIDDEN_PYTHON_MODULES:
                    if forbidden in mod.split("."):
                        violations.append(
                            f"{py_file.as_posix()}:{node.lineno} importa módulo proibido '{mod}'"
                        )

    assert not violations, "Imports proibidos encontrados em src/:\n" + "\n".join(
        f"  - {v}" for v in violations
    )
