# Ciclo de Desenvolvimento por Sprints — Governança e Regras de Engenharia
# Projeto: Study Reviewer

Este documento estabelece as regras inegociáveis para o desenvolvimento de todas as Sprints do projeto **Study Reviewer**. O assistente e os desenvolvedores devem aderir estritamente a estas diretrizes em todas as interações.

---

## 1. Regras de Ouro Inegociáveis

1. **1 Sprint = 1 Branch de Feature = 1 PR Aberta no GitHub para Staging:**
   - ⚠️ **REGRA MANDATÓRIA DE FECHAMENTO (ZERO EXCEÇÕES):** Nenhuma sprint é dada como finalizada sem que a Pull Request formal seja efetivamente criada no GitHub apontando da branch `feature/sprint-XX-<nome>` para `staging`.
   - **Gerar apenas o documento markdown (`docs/sprints/sprint-XX/02-pull-request-sprint-XX.md`) NÃO finaliza a sprint!** O agente orquestrador DEVE obrigatoriamente executar os seguintes comandos:
     1. `git push -u origin feature/sprint-XX-<nome>`
     2. `gh pr create --base staging --head feature/sprint-XX-<nome> --title "Sprint XX — <Título>" --body-file docs/sprints/sprint-XX/02-pull-request-sprint-XX.md`
   - O encerramento de qualquer sprint só ocorre quando o comando `gh pr create` conclui com sucesso e o link ativo da PR (`https://github.com/.../pull/X`) é fornecido ao usuário.
   - O merge de `staging` para `main` é de responsabilidade exclusiva do usuário após validação em ambiente de homologação.
   - A PR para `staging` deve conter o template oficial completamente preenchido e assinado por todos os 13 especialistas.

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

6. **CI/CD Modular com 100% de Cobertura e Processos Isolados:**
   - O CI/CD é dividido em workflows independentes e especializados em `.github/workflows/`:
     - **Backend:** Lint/Format (Ruff), Type Check (Mypy Strict), Governança Arquitetural & Segurança (AST) e Testes com 100% de Cobertura (`--cov-fail-under=100`).
     - **Frontend:** Build e minificação de assets estáticos (Tailwind CSS) e Integridade de Templates (Jinja2 / UI) em ambientes Node/Python isolados.
     - **Delivery:** Build e paridade de contêiner Docker multi-stage com usuário não-root.

7. **Auditoria Unânime pelos 13 Especialistas:**
   - Antes da abertura da PR, todas as 13 personas técnicas devem auditar o código e emitir seus pareceres formais:
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
     11. Especialista de Performance de Programação Python
     12. Especialista de Performance de Frontend
     13. Especialista de Performance de Banco de Dados
   - Status válidos para cada parecer: `[APROVADO]` ou `[N/A JUSTIFICADO]`. Nenhum especialista pode ser omitido.

8. **Protocolo de Auditoria Concorrente por Clusters (`invoke_subagent`):**
   - Na fase de auditoria final da PR, a avaliação dos 13 especialistas é realizada de forma **estritamente paralela** via multi-agente, agrupados em 4 clusters de competência afins:
     - **Cluster 1 (Core & Arquitetura):** Especialistas #1 (Produto), #2 (QA) e #3 (Arquiteto).
     - **Cluster 2 (Segurança & Compliance):** Especialistas #4 (Segurança), #5 (Telemetria) e #10 (LGPD).
     - **Cluster 3 (Experiência & Interface):** Especialistas #6 (UX), #7 (UI), #9 (Acessibilidade) e #12 (Performance Frontend).
     - **Cluster 4 (Engenharia, Dados & Ops):** Especialistas #8 (DevOps), #11 (Performance Python) e #13 (Performance de Banco de Dados).
   - O assistente orquestrador despacha os 4 clusters concorrentemente em uma única chamada de `invoke_subagent`, consolidando os pareceres na tabela oficial da PR.

9. **Protocolo Automatizado de Fechamento de Sprint (Gatekeeper Inegociável da PR):**
   - Nenhuma sprint pode ser declarada "concluída", "finalizada" ou com o comando `/goal` atingido sem seguir a risca o fluxo sequencial estrito de encerramento:
     1. **Testes & Cobertura:** `pytest --cov=src --cov-fail-under=100` (100.00% de cobertura estrita em `src/`).
     2. **Qualidade Estática de Código:** `ruff check`, `ruff format --check` e `mypy` sem nenhum erro.
     3. **Auditoria Concorrente dos 13 Especialistas:** Despachar os 4 clusters via `invoke_subagent` e obter parecer `[APROVADO]` unânime.
     4. **Documentação Oficial da PR:** Consolidar métricas e a tabela dos 13 pareceres em `docs/sprints/sprint-XX/02-pull-request-sprint-XX.md`.
     5. **Commit de Fechamento:**
        ```bash
        git add .
        git commit -m "feat(sprint-XX): <descrição concisa>"
        ```
     6. **Push da Branch para o Remote:**
        ```bash
        git push -u origin feature/sprint-XX-<nome>
        ```
     7. **Criação Efetiva do Pull Request no GitHub:**
        ```bash
        gh pr create --base staging --head feature/sprint-XX-<nome> --title "Sprint XX — <Título>" --body-file docs/sprints/sprint-XX/02-pull-request-sprint-XX.md
        ```
     8. **Entrega da URL ao Usuário:** O assistente deve exibir na mensagem final a URL clicável do PR criado (ex: `https://github.com/gabrielffreitas94-commits/study_reviewer/pull/X`).
   - ⛔ **TRAVA DE SEGURANÇA:** Se a PR não for criada no GitHub via `gh pr create`, a sprint é considerada **INCOMPLETA**. O agente não deve dar a sprint por encerrada antes de cumprir este passo.
