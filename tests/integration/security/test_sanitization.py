"""Testes de segurança para a sanitização de inputs contra XSS (Camada 4 - Infraestrutura)."""

import pytest

from src.infrastructure.security.sanitization import sanitize_html_content


@pytest.mark.security
def test_sanitize_removes_script_tags() -> None:
    """Vulnerabilidade prevenida: Execução de código arbitrário via Stored

    Cross-Site Scripting (XSS).

    Garantia de segurança: Assegura que tags <script> sejam completamente removidas
    e neutralizadas dos campos de texto do usuário.
    """
    malicious = "Pergunta normal <script>alert('xss attack');</script> restante"
    clean = sanitize_html_content(malicious)

    assert "<script>" not in clean
    assert "alert('xss attack');" not in clean
    assert "Pergunta normal" in clean


@pytest.mark.security
def test_sanitize_removes_inline_event_handlers() -> None:
    """Vulnerabilidade prevenida: Execução de scripts via manipuladores de evento

    HTML inline (DOM-based XSS).

    Garantia de segurança: Assegura que atributos maliciosos como onerror, onclick e onload
    sejam extirpados de elementos HTML permitidos.
    """
    malicious = '<img src="invalido.jpg" onerror="alert(document.cookie)">'
    clean = sanitize_html_content(malicious)

    assert "onerror" not in clean
    assert "document.cookie" not in clean


@pytest.mark.security
def test_sanitize_preserves_safe_formatting_tags() -> None:
    """Vulnerabilidade prevenida: Supressão indevida de formatação legítima

    do usuário em flashcards.

    Garantia de segurança: Assegura que tags seguras de formatação (b, i, em, strong, p, br, code)
    permaneçam válidas sem introduzir brechas de segurança.
    """
    safe_input = (
        "<p>O conceito de <strong>Clean Architecture</strong> é <em>crucial</em>.<br>"
        "<code>x = 10</code></p>"
    )
    clean = sanitize_html_content(safe_input)

    assert "<strong>Clean Architecture</strong>" in clean
    assert "<em>crucial</em>" in clean
    assert "<code>x = 10</code>" in clean


@pytest.mark.security
def test_sanitize_empty_or_none_input() -> None:
    """Vulnerabilidade prevenida: Negação de serviço ou crash por valores nulos na sanitização.

    Garantia de segurança: Assegura que strings vazias retornem string vazia sem exceções.
    """
    assert sanitize_html_content("") == ""
