# Matriz de Casos de Uso e Cenários de Borda — Sprint 02
## Módulo: Autenticação & Multi-tenancy com Google (OAuth2 / OIDC)
### Projeto: Study Reviewer

---

## 1. Visão Geral e Escopo da Sprint 02

Esta matriz detalha os requisitos da **Sprint 02** definidos no [PRD.md](../../PRD.md) v6.0, no [ADR-006](../../docs/adrs/ADR-006-google-oauth2-oidc-multitenancy.md), no [ADR-007](../../docs/adrs/ADR-007-session-management-aes-256-gcm.md) e na [SPEC Técnica](../../docs/specs/sprint-02-auth-multitenancy-spec.md).

Cobre a taxonomia completa de Casos de Uso e Cenários de Borda em formato BDD/Gherkin estruturados em 8 categorias inegociáveis, servindo de base para o ciclo de desenvolvimento em TDD estrito (Red-Green-Refactor).

---

## 2. Matriz de Casos de Uso e Cenários de Borda (BDD / Gherkin)

### Categoria 1: Caminho Feliz & Variações Válidas (Happy Path & Valid Variations)

#### UC-S02-01: Autenticação via Google OIDC com Primeiro Acesso (JIT Provisioning)
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / `AuthenticateWithGoogleUseCase`
```gherkin
Cenário: Primeiro login bem-sucedido de estudante via Google (Just-in-Time Provisioning)
  Dado que um usuário autoriza o acesso no Google com sub="google-sub-001", email="maria@exemplo.com", name="Maria Silva", picture="https://lh3.google.com/avatar.jpg"
  E o usuário ainda não está cadastrado na base de dados
  Quando o caso de uso AuthenticateWithGoogle for acionado com o código de autorização válido
  Então uma nova entidade User é criada e persistida com ID único UUIDv4
  E os campos google_sub="google-sub-001", email="maria@exemplo.com", name="Maria Silva" e avatar_url="https://lh3.google.com/avatar.jpg" são registrados
  E a flag is_new_user é retornada como True
  E um token de sessão cifrado com AES-256-GCM contendo user_id e expiração é gerado
```

#### UC-S02-02: Autenticação via Google OIDC com Usuário Já Cadastrado (Sincronização de Perfil)
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / `AuthenticateWithGoogleUseCase`
```gherkin
Cenário: Login de estudante recorrente com sincronização de foto de perfil
  Dado que existe um usuário pré-cadastrado com google_sub="google-sub-001", name="Maria Silva" e avatar_url="https://antigo.url/foto.jpg"
  Quando o usuário efetuar login e o Google retornar name="Maria Silva" e picture="https://novo.url/foto_nova.jpg"
  Então o usuário existente é localizado sem criar novo registro
  E o campo avatar_url é atualizado para "https://novo.url/foto_nova.jpg"
  E a flag is_new_user é retornada como False
  E uma nova sessão autenticada válida é emitida
```

#### UC-S02-03: Navegação de Estudo Autenticada com Cookie Válido
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Adaptador Web / Middleware de Segurança
```gherkin
Cenário: Acesso autenticado a página privada de flashcards
  Dado que o usuário possui um cookie "session_token" válido cifrado com AES-256-GCM
  Quando o usuário requisitar a rota GET "/flashcards/study"
  Então o middleware get_current_user decifra o token com sucesso
  E injeta a entidade User no contexto da requisição
  E a página de estudos é renderizada com as matérias e progresso exclusivos deste usuário
```

#### UC-S02-04: Autenticação via API REST com id_token (Suporte Flutter / Mobile)
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Adaptador API REST / `POST /api/v1/auth/google`
```gherkin
Cenário: Autenticação de cliente mobile via id_token
  Dado que um aplicativo mobile envia um payload JSON {"id_token": "valid-jwt-token"}
  Quando o endpoint POST "/api/v1/auth/google" for requisitado
  Então a assinatura do id_token é validada pela porta IGoogleAuthClient
  E o usuário é autenticado ou provisionado
  E a resposta HTTP 200 retorna {"access_token": "aes-gcm-token", "token_type": "bearer", "user": {...}}
```

#### UC-S02-05: Encerramento de Sessão (Logout) com Limpeza de Cookie
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Adaptador Web / `POST /auth/logout`
```gherkin
Cenário: Logout voluntário do estudante
  Dado que o usuário está logado com cookie de sessão ativo
  Quando for enviado um POST para "/auth/logout"
  Então a resposta HTTP 302 redireciona para "/auth/login"
  E o cabeçalho Set-Cookie instrui a expiração imediata do cookie "session_token" (Max-Age=0)
```

---

### Categoria 2: Cenários de Borda & Limites Matemáticos (Edge Cases & Boundary Values)

#### UC-S02-06: Sessão no Limite Exato de Expiração (Último Segundo Válido)
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Aplicação / `ISessionTokenService`
```gherkin
Cenário: Sessão avaliada exatamente no instante exp - 1
  Dado que um token de sessão possui expiração no timestamp T_EXP
  Quando o token for validado no instante T_EXP - 1 segundo
  Então a validação é bem-sucedida
  E os dados do payload são retornados íntegros
```

#### UC-S02-07: Sessão Expirada por 1 Segundo (Rejeição Imediata)
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Aplicação / `ISessionTokenService`
```gherkin
Cenário: Sessão avaliada exatamente 1 segundo após o vencimento
  Dado que um token de sessão possuía expiração no timestamp T_EXP
  Quando o token for validado no instante T_EXP + 1 segundo
  Então a validação falha
  E o serviço retorna None ou lança UnauthorizedError
```

#### UC-S02-08: Skew Temporal na Validação de Token OIDC (Tolerância de 30s)
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Infraestrutura / `GoogleOAuthClient`
```gherkin
Cenário: Pequena discrepância de relógio entre os servidores
  Dado que o token OIDC do Google possui carimbo de emissão (iat) 10 segundos à frente do relógio local
  Quando o validador inspecionar o token aplicando margem de tolerância (clock skew) de 30 segundos
  Então o token é aceito normalmente sem falso positivo de rejeição
```

#### UC-S02-09: Usuário com Nome no Limite Máximo de Caracteres (150 caracteres)
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Domínio / `User`
```gherkin
Cenário: Nome com exatamente 150 caracteres
  Dado que o Google retorna um nome com exatamente 150 caracteres válidos
  Quando a entidade User for instanciada
  Então o nome é aceito e armazenado sem truncamento ou erro de validação
```

#### UC-S02-10: Usuário sem Imagem de Avatar no Google (picture ausente)
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Domínio / `User`
```gherkin
Cenário: Cadastro de usuário sem foto na conta Google
  Dado que as claims do Google trazem picture como None ou ausente
  Quando o usuário for provisionado
  Então o campo avatar_url é armazenado como None
  E a interface web renderiza o avatar padrão com as iniciais do nome do estudante
```

---

### Categoria 3: Validação de Entrada & Rejeição de Payloads (Input & Schema Validation)

#### UC-S02-11: Callback sem Parâmetro code ou com Código Vazio
* **Categoria:** Validação de Entrada
* **Camada Alvo:** Adaptador Web / `GET /auth/callback`
```gherkin
Cenário: Tentativa de acessar callback sem código de autorização
  Dado que uma requisição GET "/auth/callback?state=xyz" é recebida sem o parâmetro "code"
  Quando o controlador processar a requisição
  Então a requisição é rejeitada com erro amigável
  E o usuário é redirecionado para "/auth/login?error=missing_code" sem emissão de sessão
```

#### UC-S02-12: Callback com Parâmetro state Ausente ou Corrompido
* **Categoria:** Validação de Entrada / Segurança
* **Camada Alvo:** Adaptador Web / `GET /auth/callback`
```gherkin
Cenário: Acesso ao callback sem parâmetro state
  Dado que uma requisição chega com "code=123", mas sem o parâmetro "state"
  Quando o controlador validar os parâmetros
  Então a requisição é bloqueada por violação de protocolo CSRF
  E nenhuma chamada ao Google é efetuada
```

#### UC-S02-13: Ataque CSRF no Fluxo OAuth com State Divergente do Cookie
* **Categoria:** Validação de Entrada / Segurança
* **Camada Alvo:** Adaptador Web / Proteção Anti-CSRF
```gherkin
Cenário: State retornado não confere com o cookie temporário oauth_state
  Dado que o cookie temporário contém oauth_state="token-legitimo-123"
  Quando o atacante submeter o callback com "?state=token-forjado-999"
  Então a validação de igualdade constante de tempo (constant-time compare) falha
  E a requisição é abortada com HTTP 400 Bad Request ("Parâmetro de segurança state inválido")
```

#### UC-S02-14: Token de Sessão Criptografado com Formato Inválido ou Truncado
* **Categoria:** Validação de Entrada
* **Camada Alvo:** Aplicação / `ISessionTokenService`
```gherkin
Cenário: Decodificação de token malformado
  Dado que uma requisição envia o cookie session_token="string-aleatoria-nao-base64"
  Quando o serviço tentar decifrar o token
  Então o erro de formato é capturado com segurança
  E a sessão é tratada como inexistente/anônima sem propagar 500 para o cliente
```

#### UC-S02-15: Provedor Google Retorna E-mail Inválido ou Vazio
* **Categoria:** Validação de Entrada
* **Camada Alvo:** Domínio / `User`
```gherkin
Cenário: Resposta do Google com formato de e-mail inválido
  Dado que as claims retornadas pelo Google contêm email="invalido@@com"
  Quando o caso de uso tentar instanciar a entidade User
  Então a validação de domínio lança InvalidEmailError
  E o provisionamento é cancelado antes de tocar no banco de dados
```

---

### Categoria 4: Invariantes de Domínio & Multi-tenancy IDOR (Business Rules & Domain Invariants)

#### UC-S02-16: Isolamento Multi-tenant na Listagem de Matérias
* **Categoria:** Invariantes de Domínio / Multi-tenancy
* **Camada Alvo:** Aplicação / `ListSubjectsUseCase`
```gherkin
Cenário: Usuário lista apenas suas próprias matérias
  Dado que o Usuário A possui as matérias ["Direito Constitucional", "Direito Administrativo"]
  E o Usuário B possui a matéria ["Bioquímica"]
  Quando o Usuário A executar ListSubjects
  Então o resultado retorna exclusivamente ["Direito Constitucional", "Direito Administrativo"]
  E nenhuma matéria do Usuário B é vazada na consulta
```

#### UC-S02-17: Tentativa de Acesso Direto a Matéria de Outro Usuário via IDOR (Retorno 404 Estrito)
* **Categoria:** Invariantes de Domínio / Segurança
* **Camada Alvo:** Aplicação / Repositório
```gherkin
Cenário: Usuário A tenta acessar matéria criada pelo Usuário B via URL direta
  Dado que o Usuário B é proprietário da matéria com ID "sub-B-uuid"
  Quando o Usuário A autenticado tentar acessar "/subjects/sub-B-uuid"
  Então o repositório filtra por subject_id="sub-B-uuid" AND owner_id=UsuarioA.id
  E como nenhum registro é retornado, o sistema emite EntityNotFoundError (HTTP 404)
  E o Usuário A não descobre se o ID existe ou não
```

#### UC-S02-18: Tentativa de Criação de Tópico Vinculado a Matéria de Outro Usuário
* **Categoria:** Invariantes de Domínio / Segurança
* **Camada Alvo:** Aplicação / `CreateTopicUseCase`
```gherkin
Cenário: Usuário A tenta injetar um tema dentro da matéria do Usuário B
  Dado que existe uma matéria "sub-B" pertencente ao Usuário B
  Quando o Usuário A tentar executar CreateTopic informando subject_id="sub-B"
  Então o caso de uso verifica a titularidade da matéria para o owner_id do Usuário A
  E ao detectar que a matéria não pertence ao Usuário A, lança ResourceOwnershipError
  E nenhum tópico é persistido
```

#### UC-S02-19: Unicidade de Nome de Matéria Escopada por Usuário
* **Categoria:** Invariantes de Domínio / Multi-tenancy
* **Camada Alvo:** Aplicação / Repositório
```gherkin
Cenário: Dois usuários cadastram matérias com o mesmo nome
  Dado que o Usuário A já possui uma matéria chamada "Português"
  Quando o Usuário B tentar cadastrar uma matéria também chamada "Português"
  Então a operação é concluída com sucesso para o Usuário B
  E a restrição de unicidade não causa conflito, pois o índice é composto por (owner_id, name)
```

#### UC-S02-20: Isolamento de Sessão de Estudo da Pool entre Dois Usuários Simultâneos
* **Categoria:** Invariantes de Domínio / Multi-tenancy
* **Camada Alvo:** Domínio / Aplicação
```gherkin
Cenário: Sessões independentes para a mesma matéria conceitual
  Dado que Usuário A está na Rodada 3 (card posição 500)
  E Usuário B está na Rodada 1 (card posição 100)
  Quando Usuário A avançar para o próximo card
  Então apenas a FlashcardPoolSession do Usuário A é atualizada
  E a posição e rodada do Usuário B permanecem rigorosamente inalteradas
```

---

### Categoria 5: Ciclo de Vida, Histórico e Transições de Estado (State Lifecycle & Historical Traceability)

#### UC-S02-21: Acesso a Rota Privada sem Sessão com Redirecionamento e Preservação de next
* **Categoria:** Transições de Estado
* **Camada Alvo:** Adaptador Web / Middleware
```gherkin
Cenário: Usuário não autenticado tenta acessar o painel de estudos
  Dado que o navegador não possui o cookie "session_token"
  Quando for feita uma requisição GET para "/flashcards/study"
  Então o middleware intercepta a requisição
  E redireciona (HTTP 302) para "/auth/login?next=%2Fflashcards%2Fstudy"
```

#### UC-S02-22: Retorno para a Rota de Destino next após Autenticação Bem-sucedida
* **Categoria:** Transições de Estado
* **Camada Alvo:** Adaptador Web / Callback
```gherkin
Cenário: Redirecionamento amigável pós-login
  Dado que o estudante iniciou o fluxo OAuth com next="/subjects/nova"
  Quando a autenticação no Google for concluída com sucesso
  Então a resposta final redireciona o navegador diretamente para "/subjects/nova"
```

#### UC-S02-23: Tentativa de Navegação após Sessão Encerrada por Logout
* **Categoria:** Transições de Estado
* **Camada Alvo:** Adaptador Web / Middleware
```gherkin
Cenário: Navegação logo após ter efetuado logout
  Dado que o usuário acionou o logout e teve o cookie de sessão removido
  Quando ele tentar clicar em "Próximo Card" via HTMX
  Então o middleware identifica ausência de sessão
  E responde com o cabeçalho "HX-Redirect: /auth/login"
  E a interface do navegador é redirecionada para a tela de login
```

---

### Categoria 6: Concorrência & Idempotência (Concurrency & Idempotency)

#### UC-S02-24: Duplo Callback OAuth Concorrente para o Mesmo Usuário
* **Categoria:** Concorrência & Idempotência
* **Camada Alvo:** Aplicação / Persistência
```gherkin
Cenário: Disparo de duas requisições simultâneas de callback com o mesmo google_sub
  Dado que duas threads processam simultaneamente o login do mesmo usuário novo
  Quando ambas executarem o JIT Provisioning concorrentemente
  Então o índice único em "google_sub" previne a duplicação
  E a transação concorrente trata a integridade, garantindo exatamente 1 registro de User
  E ambas as requisições emitem tokens de sessão válidos para o mesmo usuário
```

#### UC-S02-25: Múltiplas Requisições Simultâneas de Estudo na Mesma Sessão do Usuário
* **Categoria:** Concorrência & Idempotência
* **Camada Alvo:** Aplicação / `GetNextFlashcardUseCase`
```gherkin
Cenário: Cliques rápidos consecutivos no botão "Avançar"
  Dado que o usuário dispara duas requisições com 10ms de diferença
  Quando o use case processar as requisições
  Então as transações de banco atualizam a FlashcardPoolSession atomicamente
  E o estado da rodada permanece íntegro sem pular posições desordenadamente
```

---

### Categoria 7: Busca & Filtros Multi-tenant (Search & Filtering Invariants)

#### UC-S02-26: Contagem e Pool Global de Flashcards Restrita Estritamente ao Usuário Ativo
* **Categoria:** Busca & Filtros
* **Camada Alvo:** Aplicação / `IFlashcardRepository`
```gherkin
Cenário: Contagem total de cards da pool no dashboard
  Dado que o banco contém 500 cards do Usuário A e 300 cards do Usuário B
  Quando a aplicação consultar count_pool_by_owner para o Usuário B
  Então o resultado retornado é exatamente 300
  E os 500 cards do Usuário A são completamente ignorados
```

#### UC-S02-27: Filtro por Matéria com Validação de Propriedade
* **Categoria:** Busca & Filtros
* **Camada Alvo:** Aplicação / Repositório
```gherkin
Cenário: Filtrar flashcards por tema pertencente a outro usuário
  Dado que o Tema 99 pertence ao Usuário A
  Quando o Usuário B tentar filtrar a pool informando topic_id=99
  Então a busca retorna lista vazia ou lança ResourceOwnershipError
  E nenhum flashcard do Usuário A é exposto
```

---

### Categoria 8: Tratamento de Falhas e Segurança (Error Handling, Resilience & Security)

#### UC-S02-28: Indisponibilidade dos Serviços Google (HTTP 5xx / Timeout)
* **Categoria:** Tratamento de Falhas & Resiliência
* **Camada Alvo:** Adaptador Web / Cliente Google
```gherkin
Cenário: Falha de comunicação ou timeout com a API do Google
  Dado que a API do Google retorna HTTP 503 Service Unavailable durante a troca de código
  Quando o callback interceptar a exceção de rede
  Então a falha é registrada nos logs estruturados com correlation_id
  E o usuário recebe uma página de erro clara: "Não foi possível conectar ao Google. Tente novamente em instantes."
  E nenhum detalhe interno de infraestrutura ou stacktrace é vazado
```

#### UC-S02-29: Cookie de Sessão com Tag de Autenticação GCM Adulterada (Ataque de Modificação de Bits)
* **Categoria:** Segurança / Criptografia
* **Camada Alvo:** Aplicação / `AesGcmSessionTokenService`
```gherkin
Cenário: Tentativa de manipulação maliciosa do cookie cifrado (Bit-Flipping Attack)
  Dado que um atacante altera 1 único bit do payload criptografado do cookie session_token
  Quando o serviço AesGcmSessionTokenService tentar decifrar com a tag GCM
  Então a verificação de integridade AEAD falha instantaneamente
  E a decifração é rejeitada com InvalidSessionTokenError
  E o acesso é sumariamente bloqueado como não-autorizado
```

#### UC-S02-30: Rota Privada Acessada via HTMX sem Sessão (Header HX-Redirect)
* **Categoria:** Segurança / UX
* **Camada Alvo:** Adaptador Web / Middleware
```gherkin
Cenário: Requisição parcial HTMX disparada com sessão expirada
  Dado que o navegador dispara um POST HTMX (cabeçalho HX-Request: "true") sem cookie válido
  Quando o middleware de autenticação interceptar a requisição
  Então a resposta HTTP 200/401 inclui o cabeçalho "HX-Redirect: /auth/login"
  E o cliente HTMX força o redirecionamento completo da janela do navegador para o login
```

---

## 3. Matriz de Rastreabilidade de Segurança (@pytest.mark.security)

Para atender à governança de segurança do projeto e ao meta-teste de AST (`tests/governance/test_security_governance.py`), todos os testes vinculados aos cenários de segurança abaixo conterão docstring estruturada obrigatória:

| Caso de Uso | Cenário Testado | Vulnerabilidade Prevenida | Garantia de Segurança |
| :--- | :--- | :--- | :--- |
| **UC-S02-12 / 13** | Validação de State no Callback OAuth | Cross-Site Request Forgery (CSRF) no fluxo de login | Comparação constante de tempo do parâmetro `state` contra cookie assinado. |
| **UC-S02-14 / 29** | Adulteração do Token AES-256-GCM | Falsificação de Sessão, Privilege Escalation e Bit-Flipping | Criptografia autenticada AEAD rejeita qualquer payload sem tag GCM válida. |
| **UC-S02-16 / 17** | Acesso a Matéria de Terceiro | Insecure Direct Object Reference (IDOR) | Cláusulas de query forçam compulsoriamente `owner_id == user_id` retornando 404 estrito. |
| **UC-S02-18** | Injeção de Tópico em Matéria Alheia | Quebra de Integridade Referencial Multi-tenant | Validação prévia de titularidade no caso de uso bloqueia persistência indevida. |

---

### 🛡️ Validação Técnica de QA (qa-use-cases-validator)
* **Status:** `[APROVADO PARA TDD]`
* **Data da Auditoria:** 2026-10-03
* **Auditor:** Especialista QA (Persona #2)
* **Parecer Técnico:** A matriz com **30 casos de uso** foi auditada integralmente. Todas as 8 categorias obrigatórias foram cobertas com critérios determinísticos, entradas explícitas, invariantes de isolamento multi-tenant e asserções testáveis. As regras de governança de segurança contra CSRF, IDOR e integridade criptográfica AES-256-GCM foram minuciosamente mapeadas. O ciclo de desenvolvimento TDD está formalmente liberado para início.
