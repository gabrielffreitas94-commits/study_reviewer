---
name: security-test-enforcer
description: Reviews all features and tests in the sprint, enforces the @pytest.mark.security decorator and mandatory docstrings, and validates compliance via the AST security governance test.
---

# Security Test Enforcer (Skill do Especialista de Segurança)

Esta skill é utilizada pelo **Especialista de Segurança** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é revisar todas as funcionalidades e testes implementados na sprint para garantir que **todo teste relacionado a segurança ou vulnerabilidade possua o decorator `@pytest.mark.security` e uma docstring explicativa obrigatória**, comprovando a conformidade através da execução do meta-teste automatizado de AST.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * Todos os arquivos de teste em `tests/`.
  * Meta-teste de governança de segurança em `tests/governance/test_security_governance.py`.
* **Gatilho de Execução:** Auditoria de PR, em conjunto com o `security-owasp-auditor`.

---

## 2. Checklist Exaustivo de Governança de Testes de Segurança

O Especialista de Segurança executa uma auditoria minuciosa em quatro etapas:

1. **Mapeamento de Funcionalidades com Impacto de Segurança:**
   * O especialista inspeciona o diff de código em busca de rotinas que toquem:
     * Validação e sanitização de inputs de usuários.
     * Controle de acesso, autenticação e autorização (quem pode acessar o quê).
     * Manipulação de identificadores sensíveis ou foreign keys (prevenção de IDOR).
     * Regras contra injeção de dados (SQL, XSS, scripts maliciosos).
     * Tratamento de falhas e proteção de segredos.
   * *Para cada ponto mapeado, deve existir pelo menos um teste automatizado cobrindo a proteção.*

2. **Auditoria do Decorator `@pytest.mark.security`:**
   * Todos os testes que validam cenários de segurança mapeados na etapa 1 estão explicitamente decorados com `@pytest.mark.security`?
   * *Se algum teste avaliar segurança sem o decorator, ele deve ser marcado imediatamente.*

3. **Auditoria da Docstring Explicativa Obrigatória:**
   * Cada teste com o decorator `@pytest.mark.security` possui uma docstring contendo impreterivelmente:
     * `Vulnerabilidade prevenida:` Descrição detalhada da vulnerabilidade, ameaça ou vetor de ataque mitigado (ex: SQL Injection via query string, bypass de autorização horizontal, injeção de tags HTML).
     * `Garantia de segurança:` Descrição técnica precisa de como a asserção garante que o sistema permaneça estritamente seguro e resiliente.
   * A docstring possui pelo menos 30 caracteres e conteúdo substantivo (proibido texto vago como "testa segurança").

4. **Execução e Comprovação do Meta-Teste AST:**
   * O especialista executa o meta-teste via terminal:
     ```bash
     uv run pytest tests/governance/test_security_governance.py -v
     ```
   * O teste inspeciona a AST (Abstract Syntax Tree) de toda a árvore de testes e garante 100% de conformidade, bloqueando o merge caso encontre qualquer função não conforme.

---

## 3. Emissão de Parecer na PR

A skill gera a validação formal a ser inserida na seção de segurança da Pull Request:

### Caso Aprovado:
```markdown
- [x] Todos os testes que validam segurança ou vulnerabilidades foram decorados com `@pytest.mark.security`.
- [x] Todas as docstrings de testes de segurança contêm 'Vulnerabilidade prevenida:' e 'Garantia de segurança:'.
- [x] O meta-teste de AST (`tests/governance/test_security_governance.py`) passou com 100% de sucesso (XX testes de segurança verificados).
```

### Se houver Violação / Bloqueante:
```markdown
| **4** | **Especialista de Segurança** | `[BLOQUEANTE]` | Governança de testes de segurança reprovada: [apontar quais testes de segurança estão sem decorator ou sem docstrings estruturadas, ou falha no meta-teste AST]. Correção obrigatória antes do merge. |
```
