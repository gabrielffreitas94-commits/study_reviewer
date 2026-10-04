# ADR-006: Autenticação via Google OAuth2 / OIDC, JIT Provisioning, Isolamento Multi-tenant e Compartilhamento Read-Only

* **Status:** `Proposto` (Aguardando aprovação do usuário)
* **Data:** 2026-10-03
* **Autor:** Especialista Arquiteto
* **Contexto Técnico:** [PRD.md](../../PRD.md) v6.0 (Seção 8 - Sprint 2), [ADR-001](ADR-001-clean-architecture-layering.md) e [.gemini/rules/sprint-development-lifecycle.md](../../.gemini/rules/sprint-development-lifecycle.md)

---

## 1. Contexto e Problema

O **Study Reviewer** completou a Sprint 01 operando em modo de usuário único compartilhado. Para que a aplicação evolua de forma segura em ambiente de produção (Render + Neon PostgreSQL) e atenda a múltiplos estudantes simultaneamente, faz-se necessário:
1. **Identificação e Autenticação Confiável:** Prover login seguro sem a complexidade, atrito e vulnerabilidades inerentes ao armazenamento local de senhas (ataques de força bruta, vazamento de hashes, necessidade de fluxos de recuperação de senha por e-mail).
2. **Isolamento de Dados Estrito (Multi-tenancy):** Garantir que matérias, temas, flashcards e sessões de estudo pertençam ao estudante que os criou, impedindo categoricamente qualquer acesso não autorizado ou vazamento de dados entre usuários (vulnerabilidade IDOR — *Insecure Direct Object Reference*).
3. **Compartilhamento de Conteúdo sem Conflito de Edição:** Permitir que estudantes compartilhem seus decks de matérias com colegas ou que um mentor/professor disponibilize matérias para estudo, sem que usuários secundários possam alterar ou corromper as perguntas e respostas originais.
4. **Desacoplamento Arquitetural:** Suportar tanto a navegação web atual (Jinja2 + HTMX) quanto o futuro aplicativo mobile nativo (Flutter na Sprint 5), permitindo que ambos os canais compartilhem os mesmos casos de uso e contratos de domínio sem replicação de lógica.

---

## 2. Decisão Arquitetural

Adotar a autenticação federada centralizada via **Google OAuth 2.0 / OpenID Connect (OIDC)** com **Just-In-Time (JIT) Provisioning**, isolamento relacional multi-tenant por `owner_id` e modelo de **Compartilhamento Read-Only por Padrão**:

### 2.1 Fluxo de Autenticação OIDC & JIT Provisioning
* A aplicação utiliza os endpoints oficiais do Google Identity Services:
  - Web: Fluxo de código de autorização (`Authorization Code Flow`) com parâmetro de segurança `state` assinado criptograficamente para prevenção contra CSRF.
  - API / Mobile: Recepção direta do `id_token` JWT assinado pelo Google (`POST /api/v1/auth/google`).
* **Just-In-Time (JIT) Provisioning:**
  - Ao validar as credenciais junto ao Google (audiência `client_id`, emissor `accounts.google.com` e assinatura criptográfica), o use case busca o usuário pelo `google_sub` (identificador unívoco e imutável emitido pelo Google).
  - Se o usuário não existir, é criado instantaneamente no banco de dados (`User`), associando `email`, `name` e `avatar_url`.
  - Se o usuário já existir, seus dados mutáveis de perfil (`name`, `avatar_url`) são sincronizados caso tenham sido alterados na conta Google.

### 2.2 Isolamento Multi-tenant e Titularidade de Recursos
* **Entidade `User`:** Adicionada ao núcleo de domínio com identificador UUIDv4 próprio.
* **Titularidade de Recursos:**
  - `Subject` passa a conter o atributo imutável `owner_id: UUID` e a flag `is_public: bool = False`.
  - `FlashcardPoolSession` passa a conter o atributo `user_id: UUID`.
  - Temas (`Topic`) e Flashcards (`Flashcard`) herdam o isolamento através de sua matéria de origem (`Subject`).

### 2.3 Modelo de Compartilhamento Read-Only & Governança de Alterações
Para viabilizar o estudo colaborativo mantendo integridade pedagógica e eliminando conflitos de concorrência:
1. **Regra de Mutação (Write - Apenas Owner):**
   * Apenas o criador original (`current_user.id == subject.owner_id`) tem permissão de:
     - Editar o nome da matéria ou alternar sua visibilidade pública (`is_public`).
     - Criar, editar ou excluir temas (`Topic`).
     - Criar, editar ou excluir flashcards (`Flashcard`).
     - Excluir a matéria completa.
   * Tentativas de mutação por usuários que não sejam o proprietário são sumariamente bloqueadas com `ResourceOwnershipError` (HTTP 403 Forbidden).
2. **Regra de Leitura e Estudo (Read-Only para Assinantes/Público):**
   * Qualquer usuário autenticado tem permissão para visualizar e estudar matérias onde:
     - Ele é o dono (`subject.owner_id == current_user.id`), **OU**
     - A matéria foi marcada como pública/compartilhada (`subject.is_public == True`).
3. **Isolamento de Progresso de Estudo (Sessão 100% Individual):**
   * Mesmo quando 50 estudantes estão estudando a mesma matéria pública em modo Read-Only, **cada estudante possui sua própria `FlashcardPoolSession`** (`user_id = current_user.id`).
   * A posição na rodada (`current_position`), o contador de rodadas e o shuffle de cards operam de forma 100% isolada e assíncrona por estudante, garantindo que um aluno não interfira no ritmo do outro.

### 2.4 Roadmap Estratégico de Colaboração Avançada (Fase Pré-IA)
Decidido formalmente adiar para as **Sprints Pré-IA (Sprints 6 e 7)** a análise e eventual implementação de:
* **Clonagem / Fork de Matérias:** Permitir que um estudante faça uma cópia independente de uma matéria Read-Only para a sua conta, podendo editá-la livremente.
* **Colaboração com Múltiplos Editores (Workspaces):** Gestão de grupos de estudo com papéis granulares de `Editor` e `Viewer`.
* **Transferência de Propriedade (Ownership Transfer):** Permitir a um usuário passar a titularidade de uma matéria e seus cards para outro estudante.

---

## 3. Consequências

### Impactos Positivos:
* **Segurança Reforçada & Zero Armazenamento de Senhas:** Eliminação completa dos riscos de armazenamento de credenciais, hashing e vazamento de senhas no banco de dados.
* **Atrito Zero para o Estudante:** Login em 1 clique ("Continuar com o Google") sem formulários manuais de cadastro ou verificação de e-mail.
* **Compartilhamento Seguro sem Conflitos:** Permite a circulação de matérias e decks de estudo entre colegas ou professores sem o risco de edições indesejadas, desconfiguração de cards ou corridas de concorrência.
* **Progresso Cognitivo Individual Preservado:** A separação estrita entre conteúdo mestre e sessão da pool garante foco e consistência pedagógica.
* **Conformidade com a LGPD:** Minimização estrita de dados coletados (`sub`, `email`, `name`, `picture`), sem solicitar permissões invasivas (apenas escopos `openid`, `email` e `profile`).

### Custos e Mitigações:
* **Dependência do Provedor Google:** Usuários necessitam de uma conta Google para acessar a aplicação. *Mitigação: Compatível com a imensa maioria dos estudantes universitários e concurseiros que utilizam Gmail e Google Workspace.*
* **Ambiente de Desenvolvimento Local:** Necessidade de mock do provedor Google nos testes automatizados. *Mitigação: Criação da porta abstrata `IGoogleAuthClient` com implementação em memória para os testes de integração e TDD, assegurando 100% de cobertura com execução em milissegundos sem chamadas de rede externas.*
