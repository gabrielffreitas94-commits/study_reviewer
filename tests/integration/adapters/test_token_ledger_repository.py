"""Testes de integração para o repositório SQLAlchemy de TokenLedger e TokenTransaction."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters.persistence.repositories import (
    SqlAlchemyTokenLedgerRepository,
    SqlAlchemyUserRepository,
)
from src.domain.entities import TokenLedger, TokenTransaction, User
from src.infrastructure.database import Base


@pytest.fixture
def db_session() -> Generator[Session]:
    """Cria banco SQLite em memória isolado para os testes de integração."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.integration
def test_token_ledger_repository_crud_lifecycle(db_session: Session) -> None:
    user_repo = SqlAlchemyUserRepository(db_session)
    ledger_repo = SqlAlchemyTokenLedgerRepository(db_session)

    user = User(google_sub="sub-token-1", email="tokens@test.com", name="FinOps User")
    user_repo.save(user)

    # 1. Busca usuário sem ledger
    assert ledger_repo.get_by_user_id(user.id) is None

    # 2. Cria ledger inicial
    ledger = TokenLedger(user_id=user.id, balance=1500, held_balance=0)
    saved = ledger_repo.save(ledger)
    assert saved.user_id == user.id
    assert saved.balance == 1500
    assert saved.held_balance == 0

    # 3. Atualiza ledger existente
    saved.hold(500)
    updated = ledger_repo.save(saved)
    assert updated.balance == 1500
    assert updated.held_balance == 500
    assert updated.available_balance == 1000

    # 4. Registra transações no extrato
    tx1 = TokenTransaction(
        user_id=user.id,
        transaction_type="DEPOSIT",
        amount=1500,
        reference_id="PURCHASE_1",
    )
    tx2 = TokenTransaction(
        user_id=user.id,
        transaction_type="HOLD",
        amount=500,
        reference_id="Q_1",
    )
    ledger_repo.record_transaction(tx1)
    ledger_repo.record_transaction(tx2)

    # 5. Listagem com ordenação e limite
    transactions = ledger_repo.list_transactions(user_id=user.id, limit=10)
    assert len(transactions) == 2
    types = [t.transaction_type for t in transactions]
    assert "DEPOSIT" in types
    assert "HOLD" in types
