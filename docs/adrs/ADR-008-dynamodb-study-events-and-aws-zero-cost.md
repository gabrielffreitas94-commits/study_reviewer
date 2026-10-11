# ADR-008: Histórico de Eventos de Estudo com Amazon DynamoDB e Arquitetura Serverless com Custo Zero na AWS

* **Status:** `Aprovado`
* **Data:** 2026-10-05
* **Autor:** Especialista Arquiteto & Especialista de DevOps
* **Contexto Técnico:** [PRD.md](file:///c:/Users/Pichau/Desktop/study_reviewer/PRD.md), [ADR-001](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/adrs/ADR-001-clean-architecture-layering.md), [ADR-003](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/adrs/ADR-003-docker-dev-prod-parity-and-migrations.md) e [SPEC Sprint 02](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/specs/study-sessions-high-scale-spec.md)

---

## 1. Contexto e Problema
O Study Reviewer gera um volume expressivo de eventos de estudo append-only através do endpoint `POST /api/v1/study/sync-answers`, despachados em segundo plano pelo Dedicated Web Worker (`study-sync.worker.js`). 

Para o deploy em produção na nuvem da AWS com restrição orçamentária rigorosa (**R$ 0,00 de custo fixo / Free Tier perpétuo**) e alta capacidade de escrita concorrente sem contenção de locks relacionais:
1. O banco relacional tradicional gerenciado (Amazon RDS) gera custo fixo mensal (~$15–$18/mês) após o período inicial de 12 meses.
2. O histórico de eventos de estudo (`study_events`) é 99% append-only e requer expurgo temporal para conformidade com a LGPD (Lei nº 13.709/2018).
3. Na Clean Architecture (ADR-001), o caso de uso `SyncStudyAnswersUseCase` depende da interface abstrata `IStudyEventRepository`, permitindo a interoperabilidade transparente entre PostgreSQL e DynamoDB sem impacto nas regras de negócio.

---

## 2. Decisão Arquitetural

Adotar a seguinte arquitetura híbrida e desacoplada:

### 2.1 Implementação do Adaptador `DynamoDbStudyEventRepository`
Implementar o adaptador concreto `DynamoDbStudyEventRepository` aderente ao protocolo `IStudyEventRepository`:
* **Tabela DynamoDB:** `study_events` configurada em modo **On-Demand (Pay-per-request)** com consumo coberto pelo Free Tier perpétuo da AWS (25 GB de armazenamento + 25 WCU/RCU gratuitos todo mês).
* **Esquema de Chaves:**
  * **Partition Key (PK):** `USER#<user_id>` (ou `ANONYMOUS` para eventos desidentificados).
  * **Sort Key (SK):** `EVENT#<reviewed_at_iso>#<event_id>`.
* **Indexação & Ordenação:** Consultas por usuário utilizam `KeyConditionExpression="PK = :pk AND begins_with(SK, 'EVENT#')"` com `ScanIndexForward=False` para ordenação cronológica reversa nativa em O(1).
* **Expurgo Atômico via DynamoDB TTL (LGPD):** Atributo numérico `ttl` preenchido como Unix timestamp (`reviewed_at + 90 dias`). O DynamoDB descarta os eventos expirados automaticamente em segundo plano **sem consumir unidades de escrita (0 WCU)** e sem onerar banco relacional com rotinas de `VACUUM`.
* **Anonimização Irreversível (LGPD Art. 16, IV):** O método `anonymize_user_events` remove a associação do usuário, transferindo os registros para a partição `ANONYMOUS` e removendo `user_id` e `device_id`.

### 2.2 Arquitetura AWS Serverless com Custo R$ 0,00 (Always Free)
1. **Computação Backend:** AWS Lambda com **Lambda Function URL** (FastAPI executado via container image ou Mangum/Lambda Web Adapter).
   * Free Tier perpétuo: **1.000.000 de requisições gratuitas/mês** + 3.200.000 segundos de computação.
   * Lambda Function URL oferece endpoint HTTPS com certificado SSL gerenciado gratuitamente pela AWS (dispensando Application Load Balancer que custaria ~$18/mês).
2. **Eventos de Estudo (Alta Escala):** Amazon DynamoDB (Free Tier perpétuo de 25 GB e 25 WCU/RCU).
3. **Catálogo Relacional:** PostgreSQL Serverless no Neon (Free Tier perpétuo de 500 MB) ou Aurora Serverless / SQLite embarcado.
4. **Cache Efêmero de Estudo:** Upstash Redis Serverless (Free Tier perpétuo de 10.000 comandos/dia).
5. **Logs de Aplicação:** Amazon CloudWatch Logs (Free Tier perpétuo de 5 GB de ingestão e 5 GB de retenção).

---

## 3. Consequências e Trade-offs

### Impactos Positivos:
* **Custo Zero Real na Nuvem:** Aderência estrita ao Free Tier perpétuo da AWS, viabilizando colocar em produção sem nenhuma cobrança de cartão de crédito.
* **Escalabilidade Ilimitada de Escrita:** O DynamoDB absorve picos de sincronização em lote de milhares de estudantes concorrentes sem lock contention.
* **Conformidade Automática com LGPD:** Limpeza contínua via TTL sem necessidade de cron jobs ou scripts manuais de limpeza.
* **Inversão de Dependência:** A seleção do backend (`postgres` ou `dynamodb`) é controlada via variável de ambiente `STUDY_EVENTS_BACKEND`, garantindo paridade em testes locais e produção.

### Trade-offs:
* Requer a biblioteca `boto3` para comunicação com a AWS.
* Ambientes locais de teste utilizam mock com a biblioteca `moto` para manter a suíte de testes 100% rápida e sem necessidade de conexão ativa com a AWS.
