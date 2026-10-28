---
name: study-questions-json
description: Generates deep, complex active-recall study questions in strict JSON format with rich GitHub Flavored Markdown (code snippets, tables, bold concepts, lists, headings) for import into the RPG Study Tree / Grimoire.
---

# Study Questions JSON Generator

This skill instructs an AI to generate deep, high-yield active-recall questions for the Spaced Repetition System (SRS) and Study Arena, exported exclusively in a valid JSON array format with GitHub Flavored Markdown.

## Objectives & Question Quality Principles

1. **Active Recall & Deep Retrieval**: Avoid superficial trivia, pure definition queries, or trivial true/false prompts. Craft questions that require synthetic thinking, diagnosis, architectural reasoning, and trade-off evaluation.
2. **Scenario & Engineering Focus**: Present concrete scenarios, architecture diagrams, buggy code snippets, real-world edge cases, and performance bottlenecks.
3. **Structured Evaluation Criteria (Gabarito)**: The `expected_answer` must not simply be a single sentence. It should be a comprehensive, structured rubric breaking down key criteria, technical trade-offs, and corrective insights.
4. **Markdown Formatting**: Use rich GitHub Flavored Markdown:
   - `### Headings` for sections and rubrics.
   - `**bold**` for critical terminology and concepts.
   - Code blocks with language syntax tags (e.g., ```` ```python ````, ```` ```sql ````, ```` ```typescript ````, ```` ```rust ````).
   - Bulleted lists (`- item`) for scannable review criteria.
   - `> Blockquotes` for caveats, performance impacts, or security considerations.
   - Markdown tables for comparative trade-offs.

---

## Output Format Specification

The AI must output **EXCLUSIVELY** a valid JSON array of objects. Do not wrap the response with introductory or concluding commentary outside the JSON.

```json
[
  {
    "prompt": "### Contexto / Problema\nEnunciado aprofundado com **termos-chave** e código...\n```python\n# Trecho para análise ou depuração\n```",
    "expected_answer": "### Critérios de Avaliação\n- **Ponto 1:** Explicação técnica objetiva.\n- **Ponto 2:** Análise de trade-off ou complexidade assintótica `O(n)`.\n> **Atenção:** Ressalva prática importante."
  }
]
```

### Strict JSON Escaping Rules
- Strings must be valid JSON:
  - Newlines must be encoded as `\n`.
  - Double quotes inside markdown must be escaped as `\"`.
  - Backslashes (e.g. in LaTeX or regex) must be escaped as `\\`.

---

## Prompting Template for AI

When generating questions for a topic, instruct the AI with the following prompt:

```markdown
Você é um especialista em Ciência da Computação e Engenharia de Software encarregado de criar questões de recordação ativa de alto nível para o sistema de repetição espaçada (SRS).

Gere de 3 a 5 questões aprofundadas sobre o tópico solicitado.

Critérios Obrigatórios:
1. Nível Avançado: Foque em cenários reais, depuração de código, trade-offs arquiteturais, falhas em produção ou casos de borda.
2. Formato: Retorne EXCLUSIVAMENTE um array JSON no formato:
[
  {
    "prompt": "Enunciado em Markdown...",
    "expected_answer": "Critérios de avaliação detalhados em Markdown..."
  }
]
3. Markdown Rico:
   - Use '###' para estruturar cabeçalhos.
   - Use '**negrito**' para conceitos capitais.
   - Use blocos de código com identificador de linguagem.
   - Use listas com '-' e citações '>' para notas críticas.
4. Strings JSON Válidas: Escape quebras de linha com '\\n' e aspas duplas com '\\\"'.
```

---

## Example JSON Output

```json
[
  {
    "prompt": "### Cenário de Concorrência em PostgreSQL\n\nEm um sistema de pagamentos de alta concorrência, duas transações executam simultaneamente sob o nível de isolamento **Read Committed**:\n\n```sql\n-- Transação A                     -- Transação B\nBEGIN;                             BEGIN;\nSELECT saldo FROM conta WHERE id=1;\n                                   UPDATE conta SET saldo = saldo - 100 WHERE id=1;\n                                   COMMIT;\nUPDATE conta SET saldo = saldo + 50 WHERE id=1;\nCOMMIT;\n```\n\nQual problema clássico de anomalia de concorrência ocorre neste cenário e qual abordagem arquitetural previne a inconsistência sem degradar a vazão global?",
    "expected_answer": "### Critérios Técnicos de Avaliação\n\n- **Anomalia Identificada:** *Lost Update* (Atualização Perdida). Como a leitura inicial foi desprotegida, a Transação A sobrescreve o débito da Transação B com base em um saldo defasado lido anteriormente.\n- **Soluções Recomendadas:**\n  1. **Atualização Atômica In-Place:** `UPDATE conta SET saldo = saldo + 50 WHERE id = 1;` (evita leitura seguida de escrita na aplicação).\n  2. **Pessimistic Locking:** `SELECT saldo FROM conta WHERE id = 1 FOR UPDATE;` garantindo que outras transações aguardem.\n  3. **Optimistic Locking:** Controle de versão (`version_id` ou timestamp).\n> **Nota:** O isolamento *Repeatable Read* ou *Serializable* abortaria a transação com erro de serialização (`could not serialize access due to concurrent update`), exigindo retry na aplicação."
  },
  {
    "prompt": "### Análise de Complexidade & Cache-Locality\n\nCompare a travessia de uma **Matriz 2D** em memória implementada em linguagens como C ou Rust:\n\n```c\n// Ordem Linha-Coluna (Row-major)\nfor (int i = 0; i < N; i++) {\n    for (int j = 0; j < N; j++) sum += matrix[i][j];\n}\n\n// Ordem Coluna-Linha (Column-major)\nfor (int j = 0; j < N; j++) {\n    for (int i = 0; i < N; i++) sum += matrix[i][j];\n}\n```\n\nEmbora ambas tenham complexidade teórica `O(N^2)`, por que a ordem de iteração impacta drasticamente o tempo real de execução em processadores modernos?",
    "expected_answer": "### Critérios de Gabarito\n\n- **Cache Lines e Espacialidade:** A memória de arrays 2D em C/Rust é contígua por linhas (*row-major*). Ao acessar `matrix[i][j]` sequencialmente, blocos inteiros de cache (geralmente 64 bytes) são pré-carregados pelo hardware prefetcher (*spatial locality*).\n- **Cache Misses:** A iteração por colunas (`matrix[i][j]` variando `i`) causa saltos de `N * sizeof(int)` bytes na memória a cada acesso, invalidando a linha de cache e provocando *L1/L2 cache misses* a cada iteração.\n- **Impacto Prático:** A versão Row-major é tipicamente de 5x a 20x mais rápida para valores grandes de `N`."
  }
]
```
