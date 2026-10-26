import pytest
from uuid import uuid4
from src.domain.entities import KnowledgeSource, Question, StudyNode
from src.domain.exceptions import DomainValidationError


def test_study_node_holds_and_updates_theory_content() -> None:
    node = StudyNode(
        map_id=uuid4(),
        title="Álgebra Linear",
        theory_content="  Matrizes ortogonais preservam normas.  ",
    )
    assert node.theory_content == "Matrizes ortogonais preservam normas."
    node.update_theory("Decomposição SVD e autovalores.")
    assert node.theory_content == "Decomposição SVD e autovalores."
    node.update_theory("   ")
    assert node.theory_content == ""


def test_study_node_default_theory_content() -> None:
    node = StudyNode(
        map_id=uuid4(),
        title="Álgebra Linear",
    )
    assert node.theory_content == ""


def test_question_and_knowledge_source_accept_direct_node_id() -> None:
    node_id = uuid4()
    q = Question(
        prompt="O que é uma matriz ortogonal?",
        expected_answer="Uma matriz Q tal que Q^T Q = I.",
        node_id=node_id,
    )
    assert q.node_id == node_id
    assert q.prompt == "O que é uma matriz ortogonal?"
    assert q.topic_ids == (node_id,)

    src = KnowledgeSource(
        title="Pergaminho de Matrizes",
        node_id=node_id,
        raw_text="Texto integral do pergaminho para leitura no Tomo.",
        content_type="TEXT",
    )
    assert src.node_id == node_id
    assert src.raw_text == "Texto integral do pergaminho para leitura no Tomo."
    assert src.topic_ids == (node_id,)


def test_question_requires_at_least_topic_or_node() -> None:
    with pytest.raises(DomainValidationError, match="associada a pelo menos 1 tema"):
        Question(
            prompt="Pergunta sem tema nem nó?",
            expected_answer="Resposta válida",
        )


def test_knowledge_source_requires_at_least_topic_or_node() -> None:
    with pytest.raises(DomainValidationError, match="associada a pelo menos 1 tema"):
        KnowledgeSource(
            title="Material sem tema nem nó",
            content_type="TEXT",
        )
