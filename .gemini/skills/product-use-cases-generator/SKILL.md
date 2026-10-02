---
name: product-use-cases-generator
description: Generates a comprehensive matrix of Use Cases and Edge Cases in BDD/Gherkin format for the current sprint based on PRD.md before TDD starts.
---

# Product Use Cases Generator (Skill do Especialista de Produto)

Esta skill é utilizada pelo **Especialista de Produto** antes do início da implementação em TDD de qualquer sprint. Seu objetivo é dissecar os requisitos da sprint definidos no [PRD.md](file:///c:/Users/Pichau/Desktop/study_reviewer/PRD.md) e transformá-los em uma matriz estruturada e exaustiva de Casos de Uso e Cenários de Borda (Edge Cases).

---

## 1. Entrada e Gatilho
* **Arquivo Base:** `PRD.md` (seção da Sprint em execução).
* **Entrada Complementar:** Documento SPEC aprovado (`docs/specs/sprint-XX-*-spec.md`) e ADRs vigentes.
* **Gatilho de Execução:** Fase inicial da Sprint, imediatamente antes da validação pelo QA e da escrita dos testes TDD.

---

## 2. Categorias Obrigatórias de Cenários

A matriz gerada DEVE cobrir impreterivelmente quatro categorias para cada funcionalidade:

1. **Caminho Feliz (Happy Path):**
   * Fluxo ideal onde entradas válidas geram transições de estado bem-sucedidas.
2. **Cenários de Borda (Edge Cases):**
   * Limites matemáticos e coleções especiais (lista com 0 itens, 1 item, 2 itens).
   * Arredondamento do cálculo dos primeiros 10% da pool: $\max(1, \lfloor 0.1 \times N \rfloor)$.
   * Transições de fronteira (ex: último card da pool provocando shuffle automático, nível 6 do SRS regredindo ao nível 2).
   * Datas de virada de mês/ano no formato puramente calendários `YYYY-MM-DD`.
3. **Validações de Entrada e Rejeição:**
   * Textos vazios, campos nulos onde não é permitido, strings com apenas espaços em branco.
   * Chaves estrangeiras inexistentes (ex: criar card para tema inexistente).
   * Valores numéricos fora da escala (ex: score < 0 ou score > 100).
4. **Falhas e Inconsistências de Negócio:**
   * Tentativas de operação em entidades inativas ou excluídas.
   * Conflitos de estado concorrente.

---

## 3. Padrão Estrutural dos Casos de Uso (BDD / Gherkin)

Cada use case deve ser estruturado com:
- **ID:** `UC-S<Sprint>-<Numero>` (ex: `UC-S01-01`)
- **Título do Cenário:** Claro e autoexplicativo.
- **Categoria:** `Caminho Feliz` | `Edge Case` | `Validação de Entrada` | `Falha de Negócio` | `Segurança`
- **Especificação BDD:**
  ```gherkin
  Cenário: [Título]
    Dado que [contexto prévio ou estado inicial do sistema]
    Quando [ação ou comando executado pelo usuário/sistema com entradas explícitas]
    Então [resultado esperado, mutação de estado e resposta da camada]
  ```
- **Camada Alvo da Clean Architecture:** `Entities/Domain Service` | `Use Case` | `Interface Adapter/Controller`

---

## 4. Destino do Artefato
O resultado gerado deve ser salvo formalmente em:
`docs/sprints/sprint-XX/01-use-cases-and-edge-cases.md`

Ao salvar o arquivo, o Especialista de Produto notifica que a matriz está pronta para ser inspecionada pela skill `qa-use-cases-validator` do Especialista QA.
