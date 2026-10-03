# ADR-006: Autenticação via Google OAuth2 / OIDC, JIT Provisioning e Isolamento Multi-tenant

* **Status:** `Proposto` (Aguardando aprovação do usuário)
* **Data:** 2026-10-03
* **Autor:** Especialista Arquiteto
* **Contexto Técnico:** [PRD.md](../../PRD.md) v6.0 (Seção 8 - Sprint 2), [ADR-001](ADR-001-clean-architecture-layering.md) e [.gemini/rules/sprint-development-lifecycle.md](../../.gemini/rules/sprint-development-lifecycle.md)

---

## 1. Contexto e Problema

O **Study Reviewer** completou a Sprint 01 operando em modo de usuário único compartilhado. Para que a aplicação evolua de forma segura em ambiente de produção (Render + Neon PostgreSQL) e atenda a múltiplos estudantes simultaneamente, faz-se necessário:
1. **Identificação e Autenticação Confiável:** Prover login seguro sem a complexidade, atrito e vulnerabilidades inerentes ao armazenamento local de senhas (ataques de força bruta, vazamento de hashes, necessidade de fluxos de recuperação de senha por e-mail).
2. **Isolamento de Dados Estrito (Multi-tenancy):** Garantir que matérias, temas, flashcards e sessões de estudo pertençam exclusivamente ao estudante que os criou, impedindo categoricamente qualquer acesso não autorizado ou vazamento de dados entre usuários (vulnerabilidade IDOR — *Insecure Direct Object Reference*).
3. **Desacoplamento Arquitetural:** Suportar tanto a navegação web atual (Jinja2 + HTMX) quanto o futuro aplicativo mobile nativo (Flutter na Sprint 5), permitindo que ambos os canais compartilhem os mesmos casos de uso e contratos de domínio sem replicação de lógica.

---

## 2. Decisão Arquitetural

Adotar a autenticação federada centralizada via **Google OAuth 2.0 / OpenID Connect (OIDC)** com **Just-In-Time (JIT) Provisioning** e isolamento relacional multi-tenant por `owner_id`:

### 2.1 Fluxo de Autenticação OIDC & JIT Provisioning
* A aplicação utiliza os endpoints oficiais do Google Identity Services:
  - Web: Fluxo de código de autorização (`Authorization Code Flow`) com parâmetro de segurança `state` assinado criptograficamente para prevenção contra CSRF.
  - API / Mobile: Recepção direta do `id_token` JWT assinado pelo Google (`POST /api/v1/auth/google`).
* **Just-In-Time (JIT) Provisioning:**
  - Ao validar as credenciais junto ao Google (audiência `client_id`, emissor `accounts.google.com` e assinatura criptográfica), o use case busca o usuário pelo `google_sub` (identificador unívoco e imutável emitido pelo Google).
  - Se o usuário não existir, é criado instantaneamente no banco de dados (`User`), associando `email`, `name` e `avatar_url`.
  - Se o usuário já existir, seus dados mutáveis de perfil (`name`, `avatar_url`) são sincronizados caso tenham sido alterados na conta Google.

### 2.2 Isolamento Multi-tenant Estrito no Domínio e Persistência
* **Entidade `User`:** Adicionada ao núcleo de domínio com identificador UUIDv4 próprio.
* **Titularidade de Recursos:**
  - `Subject` passa a conter o atributo imutável `owner_id: UUID`.
  - `FlashcardPoolSession` passa a conter o atributo `user_id: UUID`.
  - Temas (`Topic`) e Flashcards (`Flashcard`) herdam o isolamento através de sua matéria de origem (`Subject`).
* **Barreira contra IDOR:**
  - Todos os casos de uso de leitura, listagem, mutação e exclusão passam a exigir `user_id: UUID` verificado pela sessão.
  - Todas as queries nos repositórios SQLAlchemy filtram compulsoriamente pelo `owner_id` / `user_id` do usuário requisitante. Tentativas de acessar registros de terceiros retornam `EntityNotFoundError` (status 404), não revelando sequer a existência do registro a invasores.

---

## 3. Consequências

### Impactos Positivos:
* **Segurança Reforçada & Zero Armazenamento de Senhas:** Eliminação completa dos riscos de armazenamento de credenciais, hashing e vazamento de senhas no banco de dados.
* **Atrito Zero para o Estudante:** Login em 1 clique ("Continuar com o Google") sem formulários manuais de cadastro ou verificação de e-mail.
* **Conformidade com a LGPD:** Minimização estrita de dados coletados (`sub`, `email`, `name`, `picture`), sem solicitar permissões invasivas (apenas escopos `openid`, `email` e `profile`).
* **Preparação para o Flutter:** A arquitetura do caso de uso `AuthenticateWithGoogleUseCase` é 100% reutilizável pelo backend da API do aplicativo mobile.

### Custos e Mitigações:
* **Dependência do Provedor Google:** Usuários necessitam de uma conta Google para acessar a aplicação. *Mitigação: Compatível com a imensa maioria dos estudantes universitários e concurseiros que utilizam Gmail e Google Workspace.*
* **Ambiente de Desenvolvimento Local:** Necessidade de mock do provedor Google nos testes automatizados. *Mitigação: Criação da porta abstrata `IGoogleAuthClient` com implementação em memória para os testes de integração e TDD, assegurando 100% de cobertura com execução em milissegundos sem chamadas de rede externas.*
