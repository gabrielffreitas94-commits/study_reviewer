# ADR-010: Autenticação Local Offline e Arquitetura de Workspace Autossuficiente

* **Status:** `Aceito`
* **Data:** 2026-11-19
* **Autor:** Equipe de Arquitetura — Study Reviewer
* **Contexto Técnico:** [PRD.md](../../PRD.md), [ADR-001](ADR-001-clean-architecture-layering.md), [ADR-007](ADR-007-session-management-aes-256-gcm.md), [ADR-009](ADR-009-audit-logs-and-historical-retention.md)

---

## 1. Contexto

Nas iterações anteriores do **Study Reviewer**, a autenticação de usuários dependia de Google OAuth 2.0 / OIDC, o estudo dissertativo era acoplado a chamadas remotas para avaliação por inteligência artificial (Gemini), embeddings vetoriais (RAG), gravação de áudio e fluxo de disputa multiagente, e o frontend carregava fontes e scripts de CDNs externas (`fonts.googleapis.com`, `unpkg.com`).

Esse modelo impunha dependências externas obrigatórias para execução:
1. Impossibilidade de operar em modo 100% local e offline sem credenciais de nuvem, chaves de API externas ou acesso à internet.
2. Complexidade operacional desnecessária (client IDs OAuth, billing de tokens, serviços externos) para um workspace individual ou de estudo local.
3. Risco de indisponibilidade de interface e vazamento de metadados de rede ao carregar assets de terceiros via CDN.

Para consolidar o produto como um workspace educacional autossuficiente, privado e executável integralmente em máquina local, tornou-se necessário substituir a dependência de OAuth/IA/nuvem por autenticação local, autoavaliação estruturada e empacotamento estático completo dos assets.

---

## 2. Decisão

Adota-se uma arquitetura 100% local e offline estruturada em quatro pilares:

### 2.1 Autenticação Local de Workspace com Credenciais Próprias
* Substitui-se o fluxo Google OAuth2/OIDC por registro e login locais baseados em identificador/e-mail e senha armazenada exclusivamente em formato de hash criptográfico seguro com salt aleatório.
* A gestão de sessão mantém o protocolo stateless cifrado com **AES-256-GCM** ([ADR-007](ADR-007-session-management-aes-256-gcm.md)), emitido em cookies `HttpOnly` / `SameSite=Lax` para a interface Web e em Bearer Tokens para a API REST.
* A operação em desenvolvimento e uso pessoal suporta inicialização rápida com dados de demonstração via `python -m scripts.seed_demo`.

### 2.2 Persistência Local e Independência de Nuvem
* **Banco de Dados:** SQLite como padrão imediato local (`sqlite:///./study_reviewer.db`), mantendo compatibilidade com PostgreSQL local via SQLAlchemy e Alembic.
* **Cache de Sessão / Pool:** Suporte opcional a Redis local com fallback em memória (`fakeredis` / repositório em memória), sem dependência de serviços gerenciados em nuvem (AWS, Neon ou equivalentes).

### 2.3 Fluxo de Estudo Ativo e Autoavaliação Determinística (Zero IA)
* **Flashcards:** Mantém a Pool Contínua com Gap Indexing (múltiplos de 100), flip 3D client-side e atalhos de teclado.
* **Perguntas Abertas (SRS):** Mantém os intervalos determinísticos `[1, 7, 15, 30, 60, 90, 180]` dias com regressão no Nível 6 em caso de nota `< 100%`. O estudante escolhe entre:
  * **Responder por Escrito (`WRITTEN_SELF_REVIEW`):** redige sua resposta localmente, revela o gabarito para comparação lado a lado e atribui sua nota (0–100%).
  * **Gabarito Direto (`MANUAL`):** realiza recordação mental, revela o gabarito e atribui sua nota (0–100%) ou usa os 4 botões SRS no Tomo do Nó (`again`, `hard`, `good`, `easy`).
* **Biblioteca de Materiais:** Armazena textos e extrai conteúdo localmente de arquivos `.pdf`, `.docx`, `.txt` e `.md` via `pypdf` e `python-docx`, sem embeddings ou chamadas externas.

### 2.4 Assets 100% Locais e Soberania de Privacidade
* Remoção integral de links de CDNs externas (Google Fonts e `unpkg.com`), servindo `htmx.min.js`, `tailwind.css`, `app.css`, `study.js`, `study_canvas.js` e `rpg_icons.js` diretamente de `src/adapters/web/static/`.
* Conformidade LGPD preservada com exportação local em JSON/CSV e exclusão/anonimização de conta diretamente na instância local.

---

## 3. Consequências

### Positivas:
* **Execução 100% Offline:** A aplicação inicia e opera integralmente sem conexão à internet, chaves de API externas ou contas de provedores de nuvem.
* **Setup Simplificado:** Um único comando com SQLite padrão permite subir o workspace completo em segundos.
* **Privacidade Integral:** Nenhum conteúdo de estudo, resposta escrita ou dado pessoal trafega para serviços externos.
* **Preservação da Clean Architecture:** As camadas de Domínio e Aplicação permanecem desacopladas de frameworks e infraestrutura ([ADR-001](ADR-001-clean-architecture-layering.md)).

### Negativas / Mitigações:
* **Ausência de Correção Semântica Automática:** O estudante realiza autoavaliação comparando sua resposta escrita ou mental com o gabarito oficial. *Mitigação:* Fluxo explícito de rascunho escrito + revelação de gabarito + escala de 0–100% e botões SRS granulares preservam o rigor da recordação ativa.
* **Responsabilidade do Usuário por Backups:** Como os dados residem localmente, backups dependem do usuário. *Mitigação:* Exportação estruturada em JSON e CSV disponível no Hub de Desempenho (`Crônicas & Atributos`).
