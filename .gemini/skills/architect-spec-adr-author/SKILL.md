---
name: architect-spec-adr-author
description: Authors the technical specification (SPEC) and Architecture Decision Records (ADRs) for a sprint, detailing domain entities, ports, adapters, and structural design choices before user approval.
---

# Architect SPEC & ADR Author (Skill do Especialista Arquiteto)

Esta skill é utilizada pelo **Especialista Arquiteto** na fase preparatória da sprint, antes do início da codificação. Seu objetivo é projetar a estrutura técnica detalhada da entrega na forma de um documento **SPEC** e registrar decisões estruturais significativas em **ADRs (Architecture Decision Records)**, submetendo-os à aprovação obrigatória do usuário.

---

## 1. Entrada e Gatilho
* **Arquivos Base:**
  * Requisitos da Sprint no `PRD.md`.
  * Matriz de Casos de Uso preliminar ou planejada.
  * ADRs já existentes no repositório em `docs/adrs/`.
* **Gatilho de Execução:** Início da preparação técnica da Sprint, antes de qualquer código de produção ou teste ser escrito.

---

## 2. Estrutura Padrão do Documento SPEC (`docs/specs/sprint-XX-*-spec.md`)

A SPEC deve documentar formalmente a transposição dos requisitos do PRD para as 4 camadas da Clean Architecture:

1. **Visão Geral e Diagrama de Camadas:**
   * Representação visual ou conceitual das fronteiras de responsabilidade do incremento.
2. **Camada 1: Núcleo de Domínio (Entities & Domain Services):**
   * **Entidades e Value Objects:** Atributos, invariantes de validação e métodos de mutação de estado.
   * **Domain Services:** Lógicas de domínio que envolvem múltiplas entidades ou cálculos puros de regras de negócio.
   * **Hierarquia de Exceções de Domínio:** Exceções específicas lançadas pelo núcleo ao violar regras.
3. **Camada 2: Casos de Uso (Application Layer):**
   * **Use Cases / Interactors:** Responsabilidade única de cada caso de uso da sprint.
   * **DTOs de Entrada e Saída (Input/Output Boundaries):** Estruturas de dados desacopladas que transportam informações para dentro e fora da camada de aplicação.
   * **Portas / Interfaces de Saída (Ports):** Definição de contratos abstratos (`Protocols` no Python) para repositórios, gateways ou serviços externos (ex: `IFlashcardRepository`).
4. **Camada 3: Adaptadores de Interface (Interface Adapters):**
   * **Controllers e Routers:** Endpoints HTTP, mapeamento de requisições, status codes e schemas de validação de payload (ex: Pydantic).
   * **Implementação de Repositórios:** Adaptadores concretos que implementam as portas utilizando o ORM ou banco de dados (ex: `SqlAlchemyFlashcardRepository`).
   * **Mapeadores (Mappers):** Conversão bidirecional entre modelos de persistência/banco e entidades puras de domínio.
5. **Camada 4: Frameworks & Drivers:**
   * Modelos ORM de banco de dados, migrações de schema, configurações de conexão e contêiner de injeção de dependências.
6. **Mapeamento de Fluxo de Execução:**
   * Rastreio do ciclo de vida de uma requisição típica através de todas as camadas.

---

## 3. Elaboração de Architecture Decision Records (ADRs) (`docs/adrs/ADR-XXX-*.md`)

Sempre que a sprint introduzir uma decisão técnica de impacto duradouro (ex: escolha de biblioteca, estratégia de persistência, modelo de concorrência, padrão de integração), um ADR deve ser redigido seguindo o padrão Nygard:

* **Número e Título:** `ADR-XXX-[titulo-curto-kebab-case].md`
* **Status:** `Proposto` (aguardando aprovação do usuário) | `Aprovado` | `Deprecado` | `Substituído`
* **Contexto e Forças:** O problema técnico a resolver, restrições e alternativas avaliadas.
* **Decisão Tomada:** A solução estrutural escolhida e sua justificativa técnica.
* **Consequências e Trade-offs:**
  * *Impactos Positivos:* Benefícios, simplificação, ganho de performance ou desacoplamento.
  * *Impactos Negativos / Custos:* Complexidade adicional, esforço de manutenção ou restrições introduzidas.

---

## 4. Portão Obrigatório de Submissão ao Usuário

Ao concluir a redação da SPEC e dos ADRs da Sprint:
* Os arquivos são persistidos em suas respectivas pastas (`docs/specs/` e `docs/adrs/`).
* O Especialista Arquiteto **bloqueia o avanço do desenvolvimento** e notifica o usuário, apresentando o resumo da arquitetura proposta e solicitando formalmente a sua aprovação explícita.
