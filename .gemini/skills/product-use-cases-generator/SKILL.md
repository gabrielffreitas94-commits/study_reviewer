---
name: product-use-cases-generator
description: Generates a comprehensive matrix of Use Cases and Edge Cases in BDD/Gherkin format for the current sprint based on the active PRD.md before TDD starts.
---

# Product Use Cases Generator (Skill do Especialista de Produto)

Esta skill é utilizada pelo **Especialista de Produto** antes do início da implementação em TDD de qualquer sprint. Seu objetivo é dissecar os requisitos da sprint definidos no documento de requisitos do projeto (`PRD.md`) e transformá-los em uma matriz estruturada e exaustiva de Casos de Uso e Cenários de Borda (Edge Cases).

O funcionamento desta skill é agnóstico a projetos, extraindo as regras de negócio diretamente do `PRD.md` vigente no repositório.

---

## 1. Entrada e Gatilho
* **Arquivo Base:** `PRD.md` (seção da Sprint atual).
* **Entrada Complementar:** Documento SPEC aprovado (`docs/specs/sprint-XX-*-spec.md`) e ADRs vigentes.
* **Gatilho de Execução:** Fase inicial da Sprint, imediatamente antes da validação pelo Especialista QA e da escrita dos testes TDD.

---

## 2. Categorias Obrigatórias de Cenários

A matriz gerada DEVE cobrir impreterivelmente quatro categorias para cada funcionalidade descrita no PRD:

1. **Caminho Feliz (Happy Path):**
   * Fluxo ideal onde entradas válidas geram transições de estado bem-sucedidas e os resultados esperados são alcançados.
2. **Cenários de Borda (Edge Cases):**
   * Limites matemáticos, extremos de intervalos, valores mínimos e máximos permitidos.
   * Coleções especiais (listas vazias, com 1 elemento, coleções cheias).
   * Transições de estado nos nós de fronteira do ciclo de vida das entidades.
   * Formatação de dados no padrão especificado pelo PRD (ex: formatos de data, códigos, chaves).
3. **Validações de Entrada e Rejeição:**
   * Textos vazios, campos nulos onde não é permitido, strings com apenas espaços em branco.
   * Chaves e relacionamentos com identificadores inexistentes.
   * Valores numéricos fora das faixas válidas especificadas no PRD.
   * Tipos de dados incompatíveis.
4. **Falhas e Inconsistências de Negócio:**
   * Tentativas de operação em entidades em estados inválidos conforme as regras do PRD.
   * Violações de invariantes de domínio e restrições de unicidade.

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
- **Camada Alvo da Arquitetura:** Camada correspondente segundo os padrões do projeto (ex: Domínio, Aplicação, Adaptadores).

---

## 4. Destino do Artefato
O resultado gerado deve ser salvo formalmente em:
`docs/sprints/sprint-XX/01-use-cases-and-edge-cases.md`

Ao salvar o arquivo, o Especialista de Produto notifica que a matriz está pronta para ser inspecionada pela skill `qa-use-cases-validator` do Especialista QA.
