"""Testes unitários para o módulo de sanitização (Camada 4 - Infraestrutura)."""

import pytest

from src.infrastructure.security.sanitization import (
    ALLOWED_TAGS,
    MarkdownSanitizerService,
    sanitize_html_content,
)


@pytest.mark.security
def test_allowed_tags_contains_expected_markdown_elements() -> None:
    expected_tags = {
        "b",
        "i",
        "em",
        "strong",
        "p",
        "br",
        "code",
        "pre",
        "span",
        "ul",
        "ol",
        "li",
        "img",
        "blockquote",
        "h1",
        "h2",
        "h3",
        "h4",
        "hr",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    }
    assert expected_tags.issubset(ALLOWED_TAGS)
    assert expected_tags.issubset(MarkdownSanitizerService.ALLOWED_TAGS)


@pytest.mark.security
def test_sanitize_html_content_empty_and_valid() -> None:
    assert sanitize_html_content("") == ""
    assert sanitize_html_content("   ") == "   "
    clean = sanitize_html_content("<p>Texto <strong>negrito</strong> e <code>código</code></p>")
    assert "<p>Texto <strong>negrito</strong> e <code>código</code></p>" in clean


@pytest.mark.security
def test_sanitize_html_content_removes_dangerous_tags() -> None:
    malicious = "<script>alert('xss')</script><iframe src='https://evil.com'></iframe><p>OK</p>"
    clean = sanitize_html_content(malicious)
    assert "<script>" not in clean
    assert "<iframe>" not in clean
    assert "<p>OK</p>" in clean


@pytest.mark.security
def test_markdown_sanitizer_service_empty_and_safe_elements() -> None:
    assert MarkdownSanitizerService.sanitize("") == ""
    raw = (
        "<h1>Título 1</h1>"
        "<h2>Título 2</h2>"
        "<h3>Título 3</h3>"
        "<h4>Título 4</h4>"
        "<hr>"
        "<blockquote>Citação</blockquote>"
        "<table><thead><tr><th>Cabeçalho</th></tr></thead>"
        "<tbody><tr><td>Célula</td></tr></tbody></table>"
        '<img src="https://example.com/image.png" alt="Exemplo">'
    )
    clean = MarkdownSanitizerService.sanitize(raw)
    assert "<h1>Título 1</h1>" in clean
    assert "<h4>Título 4</h4>" in clean
    assert "<hr>" in clean
    assert "<blockquote>Citação</blockquote>" in clean
    assert "<table>" in clean
    assert "<th>Cabeçalho</th>" in clean
    assert "<td>Célula</td>" in clean
    assert 'src="https://example.com/image.png"' in clean


@pytest.mark.security
def test_markdown_sanitizer_service_removes_xss() -> None:
    malicious = (
        "<p>Alvo</p><script>alert(1)</script>"
        '<img src="http://insecure.com/x.png" onerror="alert(2)">'
    )
    clean = MarkdownSanitizerService.sanitize(malicious)
    assert "<script>" not in clean
    assert "onerror" not in clean
    assert "http://insecure.com/x.png" not in clean
