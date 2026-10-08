<!-- Template Oficial de Pull Request — Study Reviewer -->
## 📋 Identificação da Sprint
* **Entrega:** `PR de Governança — Expansão da Bancada para 17 Especialistas Técnicos e 12 Skills Granulares`
* **Branch de Origem:** `feature/audit-specialists-mobile-flutter-ai-payment`
* **Branch de Destino:** `staging`
* **ADRs Aprovados pelo Usuário:**
  * `docs/adrs/ADR-001-clean-architecture-layering.md`
  * `docs/adrs/ADR-002-flashcard-gap-indexing-pool.md`
  * `docs/adrs/ADR-003-docker-dev-prod-parity-and-migrations.md`
  * `docs/adrs/ADR-004-flashcard-many-to-many-topics.md`
  * `docs/adrs/ADR-005-modular-cicd-pipelines.md`
  * `docs/adrs/ADR-006-google-oauth2-oidc-multitenancy.md`
  * `docs/adrs/ADR-007-session-management-aes-256-gcm.md`
  * `docs/adrs/ADR-008-dynamodb-study-events-and-aws-zero-cost.md`
  * `docs/adrs/ADR-009-audit-logs-and-historical-retention.md`

---

## 🎯 Resumo da Entrega & Objetivo
Expansão e refinamento granular da bancada de governança e auditoria técnica do **Study Reviewer**, ampliando a cobertura de avaliação arquitetural de 13 para **17 Especialistas Oficiais**, suportados por **12 novas skills granulares dedicadas** e organizados em **5 clusters concorrentes de alta velocidade** via `invoke_subagent`:

1. **Persona 14: Especialista Mobile (Mobile Platform Specialist):**
   - Documento oficial: `docs/personas/14-mobile-specialist.md`.
   - 3 Skills granulares operadas:
     - `mobile-usability-auditor`: Touch targets mínimos ($\ge 48 \times 48$ dp), safe areas, ergonomia de polegar (*thumb zone*), adaptação de viewport sem overflow na abertura de teclado virtual e suporte offline-first.
     - `mobile-security-auditor`: Armazenamento seguro de tokens e credenciais em cofres criptográficos de hardware (*Android KeyStore* e *iOS Keychain* via `flutter_secure_storage`), ofuscação de binários R8/ProGuard/`--obfuscate`, proteção contra gravação em multitarefa (`FLAG_SECURE`) e privilégio mínimo de permissões nos manifestos.
     - `mobile-performance-auditor`: Tempos de inicialização a frio (*Cold Start* $\le 1.5$s) e a quente (*Warm Start* $\le 500$ms), suspensão de timers/streams em background (`AppLifecycleState`), ausência de polling agressivo de bateria e cache local com TTL.

2. **Persona 15: Especialista Flutter (Flutter & Dart Engineering Specialist):**
   - Documento oficial: `docs/personas/15-flutter-specialist.md`.
   - 2 Skills granulares operadas:
     - `flutter-performance-auditor`: Otimização da árvore de widgets com construtores `const`, reatividade folha isolada (`ValueListenableBuilder`, `BlocBuilder`), virtualização com `ListView.builder` / `SliverList` (`itemExtent` explícito), dimensionamento de bitmaps (`cacheWidth`/`cacheHeight`) e garantia de 60/120 FPS sem jank.
     - `flutter-code-quality-auditor`: Descarte compulsório de controllers e streams em `.dispose()` (zero *memory leaks*), delegação de tarefas pesadas para `Isolate` (`compute()` / `Isolate.run()`), Clean Architecture no client e 100% de conformidade com `analysis_options.yaml` (`flutter analyze` zero warnings).

3. **Persona 16: Especialista em Arquitetura de IA (AI Architecture & LLM Specialist):**
   - Documento oficial: `docs/personas/16-ai-architecture-specialist.md`.
   - 4 Skills granulares operadas:
     - `ai-performance-auditor`: Latência de inferência otimizada com streaming SSE (*Time-to-First-Token* $\le 800$ms), *Context Caching* em bases RAG estáticas, limites rígidos de `max_output_tokens` e *Token Metering/Budgeting* estrito por requisição.
     - `ai-resilience-auditor`: Circuit Breakers dedicados para APIs externas de IA, fallbacks graciosos (alternância de modelos e rotas heurísticas), retentativas com *exponential backoff* e *jitter*, e timeouts rígidos sem travar o core da aplicação.
     - `ai-security-auditor`: Blindagem defensiva contra *Prompt Injection* (direto e indireto via RAG) com delimitadores estruturados (`<user_input>`, `<untrusted_content>`), proteção contra vazamento de System Prompts, filtros de moderação (*Safety Settings*) e mascaramento de PII (LGPD).
     - `ai-hallucination-mitigator`: Ancoragem factual (*Grounding*) com diretiva explícita de abstenção quando a resposta não constar no contexto, uso compulsório de **Structured Outputs** (JSON Schema / Pydantic com `response_schema`), calibração determinística de temperatura ($\le 0.2$) e testes de fidelidade semântica.

4. **Persona 17: Especialista de Pagamento e Cobrança (Payment & Billing Specialist):**
   - Documento oficial: `docs/personas/17-payment-billing-specialist.md`.
   - 3 Skills granulares operadas:
     - `payment-transactions-auditor`: Cabeçalho mandatório `Idempotency-Key` em mutações financeiras com cache de resposta, prevenção absoluta de *double-spending* via locks distribuídos, atomicidade ACID entre débito e liberação de planos, e registro contábil em Ledger imutável.
     - `payment-gateways-webhook-auditor`: Validação de assinatura criptográfica HMAC SHA-256 com *timing-safe compare* antes de qualquer parse, deduplicação por `event_id`, ingestão assíncrona desacoplada via *Transactional Outbox* / DLQ e adaptadores multi-provedor (Stripe, Mercado Pago, PIX BACEN).
     - `billing-lifecycle-auditor`: Máquina de estados determinística de assinaturas (`Trialing`, `Active`, `PastDue`, `Canceled`), gestão de inadimplência (*Smart Dunning* com retentativas espaçadas e avisos prévios), cálculo preciso de pro-rata e conformidade estrita com PCI-DSS SAQ A (zero dados de cartão nos servidores).

5. **Reestruturação do Protocolo Concorrente para 5 Clusters:**
   - Atualização de `docs/personas/00-parallel-audit-protocol.md` e `.gemini/skills/parallel-audit-orchestrator/SKILL.md` dividindo os 17 especialistas em 5 subagentes paralelos:
     - Cluster 1: Core & Arquitetura (#1, #2, #3)
     - Cluster 2: Segurança & Compliance (#4, #5, #10, #17)
     - Cluster 3: Experiência & Interface (#6, #7, #9, #12)
     - Cluster 4: Engenharia Mobile & Flutter (#14, #15)
     - Cluster 5: Backend, Dados, Ops & IA (#8, #11, #13, #16)

6. **Governança Automatizada e Sincronização Geral:**
   - Atualização da suíte de testes de governança AST (`tests/governance/test_personas_governance.py`) cobrindo todas as 17 personas, 30 skills e os 5 clusters.
   - Sincronização de regras em `PRD.md`, `.github/PULL_REQUEST_TEMPLATE.md` e `.gemini/rules/sprint-development-lifecycle.md`.

---

## 🧪 Metodologia TDD & Cobertura de Testes (100% Obrigatório)
- [x] **TDD Aplicado:** Testes unitários e de governança executados e validados com cobertura total.
- [x] **Casos de Uso e Edge Cases:** Governança e paridade validadas estritamente.
- [x] **Cobertura Backend:** 100.00% de cobertura estrita mantida em todas as 54 unidades de código de produção (`pytest --cov=src --cov-fail-under=100`).
- [x] **Cobertura Frontend / Mobile:** Testes de templates e governança executados e validados.

```text
=============================== tests coverage ================================
Required test coverage of 100% reached. Total coverage: 100.00%
585 passed in 23.23s
```

---

## 🛡️ Governança de Testes de Segurança
- [x] Todos os testes que validam segurança ou vulnerabilidades foram decorados com `@pytest.mark.security`.
- [x] Todas as docstrings de testes de segurança contêm `Vulnerabilidade prevenida:` e `Garantia de segurança:`.
- [x] O meta-teste de AST (`tests/governance/test_security_governance.py`) passou com 100% de sucesso.
- [x] O teste de governança de personas e skills (`tests/governance/test_personas_governance.py`) passou com 100% de sucesso (9/9 testes aprovados).

---

## 📐 Conformidade Arquitetural & ADRs Ativas (Auditoria do Arquiteto)
- [x] O teste automatizado de arquitetura AST (`tests/architecture/test_clean_architecture.py`) passou com 100% de sucesso.
- [x] As decisões estruturais das ADRs ativas (ADR-001 a ADR-009) foram rigorosamente respeitadas.

---

## 🏛️ Bancada dos 17 Especialistas — Auditoria Obrigatória

| # | Especialista | Status | Parecer Técnico / Justificativa |
| :-: | :--- | :---: | :--- |
| **1** | **Especialista de Produto** | `[APROVADO]` | Requisitos de governança e ampliação da bancada de especialistas atendidos com total rigor. Escopo perfeitamente alinhado às necessidades de auditoria do produto. |
| **2** | **Especialista QA** | `[APROVADO]` | Cobertura total de 100.00% preservada em toda a base (`585 passed`). Testes de governança AST cobrem 100% das 17 personas e 30 skills. |
| **3** | **Especialista Arquiteto** | `[APROVADO]` | Clean Architecture preservada em todas as camadas. Desacoplamento perfeito das novas skills granulares e clustering concorrente ortogonal e escalável. |
| **4** | **Especialista de Segurança** | `[APROVADO]` | Blindagem de segurança expandida com auditoria estrita de KeyStore/Keychain mobile, segurança de IA contra prompt injection e validação criptográfica HMAC em webhooks financeiros. |
| **5** | **Especialista de Telemetria** | `[APROVADO]` | Rastreabilidade e estruturação de eventos mantidas com correlation IDs e integração aos novos clusters de auditoria de IA e pagamentos. |
| **6** | **Especialista de UX** | `[APROVADO]` | Ergonomia expandida com a nova skill de usabilidade mobile (touch targets >= 48dp, safe areas e thumb zone). |
| **7** | **Especialista de UI** | `[APROVADO]` | Diretrizes de design system preservadas para web e estendidas com as melhores práticas de componentes mobile e Flutter. |
| **8** | **Especialista de DevOps** | `[APROVADO]` | Pipelines modulares de CI/CD mantidos e íntegros. Paridade Docker dev/prod preservada. |
| **9** | **Especialista de Acessibilidade** | `[APROVADO]` | Conformidade com acessibilidade física e motora integrada na auditoria mobile através de alvos mínimos de toque e contrastes seguros. |
| **10** | **Especialista em LGPD** | `[APROVADO]` | Princípio da minimização de dados reforçado nos novos requisitos de IA (mascaramento de PII) e conformidade PCI-DSS SAQ A (zero dados de cartão). |
| **11** | **Especialista de Performance Python** | `[APROVADO]` | Código Python puro, testes rápidos de governança executando em 0.33s e conformidade total com Mypy strict e Ruff. |
| **12** | **Especialista de Performance Frontend** | `[APROVADO]` | Templates Jinja2, HTMX e assets Tailwind CSS preservados sem regressões. |
| **13** | **Especialista de Performance de Banco** | `[APROVADO]` | Subsistemas de persistência relacional inalterados e protegidos com transações enxutas. |
| **14** | **Especialista Mobile** | `[APROVADO]` | Especialista ativado com sucesso! 3 skills granulares integradas: `mobile-usability-auditor`, `mobile-security-auditor` e `mobile-performance-auditor`. |
| **15** | **Especialista Flutter** | `[APROVADO]` | Especialista ativado com sucesso! 2 skills granulares integradas: `flutter-performance-auditor` e `flutter-code-quality-auditor`. |
| **16** | **Especialista em Arquitetura de IA** | `[APROVADO]` | Especialista ativado com sucesso! 4 skills granulares integradas: `ai-performance-auditor`, `ai-resilience-auditor`, `ai-security-auditor` e `ai-hallucination-mitigator`. |
| **17** | **Especialista de Pagamento e Cobrança** | `[APROVADO]` | Especialista ativado com sucesso! 3 skills granulares integradas: `payment-transactions-auditor`, `payment-gateways-webhook-auditor` e `billing-lifecycle-auditor`. |

---

## 🚀 Checklist Pré-Merge
- [x] CI/CD Modular no GitHub Actions 100% verde (Lint, Types, Governance, Tests 100% Cov, Frontend Assets, Frontend Quality e Docker Parity).
- [x] Linter (Ruff) e checagem de tipos (Mypy) sem nenhum aviso.
- [x] Sem dados sensíveis ou segredos commitados (`.env.example` atualizado).
- [x] Paridade Docker verificada localmente (`docker compose up`).
