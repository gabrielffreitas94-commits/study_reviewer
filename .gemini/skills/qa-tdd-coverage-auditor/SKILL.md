---
name: qa-tdd-coverage-auditor
description: Audits the automated test suite, verifies 100% test coverage in isolated backend and frontend processes, inspects assertion quality, and enforces TDD rigor during PR review.
---

# QA TDD & Coverage Auditor (Skill do Especialista QA)

Esta skill é utilizada pelo **Especialista QA** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é auditar a suíte de testes automatizados, garantir o cumprimento inegociável da barreira de **100% de cobertura de código**, verificar a qualidade e profundidade das asserções e assegurar que a entrega seja resiliente, determinística e livre de testes frágeis (*flaky*).

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Suíte de testes em `tests/` e código de produção em `src/`.
  * Matriz de use cases aprovada em `docs/sprints/sprint-XX/01-use-cases-and-edge-cases.md`.
  * Relatórios de cobertura gerados pelo `pytest-cov` e pelos runners de teste de frontend.
* **Gatilho de Execução:** Conclusão da implementação da Sprint e prontidão para a auditoria formal da Pull Request.

---

## 2. Checklist Exaustivo de Auditoria de QA

O Especialista QA realiza uma inspeção aprofundada baseada em cinco pilares fundamentais:

1. **Barreira Inegociável de 100% de Cobertura de Código:**
   * **Backend:** A execução de `pytest --cov=src --cov-fail-under=100` atinge 100% estrito de cobertura de linhas e branches? Nenhuma linha ou desvio condicional ficou de fora?
   * **Frontend:** Os testes de templates, componentes e rotinas de interface foram executados em processo isolado e registraram aprovação integral?
   * **Zero Linhas Mortas:** Há código de produção escrito que não seja exercitado por nenhum teste? *Se houver, o código deve ser removido ou o teste deve ser escrito.*

2. **Qualidade e Profundidade das Asserções:**
   * **Proibição de Asserções Fracas/Ocas:** Não são permitidos testes com `assert True`, `assert response.status_code == 200` desacompanhado da validação do payload, ou `assert result is not None` quando valores exatos deveriam ser inspecionados.
   * **Validação de Efeitos Colaterais:** Além do valor de retorno, o teste valida se o estado persistido no banco ou no repositório foi alterado conforme o esperado?
   * **Testes de Exceção:** Quando uma exceção de domínio é esperada, o teste valida tanto o tipo da exceção quanto a mensagem semântica associada (`pytest.raises(..., match=...)`)?

3. **Aderência à Pirâmide de Testes:**
   * **Testes Unitários:** O núcleo de domínio (entidades, value objects e domain services) possui testes puros, extremamente rápidos e sem necessidade de mocks ou bancos de dados?
   * **Testes de Integração:** Os adaptadores (repositórios, controllers da API, clientes) são testados contra instâncias de teste efêmeras ou isoladas?
   * **Testes Ponta a Ponta (E2E):** Os fluxos críticos de ponta a ponta foram exercitados sem que a base de testes fique excessivamente pesada?

4. **Isolamento, Determinismo e Ausência de Fragilidade (*Flakiness*):**
   * **Controle de Tempo:** Os testes que dependem de datas ou prazos utilizam injeção explícita de data ou bibliotecas de congelamento de tempo, eliminando qualquer risco de quebra por virada de meia-noite ou fuso horário?
   * **Isolamento de Estado:** A execução de um teste não deixa resíduos de dados que afetem a execução dos testes subsequentes (cada teste é executado em transação isolada ou com limpeza automática)?
   * **Independência de Ordem:** A suíte de testes passa com sucesso independentemente da ordem em que os testes são executados?
   * **Zero Rede Externa:** Nenhum teste faz chamadas HTTP para servidores ou serviços externos reais na internet.

5. **Rastreabilidade Integral com os Use Cases:**
   * Cada caso de uso aprovado na matriz `01-use-cases-and-edge-cases.md` possui pelo menos um teste correspondente implementado na suíte?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **2** | **Especialista QA** | `[APROVADO]` | Suíte auditada: 100% de cobertura confirmada no backend (pytest-cov) e no frontend em processos separados. Ausência de testes flaky, asserções profundas e determinísticas. Todos os XX casos de uso foram cobertos. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **2** | **Especialista QA** | `[BLOQUEANTE]` | Auditoria reprovada: [descrever se a cobertura ficou abaixo de 100%, se foram identificadas asserções frágeis ou testes não determinísticos]. Necessário ajuste imediato antes do merge. |
```
