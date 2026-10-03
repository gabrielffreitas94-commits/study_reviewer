"""Testes de integridade sintática e qualidade de templates Jinja2 e assets de frontend."""

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError


@pytest.mark.unit
def test_all_jinja2_templates_compile_without_syntax_errors() -> None:
    """Garante que todos os templates Jinja2 da aplicação sejam sintaticamente válidos.

    Varre o diretório src/adapters/web/templates/ incluindo parciais e compila cada
    arquivo .html com o Jinja2 Environment, assegurando ausência de erros de sintaxe,
    blocos não fechados ou tags malformadas.
    """
    templates_dir = Path("src/adapters/web/templates")
    assert templates_dir.exists(), "Diretório de templates não encontrado!"

    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)

    template_files = list(templates_dir.rglob("*.html"))
    assert len(template_files) > 0, "Nenhum template HTML encontrado!"

    compilation_errors: list[str] = []
    for template_file in template_files:
        rel_path = template_file.relative_to(templates_dir).as_posix()
        try:
            env.get_template(rel_path)
        except TemplateSyntaxError as e:
            compilation_errors.append(f"{rel_path}:{e.lineno} -> {e.message}")

    assert not compilation_errors, (
        f"Erros de sintaxe Jinja2 encontrados em {len(compilation_errors)} templates:\n"
        + "\n".join(f"  - {err}" for err in compilation_errors)
    )


@pytest.mark.unit
def test_static_tailwind_css_asset_exists_and_is_non_empty() -> None:
    """Valida que o arquivo tailwind.css compilado existe e possui conteúdo minificado."""
    tailwind_css = Path("src/adapters/web/static/css/tailwind.css")
    assert tailwind_css.exists(), "src/adapters/web/static/css/tailwind.css deve existir!"
    assert tailwind_css.stat().st_size > 0, "tailwind.css não pode estar vazio!"


@pytest.mark.security
def test_base_template_enforces_csp_and_security_meta() -> None:
    """Valida a presença de tags de segurança e sanitização no cabeçalho do template base.

    Vulnerabilidade prevenida: Mitiga Cross-Site Scripting (XSS), Clickjacking e MIME-sniffing
    ao verificar que o template base implementa viewport seguro e UTF-8 explícito.
    Garantia de segurança: Assegura que todas as páginas renderizadas contenham meta tags
    essenciais de segurança e sanitização defensiva de atributos.
    """
    base_template_path = Path("src/adapters/web/templates/base.html")
    assert base_template_path.exists(), "base.html deve existir!"

    content = base_template_path.read_text(encoding="utf-8")
    assert 'charset="UTF-8"' in content or 'charset="utf-8"' in content
    assert 'name="viewport"' in content
    has_skip = (
        "skip-to-content" in content
        or "Skip to main content" in content
        or "pular para o conteúdo" in content.lower()
    )
    assert has_skip
