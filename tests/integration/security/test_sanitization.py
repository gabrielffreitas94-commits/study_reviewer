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

    assert sanitize_html_content("") == ""


@pytest.mark.security
def test_markdown_sanitizer_service_removes_scripts_and_malicious_protocols() -> None:
    """Vulnerabilidade prevenida: XSS e injeção de scripts via Markdown em perguntas abertas.

    Garantia de segurança: Assegura que tags de script, esquemas javascript: e handlers inline
    sejam neutralizados.
    """
    from src.infrastructure.security.sanitization import MarkdownSanitizerService

    malicious = (
        "Enunciado normal <script>alert(1)</script>"
        '<img src="javascript:alert(2)" onerror="alert(3)">'
        '<a href="javascript:void(0)">Link</a>'
    )
    clean = MarkdownSanitizerService.sanitize(malicious)
    assert "<script>" not in clean
    assert "javascript:" not in clean
    assert "onerror" not in clean


@pytest.mark.security
def test_markdown_sanitizer_service_allows_https_images_and_safe_tags() -> None:
    """Vulnerabilidade prevenida: Quebra indevida de conteúdo com formatação legítima.

    Garantia de segurança: Permite imagens HTTPS e formatação semântica H1..H3, blockquote, code.
    """
    from src.infrastructure.security.sanitization import MarkdownSanitizerService

    safe_md = (
        "<h1>Título da Pergunta</h1>"
        "<blockquote>Citação importante</blockquote>"
        '<p>Veja a imagem: <img src="https://cdn.example.com/diagram.png" '
        'alt="Diagrama" title="Legenda"></p>'
        "<pre><code>print('ok')</code></pre>"
    )
    clean = MarkdownSanitizerService.sanitize(safe_md)
    assert "<h1>Título da Pergunta</h1>" in clean
    assert "<blockquote>Citação importante</blockquote>" in clean
    assert 'src="https://cdn.example.com/diagram.png"' in clean
    assert 'alt="Diagrama"' in clean
    assert "<pre><code>print('ok')</code></pre>" in clean


@pytest.mark.security
def test_markdown_sanitizer_service_rejects_insecure_http_images() -> None:
    """Vulnerabilidade prevenida: Mixed Content e interceptação insegura via HTTP não criptografado.

    Garantia de segurança: Rejeita e extirpa o atributo src com protocolo http://, aceitando apenas https://.
    """
    from src.infrastructure.security.sanitization import MarkdownSanitizerService

    insecure_img = '<img src="http://insecure.example.com/bad.png" alt="Inseguro">'
    clean = MarkdownSanitizerService.sanitize(insecure_img)
    assert "http://insecure.example.com/bad.png" not in clean
    assert 'alt="Inseguro"' in clean


@pytest.mark.security
def test_markdown_sanitizer_service_handles_empty_input() -> None:
    """Vulnerabilidade prevenida: Negação de serviço ou crash por input vazio em perguntas abertas.

    Garantia de segurança: Assegura que strings vazias retornem string vazia sem exceção.
    """
    from src.infrastructure.security.sanitization import MarkdownSanitizerService

    assert MarkdownSanitizerService.sanitize("") == ""
