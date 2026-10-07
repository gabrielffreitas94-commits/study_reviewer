"""Módulo de sanitização defensiva contra XSS (Camada 4 - Infraestrutura)."""

import nh3

ALLOWED_TAGS = {"b", "i", "em", "strong", "p", "br", "code", "pre", "span", "ul", "ol", "li"}


class MarkdownSanitizerService:
    """Serviço de higienização de Markdown/HTML no write-time contra XSS e SSRF."""

    ALLOWED_TAGS: set[str] = {
        "p",
        "b",
        "i",
        "em",
        "strong",
        "code",
        "pre",
        "ul",
        "ol",
        "li",
        "blockquote",
        "img",
        "h1",
        "h2",
        "h3",
        "span",
        "br",
    }

    ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
        "img": {"src", "alt", "title"},
    }

    ALLOWED_URL_SCHEMES: set[str] = {"https"}

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Sanitiza o conteúdo preservando tags permitidas e restringindo imagens a HTTPS."""
        if not text:
            return ""
        return nh3.clean(
            text,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            url_schemes=cls.ALLOWED_URL_SCHEMES,
            strip_comments=True,
        )


def sanitize_html_content(raw_html: str) -> str:
    """Sanitiza o conteúdo HTML de entrada permitindo tags seguras e neutralizando scripts

    e handlers inline.
    """
    if not raw_html:
        return ""
    return nh3.clean(raw_html, tags=ALLOWED_TAGS, strip_comments=True)
