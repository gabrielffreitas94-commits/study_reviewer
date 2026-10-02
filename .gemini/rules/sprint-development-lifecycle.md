# Ciclo de Desenvolvimento por Sprints — Governança e Regras de Engenharia
# Projeto: Study Reviewer

Este documento estabelece as regras inegociáveis para o desenvolvimento de todas as Sprints do projeto **Study Reviewer**. O assistente e os desenvolvedores devem aderir estritamente a estas diretrizes em todas as interações.

---

## 1. Regras de Ouro Inegociáveis

1. **1 Sprint = 1 Branch de Feature = 1 PR Aberta para Staging:**
   - Nenhuma sprint é concluída sem que uma Pull Request formal seja aberta da branch `feature/sprint-XX-<nome>` para `staging`.
   - O merge de `staging` para `main` é de responsabilidade exclusiva do usuário após validação em ambiente de homologação.
   - A PR para `staging` deve conter o template oficial completamente preenchido e assinado por todos os 10 especialistas.

2. **TDD Estrito (Test-Driven Development — Red, Green, Refactor):**
   - **🔴 RED:** Nenhum código de produção deve ser escrito antes de existir um teste unitário/de integração correspondente que falhe.
   - **🟢 GREEN:** Escrever apenas o código de produção estritamente necessário para fazer os testes passarem.
   - **🔵 REFACTOR:** Refatorar o código garantindo Clean Architecture (4 camadas concêntricas) sem quebrar nenhum teste.

3. **Mapeamento Prévio de Casos de Uso e Edge Cases:**
   - Antes de iniciar a implementação do código de qualquer sprint:
     - A persona **Especialista de Produto** utiliza a skill `product-use-cases-generator` para mapear todos os cenários em BDD/Gherkin (Caminho Feliz, Casos de Borda, Validações, Falhas e Segurança).
     - A persona **Especialista QA** utiliza a skill `qa-use-cases-validator` para auditar a completude e consistência.
     - A codificação TDD só inicia após essa validação autônoma.

4. **Documento SPEC e ADRs Pré-Sprint Aprovados pelo Usuário:**
   - Antes de iniciar a implementação da Sprint 1 e de sprints com decisões estruturais, o **Especialista Arquiteto** deve redigir:
     - O documento de **SPEC Técnica** (`docs/specs/sprint-XX-<nome>-spec.md`).
     - Os devidos **ADRs (Architecture Decision Records)** em `docs/adrs/`.
   - ⚠️ **Portão Obrigatório:** Tanto a SPEC quanto os ADRs DEVEM ser apresentados ao usuário e aprovados formalmente por ele antes do início de qualquer escrita de código da sprint.

5. **Testes de Segurança e Meta-teste AST:**
   - Qualquer teste relacionado a segurança, controle de acesso, injeção, sanitização, vazamento de dados ou vulnerabilidades DEVE:
     - Conter o decorator `@pytest.mark.security`.
     - Conter uma docstring rica e obrigatória detalhando:
       - `Vulnerabilidade prevenida:` Explicação clara da vulnerabilidade mitigada.
       - `Garantia de segurança:` Como o teste assegura que o sistema permaneça estritamente seguro.
   - O meta-teste de AST (`tests/governance/test_security_governance.py`) inspeciona todo o código e barra a pipeline se essa regra for violada.

6. **CI/CD com 100% de Cobertura e Processos Isolados:**
   - A pipeline de CI/CD deve exigir 100% de cobertura de código (`--cov-fail-under=100`).
   - Testes de Backend e Frontend devem rodar em processos totalmente isolados.
   - Linters e checagem de tipos estrita (Ruff e Mypy) devem passar sem avisos.

7. **Auditoria Unânime pelos 10 Especialistas:**
   - Antes da abertura da PR, todas as 10 personas técnicas devem auditar o código e emitir seus pareceres formais:
     1. Especialista de Produto
     2. Especialista QA
     3. Especialista Arquiteto
     4. Especialista de Segurança
     5. Especialista de Telemetria
     6. Especialista de UX
     7. Especialista de UI
     8. Especialista de DevOps
     9. Especialista de Acessibilidade
     10. Especialista em LGPD
   - Status válidos para cada parecer: `[APROVADO]` ou `[N/A JUSTIFICADO]`. Nenhum especialista pode ser omitido.
