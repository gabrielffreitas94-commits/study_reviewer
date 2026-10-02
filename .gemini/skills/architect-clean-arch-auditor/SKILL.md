---
name: architect-clean-arch-auditor
description: Audits pull request changes against Clean Architecture, dependency rule, interface inversion, domain purity, and decoupling standards.
---

# Architect Clean Architecture Auditor (Skill do Especialista Arquiteto)

Esta skill é utilizada pelo **Especialista Arquiteto** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é auditar o código implementado para garantir a conformidade estrita com a **Clean Architecture**, a preservação da **Regra de Dependência**, a inversão de dependências e a integridade das fronteiras entre domínio, aplicação, adaptadores e frameworks.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra `staging` / `main`.
  * Documento SPEC aprovado (`docs/specs/sprint-XX-*-spec.md`) e ADRs vigentes.
  * Estrutura de pacotes e arquivos em `src/`.
* **Gatilho de Execução:** Conclusão da implementação e suíte de testes passando com 100% de cobertura, durante o processo de auditoria de PR.

---

## 2. Checklist Exaustivo de Auditoria Arquitetural

O Especialista Arquiteto inspeciona a base de código respondendo a seis critérios estruturais inegociáveis:

1. **Cumprimento Estrito da Regra de Dependência (Dependency Rule):**
   * *O código das camadas internas aponta exclusivamente para dentro?*
   * **Núcleo de Domínio (`domain/`):** Possui zero imports de bibliotecas de infraestrutura, ORMs (ex: SQLAlchemy), frameworks web (ex: FastAPI), schemas de validação web (ex: Pydantic na camada de API) ou clientes de banco de dados. O domínio é Python puro.
   * **Camada de Casos de Uso (`application/`):** Importa apenas o domínio e define suas próprias portas (Protocols). Não importa adaptadores de banco, rotas web ou controllers.

2. **Inversão de Dependência (Dependency Inversion Principle - DIP):**
   * Os casos de uso e serviços de aplicação dependem exclusivamente de interfaces abstratas (`typing.Protocol` ou `abc.ABC`), nunca de classes concretas de repositórios ou gateways?
   * As implementações concretas residem na camada de adaptadores (`adapters/`) e são injetadas na inicialização ou via dependency injection?

3. **Pureza e Riqueza do Modelo de Domínio (Rich vs. Anemic):**
   * As entidades e agregados encapsulam suas regras de validação, cálculo e mutação de estado?
   * O código evita o antipadrão de *Modelos Anêmicos* (onde entidades são meras estruturas de dados manipuladas por serviços procedurais desordenados)?

4. **Fronteiras e DTOs de Entrada e Saída (Boundary Decoupling):**
   * Entidades de domínio internas são expostas diretamente em rotas HTTP ou serializadas cruas para a interface? *Se forem, devem ser encapsuladas por DTOs ou Schemas dedicados de saída.*
   * Requisições externas são validadas na borda e convertidas em DTOs de comando antes de atingirem os use cases?

5. **Isolamento de Persistência e Infraestrutura:**
   * Modelos de tabela de banco de dados (ex: classes `Base` do SQLAlchemy) estão fisicamente separados das entidades de domínio?
   * Existe um mapeador (*Mapper*) explícito que converte entre entidades de domínio e modelos de persistência, evitando acoplamento de colunas com regras de negócio?
   * Sessões de banco de dados, transações (`commit`/`rollback`) e queries SQL estão 100% contidas nos adaptadores de repositório?

6. **Modularidade, Coesão e Ausência de Ciclos:**
   * Os módulos são coesos, com responsabilidades bem delimitadas?
   * Há alguma dependência circular entre módulos ou pacotes? *Se houver, é bloqueio imediato.*

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **3** | **Especialista Arquiteto** | `[APROVADO]` | Arquitetura validada com louvor. Regra de dependência estritamente cumprida: núcleo de domínio 100% puro e desacoplado. Inversão de dependência implementada via Protocols, persistência contida em adaptadores e fronteiras desacopladas por DTOs. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **3** | **Especialista Arquiteto** | `[BLOQUEANTE]` | Violação arquitetural identificada: [descrever se houve vazamento de framework para o domínio, dependência concreta em use cases, modelo anêmico ou quebra da regra de dependência]. Refatoração obrigatória antes do merge. |
```
