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

A matriz gerada DEVE cobrir impreterivelmente uma taxonomia completa de cenários para cada funcionalidade descrita no PRD:

1. **Caminho Feliz (Happy Path & Variações Válidas):**
   * Fluxo nominal principal com entradas típicas e sucesso absoluto.
   * Variações válidas secundárias (ex: ações com parâmetros opcionais omitidos vs preenchidos).
   * Persistência correta do estado final e integridade dos dados retornados.

2. **Cenários de Borda e Fronteiras Matemáticas (Edge Cases & Boundary Values):**
   * **Limites de Coleções:** Listas vazias (0 elementos), coleções unitárias (1 elemento), coleções no tamanho exato de corte/página, coleções extensas.
   * **Fronteiras Numéricas e Fórmulas:** Valores no limite exato inferior, limite exato superior, imediatamente abaixo e imediatamente acima dos limites permitidos pelo PRD.
   * **Arredondamento e Frações:** Comportamento diante de divisão inteira, arredondamento para cima/baixo (`ceil`/`floor`), valores decimais e proporções percentuais.
   * **Fronteiras Temporais:** Transições de início e fim de período, viradas de dia, mês e ano, anos bissextos e datas no formato estrito exigido pelo PRD.

3. **Validação de Entrada e Rejeição de Payloads (Input & Schema Validation):**
   * **Campos de Texto:** Strings vazias, strings compostas exclusivamente por espaços em branco, limites mínimos e máximos de caracteres permitidos.
   * **Tipagem e Formatação:** Valores de tipos incompatíveis (ex: texto em campo numérico), formatos de data inválidos, valores fora de listas permitidas (enums).
   * **Identificadores e Chaves:** UUIDs malformados, referências a identificadores inexistentes no banco/sistema.
   * **Campos Obrigatórios vs Opcionais:** Omissão de atributos requeridos e tentativa de envio de campos extras não mapeados.

4. **Invariantes de Domínio e Regras de Negócio (Business Rules & Invariants):**
   * Violação direta de restrições expressas no PRD (ex: notas fora de escala, operações fora da janela permitida, violações de precedência).
   * Restrições de unicidade (tentativas de duplicidade de chaves, nomes únicos ou vínculos exclusivos).
   * Integridade de relacionamento (ex: exclusão de entidades pai com filhos ativos, consistência de dados históricos).

5. **Ciclo de Vida e Transições de Estado (State Lifecycle & Transitions):**
   * Operações válidas permitidas apenas em estados específicos da entidade.
   * Tentativas de transição de estado proibidas (ex: pular etapas obrigatórias ou reverter estados terminais).
   * Operações sobre entidades arquivadas, canceladas ou inativas.

6. **Concorrência, Idempotência e Repetição de Ações (Idempotency & Concurrency):**
   * Repetição imediata da mesma requisição/ação (garantindo comportamento idempotente quando esperado).
   * Tentativas de submissão duplicada (ex: duplo clique ou envios consecutivos rápidos).
   * Consistência do estado diante de operações em sequência na mesma entidade.

7. **Tratamento de Falhas e Mensagens de Feedback (Error Handling & User Feedback):**
   * Garantia de que falhas de negócio retornam mensagens semânticas, claras e acionáveis para o usuário, sem expor dados internos de infraestrutura ou stack traces.
   * Preservação da atomicidade (se a operação falhar no meio, nenhuma alteração parcial de estado deve persistir).

---

## 3. Padrão Estrutural dos Casos de Uso (BDD / Gherkin)

Cada use case deve ser estruturado com:
- **ID:** `UC-S<Sprint>-<Numero>` (ex: `UC-S01-01`)
- **Título do Cenário:** Claro e autoexplicativo.
- **Categoria:** `Caminho Feliz` | `Edge Case & Limites` | `Validação de Entrada` | `Invariante de Domínio` | `Transição de Estado` | `Concorrência & Idempotência` | `Tratamento de Falhas` | `Segurança`
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
