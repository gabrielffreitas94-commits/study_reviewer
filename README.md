# Study Reviewer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Study Reviewer** é uma aplicação web **100% local e offline** de revisão ativa e repetição espaçada (SRS), construída com **FastAPI**, **Jinja2**, **HTMX**, **Tailwind CSS** e **SQLAlchemy** seguindo os princípios da **Clean Architecture**.

O sistema combina:
- **Códice de Habilidades (Árvore de Estudos RPG):** Canvas interativo de nós e pré-requisitos, com **Tomo do Nó** (editor Markdown, materiais anexados, arena SRS de 4 níveis e importação em lote via JSON).
- **Provações Diárias (Perguntas Abertas SRS):** Repetição espaçada determinística (`[1, 7, 15, 30, 60, 90, 180]` dias) com modos **Responder por Escrito** (`WRITTEN_SELF_REVIEW`) para comparação com o gabarito e **Gabarito Direto** (`MANUAL`), além de edição inline.
- **Flashcards em Pool Contínua:** Rotação contínua com Gap Indexing, flip 3D client-side instantâneo e atalhos de teclado.
- **Biblioteca de Materiais:** Cadastro de anotações e extração local de texto de arquivos `.pdf`, `.docx`, `.txt` e `.md`.
- **Crônicas & Atributos (Hub de Desempenho):** Métricas de retenção madura, histórico imutável de revisões e exportação LGPD em **JSON** e **CSV**.
- **Autenticação Local & Segurança:** Cadastro e login locais sem dependências externas, cookies `HttpOnly` / Bearer tokens cifrados com **AES-256-GCM** e sanitização contra XSS (`nh3`).

---

## Arquitetura do Projeto

O código segue a separação estrita em camadas concêntricas descrita em [ADR-001](docs/adrs/ADR-001-clean-architecture-layering.md) e [ADR-010](docs/adrs/ADR-010-local-offline-auth-and-workspace-architecture.md):

```text
src/
├── domain/           # Entidades, exceções, protocolos e serviços em Python puro
├── application/      # Casos de uso agnósticos e DTOs
├── adapters/         # Controladores Web (Jinja2/HTMX), API REST, repositórios e assets estáticos
└── infrastructure/   # Configuração, banco (SQLite/PostgreSQL), segurança AES-256-GCM e logging
```

---

## Requisitos e Instalação Local

- **Python** `>= 3.13`
- **[uv](https://docs.astral.sh/uv/)** (recomendado) ou `pip`
- Banco padrão: **SQLite** local (zero configuração adicional), com suporte opcional a **PostgreSQL** e **Redis** locais.

### 1. Clonar e configurar o ambiente

Com `uv`:
```bash
uv sync
```

Ou com `pip`:
```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Variáveis de Ambiente

Copie `.env.example` para `.env` e ajuste conforme necessário (para uso local imediato, o padrão SQLite funciona sem serviços externos):

```bash
cp .env.example .env
```

> Em produção ou uso persistente, defina uma `SECRET_KEY` forte com pelo menos 32 bytes.

### 3. Popular dados de demonstração (opcional)

```bash
python -m scripts.seed_demo
```

### 4. Iniciar o servidor local

```bash
uvicorn src.main:app --reload
```

Acesse `http://localhost:8000` no navegador. Todos os scripts e estilos são servidos localmente pela própria aplicação, sem requisições a CDNs ou APIs externas.

---

## Testes, Lint e Verificação de Tipos

```bash
# Executar suíte de testes
pytest

# Verificar estilo e lint com Ruff
ruff check .

# Verificar tipagem estrita com Mypy
mypy src
```

---

## Documentação e Licenças

- **Especificação do Produto:** [PRD.md](PRD.md)
- **Decisões Arquiteturais (ADRs):** [docs/adrs/](docs/adrs/)
- **Licença do Projeto:** [MIT License](LICENSE)
- **Licenças de Terceiros:** Consulte [docs/THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md) para detalhes sobre o **HTMX 1.9.12** (BSD-2-Clause) e os ícones vetoriais adaptados de **Game-Icons.net** (CC BY 3.0).
