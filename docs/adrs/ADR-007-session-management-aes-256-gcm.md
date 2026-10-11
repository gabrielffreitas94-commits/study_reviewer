# ADR-007: Gestão de Sessão Stateless com Cookies Criptografados em AES-256-GCM e Suporte a Bearer Tokens

* **Status:** `Proposto` (Aguardando aprovação do usuário)
* **Data:** 2026-10-03
* **Autor:** Especialista Arquiteto
* **Contexto Técnico:** [PRD.md](../../PRD.md) v6.0 (Seção 8 - Sprint 2), [ADR-001](ADR-001-clean-architecture-layering.md) e [ADR-006](ADR-006-google-oauth2-oidc-multitenancy.md)

---

## 1. Contexto e Problema

Com a introdução da autenticação na Sprint 2, a aplicação precisa manter a sessão autenticada do usuário através de requisições HTTP subsequentes, atendendo a dois canais distintos:
1. **Canal Web (Navegador):** Requisições Jinja2 + HTMX via cookies HTTP normais.
2. **Canal API REST / Mobile (Flutter na Sprint 5):** Requisições desacopladas via cabeçalho `Authorization: Bearer <token>`.

### Alternativas Avaliadas:
* **Alternativa A — Sessão Stateful em Banco Relacional / Redis:** Armazenar cada sessão em uma tabela no PostgreSQL ou instância de Redis, enviando apenas um session ID opaco para o cliente.
  * *Problema:* Exige uma consulta ao banco de dados ou conexão com Redis a cada única requisição HTTP feita pelo usuário (navegação de cards, flips de HTMX, etc.), aumentando a latência e gerando custos de infraestrutura no plano gratuito/serverless do Neon PostgreSQL.
* **Alternativa B — JWT Padrão Assinado (HMAC/RSA):** Utilizar JWT assinado (JWS).
  * *Problema:* O payload é apenas codificado em Base64 e pode ser lido por qualquer entidade intermediária. Além disso, bibliotecas genéricas de JWT introduzem complexidade desnecessária e potenciais vetores de ataque conhecidos (ex: algoritmo `none`, confusão de chaves públicas/privadas).
* **Alternativa C — Token Stateless Criptografado com Criptografia Autenticada AES-256-GCM (AEAD):** Cifrar o payload da sessão contendo os dados essenciais de autenticação (`user_id`, `email`, `exp`, `iat`) utilizando o padrão da indústria **AES-256-GCM**.

---

## 2. Decisão Arquitetural

Adotar a **Alternativa C**: Gestão de sessão **Stateless Criptografada com AES-256-GCM (AEAD)**, implementada através do protocolo desacoplado `ISessionTokenService`:

### 2.1 Estrutura e Segurança do Token Cifrado
* **Algoritmo Criptográfico:** `AES-256-GCM` via módulo nativo `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.
  - Criptografia simétrica com chave de 256 bits derivada da variável de ambiente `SECRET_KEY`.
  - Cada token gerado utiliza um vetor de inicialização (*nonce*) criptograficamente seguro e aleatório de 12 bytes (`os.urandom(12)`), garantindo que duas sessões para o mesmo usuário gerem sequências cifradas completamente distintas.
  - A autenticidade e a integridade são garantidas pela *tag de autenticação GCM* de 16 bytes. Qualquer tentativa de adulteração do token resulta em erro imediato de decifração em tempo $\mathcal{O}(1)$.
* **Payload Mínimo (LGPD por Design):**
  ```json
  {
    "user_id": "c1f7a224-b1c4-4b53-a72e-c5e3d7491cf0",
    "email": "estudante@dominio.com",
    "iat": 1790928000,
    "exp": 1793520000
  }
  ```
* **Prazo de Validade:** 30 dias de expiração (`Max-Age = 2.592.000` segundos).

### 2.2 Estratégia de Entrega por Canal
1. **Canal Web (Navegador):**
   * O token cifrado é gravado em um cookie HTTP nomeado `session_token`.
   * Flags obrigatórias de segurança:
     - `HttpOnly`: Impede estritamente o acesso via scripts JavaScript no navegador, neutralizando roubo de sessão via ataques XSS.
     - `SameSite=Lax`: Proteção robusta contra ataques Cross-Site Request Forgery (CSRF).
     - `Secure`: Ativado compulsoriamente em produção (tráfego exclusivo HTTPS).
     - `Path=/`: Escopo global na aplicação.
2. **Canal API REST (Mobile / Headless):**
   * O mesmo token cifrado é emitido no corpo JSON de resposta (`POST /api/v1/auth/google`) e recebido nas requisições pelo cabeçalho `Authorization: Bearer <session_token>`.
3. **Injeção de Dependências FastAPI (`get_current_user`):**
   * A dependência inspeciona primeiramente o cabeçalho `Authorization: Bearer <token>`.
   * Caso ausente, inspeciona o cookie `session_token`.
   * Realiza a decriptação e validação em memória sem tocar no banco de dados.

---

## 3. Consequências

### Impactos Positivos:
* **Performance Máxima $\mathcal{O}(1)$:** Validação de autenticidade instantânea em CPU, eliminando 100% das queries de sessão no PostgreSQL.
* **Escalabilidade Horizontal Zero-State:** A aplicação pode escalar para múltiplas instâncias no Render sem necessidade de sticky sessions ou sincronização de cache de sessão.
* **Segurança Criptográfica Militar:** AES-256-GCM impede tanto a leitura dos dados do token (confidencialidade) quanto a sua falsificação ou adulteração (integridade).
* **Paridade Web e API:** A mesma porta de serviço e a mesma lógica atendem simultaneamente o fluxo de navegação web e o consumo mobile.

### Custos e Mitigações:
* **Tamanho do Cookie:** Tokens cifrados em AES-256-GCM em Base64 URL-safe ocupam aproximadamente 150 a 200 bytes. *Impacto irrelevante frente ao limite de 4.096 bytes dos navegadores.*
* **Invalidação Instantânea no Lado do Servidor:** Como os tokens são stateless, o encerramento de sessão padrão limpa o cookie no cliente. Para cenários de revogação forçada global (ex: suspeita de vazamento de conta), é viável comparar o `iat` com um campo `token_valid_after` na entidade `User` quando estritamente necessário.
