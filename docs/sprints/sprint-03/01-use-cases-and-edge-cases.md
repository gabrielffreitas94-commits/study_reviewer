# Matriz de Casos de Uso e Cenários de Borda — Sprint 03
## Módulo: Perguntas Abertas & Repetição Espaçada (SRS Estrito — Fase 1 MVP)
### Projeto: Study Reviewer

---

## 1. Visão Geral e Escopo Exaustivo da Sprint 03

Esta matriz detalha os requisitos da **Sprint 03** definidos no [PRD.md](../../PRD.md) v7.0, no [ADR-001](../../docs/adrs/ADR-001-clean-architecture-layering.md), no [ADR-006](../../docs/adrs/ADR-006-google-oauth2-oidc-multitenancy.md) e na [SPEC Técnica](../../docs/specs/sprint-03-open-questions-srs-spec.md).

Após auditoria rigorosa com os **13 Especialistas de Engenharia** e expansão combinatória exaustiva de todos os subsistemas, esta matriz contempla **64 cenários BDD/Gherkin organizados nas 8 categorias normativas**, cobrindo 100% dos fluxos de sucesso, valores de borda matemáticos, entradas inválidas, concorrência, vetores de ataque OWASP, acessibilidade WCAG 2.1 AA e privacidade LGPD.

---

## 2. Matriz Completa de Casos de Uso e Cenários de Borda (BDD / Gherkin)

---

### Categoria 1: Caminho Feliz & Variações Válidas (Happy Path & Valid Variations)

#### UC-S03-01: Cadastro de Pergunta Aberta pelo Proprietário com Progresso Imediato
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / `CreateQuestionUseCase`
```gherkin
Cenário: Cadastro de nova pergunta aberta em tema próprio
  Dado que o estudante autenticado "Prof. Carlos" é o proprietário (owner) da matéria "Direito Constitucional"
  E existe um tema "Direitos Fundamentais" vinculado a esta matéria
  Quando o caso de uso CreateQuestion for acionado com topic_id, prompt="O que é o princípio da proporcionalidade?" e expected_answer="É um princípio hermenêutico composto por adequação, necessidade e proporcionalidade em sentido estrito."
  Então uma nova entidade Question é persistida com ID único UUIDv4
  E um registro de UserQuestionProgress é criado para Carlos com current_level=0 e next_review_date=hoje
  E a pergunta passa a constar imediatamente na fila de estudos do dia de Carlos
```

#### UC-S03-02: Consulta da Fila do Dia (Due Questions) com Ordenação Determinística
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / `GetDueQuestionsUseCase`
```gherkin
Cenário: Aluno consulta perguntas pendentes com next_review_date <= hoje
  Dado que o estudante possui 3 perguntas agendadas para datas passadas ou hoje (due)
  E possui 2 perguntas agendadas para amanhã (future)
  Quando o caso de uso GetDueQuestions for executado na data de referência "hoje"
  Então exatamente 3 perguntas são retornadas
  E a lista está estritamente ordenada por next_review_date ASC, current_level ASC, question_id ASC
  E a contagem de pendências para o badge da aba "Revisão" retorna o número 3
```

#### UC-S03-03: Promoção Estrita de Nível 0 para Nível 1 (+7 dias) com Score = 100
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Domínio / `SpacingPolicyService` & Aplicação / `ReviewQuestionUseCase`
```gherkin
Cenário: Estudante atinge score 100% em pergunta de Nível 0
  Dado que a pergunta está no Nível 0 (intervalo base de 1 dia)
  Quando o estudante submeter a nota 100 na data de revisão "2026-10-10"
  Então a pergunta é promovida para o Nível 1
  E a next_review_date é reagendada para "2026-10-17" (2026-10-10 + 7 dias)
  E o timestamp last_reviewed_at é registrado com a hora atual
```

#### UC-S03-04: Promoção Estrita de Nível 1 para Nível 2 (+15 dias) com Score = 100
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Estudante atinge score 100% em pergunta de Nível 1
  Dado que a pergunta está no Nível 1 (intervalo de 7 dias)
  Quando o estudante submeter a nota 100 na data de revisão "2026-10-10"
  Então a pergunta é promovida para o Nível 2
  E a next_review_date é reagendada para "2026-10-25" (2026-10-10 + 15 dias)
```

#### UC-S03-05: Promoção Estrita de Nível 2 para Nível 3 (+30 dias) com Score = 100
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Estudante atinge score 100% em pergunta de Nível 2
  Dado que a pergunta está no Nível 2 (intervalo de 15 dias)
  Quando o estudante submeter a nota 100 na data de revisão "2026-10-10"
  Então a pergunta é promovida para o Nível 3
  E a next_review_date é reagendada para "2026-11-09" (2026-10-10 + 30 dias)
```

#### UC-S03-06: Promoção Estrita de Nível 3 para Nível 4 (+60 dias) com Score = 100
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Estudante atinge score 100% em pergunta de Nível 3
  Dado que a pergunta está no Nível 3 (intervalo de 30 dias)
  Quando o estudante submeter a nota 100 na data de revisão "2026-10-10"
  Então a pergunta é promovida para o Nível 4
  E a next_review_date é reagendada para "2026-12-09" (2026-10-10 + 60 dias)
```

#### UC-S03-07: Promoção Estrita de Nível 4 para Nível 5 (+90 dias) com Score = 100
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Estudante atinge score 100% em pergunta de Nível 4
  Dado que a pergunta está no Nível 4 (intervalo de 60 dias)
  Quando o estudante submeter a nota 100 na data de revisão "2026-10-10"
  Então a pergunta é promovida para o Nível 5
  E a next_review_date é reagendada para "2027-01-08" (2026-10-10 + 90 dias)
```

#### UC-S03-08: Promoção Estrita de Nível 5 para Nível 6 (+180 dias) com Score = 100
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Estudante atinge score 100% em pergunta de Nível 5
  Dado que a pergunta está no Nível 5 (intervalo de 90 dias)
  Quando o estudante submeter a nota 100 na data de revisão "2026-10-10"
  Então a pergunta é promovida para o Nível 6
  E a next_review_date é reagendada para "2027-04-08" (2026-10-10 + 180 dias)
```

#### UC-S03-09: Revisão com Score 100 no Nível Máximo (Nível 6) Reagendando (+180 dias)
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Estudante atinge score 100% em pergunta já consolidada no Nível 6
  Dado que a pergunta está no Nível 6 (intervalo máximo de 180 dias)
  Quando o estudante submeter a nota 100 na data "2026-10-10"
  Então a pergunta permanece no Nível 6 (sem estourar o teto)
  E a next_review_date é reagendada para "2027-04-08" (2026-10-10 + 180 dias)
```

#### UC-S03-10: Revisão com Nota Parcial ou Erro (< 100%) nos Níveis 0 a 5 Mantendo o Nível
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Estudante obtém nota 75% em pergunta de Nível 3
  Dado que a pergunta está no Nível 3 (intervalo de 30 dias)
  Quando o estudante submeter score=75 na data "2026-10-10"
  Então a pergunta permanece no Nível 3 (sem avanço para o nível 4)
  E a next_review_date é reagendada para "2026-11-09" (2026-10-10 + 30 dias)
```

#### UC-S03-11: Estudo com Filtro Explícito por Matéria Pública com Provisionamento em Lote
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / `GetDueQuestionsUseCase`
```gherkin
Cenário: Aluno seleciona matéria pública para iniciar estudo ativo
  Dado que a matéria pública "História Geral" possui 20 perguntas cadastradas
  E o estudante visitante nunca estudou essa matéria anteriormente
  Quando o estudante acessar GET "/questions/study?subject_id={id_historia}"
  Então o sistema executa initialize_progress_for_questions em lote com ON CONFLICT DO NOTHING
  E as 20 perguntas passam a constar na fila com current_level=0 e next_review_date=hoje
```

#### UC-S03-12: Estudo com Filtro por Tema com Isolamento de Escopo
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / `GetDueQuestionsUseCase`
```gherkin
Cenário: Aluno filtra a fila de revisão por um tema específico
  Dado que o estudante possui perguntas vencidas nos temas "Direitos Reais" e "Contratos"
  Quando o estudante acessar GET "/questions/study?topic_id={id_contratos}"
  Então apenas as perguntas vinculadas ao tema "Contratos" são retornadas na fila
```

#### UC-S03-13: Conclusão de Todas as Revisões e Estado "Inbox Zero" com Próxima Data
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Adaptador Web / `GET /questions/study`
```gherkin
Cenário: Estudante conclui a última pergunta da fila do dia
  Dado que o estudante acabou de responder a última pergunta pendente da fila
  Quando a rota GET "/questions/study" for requisitada via HTMX
  Então a resposta HTTP 200 renderiza o componente comemorativo "Inbox Zero"
  E é exibida a mensagem "Tudo em dia por hoje! Nenhuma pergunta pendente."
  E o método get_next_review_date consulta o próximo vencimento e exibe "Próxima revisão em: {data}"
  E o badge da aba "Revisão" é atualizado para 0
```

#### UC-S03-14: Atualização Dinâmica do Badge na Topbar Desktop e Navbar Mobile via HTMX OOB
* **Categoria:** Caminho Feliz & Variações / UI
* **Camada Alvo:** Interface Web / Jinja2 `base.html` & HTMX OOB
```gherkin
Cenário: Contador de perguntas pendentes atualizado em tempo real
  Dado que o estudante possui 3 perguntas pendentes de revisão
  Quando a página carrega ou após submeter uma resposta
  Então o link da aba "Revisão" exibe um badge com o número "3" na topbar e na barra inferior mobile (grid de 4 colunas)
  E quando a última pergunta for respondida
  Então a resposta HTMX atualiza out-of-band (hx-swap-oob="true") o badge para 0
```

#### UC-S03-15: Edição de Pergunta pelo Proprietário Preservando Progresso SRS Existente
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / `UpdateQuestionUseCase`
```gherkin
Cenário: Autor atualiza o gabarito de uma pergunta já em estudo por alunos
  Dado que o autor edita o texto do expected_answer de uma pergunta existente
  Quando a alteração for salva com sucesso
  Então o texto da pergunta é atualizado no catálogo
  E os registros existentes em UserQuestionProgress para todos os estudantes mantêm seus níveis e datas inalterados
```

#### UC-S03-16: Exclusão de Pergunta pelo Proprietário com Limpeza em Cascata
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Aplicação / `DeleteQuestionUseCase`
```gherkin
Cenário: Autor remove pergunta de seu tema
  Dado que o autor solicita a exclusão de uma pergunta de sua propriedade
  Quando a exclusão for confirmada
  Então o registro em Question é removido
  E a cláusula ON DELETE CASCADE limpa os registros correspondentes em UserQuestionProgress
```

#### UC-S03-17: Visualização Read-Only de Perguntas de Matéria Pública por Visitante
* **Categoria:** Caminho Feliz & Variações
* **Camada Alvo:** Adaptador Web / `GET /topics/{id}/questions`
```gherkin
Cenário: Estudante visualiza o banco de questões de uma matéria pública alheia
  Dado que a matéria é pública (is_public=True) e pertence a outro autor
  Quando o estudante visitante acessar a listagem de perguntas do tema
  Então as perguntas são exibidas em modo leitura (read-only)
  E os botões de ação "Editar Pergunta" e "Excluir Pergunta" NÃO são renderizados no DOM
```

---

### Categoria 2: Cenários de Borda & Limites Matemáticos (Edge Cases & Boundary Values)

#### UC-S03-18: Penalidade de Regressão Severa no Nível 6 com Nota < 100%
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Estudante comete falha em pergunta de Nível 6 (180 dias)
  Dado que uma pergunta está no Nível 6
  Quando o estudante submeter score=99 (ou qualquer nota < 100) na data "2026-10-10"
  Então a pergunta sofre regressão estrita para o Nível 2
  E a next_review_date é reagendada para exatamente hoje + 15 dias ("2026-10-25")
```

#### UC-S03-19: Limiar Exato de Promoção: Score = 99% vs Score = 100%
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Comparação do comportamento no limiar de promoção
  Dado que duas perguntas idênticas estão no Nível 0 (intervalo 1 dia)
  Quando a primeira pergunta receber score=99
  Então ela permanece no Nível 0 e é reagendada para hoje + 1 dia
  Quando a segunda pergunta receber score=100
  Então ela é promovida para o Nível 1 e é reagendada para hoje + 7 dias
```

#### UC-S03-20: Limite Inferior de Nota: Score = 0% (Erro Absoluto) e Score = 1%
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Estudante erra integralmente a pergunta
  Dado que uma pergunta está no Nível 4 (intervalo 60 dias)
  Quando o estudante submeter score=0 (ou score=1) na data "2026-10-10"
  Então o score é aceito como válido
  E a pergunta permanece no Nível 4 com next_review_date reagendada para hoje + 60 dias
```

#### UC-S03-21: Todos os 5 Presets Neutros de Nota (0%, 25%, 50%, 75%, 100%) e Seus Resultados
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Teste exaustivo dos 5 presets de nota para pergunta no Nível 2 (+15d)
  Dado que cinco perguntas idênticas estão no Nível 2
  Quando a primeira receber 0%, ela permanece no Nível 2 (+15d)
  Quando a segunda receber 25%, ela permanece no Nível 2 (+15d)
  Quando a terceira receber 50%, ela permanece no Nível 2 (+15d)
  Quando a quarta receber 75%, ela permanece no Nível 2 (+15d)
  Quando a quinta receber 100%, ela avança para o Nível 3 (+30d)
```

#### UC-S03-22: Pergunta Vencida com Atraso Elevado (Overdue há 10, 30 e 90 dias) Reagendada a Partir de Hoje
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Domínio / `SpacingPolicyService` & Aplicação / `ReviewQuestionUseCase`
```gherkin
Cenário: Pergunta vencida há 45 dias respondida com sucesso hoje
  Dado que uma pergunta do Nível 2 (+15 dias) tinha next_review_date="2026-08-25"
  E a data de estudo real é "2026-10-10" (46 dias de atraso acumulado)
  Quando o estudante submeter score=100 em "2026-10-10"
  Então o novo nível passa a ser 3 (intervalo de 30 dias)
  E a nova data é calculada como 2026-10-10 + 30 dias = "2026-11-09" (calculada rigorosamente a partir da data real de resposta)
```

#### UC-S03-23: Limites Extremos de Tamanho de Prompt e Gabarito (1 caractere e 10.000 caracteres)
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Domínio / Entidade `Question`
```gherkin
Cenário: Validação de strings nos limites extremos
  Dado um prompt com exatamente 1 caractere "A" e expected_answer com 1 caractere "B"
  Quando a entidade Question for instanciada
  Então a pergunta é criada com sucesso
  Dado um prompt com exatamente 10.000 caracteres de texto Markdown válido
  Quando a entidade Question for instanciada
  Então a pergunta é aceita com sucesso sem truncamento
```

#### UC-S03-24: Rejeição de Revisão Prematura de Pergunta com Vencimento Futuro (next_review_date > hoje)
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Aplicação / `ReviewQuestionUseCase`
```gherkin
Cenário: Tentativa de responder pergunta antes da data de vencimento
  Dado que a pergunta possui next_review_date="2026-10-25" (agendada para o futuro)
  E a data atual de estudo é "2026-10-10"
  Quando o estudante tentar submeter uma revisão para esta pergunta via POST
  Então a operação é rejeitada com QuestionNotDueError
  E a resposta HTTP retorna código 400 Bad Request
  E nenhum avanço de nível ou data é efetuado
```

#### UC-S03-25: Reagendamento com Transição em Virada de Mês, Ano e Ano Bissexto
* **Categoria:** Cenários de Borda & Limites
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Cálculo de intervalo atravessando virada de ano e mês bissexto
  Dado uma revisão realizada em "2028-02-28" (ano bissexto) com avanço de 1 dia (+1d)
  Quando o cálculo for executado
  Então a nova data calculada é "2028-02-29"
  Dado uma revisão realizada em "2026-12-15" com avanço de 30 dias (+30d)
  Quando o cálculo for executado
  Então a nova data calculada é "2027-01-14" (virada de ano correta)
```

---

### Categoria 3: Entradas Inválidas & Rejeição Precoce (Invalid Inputs & Fast-Fail)

#### UC-S03-26: Rejeição de Nota Negativa (Score < 0) e Nota Acima do Teto (Score > 100)
* **Categoria:** Entradas Inválidas & Rejeição Precoce
* **Camada Alvo:** Domínio / `SpacingPolicyService`
```gherkin
Cenário: Tentativa de envio de score fora da faixa [0, 100]
  Quando o serviço SpacingPolicyService for invocado com score=-1 ou score=101
  Então a exceção InvalidScoreError é disparada imediatamente
  E nenhuma alteração de estado ou de banco é efetuada
```

#### UC-S03-27: Rejeição de Score em Formato Não-Numérico, Decimal ou Nulo (HTTP 422)
* **Categoria:** Entradas Inválidas & Rejeição Precoce
* **Camada Alvo:** Adaptador API / Web Controller
```gherkin
Cenário: Payload de revisão com valor inválido
  Quando o endpoint POST "/questions/{id}/review" receber score="cem", score=75.5 ou score=null
  Então o framework de validação rejeita a requisição precocemente com HTTP 422 Unprocessable Entity
```

#### UC-S03-28: Rejeição de Prompt Vazio ou Composto Exclusivamente por Espaços
* **Categoria:** Entradas Inválidas & Rejeição Precoce
* **Camada Alvo:** Domínio / Entidade `Question`
```gherkin
Cenário: Tentativa de criação com prompt em branco
  Quando o caso de uso CreateQuestion for invocado com prompt="   " (somente espaços) ou prompt=""
  Então a exceção InvalidPromptError é disparada
  E a requisição web/API retorna HTTP 422 Unprocessable Entity
```

#### UC-S03-29: Rejeição de Expected Answer Vazia ou Apenas Espaços
* **Categoria:** Entradas Inválidas & Rejeição Precoce
* **Camada Alvo:** Domínio / Entidade `Question`
```gherkin
Cenário: Tentativa de criação com gabarito em branco
  Quando o caso de uso CreateQuestion for invocado com expected_answer="   " ou expected_answer=""
  Então a exceção InvalidExpectedAnswerError é disparada
  E a requisição web/API retorna HTTP 422 Unprocessable Entity
```

#### UC-S03-30: Rejeição de Prompt ou Expected Answer Excedendo 10.000 Caracteres
* **Categoria:** Entradas Inválidas & Rejeição Precoce
* **Camada Alvo:** Domínio / Entidade `Question`
```gherkin
Cenário: Prompt com 10.001 caracteres
  Quando o caso de uso CreateQuestion for invocado com prompt de 10.001 caracteres
  Então a exceção InvalidPromptError é disparada por violação de tamanho máximo
```

#### UC-S03-31: Tentativa de Criação de Pergunta com Topic ID Inexistente (HTTP 404)
* **Categoria:** Entradas Inválidas & Rejeição Precoce
* **Camada Alvo:** Aplicação / `CreateQuestionUseCase`
```gherkin
Cenário: Criação de card apontando para topic_id inexistente
  Quando o caso de uso CreateQuestion for acionado com topic_id="00000000-0000-0000-0000-000000000000"
  Então é disparada a exceção EntityNotFoundError("Tema não encontrado")
  E a resposta da API retorna HTTP 404 Not Found
```

#### UC-S03-32: Tentativa de Revisão ou Consulta de Question ID Inexistente (HTTP 404)
* **Categoria:** Entradas Inválidas & Rejeição Precoce
* **Camada Alvo:** Aplicação / `ReviewQuestionUseCase`
```gherkin
Cenário: UUID de pergunta inexistente no banco
  Quando for solicitada a revisão de question_id="00000000-0000-0000-0000-000000000000"
  Então a exceção QuestionNotFoundError é lançada
  E a resposta HTTP retorna código 404 Not Found
```

#### UC-S03-33: Tentativa de Operação sem Autenticação ou com Sessão Expirada (HTTP 401)
* **Categoria:** Entradas Inválidas & Rejeição Precoce
* **Camada Alvo:** Infraestrutura / `get_current_user` Middleware
```gherkin
Cenário: Requisição sem token de autenticação
  Quando uma requisição não-autenticada acessar GET "/questions/study" ou POST "/questions/{id}/review"
  Então o middleware de segurança intercepta a chamada
  E a resposta retorna HTTP 401 Unauthorized ou redireciona para login
```

---

### Categoria 4: Concorrência, Idempotência & Race Conditions

#### UC-S03-34: Cliques Duplos Simultâneos de Revisão Tratados com Idempotência Atômica
* **Categoria:** Concorrência, Idempotência & Race Conditions
* **Camada Alvo:** Adaptador de Persistência / `SqlAlchemyQuestionProgressRepo`
```gherkin
Cenário: Cliques duplos acidentais no botão de confirmação
  Dado que um estudante envia duas requisições simultâneas de revisão para a mesma pergunta
  Quando a primeira requisição atualizar o registro e comitar a transação
  Então a segunda requisição identifica que a pergunta já foi atualizada na data corrente
  E a operação é tratada de forma idempotente sem corromper o nível ou saltar datas em duplicidade
```

#### UC-S03-35: Exclusão de Pergunta por seu Autor Enquanto Aluno Concorrente Envia Revisão
* **Categoria:** Concorrência, Idempotência & Race Conditions
* **Camada Alvo:** Aplicação / `ReviewQuestionUseCase`
```gherkin
Cenário: Autor exclui a pergunta enquanto outro estudante estava lendo
  Dado que o Estudante B está com o card da pergunta aberto na tela
  E o Autor A exclui a pergunta do sistema
  Quando o Estudante B submeter a nota de autoavaliação
  Então o caso de uso trata a ausência do registro retornando QuestionNotFoundError
  E a interface web instrui o estudante a avançar para a próxima pergunta da fila
```

#### UC-S03-36: Criação Concorrente de Matéria/Tema durante Cadastro de Pergunta
* **Categoria:** Concorrência, Idempotência & Race Conditions
* **Camada Alvo:** Aplicação / `CreateQuestionUseCase`
```gherkin
Cenário: Exclusão do tema pai durante a submissão de cadastro de pergunta
  Dado que o autor submete a criação de uma pergunta em um tema que é excluído concorrentemente
  Quando a transação tentar inserir o registro
  Então ocorre violação de chave estrangeira gerenciada com integridade
  E a aplicação retorna HTTP 404 informando que o tema não está mais disponível
```

#### UC-S03-37: Provisionamento JIT Concorrente da Mesma Pergunta Pública (ON CONFLICT DO NOTHING)
* **Categoria:** Concorrência, Idempotência & Race Conditions
* **Camada Alvo:** Adaptador de Persistência / `initialize_progress_for_questions`
```gherkin
Cenário: Duas abas do navegador abertas pelo mesmo aluno inicializando a mesma matéria pública
  Dado que o aluno abre simultaneamente duas abas para estudar a matéria pública X
  Quando ambas as requisições dispararem a rotina initialize_progress_for_questions
  Então a cláusula ON CONFLICT DO NOTHING absorve a duplicidade sem erro de chave duplicada
  E exatamente 1 registro de progresso por pergunta é persistido
```

---

### Categoria 5: Segurança, Sanitização & Controle de Acesso (OWASP / Multi-tenancy / IDOR)

#### UC-S03-38: Tentativa de Criação de Pergunta em Tema de Matéria Alheia (Anti-IDOR / 403 Forbidden)
* **Categoria:** Segurança & Controle de Acesso
* **Camada Alvo:** Aplicação / `CreateQuestionUseCase`
```gherkin
Cenário: Usuário tenta cadastrar pergunta em tema de matéria pertencente a outro autor
  Dado que o Tema 1 pertence à matéria do Usuário A
  Quando o Usuário B (autenticado) enviar POST "/topics/{Tema_1}/questions"
  Então a aplicação verifica que subject.owner_id != user_id
  E a operação lança ResourceOwnershipError retornando HTTP 403 Forbidden
```

#### UC-S03-39: Tentativa de Edição ou Exclusão de Pergunta de Matéria Alheia (Anti-IDOR / 403 Forbidden)
* **Categoria:** Segurança & Controle de Acesso
* **Camada Alvo:** Aplicação / `UpdateQuestionUseCase` & `DeleteQuestionUseCase`
```gherkin
Cenário: Usuário tenta editar ou excluir pergunta de matéria alheia
  Dado que a pergunta pertence à matéria privada do Usuário A
  E o Usuário B (autenticado) envia um DELETE ou PUT para "/questions/{id}"
  Quando a camada de aplicação verificar a autoria da matéria
  Então é lançada a exceção ResourceOwnershipError
  E a resposta HTTP é 403 Forbidden com mensagem de auditoria registrada
```

#### UC-S03-40: Tentativa de Listagem de Perguntas de Tema em Matéria Privada Alheia (Anti-IDOR / 403 Forbidden)
* **Categoria:** Segurança & Controle de Acesso
* **Camada Alvo:** Aplicação / `ListQuestionsByTopicUseCase`
```gherkin
Cenário: Usuário não-proprietário tenta listar perguntas de matéria privada
  Dado que o Tema B pertence à Matéria Privada do Usuário A
  Quando o Usuário B autenticado requisitar GET "/topics/{topic_id}/questions"
  Então a camada de aplicação dispara ResourceOwnershipError
  E o acesso é negado com HTTP 403 Forbidden
```

#### UC-S03-41: Tentativa de Revisão de Pergunta Pertencente a Matéria Privada Alheia (Anti-IDOR / 403 Forbidden)
* **Categoria:** Segurança & Controle de Acesso
* **Camada Alvo:** Aplicação / `ReviewQuestionUseCase`
```gherkin
Cenário: Usuário tenta revisar pergunta privada pertencente a outro estudante
  Dado que a pergunta X pertence a uma matéria com is_public=False de propriedade do Usuário A
  Quando o Usuário B (autenticado) enviar POST "/questions/{X}/review"
  Então a verificação subject.can_be_studied_by(user_id) falha
  E a operação dispara ResourceOwnershipError retornando HTTP 403 Forbidden
```

#### UC-S03-42: Sanitização Contra XSS em Prompt e Gabarito com nh3 no Write-Time
* **Categoria:** Segurança & Controle de Acesso
* **Camada Alvo:** Adaptador / `MarkdownSanitizerService` (nh3 no Write-time)
```gherkin
Cenário: Tentativa de injeção de payload malicioso em prompt ou expected_answer
  Dado um enunciado contendo: "<script>alert('xss')</script> Veja a pergunta: <img src=x onerror=alert(1)>"
  Quando o conteúdo for processado para persistência
  Então as tags <script> e os manipuladores de eventos "onerror" são sumariamente removidos
  E apenas texto puro e elementos seguros autorizados são persistidos e renderizados no DOM
```

#### UC-S03-43: Neutralização de Imagens com Protocolos Inseguros (HTTP, javascript:, data:, file:)
* **Categoria:** Segurança & Controle de Acesso
* **Camada Alvo:** Adaptador / `MarkdownSanitizerService`
```gherkin
Cenário: Inclusão de imagens via Markdown com protocolo inseguro
  Dado um texto contendo imagem: "![perigo](javascript:stealCookies())" ou "![http](http://inseguro.com/foto.png)"
  Quando a sanitização for executada
  Então qualquer imagem cujo src não inicie com "https://" tem o atributo src neutralizado
```

#### UC-S03-44: Garantia Anti-SSRF (Servidor Backend Nunca Executa Download de URLs de Imagens)
* **Categoria:** Segurança & Controle de Acesso
* **Camada Alvo:** Infraestrutura / `MarkdownSanitizerService`
```gherkin
Cenário: Prompt com links para recursos internos ou de nuvem
  Dado que um prompt contenha "![meta](https://169.254.169.254/latest/meta-data/)"
  Quando a pergunta for sanitizada e renderizada
  Então o servidor backend NÃO efetua qualquer requisição de rede para a URL
  E o endereço é tratado estritamente como string para renderização client-side no navegador
```

#### UC-S03-45: Mitigação de Força Bruta e Rajada de Requisições via Rate Limiting (60 req/min)
* **Categoria:** Segurança & Controle de Acesso
* **Camada Alvo:** Infraestrutura / `RateLimiterMiddleware`
```gherkin
Cenário: Envio em rajada de revisões de perguntas
  Dado que o estudante envia mais de 60 requisições de revisão em um intervalo de 60 segundos
  Quando a 61ª requisição atingir o servidor
  Então a requisição é interceptada pelo Rate Limiter
  E a resposta retorna HTTP 429 Too Many Requests com cabeçalho Retry-After
```

#### UC-S03-46: Proteção contra Negação de Serviço por Payload Bombing (HTTP 413 se > 128 KB)
* **Categoria:** Segurança & Controle de Acesso
* **Camada Alvo:** Infraestrutura / `FastAPI Payload Guard`
```gherkin
Cenário: Tentativa de envio de payload HTTP massivo
  Quando um usuário enviar uma requisição com Content-Length superior a 128 KB para criar pergunta
  Então o servidor rejeita sumariamente a requisição com HTTP 413 Payload Too Large
  E a CPU não é onerada com parsing de dados excessivos
```

---

### Categoria 6: Resiliência de Estado, Falhas de Infraestrutura & Degradação Graciosa

#### UC-S03-47: Falha Transitória de Conexão com o Banco Durante o Commit de Revisão com Rollback
* **Categoria:** Resiliência & Degradação Graciosa
* **Camada Alvo:** Infraestrutura / `DatabaseSessionManager`
```gherkin
Cenário: Queda transitória de banco durante o envio da nota
  Dado que ocorre uma desconexão temporária com o PostgreSQL no momento do commit
  Quando a requisição de revisão falhar
  Então a transação sofre rollback automático
  E a interface HTMX exibe uma notificação de alerta com botão "Tentar Novamente"
  E o estado visual da nota no slider é preservado na tela do aluno
```

#### UC-S03-48: Tratamento de Timezone na Transição da Meia-Noite (23:59 vs 00:01) com Datas Puras
* **Categoria:** Resiliência & Degradação Graciosa
* **Camada Alvo:** Aplicação / `IClockService`
```gherkin
Cenário: Estudo realizado próximo à meia-noite (23:59 vs 00:01)
  Dado que as datas de revisão são operadas como Date puras no padrão UTC/Servidor
  Quando uma revisão é realizada às 23:59 do dia D e a próxima pergunta é avaliada às 00:01 do dia D+1
  Então cada cálculo de SRS utiliza a data de calendário exata em que foi confirmada
  E a consistência dos intervalos é mantida matematicamente
```

#### UC-S03-49: Prevenção de Cumulative Layout Shift (Zero CLS) na Expansão do Card e Imagens
* **Categoria:** Resiliência & Degradação Graciosa / Performance
* **Camada Alvo:** Adaptador Web & MarkdownSanitizerService
```gherkin
Cenário: Renderização de pergunta com imagem externa em Markdown
  Dado que o enunciado da pergunta contém uma imagem segura "![diagrama](https://img.externa.com/diagrama.png)"
  Quando a pergunta for renderizada na interface de estudos
  Então a imagem possui o atributo loading="lazy" e está contida em container com altura mínima reservada
  E a revelação da resposta ou carregamento da imagem mantém a métrica CLS <= 0.1 (zero layout shift perceptível)
```

#### UC-S03-50: Degradação Graciosa do Cliente ao Receber Resposta Parcial ou Timeout
* **Categoria:** Resiliência & Degradação Graciosa
* **Camada Alvo:** Interface Web / HTMX Event Listeners
```gherkin
Cenário: Timeout de rede durante o swap HTMX
  Dado que a conexão do aluno cai no instante em que ele clica em "Confirmar e Próxima"
  Quando o HTMX disparar o evento htmx:responseError ou htmx:sendError
  Então o spinner é removido e os controles são reabilitados
  E surge um toast de erro: "Falha na comunicação. Sua resposta não foi perdida; clique em tentar novamente."
```

---

### Categoria 7: Acessibilidade (WCAG 2.1 AA) & Experiência de Uso (UX/UI)

#### UC-S03-51: Fluxo em Duas Fases (Active Recall): Bloqueio de Nota Antes de Revelar Gabarito
* **Categoria:** Acessibilidade & UX
* **Camada Alvo:** Interface Web / Jinja2 + JS
```gherkin
Cenário: Estudante tenta interagir com a nota antes de revelar o gabarito
  Dado que o card da pergunta aberta está carregado na tela em estado inicial (não-revelado)
  Então o container de resposta esperada está oculto (aria-expanded="false")
  E os 5 botões de preset e o slider de nota estão desabilitados (disabled)
  E a tecla de atalho numérico (1 a 5) não produz efeito na nota
  Quando o estudante acionar o botão "Revelar Resposta Esperada"
  Então o gabarito oficial é exibido com foco programático movido para o painel de avaliação
  E os presets e o slider tornam-se imediatamente interativos (disabled removido)
```

#### UC-S03-52: Sincronização Bidirecional e Estados Visuais dos 5 Presets Neutros e Slider
* **Categoria:** Acessibilidade & UI
* **Camada Alvo:** Interface Web / Componente de Autoavaliação
```gherkin
Cenário: Aluno altera o valor pelo slider e pelos presets
  Dado que a resposta esperada está revelada
  Quando o aluno clicar no preset "50%"
  Então o valor do slider é alterado para 50
  E o display de texto exibe "50%"
  E o botão "50%" recebe aria-pressed="true" e classes de destaque visual neutro
  E os botões "0%", "25%", "75%" e "100%" recebem aria-pressed="false"
  Quando o aluno arrastar o slider para 80%
  Então o display de texto exibe "80%"
  E nenhum dos presets 50% ou 75% fica em estado aria-pressed="true"
```

#### UC-S03-53: Operabilidade 100% por Teclado e Foco sem Perda (Focus Retention)
* **Categoria:** Acessibilidade (WCAG 2.1 AA)
* **Camada Alvo:** Interface Web / Jinja2 + JS Acessível
```gherkin
Cenário: Estudante navega todo o fluxo de revisão exclusivamente via teclado
  Dado que a página de estudos é carregada
  Quando o estudante pressiona a tecla "Tab"
  Então o foco navega ordenadamente pelo botão "Revelar Resposta Esperada"
  E ao acionar com "Espaço" ou "Enter", a resposta é expandida
  E o foco programático é movido para o container de autoavaliação sem Focus Loss
  E os contornos visuais de foco (focus-visible) permanecem evidentes
```

#### UC-S03-54: Conformidade Estrita com WCAG 2.1.4 (Atalhos 1..5 Ativos Apenas com Resposta Revelada)
* **Categoria:** Acessibilidade (WCAG 2.1 AA)
* **Camada Alvo:** Interface Web / Listener de Teclado
```gherkin
Cenário: Uso de atalhos rápidos e guarda anti-digitação
  Dado que a resposta esperada está revelada
  Quando o estudante pressionar "3"
  Então a nota 50% é ativada imediatamente
  Dado que o estudante está com o cursor focado em um campo <input> ou <textarea>
  Quando o estudante pressionar "3"
  Então o caractere "3" é digitado no campo e o atalho de nota NÃO é disparado
```

#### UC-S03-55: Anúncio Completo em Live Region (aria-live="polite") para Leitores de Tela
* **Categoria:** Acessibilidade (WCAG 2.1 AA)
* **Camada Alvo:** Interface Web / Templates WAI-ARIA
```gherkin
Cenário: Usuário de leitor de tela acompanha as atualizações dinâmicas
  Dado que o estudante utiliza leitor de tela (NVDA / VoiceOver)
  Quando a resposta esperada é revelada
  Então o elemento `#srs-announcer[aria-live="polite"]` recebe a mensagem "Resposta esperada revelada. Utilize o slider ou as teclas de 1 a 5 para atribuir sua nota."
  Quando a nota é confirmada e a próxima pergunta carrega
  Então a live region anuncia "Próxima pergunta carregada: Pergunta 2 de 4."
```

#### UC-S03-56: Padrão WAI-ARIA Disclosure (aria-expanded e aria-controls) na Revelação
* **Categoria:** Acessibilidade (WCAG 2.1 AA)
* **Camada Alvo:** Interface Web / Componente de Revelação
```gherkin
Cenário: Conformidade WAI-ARIA no botão de revelação
  Dado que o card está fechado
  Então o botão possui aria-expanded="false" e aponta para aria-controls="expected-answer-section"
  Quando o botão for ativado
  Então aria-expanded passa a "true" e a seção vinculada se torna visível
```

#### UC-S03-57: Contraste de Cores Superior a 4.5:1 nos 5 Estados dos Presets em Modo Claro e Escuro
* **Categoria:** Acessibilidade (WCAG 2.1 AA) & UI
* **Camada Alvo:** Interface Web / Tailwind CSS
```gherkin
Cenário: Verificação de contraste cromático
  Dado os presets neutros nos temas Light e Dark
  Quando inspecionados os pares de cores de texto e fundo nos estados default, hover, active e focus
  Então a taxa de contraste calculada é superior a 4.5:1 em todos os estados
```

#### UC-S03-58: Respeito à Preferência do Sistema por Movimento Reduzido (prefers-reduced-motion)
* **Categoria:** Acessibilidade (WCAG 2.1 AA)
* **Camada Alvo:** Interface Web / Estilos CSS
```gherkin
Cenário: Usuário com sensibilidade vestibular e prefers-reduced-motion ativo
  Dado que o sistema operacional está com a preferência de movimento reduzido ativada
  Quando a pergunta for transicionada via HTMX
  Então nenhuma animação de translação ou deslizamento é executada (transition: none !important)
```

#### UC-S03-59: Responsividade Mobile-First em Telas Estreitas (<= 360px) com Grid de 4 Colunas
* **Categoria:** Acessibilidade & UI
* **Camada Alvo:** Interface Web / Tailwind CSS Layout
```gherkin
Cenário: Visualização em smartphone compacto
  Dado um dispositivo móvel com viewport de 360px de largura
  Quando a tela de revisão for renderizada
  Então os 5 botões de preset se organizam em grid sem quebrar texto
  E a barra de navegação inferior exibe 4 colunas perfeitamente alinhadas
  E nenhuma barra de rolagem horizontal é gerada na página
```

---

### Categoria 8: Privacidade de Dados (LGPD) & Retenção de Histórico

#### UC-S03-60: Expurgo em Cascata de Todo o Progresso do Usuário na Exclusão da Conta (Art. 18, VI LGPD)
* **Categoria:** Privacidade de Dados (LGPD)
* **Camada Alvo:** Banco de Dados / DDL `user_question_progress`
```gherkin
Cenário: Exclusão de conta de estudante
  Dado que um estudante possui 50 registros de progresso em UserQuestionProgress
  Quando a conta do usuário for permanentemente excluída da base de dados
  Então a cláusula ON DELETE CASCADE remove automaticamente todos os seus registros de progresso
  E nenhum dado residual ou órfão permanece armazenado no sistema
```

#### UC-S03-61: Emissão de Telemetria Estruturada sem Vazamento de Conteúdo Intelectual ou PII
* **Categoria:** Observabilidade & Privacidade de Dados
* **Camada Alvo:** Aplicação / `ReviewQuestionUseCase` & Telemetria
```gherkin
Cenário: Registro de telemetria após submissão de revisão
  Quando o caso de uso ReviewQuestion for concluído com sucesso
  Então é emitido um log estruturado em JSON contendo event="srs_question_reviewed", traceparent, user_id, question_id, score, previous_level, new_level e duration_ms
  E os textos de prompt e expected_answer NÃO são incluídos no log para proteção de privacidade e propriedade intelectual
```

#### UC-S03-62: Isolamento Estrito de Consultas sem Vazamento de Métricas de Outros Estudantes
* **Categoria:** Privacidade de Dados (LGPD)
* **Camada Alvo:** Aplicação / `GetDueQuestionsUseCase`
```gherkin
Cenário: Consulta à fila de estudos não expõe dados de terceiros
  Quando o Estudante A solicita suas perguntas para revisão
  Então a consulta SQL filtra estritamente user_id = :current_user_id
  E nenhuma informação de desempenho, notas ou datas de outros estudantes é trafegada no payload
```

#### UC-S03-63: Suporte à Portabilidade de Dados de Progresso SRS em Formato JSON Interoperável (Art. 18, V)
* **Categoria:** Privacidade de Dados (LGPD)
* **Camada Alvo:** Adaptador API REST / Export Endpoint
```gherkin
Cenário: Usuário solicita a exportação de seu histórico de aprendizado
  Dado que o estudante possui perguntas estudadas no sistema
  Quando o estudante requisitar GET "/api/v1/users/me/study-data"
  Então a API retorna um JSON estruturado contendo a lista de perguntas revisadas, níveis atuais e próximas datas
```

#### UC-S03-64: Limpeza Integral de Cache e Armazenamento Client-Side no Logout (Clear-Site-Data)
* **Categoria:** Privacidade de Dados (LGPD)
* **Camada Alvo:** Adaptador Web / `POST /auth/logout`
```gherkin
Cenário: Estudante efetua logout em computador compartilhado
  Quando o estudante acionar o logout
  Então a resposta HTTP inclui o cabeçalho Clear-Site-Data: "cache", "storage"
  E todos os dados temporários de estudo em cache ou armazenamento local são eliminados do navegador
```
