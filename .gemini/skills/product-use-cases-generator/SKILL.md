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

1. **Caminho Feliz & Variações Válidas (Happy Path & Valid Variations):**
   * **Fluxo Nominal Primário:** Fluxo ideal completo, do acionamento inicial à confirmação e persistência íntegra do estado final.
   * **Variações de Parâmetros:** Execução com todos os campos opcionais preenchidos vs. execução com apenas os campos obrigatórios.
   * **Valores Padrão (*Defaults*):** Aplicação correta de valores padrão quando o usuário/sistema não os informa explicitamente.
   * **Operação Unitária vs. Operação em Lote:** Comportamento ao processar uma única entidade vs. múltiplas entidades simultaneamente (quando aplicável pelo PRD).
   * **Ordenação Padrão Determinística:** Garantia de que listagens e coleções retornam na ordenação de negócio estipulada (ex: por data de criação, ordem alfabética ou prioridade).

2. **Cenários de Borda e Fronteiras Matemáticas (Edge Cases & Boundary Values):**
   * **Limites de Coleções:** Listas vazias (estado zero / *empty state*), coleções com 1 elemento, coleções exatamente no tamanho de corte de página/lote, coleções cheias ou volumosas.
   * **Fronteiras Numéricas:** Valor mínimo permitido, valor máximo permitido, valor imediatamente inferior ao mínimo e imediatamente superior ao máximo.
   * **Fórmulas e Arredondamentos:** Comportamento diante de divisão inteira, arredondamento para cima/baixo (`floor`, `ceil`, `round`), proporções percentuais e precisão decimal.
   * **Fronteiras Temporais e Calendário:**
     * Transições de início e fim de período (23:59:59 para 00:00:00).
     * Viradas de dia, mês e ano.
     * Anos bissextos (ex: 29 de fevereiro).
     * Datas puramente calendárias (`YYYY-MM-DD`) e independência estrita de fuso horário / horário de verão.
   * **Ciclos e Contadores:** Comportamento no primeiro ciclo/rodada, na virada de ciclo e quando contadores atingem limites de saturação.

3. **Validação de Entrada e Rejeição de Payloads (Input & Schema Validation):**
   * **Strings e Textos:** Strings vazias (`""`), strings compostas exclusivamente por espaços em branco (`"   "`), strings com espaços nas extremidades (exigindo *trimming*), limites mínimos de caracteres e limite máximo excedido por 1 caractere.
   * **Caracteres Especiais e Internacionalização:** Strings contendo caracteres acentuados (UTF-8 completo), emojis, símbolos tipográficos, quebras de linha (`\n`, `\r\n`) e caracteres com necessidade de escape.
   * **Tipagem Estrita:** Envio de texto em campos numéricos, booleanos representados como texto, números com ponto flutuante em campos inteiros e valores negativos onde se exigem números naturais.
   * **Formatação de Dados:** Datas fora do formato exigido (ex: `DD/MM/YYYY`), datas calendárias inexistentes (ex: 31 de abril, 30 de fevereiro), formatos de chaves inválidos.
   * **Identificadores e Chaves:** UUIDs com formato incorreto, strings aleatórias em campos de ID e referências a entidades inexistentes.
   * **Integridade do Payload:** Omissão de atributos obrigatórios e envio de atributos não mapeados (*payload pollution* ou campos desconhecidos).

4. **Invariantes de Domínio e Regras de Negócio (Business Rules & Domain Invariants):**
   * **Restrições Estritas do PRD:** Tentativas diretas de violar qualquer regra, fórmula, cálculo ou trava explícita documentada no PRD.
   * **Restrições de Unicidade:** Tentativa de duplicar nomes, títulos, chaves de negócio ou combinações que devem ser únicas dentro do mesmo escopo.
   * **Integridade Referencial Negocial:** Tentativa de vincular recursos a entidades que não pertencem ao mesmo proprietário/contexto.
   * **Imutabilidade de Registros:** Tentativas de mutação em campos que devem permanecer congelados após a criação (ex: data de criação, autor, valores históricos).
   * **Regras de Bloqueio:** Bloqueio de exclusão ou alteração de entidades que possuam dependentes ativos ou dados históricos protegidos.

5. **Ciclo de Vida, Histórico e Transições de Estado (State Lifecycle & Historical Traceability):**
   * **Operações por Estado:** Ações permitidas exclusivamente em determinado estado da entidade (ex: ativo, inativo, rascunho, publicado, arquivado).
   * **Transições Proibidas:** Tentativas de pular etapas obrigatórias de um fluxo ou reverter transições irreversíveis/terminais.
   * **Entidades Arquivadas / Soft-delete:** Comportamento de leitura, listagem e mutação ao interagir com entidades desativadas ou marcadas como excluídas.
   * **Congelamento Histórico:** Garantia de que alterações no nome ou atributos de uma entidade pai não modifiquem os registros históricos desnormalizados já gravados no passado.

6. **Concorrência, Idempotência e Comportamento de Fila (Concurrency, Idempotency & Queue Mechanics):**
   * **Repetição Imediata da Mesma Ação:** Envio repetido da mesma requisição (duplo clique do usuário ou retry de rede), garantindo idempotência sem duplicar registros ou efeitos colaterais.
   * **Concorrência sobre a Mesma Entidade:** Atualizações quase simultâneas sobre o mesmo recurso, garantindo que o estado final seja íntegro.
   * **Mecânica de Fila:** Inserção em posições específicas, consumo ordenado (FIFO / prioridade), esvaziamento total da fila e reinício ordenado de ciclos.

7. **Busca, Filtros, Ordenação e Paginação (Search, Filtering, Sorting & Pagination):**
   * **Busca Textual:** Busca por termo exato, busca por prefixo/termo parcial e insensibilidade a maiúsculas/minúsculas (*case-insensitivity*).
   * **Busca Vazia:** Busca por termo inexistente retornando lista vazia sem erros.
   * **Filtros Combinados:** Aplicação de múltiplos filtros simultâneos (ex: status + data + categoria) e filtros com valores mutuamente exclusivos.
   * **Paginação:** Acesso à primeira página, páginas intermediárias, última página, solicitação de página além do total disponível e alteração da quantidade de itens por página.

8. **Tratamento de Falhas, Resiliência e Feedback ao Usuário (Error Handling, Resilience & User Feedback):**
   * **Mensagens Semânticas e Polidas:** Toda falha de negócio deve retornar mensagens claras, amigáveis e explicativas, sem jargões de banco de dados, stack traces ou vazamento de arquitetura interna.
   * **Atomicidade Negocial:** Em caso de erro no meio de uma operação que envolva múltiplos passos, o sistema deve reverter integralmente o estado, sem deixar dados órfãos ou inconsistentes.
   * **Recurso Não Encontrado:** Tratamento claro e semântico quando uma entidade requisitada não existe (ex: resposta 404 semântica de negócio).

---

## 3. Padrão Estrutural dos Casos de Uso (BDD / Gherkin)

Cada use case deve ser estruturado com:
- **ID:** `UC-S<Sprint>-<Numero>` (ex: `UC-S01-01`)
- **Título do Cenário:** Claro e autoexplicativo.
- **Categoria:** `Caminho Feliz & Variações` | `Edge Case & Limites` | `Validação de Entrada` | `Invariante de Domínio` | `Transição de Estado & Histórico` | `Concorrência & Idempotência` | `Busca & Filtros` | `Tratamento de Falhas` | `Segurança`
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
