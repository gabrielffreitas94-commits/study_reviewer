---
name: python-performance-auditor
description: Audits code changes for Python runtime efficiency, asymptotic algorithmic complexity (Big-O), memory allocation, generator usage, and idiomatic high-performance practices.
---

# Python Performance Auditor (Skill do Especialista de Performance Python)

Esta skill é operada pelo **Especialista de Performance de Programação Python** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para `staging`.

Seu objetivo é inspecionar o código-fonte em busca de ineficiências algorítmicas, complexidade assintótica excessiva ($\mathcal{O}(n^2)$ desnecessária), uso ineficiente de memória, instanciações redundantes em laços críticos e desrespeito às melhores práticas de alta performance do Python 3.13+.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * Módulos de domínio (`src/domain/`), casos de uso (`src/application/`) e infraestrutura (`src/infrastructure/`).
  * Testes de unidade e benchmark/profiling em `tests/`.
* **Gatilho de Execução:** Auditoria final de PR para código Python.

---

## 2. Checklist Exaustivo de Auditoria de Performance Python

O especialista inspeciona o código respondendo a seis dimensões essenciais:

1. **Complexidade Algorítmica ($\mathcal{O}$ de Tempo):**
   * *Existem buscas lineares repetidas dentro de laços?* Buscas com operador `in` sobre listas (`O(n)`) repetidas $m$ vezes resultam em complexidade quadrática ($\mathcal{O}(n \times m)$). Exigir conversão prévia para `set` ou `dict` para lookup $\mathcal{O}(1)$.
   * *O fatiamento e indexação de dados são ótimos?* Ordenações frequentes devem ser evitadas em favor de min/max heaps ou estruturas ordenadas quando apropriado.
   * *Embaralhamento e algoritmos matemáticos:* Algoritmos como Fisher-Yates devem ter complexidade linear $\mathcal{O}(n)$ estrita.

2. **Alocação de Memória e Geradores:**
   * *O código aloca listas inteiras quando poderia consumir geradores?* Iterações em múltiplas etapas devem preferir expressões geradoras `(x for x in ...)` ou `itertools.islice`, reduzindo consumo de pico de memória RAM.
   * *O código evita cópias defensivas desnecessárias?* Uso desnecessário de `deepcopy` ou clonagem repetida de grandes coleções em memória deve ser banido.

3. **Uso de Estruturas de Dados Ideais:**
   * *Dicionários e Conjuntos:* Uso de `dict` e `set` nativos de alta performance do Python para desduplicação e correlação de entidades.
   * *Coleções Especializadas:* Uso de `collections.deque` quando inserções/remoções nas duas extremidades forem frequentes ($\mathcal{O}(1)$ vs $\mathcal{O}(n)$ em listas).
   * *Imutabilidade e Tuplas:* Uso de `tuple` em detrimento de `list` para sequências estáticas.

4. **Caching e Pré-computação:**
   * *Funções puras de cálculo intenso utilizam cache determinístico?* Uso de `@functools.lru_cache(maxsize=...)` ou `@functools.cache` para cálculos determinísticos repetitivos.
   * *Compilação prévia de Regex:* Expressões regulares devem ser compiladas em nível de módulo (`re.compile`), nunca recriadas a cada chamada de função.

5. **Serialização e Mapeamento Enxuto:**
   * *A conversão entre entidades e DTOs é direta?* Evitar múltiplos saltos de serialização e desserialização (`dict -> pydantic -> dict -> json`).
   * *Sanitização de strings:* Sanitizações com bibliotecas em Rust/C (ex: `nh3`) devem ser invocadas na borda e não repetidas internamente no domínio.

6. **Operações Concorrentes e Event Loop:**
   * *Funções assíncronas do FastAPI estão livres de bloqueios de CPU pesados?* Operações de criptografia intensiva ou processamento de arquivos volumosos em contexto async devem ser delegadas para threadpools (`asyncio.to_thread`) quando necessário.

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **11** | **Especialista de Performance Python** | `[APROVADO]` | Performance em Python auditada com sucesso. Complexidade assintótica O(1)/O(n) em todos os fluxos críticos, uso eficiente de geradores e hashing para buscas, zero loops aninhados redundantes e aderência aos padrões de alto desempenho do Python 3.13+. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **11** | **Especialista de Performance Python** | `[BLOQUEANTE]` | Ineficiência de execução identificada: [descrever o loop O(n^2), uso indevido de listas para busca, falta de geradores ou alocação excessiva de memória]. Refatoração para complexidade ótima exigida antes do merge. |
```
