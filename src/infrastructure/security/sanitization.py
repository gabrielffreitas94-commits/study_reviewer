"""Módulo de sanitização defensiva contra XSS (Camada 4 - Infraestrutura)."""

import nh3

ALLOWED_TAGS = {"b", "i", "em", "strong", "p", "br", "code", "pre", "span", "ul", "ol", "li"}


def sanitize_html_content(raw_html: str) -> str:
    """Sanitiza o conteúdo HTML de entrada permitindo tags seguras e neutralizando scripts

    e handlers inline.
    """
    if not raw_html:
        return ""
    return nh3.clean(raw_html, tags=ALLOWED_TAGS, strip_comments=True)
