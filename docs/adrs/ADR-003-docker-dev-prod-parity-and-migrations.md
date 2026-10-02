# ADR-003: Paridade Dev/Prod com Docker, Migrações com Alembic e Deploy em Nuvem Gratuita

* **Status:** `Proposto` (Aguardando aprovação do usuário)
* **Data:** 2026-10-02
* **Autor:** Especialista Arquiteto
* **Contexto Técnico:** [PRD.md](file:///c:/Users/Pichau/Desktop/study_reviewer/PRD.md) v5.2 e [SPEC Sprint 01](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/specs/sprint-01-flashcards-spec.md)

---

## 1. Contexto e Problema
O Study Reviewer necessita de um ambiente de desenvolvimento e produção com paridade absoluta (Twelve-Factor App), garantindo que a aplicação execute com as mesmas versões de banco de dados, interpretador Python e configurações tanto no ambiente local do desenvolvedor quanto no deploy em produção na nuvem gratuita (Neon PostgreSQL + Render.com).

Além disso, a evolução do modelo de dados ao longo das 8 Sprints (inclusão de flashcards na Sprint 1, perguntas abertas na Sprint 2, tabelas de auditoria imutável na Sprint 3 e RAG na Sprint 6) exige uma ferramenta formal de versionamento e migração de schema para evitar perda de dados e scripts manuais frágeis de SQL.

---

## 2. Decisão Arquitetural
Adotar a seguinte stack e infraestrutura de orquestração e versionamento:

1. **Docker e Docker Compose para Desenvolvimento Local:**
   * `docker-compose.yml` orquestrando o serviço web (`FastAPI + Uvicorn`) e o serviço de banco de dados (`PostgreSQL 16 Alpine`).
   * Configuração de **Healthcheck** ativo no banco de dados (`test: ["CMD-SHELL", "pg_isready -U postgres"]`).
   * Bloqueio de inicialização do backend até a prontidão total do banco via `depends_on: db: condition: service_healthy`.
   * Volume nomeado persistente (`postgres_data`) para garantir que os dados de estudo não sejam perdidos ao reiniciar os contêineres.
2. **Dockerfile Multi-Stage para Produção:**
   * Separação de estágios: estágio `builder` para compilar dependências com `uv` e estágio final enxuto baseado em `python:3.13-slim`.
   * Execução obrigatória como usuário não-root dedicado (`RUN useradd -m appuser && USER appuser`).
   * Arquivo `.dockerignore` configurado.
3. **Versionamento e Migrações de Banco com Alembic:**
   * Adotar oficialmente o **Alembic** integrado ao SQLAlchemy.
   * Todas as alterações de tabelas serão geradas como arquivos de migração versionados em `alembic/versions/`.
   * No startup da aplicação em contêiner ou no deploy hook do Render, o comando `alembic upgrade head` é executado automaticamente antes de subir o servidor web.
4. **Deploy em Cloud Gratuita:**
   * Banco de dados: **Neon Serverless PostgreSQL** (Free Tier).
   * Web Service: **Render.com** executando o contêiner gerado pelo Dockerfile.

---

## 3. Consequências e Trade-offs

### Impactos Positivos:
* **Paridade Real Dev/Prod:** Zero surpresas entre o comportamento local e o comportamento em produção na nuvem.
* **Evolução Segura de Schema:** Cada sprint adiciona migrações incrementais sem quebrar dados existentes ou exigir comandos manuais em produção.
* **Segurança Reforçada em Contêiner:** Imagem leve, sem compiladores em produção e rodando sob usuário sem privilégios administrativos.
* **Custo Zero:** 100% hospedado no Free Tier do Neon e Render.com.

### Custos / Impactos Negativos:
* **Disciplina de Migrações:** Qualquer alteração em modelos de banco exige a geração e conferência de arquivo de migração do Alembic. *Padronizado pelas skills de DevOps e Arquiteto.*
