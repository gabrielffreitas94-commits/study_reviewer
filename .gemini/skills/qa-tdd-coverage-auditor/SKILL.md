---
name: qa-tdd-coverage-auditor
description: Audits holistic software quality, static code health, maintainability, error resilience, and 100% test coverage in isolated backend and frontend processes during PR review.
---

# QA Quality & Coverage Auditor (Skill do Especialista QA)

Esta skill é utilizada pelo **Especialista QA** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é auditar a **qualidade integral do incremento de software**: combinando a inspeção estática de saúde do código (complexidade, tipagem, legibilidade e *code smells*), a robustez do tratamento de falhas e o cumprimento rigoroso da barreira de **100% de cobertura de testes**, com asserções profundas e determinísticas.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Código de produção em `src/` e suíte de testes em `tests/`.
  * Matriz de use cases aprovada em `docs/sprints/sprint-XX/01-use-cases-and-edge-cases.md`.
  * Relatórios de linter (Ruff), checagem estática de tipos (Mypy) e cobertura de testes (`pytest-cov` e runners de frontend).
* **Gatilho de Execução:** Conclusão da implementação da Sprint e prontidão para a auditoria formal da Pull Request.

---

## 2. Checklist Exaustivo de Auditoria Holística de QA

O Especialista QA realiza uma auditoria rigorosa estruturada em seis pilares essenciais de qualidade:

1. **Qualidade Estática do Código & Manutenibilidade:**
   * **Complexidade Ciclomática e Cognitiva:** As funções são concisas, com responsabilidade única e fluxo linear? Há condicionais aninhadas em excesso ou funções excessivamente longas? *Funções com alta complexidade devem ser refatoradas.*
   * **Tipagem Estrita sem Atalhos:** A checagem de tipos estrita passa sem erros e sem uso abusivo de `Any`, `type: ignore` ou casts inseguros.
   * **Conformidade com Linters:** O código passa limpo pelos linters sem supressões artificiais (`# noqa`) e com formatação consistente.
   * **Legibilidade e Expressividade:** Nomes de variáveis, funções e classes expressam claramente a intenção de negócio, evitando abreviações crípticas ou nomes genéricos (`data`, `temp`, `res`).
   * **Zero Código Duplicado (*DRY*) e Zero Código Morto:** Ausência de duplicações de lógica e ausência de trechos de código não utilizados ou comentados.

2. **Resiliência e Qualidade dos Contratos de Erro:**
   * **Hierarquia de Exceções Semânticas:** O sistema define exceções explícitas de domínio e aplicação para cada cenário de erro, em vez de lançar exceções genéricas (`Exception`, `ValueError` genérico).
   * **Proibição de Captura Silenciosa:** É terminantemente proibido silenciar erros (`except: pass` ou captura genérica sem tratamento). Todo erro capturado deve ser tratado, transformado em erro semântico ou devidamente registrado.
   * **Atomicidade de Operações:** O código garante que operações compostas não deixem estados inconsistentes caso uma falha ocorra no meio do processamento.

3. **Barreira Inegociável de 100% de Cobertura de Código:**
   * **Backend:** A execução de `pytest --cov=src --cov-fail-under=100` atinge 100% estrito de cobertura de linhas e branches? Nenhuma linha, desvio condicional ou bloco `else` ficou sem ser exercitado.
   * **Frontend:** Os testes de templates, componentes e scripts foram executados em processo isolado e registraram aprovação integral.

4. **Qualidade e Profundidade das Asserções:**
   * **Proibição de Asserções Fracas/Ocas:** Não são aceitos testes com `assert True`, asserções puramente de status HTTP (`assert response.status_code == 200`) sem validação do corpo da resposta, ou verificações genéricas de não-nulo (`assert result is not None`).
   * **Inspeção de Estado e Efeitos Colaterais:** O teste valida o valor de retorno, o estado das entidades e as mutações persistidas no banco/repositório.
   * **Testes de Exceção Ricos:** O teste valida tanto o tipo exato da exceção quanto a mensagem semântica esperada (`pytest.raises(CustomException, match="...")`).

5. **Isolamento, Determinismo e Pirâmide de Testes:**
   * **Pirâmide Equilibrada:** Domínio com testes unitários puros, ultra-rápidos e sem mocks desnecessários; adaptadores testados com bancos isolados/transacionais; fluxos críticos com testes ponta a ponta.
   * **Zero Testes Frágeis (*Flaky*):** A suíte passa de forma consistente e idêntica em qualquer ordem de execução e em qualquer máquina.
   * **Controle Determinístico de Tempo:** Datas e relógios são injetados ou congelados, eliminando riscos de quebra por virada de meia-noite, fuso horário ou atrasos de processamento.
   * **Zero Dependência de Rede Externa:** Nenhum teste faz conexões a serviços reais externos da internet.

6. **Rastreabilidade com a Matriz de Casos de Uso:**
   * Todos os cenários aprovados na matriz `01-use-cases-and-edge-cases.md` possuem cobertura de testes explícita e correspondência verificada.

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **2** | **Especialista QA** | `[APROVADO]` | Qualidade holística auditada: 100% de cobertura confirmada no backend e frontend em processos separados. Código estático limpo, com baixa complexidade ciclomática, tipagem estrita e sem code smells. Exceções semânticas e asserções profundas em todos os XX casos de uso. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **2** | **Especialista QA** | `[BLOQUEANTE]` | Auditoria de qualidade reprovada: [descrever se a cobertura ficou abaixo de 100%, se foram identificadas asserções frágeis, complexidade excessiva, supressão indevida de linters ou exceções mal tratadas]. Ajuste necessário antes do merge. |
```
