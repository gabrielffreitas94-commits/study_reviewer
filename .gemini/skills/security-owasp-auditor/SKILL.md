---
name: security-owasp-auditor
description: Audits pull request diff against staging for OWASP Top 10 vulnerabilities, input sanitization, injection flaws, access control, and secrets exposure.
---

# Security OWASP Auditor (Skill do Especialista de Segurança)

Esta skill é utilizada pelo **Especialista de Segurança** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é realizar uma análise rigorosa e aprofundada de segurança no código, inspecionando o diff contra a branch `staging` para mitigar vulnerabilidades baseadas no **OWASP Top 10**, no **CWE (Common Weakness Enumeration)** e nas melhores práticas de segurança defensiva.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * Definições de rotas HTTP, controladores, adaptadores de repositório e templates.
  * Arquivos de configuração, variáveis de ambiente e `.env.example`.
* **Gatilho de Execução:** Fase de auditoria de PR, após testes unitários e de integração concluídos.

---

## 2. Checklist Exaustivo de Auditoria OWASP & Defensiva

O Especialista de Segurança analisa o código com foco em dez áreas críticas de proteção:

1. **A01: Quebra de Controle de Acesso (Broken Access Control & IDOR):**
   * *O sistema valida a propriedade do recurso em todas as requisições?*
   * Garantia de que um usuário não pode acessar, mutar ou excluir recursos pertencentes a outro usuário alterando IDs na rota ou payload (Insecure Direct Object Reference).
   * Verificação de que rotas administrativas ou de escrita exigem permissões explícitas.

2. **A02: Falhas Criptográficas & Proteção de Dados Sensíveis:**
   * Nenhum dado confidencial, senha, token ou credencial é trafegado sem criptografia ou exposto em URLs de requisição (`query params`).
   * Senhas e segredos usam algoritmos modernos de hashing derivativo (ex: Argon2id, Bcrypt) com salt automático.
   * Dados sensíveis são mascarados ou omitidos em logs e mensagens de erro retornadas à interface.

3. **A03: Blindagem contra Injeções (Injection Flaws - SQLi, Command, SSTI):**
   * **SQL Injection:** Todas as operações com banco de dados utilizam estritamente queries parametrizadas (ORM / SQLAlchemy com *bound parameters*). Proibição total de interpolação direta de strings (`f"SELECT ... {input}"` ou `%s`).
   * **Command Injection:** Proibição de chamadas diretas a shell (`os.system`, `subprocess` com `shell=True`) com parâmetros fornecidos pelo usuário.
   * **Cross-Site Scripting (XSS) e SSTI:** Templates HTML escapam variáveis por padrão. Dados inseridos via HTMX ou JavaScript são devidamente sanitizados contra injeção de tags `<script>` ou eventos inline (`onerror=`).

4. **A04: Design Inseguro e Validação na Borda (Insecure Design):**
   * Todas as requisições externas são validadas na borda por schemas estritos (ex: Pydantic), aplicando tipagem, limites de comprimento e rejeição de payloads com campos desconhecidos.
   * Presença de proteção contra abusos (ex: rate limiting ou travas contra força bruta em ações críticas).

5. **A05: Configurações Seguras e Vazamento de Segredos (Security Misconfiguration):**
   * O git diff é inspecionado linha por linha para garantir que nenhum segredo real (API keys, senhas de banco, chaves privadas) foi adicionado ao versionamento.
   * O arquivo `.env.example` está atualizado sem expor valores reais de produção.
   * Cabeçalhos de segurança HTTP recomendados (ex: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`).

6. **A06: Componentes Desatualizados e Dependências:**
   * Novas dependências adicionadas ao `pyproject.toml` ou `package.json` são analisadas quanto à confiabilidade e ausência de CVEs conhecidas.

7. **A07: Identificação e Gestão Segura de Sessão:**
   * Cookies de autenticação utilizam atributos defensivos: `HttpOnly`, `SameSite=Lax` ou `Strict`, e `Secure` (em produção).
   * Invalidação completa de tokens e sessões no logout.

8. **A08: Integridade de Software e Dados:**
   * Proibição de desserialização insegura de dados externos (ex: `pickle.loads` em payloads de rede).

9. **A09: Logs de Auditoria e Monitoramento de Segurança:**
   * Eventos de segurança (ex: falhas consecutivas de login, tentativas de acesso a recursos não autorizados, violações de integridade) geram logs estruturados de auditoria, sem registrar senhas ou dados sensíveis.

10. **A10: Falsificação de Requisições do Lado do Servidor (SSRF):**
    * Se o sistema realizar requisições externas para URLs fornecidas por usuários, há validação contra faixas de IP privadas (RFC 1918), `localhost` e serviços internos de metadados de nuvem.

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **4** | **Especialista de Segurança** | `[APROVADO]` | Código auditado contra OWASP Top 10 com sucesso. Proteção completa contra SQLi (queries 100% parametrizadas), XSS/IDOR prevenidos, validação estrita de schemas na borda e zero segredos expostos no diff contra staging. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **4** | **Especialista de Segurança** | `[BLOQUEANTE]` | Vulnerabilidade de segurança identificada: [descrever a brecha de injeção, controle de acesso, exposição de segredos ou ausência de sanitização]. Correção obrigatória e imediata antes do merge. |
```
