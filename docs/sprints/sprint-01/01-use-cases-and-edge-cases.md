# Matriz de Casos de Uso e Cenários de Borda — Sprint 01
## Módulo: MVP Flashcards em Produção (Clean Architecture & Gap Indexing)
### Projeto: Study Reviewer

---

## 1. Visão Geral e Escopo da Sprint 01

Esta matriz detalha os requisitos da **Sprint 01** definidos no [PRD.md](../../PRD.md) v5.2 e na [SPEC Técnica](../../specs/sprint-01-flashcards-spec.md). Cobre a taxonomia completa de Casos de Uso em formato BDD/Gherkin abrangendo o núcleo de domínio, os fluxos de aplicação, adaptadores de persistência, interface web e segurança.

---

## 2. Matriz de Casos de Uso e Cenários de Borda (BDD / Gherkin)

### Categoria 1: Caminho Feliz & Variações Válidas (Happy Path & Valid Variations)

#### UC-S01-01: Cadastro de Matéria com Nome Válido
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / Domínio
```gherkin
Cenário: Cadastro bem-sucedido de nova matéria
  Dado que o usuário deseja cadastrar a matéria "Direito Constitucional"
  Quando o comando CreateSubject for executado com o nome "Direito Constitucional"
  Então uma nova entidade Subject é criada com ID único UUIDv4
  E o nome é persistido exatamente como "Direito Constitucional"
  E a data de criação é registrada como a data atual
```

#### UC-S01-02: Cadastro de Tema Vinculado a uma Matéria Existente
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / Domínio
```gherkin
Cenário: Cadastro de tema com vínculo à matéria
  Dado que existe uma matéria cadastrada com ID "sub-123"
  Quando o comando CreateTopic for executado com subject_id="sub-123" e nome "Direitos Fundamentais"
  Então uma nova entidade Topic é criada com ID único UUIDv4
  E o vínculo com a matéria subject_id="sub-123" é estabelecido
  E o nome "Direitos Fundamentais" é persistido
```

#### UC-S01-03: Cadastro do Primeiro Flashcard na Pool (N=0)
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Domínio / FlashcardPoolService
```gherkin
Cenário: Inserção do primeiro card em uma pool vazia
  Dado que a pool de flashcards para o tema está vazia (total_cards = 0)
  Quando um novo flashcard com frente "O que é CF/88?" e verso "Constituição da República Federativa do Brasil" for cadastrado
  Então o FlashcardPoolService atribui a posição inicial 100 ao novo card
  E o card é persistido com position = 100
```

#### UC-S01-04: Navegação Sequencial de Estudo (Próximo Card)
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / GetNextFlashcardUseCase
```gherkin
Cenário: Avanço para o próximo card da rodada
  Dado que existe uma sessão ativa com current_position = 100
  E a pool contém cards nas posições [100, 200, 300]
  Quando o caso de uso GetNextFlashcard for acionado
  Então o card da posição 200 é retornado
  E a sessão é atualizada com current_position = 200
  E o indicador round_shuffled permanece False
```

#### UC-S01-05: Alternar Frente e Verso (Flip Card)
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Adaptador Web / HTMX
```gherkin
Cenário: Revelar a resposta do card atual
  Dado que o card com ID "card-1" está em exibição mostrando a frente "O que é CF/88?"
  Quando o usuário acionar o comando de flip (via barra de espaço, clique ou touch)
  Então o componente HTMX retorna o verso "Constituição da República Federativa do Brasil"
  E o estado visual é alternado suavemente sem recarregamento de página
```

---

### Categoria 2: Cenários de Borda & Limites Matemáticos (Edge Cases & Boundary Values)

#### UC-S01-06: Inserção em Pool Unitária (N=1)
* **Categoria:** Cenários de Borda & Limites Matemáticos
* **Camada Alvo:** Domínio / FlashcardPoolService
```gherkin
Cenário: Novo card em pool com exatamente 1 card existente
  Dado que a pool possui exatamente 1 card com position = 100
  Quando o novo card for cadastrado e o sorteio definir índice 0 (cabeça)
  Então o FlashcardPoolService calcula a nova posição como floor(100 / 2) = 50
  E o novo card é persistido com position = 50 sem alterar o card existente
```

#### UC-S01-07: Inserção nos Primeiros 10% em Pool Grande (N=100)
* **Categoria:** Cenários de Borda & Limites Matemáticos
* **Camada Alvo:** Domínio / FlashcardPoolService
```gherkin
Cenário: Cálculo do índice alvo nos primeiros 10%
  Dado uma pool contendo 100 flashcards ordenados por position
  Quando calculate_target_index for invocado com N=100
  Então o índice sorteado pertence ao intervalo fechado [0, 10]
  E a nova posição é calculada como o ponto médio entre os cards adjacentes daquele índice
```

#### UC-S01-08: Inserção na Cauda da Pool (Após o Último Card)
* **Categoria:** Cenários de Borda & Limites Matemáticos
* **Camada Alvo:** Domínio / FlashcardPoolService
```gherkin
Cenário: Inserção após o último card existente
  Dado que o card anterior possui position = 400 e não há próximo card
  Quando calculate_new_position for chamado com prev_pos = 400 e next_pos = None
  Então a nova posição calculada é 400 + 100 = 500
```

#### UC-S01-09: Inserção no Início Absoluto com Espaço Reduzido
* **Categoria:** Cenários de Borda & Limites Matemáticos
* **Camada Alvo:** Domínio / FlashcardPoolService
```gherkin
Cenário: Inserção antes do primeiro card com posição ímpar
  Dado que o primeiro card da fila possui position = 3
  Quando um novo card for inserido antes dele (prev_pos = None, next_pos = 3)
  Então a nova posição calculada é floor(3 / 2) = 1
  E needs_rebalance é verificado para prevenção de colisão futura
```

---

### Categoria 3: Validação de Entrada & Rejeição de Payloads (Input & Schema Validation)

#### UC-S01-10: Rejeição de Matéria com Nome Muito Curto ou Vazio
* **Categoria:** Validação de Entrada & Rejeição de Payloads
* **Camada Alvo:** Domínio / Subject
```gherkin
Cenário: Tentativa de criar matéria com nome com menos de 2 caracteres
  Dado que a entrada informada para o nome da matéria é "A" ou "   "
  Quando a validação de domínio da entidade Subject for executada
  Então uma exceção DomainValidationError é disparada
  E a mensagem explica que o nome deve possuir entre 2 e 100 caracteres
```

#### UC-S01-11: Limpeza Automática de Espaços nas Extremidades (Trimming)
* **Categoria:** Validação de Entrada & Rejeição de Payloads
* **Camada Alvo:** Domínio / Entities
```gherkin
Cenário: Sanitização de espaços em branco antes e depois do texto
  Dado que a entrada informada é "   Matemática Financeira   "
  Quando a entidade Subject for instanciada
  Então o nome armazenado é exatamente "Matemática Financeira"
```

#### UC-S01-12: Validação de Limites de Caracteres no Flashcard
* **Categoria:** Validação de Entrada & Rejeição de Payloads
* **Camada Alvo:** Domínio / Flashcard
```gherkin
Cenário: Frente ou verso com tamanho excedendo os limites máximos
  Dado que o texto da frente possui 5.001 caracteres ou o verso possui 10.001 caracteres
  Quando a criação do Flashcard for solicitada
  Então uma exceção DomainValidationError é lançada indicando o campo inválido
```

#### UC-S01-13: Suporte Completo a Caracteres UTF-8, Acentos e Símbolos
* **Categoria:** Validação de Entrada & Rejeição de Payloads
* **Camada Alvo:** Domínio / Adapters
```gherkin
Cenário: Flashcard com fórmulas matemáticas, quebras de linha e emojis
  Dado um flashcard com frente "Qual é a fórmula de Bhaskara? 📐" e verso "x = (-b ± √(b² - 4ac)) / (2a)\nExemplo: a=1, b=-5, c=6"
  Quando o card for cadastrado e persistido
  Então todos os caracteres Unicode, quebras de linha e símbolos são preservados integralmente
```

---

### Categoria 4: Invariantes de Domínio & Regras de Negócio (Business Rules & Domain Invariants)

#### UC-S01-14: Unicidade de Matéria por Nome
* **Categoria:** Invariantes de Domínio & Regras de Negócio
* **Camada Alvo:** Aplicação / CreateSubjectUseCase
```gherkin
Cenário: Tentativa de duplicar matéria com o mesmo nome
  Dado que já existe uma matéria cadastrada com o nome "História do Brasil"
  Quando o comando CreateSubject for executado com o nome "História do Brasil" (mesmo em maiúsculas/minúsculas)
  Então uma exceção DuplicateEntityError é lançada
  E nenhum novo registro é criado no banco
```

#### UC-S01-15: Unicidade de Tema no Âmbito da Mesma Matéria
* **Categoria:** Invariantes de Domínio & Regras de Negócio
* **Camada Alvo:** Aplicação / CreateTopicUseCase
```gherkin
Cenário: Tentativa de criar tema repetido na mesma matéria
  Dado que a matéria "Biologia" já possui um tema "Genética"
  Quando o usuário tentar cadastrar outro tema "Genética" na mesma matéria "Biologia"
  Então uma exceção DuplicateEntityError é lançada
  Mas é permitido criar um tema "Genética" em outra matéria diferente
```

#### UC-S01-16: Posicionamento Positivo Obrigatório (Position >= 1)
* **Categoria:** Invariantes de Domínio & Regras de Negócio
* **Camada Alvo:** Domínio / Flashcard
```gherkin
Cenário: Garantia de posição positiva no Gap Indexing
  Dado qualquer cálculo ou atribuição de posição no Flashcard
  Quando o valor resultante for menor ou igual a zero
  Então o sistema ajusta a posição para o valor mínimo permitido de 1
```

---

### Categoria 5: Ciclo de Vida, Histórico & Transições de Estado (State Lifecycle)

#### UC-S01-17: Conclusão de Rodada e Disparo de Shuffle Completo
* **Categoria:** Ciclo de Vida, Histórico & Transições de Estado
* **Camada Alvo:** Aplicação / GetNextFlashcardUseCase & FlashcardPoolService
```gherkin
Cenário: Fim de rodada após o último card da fila
  Dado que a pool possui 3 cards nas posições [100, 200, 300]
  E a sessão atual está na posição current_position = 300 na rodada 1
  Quando o caso de uso GetNextFlashcard for acionado
  Então o FlashcardPoolService identifica o fim da rodada
  E executa o shuffle geral de todos os 3 cards
  E renumera as posições para múltiplos de 100 ([100, 200, 300]) na nova ordem aleatória
  E atualiza a sessão incrementando round_number para 2 com current_position = 100
  E retorna o primeiro card da nova rodada com round_shuffled = True
```

#### UC-S01-18: Exclusão de Flashcard no Meio da Rodada
* **Categoria:** Ciclo de Vida, Histórico & Transições de Estado
* **Camada Alvo:** Aplicação / DeleteFlashcardUseCase
```gherkin
Cenário: Exclusão do card atualmente sob revisão
  Dado que a sessão de estudo está no card com ID "card-2" e position = 200
  E a pool possui cards nas posições [100, 200, 300]
  Quando DeleteFlashcard for executado para "card-2"
  Então o card é removido da persistência
  E a sessão avança automaticamente o ponteiro para o próximo card disponível (position = 300)
```

#### UC-S01-19: Exclusão do Último Card da Rodada
* **Categoria:** Ciclo de Vida, Histórico & Transições de Estado
* **Camada Alvo:** Aplicação / DeleteFlashcardUseCase
```gherkin
Cenário: Exclusão do último card restante na rodada atual
  Dado que a sessão está no último card da rodada (position = 300)
  Quando esse card for excluído
  Então o card é removido
  E a rodada se encerra acionando o shuffle completo dos cards remanescentes
  E o round_number é incrementado para 2
```

---

### Categoria 6: Concorrência, Idempotência & Mecânica de Fila (Concurrency & Queue Mechanics)

#### UC-S01-20: Rebalanceamento Preventivo por Esgotamento de Gap
* **Categoria:** Concorrência, Idempotência & Mecânica de Fila
* **Camada Alvo:** Domínio / FlashcardPoolService
```gherkin
Cenário: Detecção de colisão quando gap <= 1
  Dado que após sucessivas inserções dois cards consecutivos possuem posições 101 e 102 (diferença = 1)
  Quando FlashcardPoolService.needs_rebalance for avaliado
  Então a função retorna True
  E a rotina rebalance_positions redistribui todos os cards em múltiplos uniformes de 100 ([100, 200, 300...]) preservando a ordem relativa
```

#### UC-S01-21: Rebalanceamento Preventivo quando Primeira Posição Atinge <= 1
* **Categoria:** Concorrência, Idempotência & Mecânica de Fila
* **Camada Alvo:** Domínio / FlashcardPoolService
```gherkin
Cenário: Detecção de esgotamento na cabeça da fila
  Dado que o primeiro card da lista atingiu position = 1
  Quando needs_rebalance for executado
  Então o serviço retorna True sinalizando necessidade imediata de redistribuição
```

---

### Categoria 7: Busca, Filtros, Ordenação & Escopo (Search, Filtering & Scope)

#### UC-S01-22: Estudo em Escopo Global (Todas as Matérias)
* **Categoria:** Busca, Filtros, Ordenação & Escopo
* **Camada Alvo:** Aplicação / GetNextFlashcardUseCase
```gherkin
Cenário: Sessão de estudo global sem filtro de matéria ou tema
  Dado que o usuário inicia os estudos sem selecionar matéria (subject_id_filter = None)
  Quando a pool de cards for carregada
  Então todos os flashcards do sistema são incluídos na rotação sequencial da sessão
```

#### UC-S01-23: Estudo Filtrado por Matéria Específica
* **Categoria:** Busca, Filtros, Ordenação & Escopo
* **Camada Alvo:** Aplicação / GetNextFlashcardUseCase
```gherkin
Cenário: Sessão de estudo restrita a uma matéria
  Dado que o usuário seleciona a matéria "Direito Civil" (ID "sub-civil")
  Quando os cards da sessão forem carregados
  Então apenas cards pertencentes aos temas da matéria "Direito Civil" são apresentados
```

#### UC-S01-24: Estudo Filtrado por Tema Específico
* **Categoria:** Busca, Filtros, Ordenação & Escopo
* **Camada Alvo:** Aplicação / GetNextFlashcardUseCase
```gherkin
Cenário: Sessão de estudo restrita a um tema
  Dado que o usuário seleciona o tema "Contratos" (ID "topic-contratos")
  Quando a pool for consultada
  Então apenas flashcards associados exclusivamente ao tema "Contratos" são retornados
```

---

### Categoria 8: Tratamento de Falhas, Resiliência & Feedback ao Usuário (Error Handling & User Feedback)

#### UC-S01-25: Tentativa de Estudo em Pool Vazia (EmptyPoolError)
* **Categoria:** Tratamento de Falhas, Resiliência & Feedback ao Usuário
* **Camada Alvo:** Aplicação / Domínio
```gherkin
Cenário: Início de sessão em matéria/tema sem nenhum card cadastrado
  Dado que a matéria selecionada não possui flashcards cadastrados
  Quando o usuário requisitar o início do estudo
  Então o sistema lança a exceção EmptyPoolError
  E a interface apresenta um estado visual amigável convidando o usuário a criar o primeiro card
```

#### UC-S01-26: Busca por Entidade Inexistente (EntityNotFoundError)
* **Categoria:** Tratamento de Falhas, Resiliência & Feedback ao Usuário
* **Camada Alvo:** Aplicação / Domínio
```gherkin
Cenário: Consulta por flashcard com UUID que não existe
  Dado que é solicitada a exclusão ou consulta do card com ID "00000000-0000-0000-0000-000000000000"
  Quando o caso de uso for processado
  Então a exceção EntityNotFoundError é lançada sem vazar stack trace de banco
```

---

### Categoria 9: Segurança, Sanitização & Proteção de Dados (Security & Data Protection)

#### UC-S01-27: Sanitização de Conteúdo contra XSS na Frente e Verso
* **Categoria:** Segurança & Proteção de Dados
* **Camada Alvo:** Infraestrutura / Sanitização
```gherkin
Cenário: Injeção de tags de script ou eventos maliciosos em flashcard
  Dado que o usuário submete um card com frente "Pergunta <script>alert('xss')</script>" e verso "Resposta <img src=x onerror=alert(1)>"
  Quando o payload passar pela camada de sanitização defensiva (nh3)
  Então as tags perigosas de script e atributos de evento inline são neutralizados
  E o texto seguro é persistido sem execução de código malicioso
```

#### UC-S01-28: Criptografia Autenticada com AES-256-GCM para Dados Protegidos
* **Categoria:** Segurança & Proteção de Dados
* **Camada Alvo:** Infraestrutura / Criptografia
```gherkin
Cenário: Cifragem e decifragem segura com tag de autenticação
  Dado uma chave secreta de 256 bits e um texto confidencial
  Quando a cifra AES-256-GCM cifrar o conteúdo com IV/Nonce exclusivo
  Então o texto cifrado gerado possui integridade autenticada
  E qualquer modificação indevida no ciphertext causa falha na decifragem
```

#### UC-S01-29: Cabeçalhos de Segurança HTTP na Aplicação Web
* **Categoria:** Segurança & Proteção de Dados
* **Camada Alvo:** Infraestrutura / Middleware HTTP
```gherkin
Cenário: Resposta HTTP com headers de segurança defensivos
  Dado qualquer requisição recebida pela aplicação web FastAPI
  Quando a resposta HTTP for retornada ao cliente
  Então os headers X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Referrer-Policy e Content-Security-Policy estão presentes
```

---

## 3. Rastreabilidade com os Requisitos da Sprint 01

| ID Caso | Requisito do PRD v5.2 / SPEC | Componente Alvo |
| :--- | :--- | :--- |
| **UC-S01-01 a 02** | CRUD e Taxonomia de Matérias/Temas | `Subject`, `Topic`, `CreateSubjectUseCase`, `CreateTopicUseCase` |
| **UC-S01-03, 06 a 09** | Gap Indexing e Inserção nos Primeiros 10% | `FlashcardPoolService.calculate_new_position` |
| **UC-S01-04, 05** | Navegação Sequencial e Flip HTMX | `GetNextFlashcardUseCase`, Web Controller `/study` |
| **UC-S01-10 a 13** | Invariantes de Entidades e Validação | Entidades de Domínio (`domain/entities.py`) |
| **UC-S01-14 a 16** | Unicidades e Posições Numéricas | Casos de Uso e Repositórios |
| **UC-S01-17** | Fim de Rodada com Shuffle e Incremento | `FlashcardPoolService.execute_round_shuffle` |
| **UC-S01-18, 19** | Exclusão de Card no Meio ou Fim da Fila | `DeleteFlashcardUseCase` |
| **UC-S01-20, 21** | Rebalanceamento Preventivo da Pool | `FlashcardPoolService.needs_rebalance` e `rebalance_positions` |
| **UC-S01-22 a 24** | Escopo Global ou Filtrado por Matéria/Tema | `FlashcardPoolSession` e `IFlashcardRepository.list_pool` |
| **UC-S01-25, 26** | Tratamento de Pool Vazia e Entidade Ausente | Exceções de Domínio |
| **UC-S01-27 a 29** | Blindagem XSS, AES-256-GCM e Headers HTTP | `src/infrastructure/security/` |

---

### 🛡️ Validação Técnica de QA (qa-use-cases-validator)
* **Status:** `[APROVADO PARA TDD]`
* **Data da Auditoria:** 2026-10-02
* **Parecer:** A matriz com 29 casos de uso foi auditada integralmente. Todas as 8 categorias obrigatórias foram cobertas com critérios determinísticos, entradas explícitas e asserções testáveis. As regras matemáticas de Gap Indexing (inserção nos 10%, rebalanceamento preventivo, múltiplos de 100 e shuffle ao fim de ciclo) e as diretrizes de Clean Architecture foram rigorosamente mapeadas. O ciclo de desenvolvimento TDD está formalmente liberado para início.
