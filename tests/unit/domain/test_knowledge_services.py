"""Testes unitários do serviço de domínio DocumentTextExtractorService."""

import io
from unittest.mock import Mock

import docx
import pypdf
import pytest

from src.domain.exceptions import DomainValidationError
from src.domain.services import DocumentTextExtractorService


@pytest.mark.unit
def test_document_text_extractor_empty_file_error() -> None:
    """Rejeita arquivo vazio com 0 bytes."""
    with pytest.raises(DomainValidationError, match="vazio"):
        DocumentTextExtractorService.extract_text(b"", "documento.pdf")


@pytest.mark.unit
def test_document_text_extractor_oversized_file_error() -> None:
    """Rejeita arquivo acima do limite de 15 MB."""
    large_bytes = b"x" * (16 * 1024 * 1024)
    with pytest.raises(DomainValidationError, match="Arquivo excede o limite máximo de 15MB."):
        DocumentTextExtractorService.extract_text(large_bytes, "grande.pdf")


@pytest.mark.unit
def test_document_text_extractor_unsupported_extension_error() -> None:
    """Rejeita formatos não suportados sem MIME type reconhecido."""
    with pytest.raises(DomainValidationError, match="Formato de arquivo não suportado"):
        DocumentTextExtractorService.extract_text(b"some binary code", "malware.exe")


@pytest.mark.unit
def test_document_text_extractor_txt_utf8_success() -> None:
    """Extrai texto normalizado de arquivo TXT em UTF-8."""
    sample_text = "Este é um texto de estudo válido para processamento local."
    raw_bytes = sample_text.encode("utf-8")
    extracted = DocumentTextExtractorService.extract_text(raw_bytes, "resumo.txt")
    assert extracted == sample_text


@pytest.mark.unit
def test_document_text_extractor_txt_latin1_fallback_success() -> None:
    """Realiza fallback para Latin-1 quando o TXT não é UTF-8 válido."""
    sample_text = "Ato administrativo com eficácia e validade perante o ordenamento jurídico."
    raw_bytes = sample_text.encode("latin-1")
    extracted = DocumentTextExtractorService.extract_text(raw_bytes, "anotacoes.txt")
    assert "Ato administrativo" in extracted


@pytest.mark.unit
@pytest.mark.parametrize("filename", ["capitulo.md", "notas.markdown", "dados.csv", "doc.json"])
def test_document_text_extractor_plain_text_extensions_success(filename: str) -> None:
    """Extrai texto de extensões textuais suportadas (.md, .markdown, .csv, .json)."""
    sample = "# Capítulo 1\n\nConteúdo essencial para estudo."
    extracted = DocumentTextExtractorService.extract_text(sample.encode("utf-8"), filename)
    assert extracted == sample


@pytest.mark.unit
def test_document_text_extractor_mime_type_routing_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suporta roteamento por MIME type quando a extensão do arquivo não é informativa."""
    text_extracted = DocumentTextExtractorService.extract_text(
        b"  Texto via mime  ", "sem_extensao", mime_type="text/plain"
    )
    assert text_extracted == "Texto via mime"

    doc = docx.Document()
    doc.add_paragraph("Conteúdo DOCX via MIME.")
    buf = io.BytesIO()
    doc.save(buf)
    docx_extracted = DocumentTextExtractorService.extract_text(
        buf.getvalue(),
        "arquivo_sem_extensao",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert docx_extracted == "Conteúdo DOCX via MIME."

    page = Mock()
    page.extract_text.return_value = "PDF via MIME."
    mock_reader = Mock(is_encrypted=False, pages=[page])
    monkeypatch.setattr(pypdf, "PdfReader", Mock(return_value=mock_reader))
    pdf_extracted = DocumentTextExtractorService.extract_text(
        b"%PDF-1.4\n...", "arquivo_sem_extensao", mime_type="application/pdf"
    )
    assert pdf_extracted == "PDF via MIME."


@pytest.mark.unit
def test_document_text_extractor_empty_text_file_error() -> None:
    """Rejeita arquivos de texto contendo apenas espaços em branco."""
    short_bytes = b"   \n\t  "
    with pytest.raises(DomainValidationError, match="arquivo de texto está vazio"):
        DocumentTextExtractorService.extract_text(short_bytes, "vazio.txt")


@pytest.mark.unit
def test_document_text_extractor_docx_success() -> None:
    """Extrai parágrafos concatenados de um documento .docx válido."""
    doc = docx.Document()
    doc.add_paragraph("Parágrafo 1 sobre direitos fundamentais e garantias individuais.")
    doc.add_paragraph("   ")
    doc.add_paragraph("Parágrafo 2 com cláusulas pétreas na constituição federal.")
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    extracted = DocumentTextExtractorService.extract_text(docx_bytes, "constituicao.docx")
    assert "Parágrafo 1 sobre direitos fundamentais" in extracted
    assert "Parágrafo 2 com cláusulas pétreas" in extracted
    assert extracted == (
        "Parágrafo 1 sobre direitos fundamentais e garantias individuais.\n\n"
        "Parágrafo 2 com cláusulas pétreas na constituição federal."
    )


@pytest.mark.unit
def test_document_text_extractor_docx_corrupted_error() -> None:
    """Rejeita arquivo .docx corrompido com DomainValidationError."""
    corrupted_bytes = b"PK\x03\x04corrupted-docx-data-not-a-valid-zip-file"
    with pytest.raises(DomainValidationError, match="Falha ao processar o arquivo Word"):
        DocumentTextExtractorService.extract_text(corrupted_bytes, "corrupted.docx")


@pytest.mark.unit
def test_document_text_extractor_docx_empty_paragraphs_error() -> None:
    """Rejeita arquivo .docx sem parágrafos com texto útil."""
    doc = docx.Document()
    doc.add_paragraph("   ")
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    with pytest.raises(DomainValidationError, match="não contém texto"):
        DocumentTextExtractorService.extract_text(docx_bytes, "vazio.docx")


@pytest.mark.unit
def test_document_text_extractor_pdf_corrupted_error() -> None:
    """Rejeita arquivo PDF corrompido com DomainValidationError."""
    corrupted_pdf = b"%PDF-1.4\ncorrupted-pdf-stream-without-objects"
    with pytest.raises(DomainValidationError, match="Falha ao processar o arquivo PDF"):
        DocumentTextExtractorService.extract_text(corrupted_pdf, "corrupted.pdf")


@pytest.mark.unit
def test_document_text_extractor_pdf_encrypted_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rejeita arquivo PDF protegido por senha ou criptografado."""
    mock_reader = Mock()
    mock_reader.is_encrypted = True
    monkeypatch.setattr(pypdf, "PdfReader", Mock(return_value=mock_reader))

    fake_pdf = b"%PDF-1.4\n..."
    with pytest.raises(DomainValidationError, match="protegidos por senha"):
        DocumentTextExtractorService.extract_text(fake_pdf, "segredo.pdf")


@pytest.mark.unit
def test_document_text_extractor_pdf_extract_pages_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Extrai e concatena páginas com texto válido ignorando páginas em branco."""
    page1 = Mock()
    page1.extract_text.return_value = "Página 1: Introdução aos conceitos fundamentais de direito."
    page_empty = Mock()
    page_empty.extract_text.return_value = "   "
    page2 = Mock()
    page2.extract_text.return_value = "Página 2: Da aplicabilidade das normas constitucionais."

    mock_reader = Mock()
    mock_reader.is_encrypted = False
    mock_reader.pages = [page1, page_empty, page2]
    monkeypatch.setattr(pypdf, "PdfReader", Mock(return_value=mock_reader))

    fake_pdf = b"%PDF-1.4\nvalid-pdf-bytes"
    extracted = DocumentTextExtractorService.extract_text(fake_pdf, "livro.pdf")
    assert extracted == (
        "Página 1: Introdução aos conceitos fundamentais de direito.\n\n"
        "Página 2: Da aplicabilidade das normas constitucionais."
    )


@pytest.mark.unit
def test_document_text_extractor_pdf_no_text_layer_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rejeita PDF escaneado sem camada de texto selecionável."""
    blank_page = Mock()
    blank_page.extract_text.return_value = "   "
    mock_reader = Mock()
    mock_reader.is_encrypted = False
    mock_reader.pages = [blank_page]
    monkeypatch.setattr(pypdf, "PdfReader", Mock(return_value=mock_reader))

    fake_pdf = b"%PDF-1.4\nscanned-image-pdf"
    with pytest.raises(DomainValidationError, match="não contém camada de texto"):
        DocumentTextExtractorService.extract_text(fake_pdf, "escaner.pdf")


@pytest.mark.unit
def test_document_text_extractor_plain_text_decode_error() -> None:
    """Propaga DomainValidationError quando nenhuma decodificação textual funciona."""
    bad_bytes = Mock(spec=bytes)
    bad_bytes.__len__ = Mock(return_value=100)

    def decode_mock(encoding: str) -> str:
        raise UnicodeDecodeError(encoding, b"", 0, 1, "invalid")

    bad_bytes.decode = Mock(side_effect=decode_mock)

    with pytest.raises(DomainValidationError, match="Falha na decodificação de texto"):
        DocumentTextExtractorService.extract_text(bad_bytes, "ruim.txt")
