"""Testes unitários dos serviços de domínio de RAG e Chunker (Sprint 07)."""

from uuid import uuid4

import pytest

from src.domain.entities import KnowledgeChunk
from src.domain.exceptions import EmptyKnowledgeContentError
from src.domain.services import KnowledgeGroundingService, SemanticChunkerService


@pytest.mark.unit
def test_semantic_chunker_basic_split() -> None:
    text = (
        "O habeas corpus é remédio constitucional. "
        "Ele protege a liberdade de locomoção contra ilegalidade ou abuso de poder. "
        "Já o mandado de segurança protege direito líquido e certo não amparado por habeas corpus. "
        "Ambos são instrumentos de garantia fundamental do cidadão."
    )
    chunks = SemanticChunkerService.chunk_text(text, chunk_size_chars=120, overlap_chars=20)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk.strip()) > 0
        assert len(chunk) <= 150  # tolerância de fronteira de frase


@pytest.mark.unit
def test_semantic_chunker_single_small_chunk() -> None:
    text = "Texto curto que cabe em um único chunk."
    chunks = SemanticChunkerService.chunk_text(text, chunk_size_chars=500, overlap_chars=50)
    assert len(chunks) == 1
    assert chunks[0] == text


@pytest.mark.unit
def test_semantic_chunker_empty_text_error() -> None:
    with pytest.raises(EmptyKnowledgeContentError, match="Texto para chunking não pode ser vazio"):
        SemanticChunkerService.chunk_text("   \n\t  ")


@pytest.mark.unit
def test_semantic_chunker_preserves_sentences_and_normalizes_whitespace() -> None:
    messy_text = "Primeira frase.   \n\n  Segunda frase com quebra   irregular.\nTerceira frase."
    chunks = SemanticChunkerService.chunk_text(messy_text, chunk_size_chars=200, overlap_chars=20)
    assert len(chunks) >= 1
    assert "  " not in chunks[0]  # espaços duplos normalizados


@pytest.mark.unit
def test_knowledge_grounding_cosine_similarity() -> None:
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]
    vec_d = [-1.0, 0.0, 0.0]

    assert pytest.approx(KnowledgeGroundingService.cosine_similarity(vec_a, vec_b), 0.001) == 1.0
    assert pytest.approx(KnowledgeGroundingService.cosine_similarity(vec_a, vec_c), 0.001) == 0.0
    assert pytest.approx(KnowledgeGroundingService.cosine_similarity(vec_a, vec_d), 0.001) == -1.0


@pytest.mark.unit
def test_knowledge_grounding_cosine_similarity_zero_norm() -> None:
    vec_zero = [0.0, 0.0, 0.0]
    vec_a = [1.0, 2.0, 3.0]
    assert KnowledgeGroundingService.cosine_similarity(vec_zero, vec_a) == 0.0


@pytest.mark.unit
def test_knowledge_grounding_rank_chunks() -> None:
    source_id = uuid4()
    topic_id = uuid4()

    c1 = KnowledgeChunk(
        source_id=source_id,
        topic_id=topic_id,
        chunk_index=0,
        content="Chunk sobre direito penal",
        embedding=(1.0, 0.0, 0.0),
    )
    c2 = KnowledgeChunk(
        source_id=source_id,
        topic_id=topic_id,
        chunk_index=1,
        content="Chunk sobre direito civil",
        embedding=(0.5, 0.5, 0.0),
    )
    c3 = KnowledgeChunk(
        source_id=source_id,
        topic_id=topic_id,
        chunk_index=2,
        content="Chunk sobre culinária",
        embedding=(0.0, 1.0, 0.0),
    )

    query_vec = [1.0, 0.0, 0.0]
    ranked = KnowledgeGroundingService.rank_chunks_by_similarity(query_vec, [c1, c2, c3], top_k=2)

    assert len(ranked) == 2
    assert ranked[0][0].id == c1.id
    assert pytest.approx(ranked[0][1], 0.01) == 1.0
    assert ranked[1][0].id == c2.id


@pytest.mark.unit
def test_semantic_chunker_with_overlap_sentences() -> None:
    text = (
        "Frase 1 curta. Frase 2 média tamanho. "
        "Frase 3 longa com mais texto relevante. Frase 4 final."
    )
    chunks = SemanticChunkerService.chunk_text(text, chunk_size_chars=40, overlap_chars=25)
    assert len(chunks) >= 2


@pytest.mark.unit
def test_knowledge_grounding_cosine_similarity_different_lengths() -> None:
    assert KnowledgeGroundingService.cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert KnowledgeGroundingService.cosine_similarity([], []) == 0.0


@pytest.mark.unit
def test_knowledge_grounding_rank_chunks_with_threshold() -> None:
    source_id = uuid4()
    topic_id = uuid4()

    c1 = KnowledgeChunk(
        source_id=source_id,
        topic_id=topic_id,
        chunk_index=0,
        content="Altamente relevante",
        embedding=(1.0, 0.0, 0.0),
    )
    c2 = KnowledgeChunk(
        source_id=source_id,
        topic_id=topic_id,
        chunk_index=1,
        content="Similaridade moderada (~0.707)",
        embedding=(0.5, 0.5, 0.0),
    )
    c3 = KnowledgeChunk(
        source_id=source_id,
        topic_id=topic_id,
        chunk_index=2,
        content="Irrelevante (0.0)",
        embedding=(0.0, 1.0, 0.0),
    )

    query_vec = [1.0, 0.0, 0.0]

    # Threshold 0.70 deve incluir c1 (1.0) e c2 (0.707), excluindo c3 (0.0)
    ranked = KnowledgeGroundingService.rank_chunks_by_similarity(
        query_vec, [c1, c2, c3], threshold=0.70, top_k=5
    )
    assert len(ranked) == 2
    assert ranked[0][0].id == c1.id
    assert ranked[1][0].id == c2.id

    # Threshold alto (0.80) deve incluir apenas c1
    ranked_high = KnowledgeGroundingService.rank_chunks_by_similarity(
        query_vec, [c1, c2, c3], threshold=0.80, top_k=5
    )
    assert len(ranked_high) == 1
    assert ranked_high[0][0].id == c1.id

    # Threshold inatingível (0.9999 no c2/c3 e query diferente) retorna vazio
    ranked_none = KnowledgeGroundingService.rank_chunks_by_similarity(
        [0.0, 0.0, 1.0], [c1, c2, c3], threshold=0.70, top_k=5
    )
    assert len(ranked_none) == 0


@pytest.mark.unit
def test_document_text_extractor_empty_file_error() -> None:
    from src.domain.exceptions import DomainValidationError
    from src.domain.services import DocumentTextExtractorService

    with pytest.raises(DomainValidationError, match="vazio"):
        DocumentTextExtractorService.extract_text(b"", "documento.pdf")


@pytest.mark.unit
def test_document_text_extractor_oversized_file_error() -> None:
    from src.domain.exceptions import DomainValidationError
    from src.domain.services import DocumentTextExtractorService

    large_bytes = b"x" * (16 * 1024 * 1024)
    with pytest.raises(DomainValidationError, match="Arquivo excede o limite máximo de 15MB."):
        DocumentTextExtractorService.extract_text(large_bytes, "grande.pdf")


@pytest.mark.unit
def test_document_text_extractor_unsupported_extension_error() -> None:
    from src.domain.exceptions import DomainValidationError
    from src.domain.services import DocumentTextExtractorService

    with pytest.raises(DomainValidationError, match="Formato de arquivo não suportado"):
        DocumentTextExtractorService.extract_text(b"some binary code", "malware.exe")


@pytest.mark.unit
def test_document_text_extractor_txt_utf8_success() -> None:
    from src.domain.services import DocumentTextExtractorService

    sample_text = "Este é um texto de estudo válido para processamento de RAG e avaliação."
    raw_bytes = sample_text.encode("utf-8")
    extracted = DocumentTextExtractorService.extract_text(raw_bytes, "resumo.txt")
    assert extracted == sample_text


@pytest.mark.unit
def test_document_text_extractor_txt_latin1_fallback_success() -> None:
    from src.domain.services import DocumentTextExtractorService

    sample_text = "Ato administrativo com eficácia e validade perante o ordenamento jurídico."
    raw_bytes = sample_text.encode("latin-1")
    extracted = DocumentTextExtractorService.extract_text(raw_bytes, "anotacoes.txt")
    assert "Ato administrativo" in extracted


@pytest.mark.unit
def test_document_text_extractor_md_success() -> None:
    from src.domain.services import DocumentTextExtractorService

    sample_md = "# Capítulo 1\n\nConteúdo essencial com **destaques** e diretrizes gerais."
    raw_bytes = sample_md.encode("utf-8")
    extracted = DocumentTextExtractorService.extract_text(raw_bytes, "capitulo.md")
    assert extracted == sample_md


@pytest.mark.unit
def test_document_text_extractor_empty_text_file_error() -> None:
    from src.domain.exceptions import DomainValidationError
    from src.domain.services import DocumentTextExtractorService

    short_bytes = b"   \n\t  "
    with pytest.raises(DomainValidationError, match="arquivo de texto está vazio"):
        DocumentTextExtractorService.extract_text(short_bytes, "vazio.txt")


@pytest.mark.unit
def test_document_text_extractor_docx_success() -> None:
    import io
    import docx
    from src.domain.services import DocumentTextExtractorService

    doc = docx.Document()
    doc.add_paragraph("Parágrafo 1 sobre direitos fundamentais e garantias individuais.")
    doc.add_paragraph("Parágrafo 2 com cláusulas pétreas na constituição federal.")
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    extracted = DocumentTextExtractorService.extract_text(docx_bytes, "constituicao.docx")
    assert "Parágrafo 1 sobre direitos fundamentais" in extracted
    assert "Parágrafo 2 com cláusulas pétreas" in extracted


@pytest.mark.unit
def test_document_text_extractor_docx_corrupted_error() -> None:
    from src.domain.exceptions import DomainValidationError
    from src.domain.services import DocumentTextExtractorService

    corrupted_bytes = b"PK\x03\x04corrupted-docx-data-not-a-valid-zip-file"
    with pytest.raises(DomainValidationError, match="Falha ao processar o arquivo Word"):
        DocumentTextExtractorService.extract_text(corrupted_bytes, "corrupted.docx")


@pytest.mark.unit
def test_document_text_extractor_pdf_corrupted_error() -> None:
    from src.domain.exceptions import DomainValidationError
    from src.domain.services import DocumentTextExtractorService

    corrupted_pdf = b"%PDF-1.4\ncorrupted-pdf-stream-without-objects"
    with pytest.raises(DomainValidationError, match="Falha ao processar o arquivo PDF"):
        DocumentTextExtractorService.extract_text(corrupted_pdf, "corrupted.pdf")


@pytest.mark.unit
def test_document_text_extractor_pdf_encrypted_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import Mock
    from src.domain.exceptions import DomainValidationError
    from src.domain.services import DocumentTextExtractorService
    import pypdf

    mock_reader = Mock()
    mock_reader.is_encrypted = True
    monkeypatch.setattr(pypdf, "PdfReader", Mock(return_value=mock_reader))

    fake_pdf = b"%PDF-1.4\n..."
    with pytest.raises(DomainValidationError, match="protegidos por senha"):
        DocumentTextExtractorService.extract_text(fake_pdf, "segredo.pdf")


@pytest.mark.unit
def test_document_text_extractor_pdf_extract_pages_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import Mock
    from src.domain.services import DocumentTextExtractorService
    import pypdf

    page1 = Mock()
    page1.extract_text.return_value = "Página 1: Introdução aos conceitos fundamentais de direito."
    page2 = Mock()
    page2.extract_text.return_value = "Página 2: Da aplicabilidade das normas constitucionais."

    mock_reader = Mock()
    mock_reader.is_encrypted = False
    mock_reader.pages = [page1, page2]
    monkeypatch.setattr(pypdf, "PdfReader", Mock(return_value=mock_reader))

    fake_pdf = b"%PDF-1.4\nvalid-pdf-bytes"
    extracted = DocumentTextExtractorService.extract_text(fake_pdf, "livro.pdf")
    assert "Página 1: Introdução" in extracted
    assert "Página 2: Da aplicabilidade" in extracted


@pytest.mark.unit
def test_document_text_extractor_pdf_no_text_layer_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import Mock
    from src.domain.exceptions import DomainValidationError
    from src.domain.services import DocumentTextExtractorService
    import pypdf

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
def test_document_text_extractor_docx_empty_paragraphs_error() -> None:
    import io
    import docx
    from src.domain.exceptions import DomainValidationError
    from src.domain.services import DocumentTextExtractorService

    doc = docx.Document()
    doc.add_paragraph("   ")
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    with pytest.raises(DomainValidationError, match="não contém texto"):
        DocumentTextExtractorService.extract_text(docx_bytes, "vazio.docx")


@pytest.mark.unit
def test_document_text_extractor_plain_text_decode_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import Mock
    from src.domain.exceptions import DomainValidationError
    from src.domain.services import DocumentTextExtractorService

    bad_bytes = Mock(spec=bytes)
    bad_bytes.__len__ = Mock(return_value=100)

    def decode_mock(encoding: str) -> str:
        raise UnicodeDecodeError(encoding, b"", 0, 1, "invalid")

    bad_bytes.decode = Mock(side_effect=decode_mock)

    with pytest.raises(DomainValidationError, match="Falha na decodificação de texto"):
        DocumentTextExtractorService.extract_text(bad_bytes, "ruim.txt")


