# Casos de Uso, BDD & Matriz de Edge Cases — Sprint 08

## 1. BDD — Avaliação Semântica Aterrada de Texto e Tarifação de Tokens

### Cenário 1: Avaliação de resposta correta com aterramento bibliográfico
- **Dado** que o estudante "Alice" possui 1.000 tokens disponíveis em seu saldo,
- **E** existe uma pergunta vencida sobre "Mitocôndrias" com chunks de conhecimento cadastrados no tema,
- **Quando** Alice submete sua resposta: "A mitocôndria é a organela responsável pela respiração celular e produção de ATP via fosforilação oxidativa.",
- **Então** o sistema retém 500 tokens preventivamente,
- **E** a IA avalia a resposta contra os chunks do tema conferindo nota 100 com citações das fontes,
- **E** consome 220 tokens reais na inferência,
- **E** liquida a operação debitando 220 tokens e liberando a retenção (saldo restante: 780 tokens),
- **E** o nível SRS da pergunta progride de 0 para 1 com agendamento para 1 dia.

### Cenário 2: Rejeição imediata por saldo insuficiente de tokens (Anti-Inadimplência)
- **Dado** que o estudante "Bob" possui apenas 50 tokens disponíveis,
- **Quando** Bob submete uma resposta para avaliação com IA exigindo 500 tokens de garantia,
- **Então** o sistema rejeita a operação com status HTTP 402 (Payment Required) e erro `InsufficientTokensError`,
- **E** nenhuma chamada ao modelo de IA é realizada,
- **E** o saldo de Bob permanece inalterado em 50 tokens.

### Cenário 3: Resiliência em Cold-Start (Tema sem Fontes de Conhecimento)
- **Dado** que o tema "Direito Tributário" não possui livros ou resumos cadastrados,
- **Quando** o estudante submete resposta para uma pergunta desse tema,
- **Então** o sistema utiliza o campo `expected_answer` da pergunta como base factual canônica,
- **E** emite nota e feedback embasado no gabarito sem interromper o fluxo de estudo.

### Cenário 4: Estorno integral de tokens em caso de falha transitória da IA
- **Dado** que o estudante submete resposta e tem 500 tokens retidos,
- **Quando** o provedor de IA retorna erro 503 (serviço indisponível),
- **Então** o sistema captura a falha,
- **E** executa o estorno do hold de 500 tokens (`refund_hold`),
- **E** o saldo do usuário volta integralmente ao valor original sem perdas financeiras.

---

## 2. Matriz de Edge Cases

| # | Edge Case | Comportamento Esperado |
|---|-----------|------------------------|
| **EC-01** | Tentativa de avaliação em pergunta futura (não vencida) | Lança `QuestionNotDueError` antes de qualquer retenção de tokens. |
| **EC-02** | Resposta em branco ou contendo apenas espaços | Lança `DomainValidationError` sem reter tokens. |
| **EC-03** | Resposta com tentativa de Prompt Injection (`Ignore previous instructions...`) | Sanitização de entrada + encapsulamento XML `<student_answer_untrusted>` + instruções de sistema forçando foco exclusivo no conteúdo. |
| **EC-04** | Usuário novo sem registro prévio no ledger | Provisionamento JIT transparente com saldo inicial padrão (ex: 1.000 tokens de cortesia). |
| **EC-05** | Tentativa de depósito de valor negativo ou zero | Lança `DomainValidationError("Quantidade de tokens para depósito deve ser positiva.")`. |
| **EC-06** | Múltiplas requisições simultâneas do mesmo usuário esgotando saldo | Lock/controle atômico de hold impede que saldo fique negativo. |
