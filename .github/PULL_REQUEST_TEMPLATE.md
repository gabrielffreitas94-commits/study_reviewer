<!-- Template de Pull Request — Study Reviewer (Offline Local Workspace) -->
## 📋 Identificação da Mudança
* **Objetivo:** `<!-- Descreva sucintamente o objetivo e valor entregue -->`
* **ADRs Relacionadas:** `docs/adrs/ADR-XXX-...`

---

## 🧪 Metodologia TDD & Cobertura de Testes (100% Obrigatório)
- [ ] **TDD Aplicado:** Testes unitários e de integração escritos/atualizados junto à mudança.
- [ ] **Cobertura Backend:** 100% de cobertura confirmada via `pytest tests/ --cov=src --cov-fail-under=100`.
- [ ] **Templates & Frontend:** `pytest tests/unit/web/test_frontend_templates.py` verde e `npm run build:css` atualizado.

```bash
# Cole aqui o resumo da execução do pytest com coverage
```

---

## 🛡️ Governança de Segurança & Offline-First
- [ ] Todos os testes de segurança decorados com `@pytest.mark.security` incluem `Vulnerabilidade prevenida:` e `Garantia de segurança:`.
- [ ] Meta-teste AST de segurança (`tests/governance/test_security_governance.py`) 100% verde.
- [ ] Meta-teste de conformidade offline (`tests/governance/test_offline_compliance_governance.py`) 100% verde (sem CDNs, sem provedores de IA externos, sem cloud/AWS/Google OAuth).

---

## 📐 Conformidade Arquitetural & Qualidade
- [ ] `tests/architecture/test_clean_architecture.py` (ADR-001) 100% verde.
- [ ] Linter e formatador (`ruff check .` e `ruff format --check .`) sem avisos.
- [ ] Tipagem estrita (`mypy src tests`) sem erros.
- [ ] Sem dados sensíveis ou segredos commitados (`.env.example` atualizado).
