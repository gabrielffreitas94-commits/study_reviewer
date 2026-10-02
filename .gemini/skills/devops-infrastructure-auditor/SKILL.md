---
name: devops-infrastructure-auditor
description: Audits pull request diff against staging for Docker containerization standards, multi-stage builds, non-root execution, dev/prod parity, healthchecks, and CI/CD pipeline rigor.
---

# DevOps Infrastructure & CI/CD Auditor (Skill do Especialista de DevOps)

Esta skill é utilizada pelo **Especialista de DevOps** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é auditar os artefatos de infraestrutura, conteinerização Docker, orquestração e pipelines de integração contínua (CI/CD) no diff contra a branch `staging`, assegurando **paridade estrita entre ambientes (Dev/Prod Parity)**, segurança em contêineres, alta resiliência e processos de automação rápidos e isolados.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`.
  * Workflows de CI/CD em `.github/workflows/` e scripts de automação.
* **Gatilho de Execução:** Auditoria final de PR para qualquer alteração que toque conteinerização, dependências, pipelines, banco de dados ou infraestrutura.

---

## 2. Checklist Exaustivo de Auditoria de DevOps

O Especialista de DevOps inspeciona a infraestrutura respondendo a sete dimensões essenciais:

1. **Segurança e Otimização de Imagens Docker (Dockerfile):**
   * **Multi-Stage Build:** O Dockerfile separa o estágio de compilação/instalação do estágio final de execução, garantindo uma imagem enxuta e sem ferramentas desnecessárias?
   * **Execução Não-Root Obrigatória:** O contêiner de execução final cria e adota expressamente um usuário não privilegiado (`RUN useradd -m appuser && USER appuser`), nunca rodando como `root`?
   * **Imagem Base Mínima e Oficial:** Utiliza imagens oficiais mínimas e seguras (ex: `python:3.13-slim`), evitando imagens pesadas e propensas a vulnerabilidades?
   * **Aproveitamento de Cache de Camadas:** Os arquivos de dependência e lock (`pyproject.toml`, `uv.lock`) são copiados antes do código-fonte para maximizar o reuso do cache do Docker?
   * **Presença de `.dockerignore`:** O arquivo `.dockerignore` existe e bloqueia o envio de `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.env` e arquivos temporários para dentro da imagem?

2. **Orquestração e Paridade Dev/Prod (Docker Compose):**
   * **Paridade de Serviços:** O ambiente local espelha a arquitetura de produção (mesma versão de banco de dados PostgreSQL, mesmas configurações essenciais de runtime)?
   * **Healthchecks em Serviços Dependentes:** O serviço de banco de dados possui teste de saúde ativo configurado (ex: `test: ["CMD-SHELL", "pg_isready -U postgres"]`)?
   * **Dependência com Barreira de Saúde:** O serviço da aplicação aguarda a prontidão real do banco antes de iniciar (`depends_on: db: condition: service_healthy`)?
   * **Persistência de Dados em Volumes:** O banco de dados utiliza volumes nomeados dedicados, garantindo que os dados não sejam perdidos ao recriar contêineres?

3. **Resiliência e Finalização Graciosa (*Graceful Shutdown*):**
   * O servidor web/app roda como processo principal ou sob gerenciador de init adequado, recebendo e tratando corretamente os sinais `SIGTERM` e `SIGINT` sem derrubar requisições ativas bruscamente?
   * O sistema expõe endpoint de verificação de integridade operacional (ex: `/health` ou `/live`) retornando status 200 OK quando apto a receber tráfego?

4. **Rigor e Isolamento nos Pipelines de CI/CD (GitHub Actions):**
   * **Processos Isolados:** Os testes de backend e de frontend rodam em jobs ou etapas de processo totalmente separadas e independentes?
   * **Barreira de 100% de Cobertura:** O pipeline falha automaticamente caso a cobertura de testes seja inferior a 100% (`--cov-fail-under=100`)?
   * **Linters e Tipagem Estrita:** Ruff (format check e lint) e Mypy (strict) são executados como barreiras obrigatórias?
   * **Gatilhos Corretos:** O workflow dispara nos eventos corretos (push e PR para `staging` e `main`)?
   * **Cache de Dependências:** O pipeline utiliza cache de ferramentas (`astral-sh/setup-uv` com `enable-cache: true`) para execuções ágeis?

5. **Gestão Segura de Configurações e Segredos (Twelve-Factor: Config):**
   * Nenhuma credencial real, chave de API ou senha de banco de dados está escrita diretamente no Dockerfile, `docker-compose.yml` ou workflows de CI?
   * O arquivo `.env.example` está rigorosamente atualizado com todas as variáveis de ambiente necessárias e com valores dummy seguros?

6. **Reprodutibilidade e Determinismo de Dependências:**
   * A instalação de pacotes no Docker e no CI utiliza estritamente o arquivo de lock (`uv.lock` ou `package-lock.json`), garantindo que o mesmo código execute exatamente com as mesmas versões de bibliotecas em qualquer máquina?

7. **Tratamento de Logs e I/O de Contêiner (Statelessness):**
   * A aplicação direciona todos os seus logs para `stdout` / `stderr`, permitindo que o Docker e os coletores de nuvem gerenciem a agregação sem gravar arquivos de log no disco interno do contêiner?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **8** | **Especialista de DevOps** | `[APROVADO]` | Infraestrutura e CI/CD auditados com sucesso. Dockerfile multi-stage enxuto com execução não-root, paridade dev/prod mantida via docker-compose com healthchecks de banco, CI executando backend e frontend em processos isolados e .env.example íntegro. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **8** | **Especialista de DevOps** | `[BLOQUEANTE]` | Falha de infraestrutura/DevOps identificada: [descrever se há execução como root, ausência de healthcheck no docker-compose, quebra no isolamento de jobs do CI, segredos expostos em arquivos de configuração ou divergência no .env.example]. Correção necessária antes do merge. |
```
