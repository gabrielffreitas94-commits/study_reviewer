# ADR-002: Mecânica de Pool Dinâmica de Flashcards com Gap Indexing (Múltiplos de 100)

* **Status:** `Proposto` (Aguardando aprovação do usuário)
* **Data:** 2026-10-02
* **Autor:** Especialista Arquiteto
* **Contexto Técnico:** [PRD.md](file:///c:/Users/Pichau/Desktop/study_reviewer/PRD.md) v5.2 e [SPEC Sprint 01](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/specs/sprint-01-flashcards-spec.md)

---

## 1. Contexto e Problema
A mecânica de Flashcards da Sprint 01 exige uma **Pool Contínua por Rodadas**:
1. Quando um novo card é criado, ele deve ser inserido aleatoriamente nos **primeiros 10%** da fila para revisão rápida.
2. O usuário revisa card a card sequencialmente até o final da lista.
3. Ao concluir o último card, a pool inteira passa por um **shuffle geral** e inicia uma nova rodada imprevisível.

Se adotássemos uma estratégia ingênua de ordenação sequencial estrita (`position = 1, 2, 3...`), a inserção de um card na posição 5 de uma pool de 5.000 cards exigiria atualizar os índices de todos os 4.995 cards subsequentes ($O(N)$ updates em banco, gerando locks de tabela e lentidão desnecessária).

---

## 2. Decisão Arquitetural
Adotar a estratégia de **Gap Indexing** (espaçamento numérico com múltiplos de 100) para o campo `position` na tabela de flashcards:

1. **Atribuição Inicial com Gaps de 100:**
   * Na inicialização ou após cada shuffle geral de rodada, os cards recebem posições: `100, 200, 300, 400, 500...`.
2. **Inserção nos Primeiros 10% por Ponto Médio ($O(1)$ Insert):**
   * Sorteia-se o índice alvo entre $0$ e $\max(1, \lfloor 0.1 \times N \rfloor)$.
   * Calcula-se a nova posição como o ponto médio inteiro entre o card anterior e o posterior:
     $$pos_{novo} = pos_{ant} + \lfloor (pos_{prox} - pos_{ant}) / 2 \rfloor$$
   * A inserção ocorre com um único comando `INSERT`, sem alterar nenhum outro registro no banco.
3. **Resiliência e Tratamento de Edge Cases:**
   * **Pool Vazia ($N=0$):** O primeiro card recebe `position = 100`.
   * **Pool Unitária ($N=1$):** Novo card recebe `position = 50` ou `position = 200`.
   * **Inserção no Início Absoluto:** Recebe $\lfloor pos_{primeiro} / 2 \rfloor$. Se $pos_{primeiro} \le 1$, dispara rebalanceamento.
   * **Esgotamento de Gap ($pos_{prox} - pos_{ant} \le 1$):** Em caso extremo de saturação consecutiva no mesmo intervalo, o sistema dispara um rebalanceamento uniforme de todos os cards em múltiplos de 100. Como cada fim de rodada já realiza o shuffle completo com redistribuição em múltiplos de 100, a saturação na prática é raríssima.
   * **Exclusão de Card:** Deleta o card e o ponteiro da sessão simplesmente avança para o próximo `position > current_position`. Se for o último card da lista, encerra a rodada e aciona o shuffle.
4. **Persistência de Sessão:**
   * Criar a entidade `FlashcardPoolSession` persistida em banco, guardando `current_position`, `round_number` e os filtros de matéria/tema.

---

## 3. Consequências e Trade-offs

### Impactos Positivos:
* **Performance $O(1)$:** Inserções de novos cards nos primeiros 10% custam exatamente uma query de inserção, sem travar o banco.
* **Persistência Confiável de Sessão:** O usuário pode fechar o navegador no meio da rodada e continuar exatamente de onde parou em qualquer dispositivo.
* **Simplicidade Relacional:** Não depende de estruturas exóticas de dados, funcionando com um simples índice numérico em `position`.

### Custos / Impactos Negativos:
* **Necessidade de Rebalanceamento Preventivo:** Requer lógica no `FlashcardPoolService` para verificar se a distância entre posições consecutivas atingiu $\le 1$ e redistribuir em múltiplos de 100 quando necessário. *Garantido por testes unitários exaustivos.*
