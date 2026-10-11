# ADR-001: Adoção de Clean Architecture com 4 Camadas Concêntricas e Inversão de Dependência

* **Status:** `Proposto` (Aguardando aprovação do usuário)
* **Data:** 2026-10-02
* **Autor:** Especialista Arquiteto
* **Contexto Técnico:** [PRD.md](file:///c:/Users/Pichau/Desktop/study_reviewer/PRD.md) v5.2 e [SPEC Sprint 01](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/specs/sprint-01-flashcards-spec.md)

---

## 1. Contexto e Problema
O **Study Reviewer** possui regras de negócio ricas e algoritmos estritos de repetição e rotação contínua (Pool dinâmica por rodadas com inserção em 10% e algoritmo de repetição espaçada por calendário de 1 a 180 dias com penalidade no nível 6). Além disso, o roadmap prevê evolução multifásica: web inicial com HTMX, posterior aplicativo nativo em Flutter na Sprint 5, e integração com múltiplos avaliadores de IA nas Sprints 7, 8 e 9.

Se as regras de negócio fossem acopladas diretamente ao framework web (FastAPI) ou ao ORM de banco de dados (SQLAlchemy), o código se tornaria frágil, difícil de testar de forma isolada e exigiria reescrita substancial quando o Flutter e a IA fossem introduzidos.

---

## 2. Decisão Arquitetural
Adotar rigorosamente a **Clean Architecture** estruturada em quatro camadas físicas concêntricas:

1. **`src/domain/` (Entities & Domain Services):**
   * Python puro, sem qualquer importação de SQLAlchemy, FastAPI, Pydantic ou bibliotecas de IO.
   * Contém as entidades ricas, invariantes de validação e domain services puros (`FlashcardPoolService`, `SpacingPolicyService`).
2. **`src/application/` (Use Cases & Ports):**
   * 100% agnóstica a protocolos de entrega (HTTP/HTML).
   * Orquestra os fluxos de trabalho através de casos de uso com responsabilidade única.
   * Define contratos abstratos de saída utilizando `typing.Protocol` (Inversão de Dependência - DIP).
3. **`src/adapters/` (Interface Adapters):**
   * Contém implementações concretas dos repositórios via SQLAlchemy.
   * Mappers explícitos entre modelos ORM e entidades de domínio.
   * Controladores Web (Jinja2/HTMX) e Controladores de API REST (JSON).
4. **`src/infrastructure/` (Frameworks & Drivers):**
   * Configuração de banco de dados, Docker, injeção de dependências e segurança.

---

## 3. Consequências e Trade-offs

### Impactos Positivos:
* **Testabilidade Unitária Ultra-rápida:** O núcleo de domínio e os casos de uso são testados em milissegundos sem necessidade de mocks complexos, banco de dados ou servidor web rodando.
* **Atingimento Seguro de 100% de Coverage:** O isolamento das camadas torna a meta inegociável de 100% de cobertura de testes limpa e sustentável.
* **Reuso Total para o App Flutter:** Quando o Flutter for integrado na Sprint 5, nenhum caso de uso precisará ser reescrito; apenas novos adaptadores de rota JSON serão adicionados na camada 3.
* **Imunidade a Mudanças de Framework:** Se o banco ou o framework web precisarem ser trocados, o domínio permanece 100% intocado.

### Custos / Impactos Negativos:
* **Código Adicional (Boilerplate):** Necessidade de manter DTOs de fronteira e Mappers explícitos para converter entre dados de banco e entidades. *Mitigado pelo ganho incomparável de estabilidade e separação de responsabilidades.*
