# Matriz de Casos de Uso e Cenários de Borda — Sprint 04
## Módulo: Auditoria Histórica de Performance & Hub de Desempenho (Métricas & Compliance LGPD)
### Projeto: Study Reviewer

---

## 1. Visão Geral da Matriz

Esta matriz de especificação funcional detalha todos os cenários de uso, regras de negócio e casos extremos da **Sprint 04**, conforme estabelecido no [PRD.md](../../PRD.md) v7.0 (Seção 4 e Marco 4), [ADR-009](../adrs/ADR-009-audit-logs-and-historical-retention.md) e na [SPEC Técnica da Sprint 04](../specs/sprint-04-audit-logs-spec.md).

---

## 2. Casos de Uso em Formato BDD / Gherkin

### 2.1 Categoria 1: Caminho Feliz & Variações Válidas (Happy Path)

#### `UC-S04-01`: Registro Atômico de Log de Auditoria na Revisão Bem-sucedida
* **Categoria:** `Caminho Feliz & Variações`
* **Camada Alvo:** `Aplicação / Domínio`
```gherkin
Cenário: Registro automático e indelével de log ao concluir revisão de pergunta aberta
  Dado que um estudante autenticado "user-123" revisa uma pergunta "q-001" da matéria "Direito Civil" e tema "Contratos"
  E a pergunta estava previamente no Nível 2
  Quando o estudante submete a nota 100 no endpoint de revisão na data 2026-10-07
  Então o progresso do estudante é avançado para o Nível 3 com vencimento em 2026-11-06 (hoje + 30d)
  E um registro em "review_audit_logs" é criado contendo:
    | user_id    | question_id | subject_id | topic_id | historical_subject_name | historical_topic_name | score | level_before | level_after | evaluation_mode | review_date |
    | "user-123" | "q-001"     | "subj-01"  | "top-01" | "Direito Civil"         | "Contratos"           | 100   | 2            | 3           | "MANUAL"        | 2026-10-07  |
  E a operação é concluída em transação atômica única no banco relacional.
```

#### `UC-S04-02`: Obtenção Completa de Estatísticas do Estudante no Hub de Desempenho
* **Categoria:** `Caminho Feliz & Variações`
* **Camada Alvo:** `Aplicação / Controladores`
```gherkin
Cenário: Estudante acessa a aba "Desempenho" e visualiza KPIs consolidados
  Dado que o estudante possui 50 revisões registradas, sendo 40 com nota 100 (80% de retenção)
  E possui 12 perguntas no Nível 4, 5 perguntas no Nível 5 e 2 perguntas no Nível 6 (19 perguntas em Retenção Madura)
  E realizou revisões em 15 datas distintas
  Quando o estudante requisita o endpoint "GET /performance" ou "GET /api/v1/performance/stats"
  Então o sistema retorna HTTP 200 com os dados:
    | retention_rate | mature_questions_count | total_reviews_count | active_days_count |
    | 80.0           | 19                     | 50                  | 15                |
  E a distribuição por níveis SRS reflete com exatidão o acervo atual do estudante.
```

#### `UC-S04-03`: Exportação Integral de Dados em Formato JSON (LGPD Art. 18)
* **Categoria:** `Caminho Feliz & Variações`
* **Camada Alvo:** `Aplicação / Controladores`
```gherkin
Cenário: Estudante solicita download de seus dados em JSON para portabilidade
  Dado que o estudante autenticado possui histórico de revisões e progresso cadastrado
  Quando ele aciona "GET /performance/export?format=json"
  Então o sistema retorna HTTP 200 com cabeçalho "Content-Type: application/json; charset=utf-8"
  E cabeçalho "Content-Disposition: attachment; filename=\"study_reviewer_export_20261007_053743.json\""
  E o nome do arquivo utiliza timestamp determinístico no padrão "study_reviewer_export_YYYYMMDD_HHMMSS.json" sem expor UUIDs internos
  E o corpo JSON contém o perfil do usuário, resumo estatístico e a lista completa de logs de auditoria.
```

#### `UC-S04-04`: Exportação Tabular de Dados em Formato CSV (LGPD Art. 18)
* **Categoria:** `Caminho Feliz & Variações`
* **Camada Alvo:** `Aplicação / Controladores`
```gherkin
Cenário: Estudante solicita download de seus dados em CSV para visualização em planilha
  Dado que o estudante autenticado possui revisões registradas
  Quando ele aciona "GET /performance/export?format=csv"
  Então o sistema retorna HTTP 200 com cabeçalho "Content-Type: text/csv; charset=utf-8"
  E cabeçalho "Content-Disposition: attachment; filename=\"study_reviewer_export_20261007_053743.csv\""
  E o arquivo inicia com o marcador UTF-8 BOM ("\ufeff") para suporte nativo ao Excel
  E contém as colunas: "Data da Revisao","Horario","Materia","Tema","Pergunta","Nota","Nivel Anterior","Novo Nivel","Status","Modo"
  E todos os valores de células são sanitizados contra CSV Injection (neutralizando "=", "+", "-", "@", "\t", "\r").
```

---

### 2.2 Categoria 2: Cenários de Borda e Fronteiras Matemáticas (Edge Cases)

#### `UC-S04-05`: Hub de Desempenho com Histórico Zero (Empty State Acolhedor)
* **Categoria:** `Edge Case & Limites`
* **Camada Alvo:** `Domínio / Interface Web`
```gherkin
Cenário: Estudante recém-cadastrado sem nenhuma revisão realizada acessa a aba "Desempenho"
  Dado que o estudante não possui nenhuma revisão registrada em "review_audit_logs"
  Quando o estudante acessa "GET /performance"
  Então o sistema calcula:
    | retention_rate | mature_questions_count | total_reviews_count | active_days_count |
    | 0.0            | 0                      | 0                   | 0                 |
  E a interface exibe o Empty State acolhedor informando que os gráficos serão gerados após as primeiras revisões
  E a divisão por zero é tratada graciosamente no serviço de domínio sem lançar exceções.
```

#### `UC-S04-06`: Transição Exata para Retenção Madura (Nível 3 para Nível 4)
* **Categoria:** `Edge Case & Limites`
* **Camada Alvo:** `Domínio / Aplicação`
```gherkin
Cenário: Pergunta atinge exatamente o corte de retenção madura de longo prazo
  Dado que uma pergunta está no Nível 3 (intervalo de 30 dias)
  Quando o estudante avalia a pergunta com score 100
  Então o nível é promovido para o Nível 4 (intervalo de 60 dias)
  E a contagem de "mature_questions_count" do estudante é incrementada em 1
  E a timeline de evolução madura registra o novo ingresso na data da revisão.
```

#### `UC-S04-07`: Limites Extremos de Pontuação (Score 0 e Score 100)
* **Categoria:** `Edge Case & Limites`
* **Camada Alvo:** `Domínio`
```gherkin
Cenário: Auditoria de pontuação mínima e pontuação máxima absoluta
  Dado que o estudante realiza duas revisões distintas
  Quando a primeira revisão é avaliada com score 0 (falha total) e a segunda com score 100 (acerto pleno)
  Então ambas as notas são persistidas com integridade na entidade "ReviewAuditLog"
  E a primeira registra "is_promoted = False" e a segunda "is_promoted = True".
```

---

### 2.3 Categoria 3: Validação de Entrada e Rejeição de Payloads

#### `UC-S04-08`: Rejeição de Formato de Exportação Não Suportado
* **Categoria:** `Validação de Entrada`
* **Camada Alvo:** `Adaptadores / Web & API`
```gherkin
Cenário: Requisição de exportação com formato inválido
  Dado um usuário autenticado
  Quando ele requisita "GET /performance/export?format=xml" ou "GET /performance/export?format=pdf"
  Então o sistema rejeita a solicitação com HTTP 400 Bad Request
  E informa que os únicos formatos válidos para exportação são "json" e "csv".
```

#### `UC-S04-09`: Rejeição de Parâmetros de Paginação Fora dos Limites
* **Categoria:** `Validação de Entrada`
* **Camada Alvo:** `Adaptadores / Web & API`
```gherkin
Cenário: Paginação com página negativa ou tamanho de página excessivo
  Dado um usuário autenticado acessando o histórico de revisões
  Quando ele informa "page=0" ou "page_size=5000"
  Então o sistema sanitiza ou rejeita com HTTP 422 Unprocessable Entity
  E aplica os tetos seguros definidos pela política de API (page >= 1, max page_size = 100).
```

---

### 2.4 Categoria 4: Invariantes de Domínio e Regras de Negócio

#### `UC-S04-10`: Imutabilidade Estrita da Trilha de Auditoria (Append-Only)
* **Categoria:** `Invariante de Domínio`
* **Camada Alvo:** `Domínio / Repositório`
```gherkin
Cenário: Garantia de que logs de auditoria não possuem métodos de edição ou mutação
  Dado que um registro de "ReviewAuditLog" foi gravado no banco de dados
  Quando a camada de aplicação ou adaptadores interage com a entidade
  Então a entidade não expõe métodos para alterar score, notas ou níveis pós-criação
  E o repositório não provê método "update()", garantindo trilha 100% append-only.
```

#### `UC-S04-11`: Invariantes de Intervalo de Níveis (0 a 6)
* **Categoria:** `Invariante de Domínio`
* **Camada Alvo:** `Domínio Puro`
```gherkin
Cenário: Tentativa de instanciar log com níveis fora do espectro permitido
  Dado um payload com "level_before = -1" ou "level_after = 7"
  Quando a entidade "ReviewAuditLog" é instanciada
  Então o domínio levanta imediatamente "DomainValidationError"
  E impede a persistência de registros corrompidos.
```

---

### 2.5 Categoria 5: Ciclo de Vida, Histórico e Transições de Estado

#### `UC-S04-12`: Preservação Integral de Histórico após Exclusão de Matéria (Snapshot Isolation)
* **Categoria:** `Transição de Estado & Histórico`
* **Camada Alvo:** `Persistência / Repositório`
```gherkin
Cenário: O usuário exclui uma matéria do catálogo após ter realizado revisões nela
  Dado que o estudante realizou revisões na matéria "Direito Tributário" (id="subj-99")
  E os logs registraram "historical_subject_name = 'Direito Tributário'"
  Quando o usuário exclui a matéria "Direito Tributário" do seu catálogo
  Então a tabela "subjects" exclui o registro "subj-99"
  E os registros em "review_audit_logs" NÃO são excluídos (sem CASCADE)
  E a chave "subject_id" em "review_audit_logs" é convertida para NULL via "ON DELETE SET NULL"
  E o campo "historical_subject_name" permanece intacto com o texto "Direito Tributário"
  E os gráficos de histórico do estudante continuam exibindo o tempo e as revisões dedicadas àquela matéria.
```

#### `UC-S04-13`: Anonimização Irreversível de Logs na Exclusão de Conta (LGPD Art. 16, IV e 18, VI)
* **Categoria:** `Transição de Estado & Histórico`
* **Camada Alvo:** `Persistência / LGPD`
```gherkin
Cenário: Titular solicita exclusão definitiva de sua conta na aplicação
  Dado que o titular "user-777" possui histórico de revisões em "review_audit_logs"
  Quando a conta do usuário é excluída no subsistema de identidade
  Então a chave estrangeira "user_id" na tabela "review_audit_logs" sofre "ON DELETE SET NULL"
  E o histórico permanece no banco como dado estatístico verdadeiramente anonimizado sem vínculo com pessoa natural.
```

---

### 2.6 Categoria 6: Concorrência e Idempotência

#### `UC-S04-14`: Submissões Simultâneas de Revisão
* **Categoria:** `Concorrência & Idempotência`
* **Camada Alvo:** `Aplicação / Persistência`
```gherkin
Cenário: Duplo clique acidental do estudante no botão de pontuação
  Dado que o estudante está avaliando a pergunta "q-01" vencida hoje
  Quando duas requisições idênticas chegam em intervalo de poucos milissegundos
  Então a primeira requisição atualiza o progresso para o próximo ciclo e gera o log
  E a segunda requisição é interceptada pela checagem de pergunta não vencida ("QuestionNotDueError")
  E apenas um log de auditoria é persistido para a data.
```

---

### 2.7 Categoria 7: Busca, Filtros e Paginação

#### `UC-S04-15`: Filtro de Histórico por Matéria Específica
* **Categoria:** `Busca & Filtros`
* **Camada Alvo:** `Aplicação / Adaptadores Web`
```gherkin
Cenário: Estudante filtra a tabela de histórico para analisar apenas uma matéria
  Dado que o estudante possui revisões de "Direito Constitucional" e "Matemática"
  Quando ele seleciona o filtro da matéria "Direito Constitucional"
  Então a tabela atualiza dinamicamente via HTMX exibindo exclusivamente os registros daquela matéria
  E o total de páginas e registros reflete apenas o subconjunto filtrado.
```

#### `UC-S04-16`: Navegação entre Páginas do Histórico
* **Categoria:** `Paginação`
* **Camada Alvo:** `Adaptadores Web / HTMX`
```gherkin
Cenário: Estudante avança para a página 2 do histórico de revisões
  Dado que o estudante possui 35 revisões com paginação configurada para 20 itens por página
  Quando ele aciona o botão da página 2
  Então o fragmento HTML da tabela é carregado via HTMX exibindo os 15 itens restantes
  E o foco do leitor de tela é preservado no cabeçalho da tabela.
```

---

### 2.8 Categoria 8: Segurança e Controle de Acesso (Anti-IDOR)

#### `UC-S04-17`: Isolamento Estrito de Estatísticas e Logs entre Usuários (Anti-IDOR / CWE-639)
* **Categoria:** `Segurança`
* **Camada Alvo:** `Aplicação / Controladores`
```gherkin
Cenário: Defesa por design contra IDOR — Extração estrita de identidade da sessão criptografada
  Dado um usuário autenticado "user-A" com cookie de sessão válido
  Quando ele requisita endpoints de estatísticas, histórico ou exportação ("/performance", "/performance/export", "/api/v1/performance/stats", "/api/v1/performance/history", "/api/v1/performance/export")
  E tenta injetar parâmetros de terceiro (ex: "?user_id=user-B" ou payload com "user_id")
  Então os controladores e casos de uso ignoram qualquer parâmetro "user_id" fornecido na requisição
  E extraem a identidade exclusivamente da sessão criptografada (AES-256-GCM / ADR-007)
  E executam as consultas e exportações vinculadas estritamente ao "user-A"
  E tentativas de forjar assinaturas de sessão ou acessar recursos protegidos com credenciais inválidas resultam em HTTP 401 Unauthorized ou HTTP 403 Forbidden.
```

#### `UC-S04-18`: Rejeição de Acesso a Visitantes Não Autenticados
* **Categoria:** `Segurança`
* **Camada Alvo:** `Infraestrutura / Autenticação`
```gherkin
Cenário: Visitante não logado tenta acessar a aba "Desempenho"
  Dado um visitante anônimo sem cookie de sessão válido
  Quando ele requisita "GET /performance" ou "GET /performance/export"
  Então o sistema intercepta a requisição e redireciona para a página de login ("/auth/login")
  E para chamadas na API REST ("/api/v1/performance/*"), retorna HTTP 401 Unauthorized.
```

### 2.9 Categoria 9: Experiência do Usuário, Design System & Acessibilidade (Cluster 3)

#### `UC-S04-19`: Navegação Mobile e Responsividade do Hub de Desempenho (4 Colunas)
* **Categoria:** `Ergonomia & UI Mobile`
* **Camada Alvo:** `Interface Web / base.html`
```gherkin
Cenário: Estudante acessa a aplicação via smartphone com viewport estreito (360px a 414px)
  Dado que o estudante está autenticado e acessa qualquer tela da aplicação no celular
  Então a barra de navegação inferior ("bottom nav") é reconfigurada para 4 colunas ("grid-cols-4")
  E exibe os links "Flashcards", "Revisão", "Desempenho" e "Cadastros"
  E cada item da barra possui altura mínima de 48px e área de toque ("touch target") conforme WCAG 2.5.5 / 2.5.8
  Quando o estudante toca no ícone de "Desempenho"
  Então a rota "/performance" é carregada
  E o item "Desempenho" recebe destaque visual de estado ativo com "aria-current='page'"
  E nenhuma rolagem horizontal indesejada (overflow-x) é produzida na viewport.
```

#### `UC-S04-20`: Acessibilidade Universal em Gráficos SVG com Tabela Oculta `.sr-only`
* **Categoria:** `Acessibilidade (WCAG 2.1 AA)`
* **Camada Alvo:** `Interface Web / performance_hub.html`
```gherkin
Cenário: Usuário de leitor de tela (NVDA/VoiceOver) navega pelo gráfico de evolução de retenção madura
  Dado que o estudante acessa o Hub de Desempenho com 19 perguntas em Retenção Madura
  Quando a seção de gráficos é renderizada
  Então o elemento <svg> possui role="img", aria-labelledby com título e descrição concisa
  E imediatamente adjacente ao SVG, é renderizada uma tabela HTML com a classe ".sr-only"
  E a tabela oculta contém <caption> explicativo, cabeçalhos <th> com scope="col" e linhas <tr> com os pontos históricos
  E o leitor de tela lê com clareza a evolução temporal das perguntas maduras sem depender da visualização gráfica.
```

#### `UC-S04-21`: Retenção Programática de Foco e Anúncio Acessível na Paginação HTMX
* **Categoria:** `Acessibilidade (WCAG 2.1 AA)`
* **Camada Alvo:** `Interface Web / HTMX`
```gherkin
Cenário: Usuário navega pelas páginas do histórico via teclado sem perda de foco
  Dado que o estudante está na página 1 do histórico e foca no botão "Próxima Página"
  Quando ele aciona a tecla "Enter" ou "Espaço"
  Então a requisição HTMX atualiza o fragmento "#history-table-container"
  E o listener "htmx:afterSwap" move programaticamente o foco para o elemento de cabeçalho da tabela com tabindex="-1"
  E nenhum Focus Loss Bug ocorre (o foco não retorna para o topo do documento)
  E a Live Region "#performance-announcer[aria-live='polite']" anuncia "Página 2 de 5 do histórico de revisões carregada com sucesso."
```

#### `UC-S04-22`: Microcopy Contextual e Acessibilidade do Indicador "Retenção Madura (Nível 4+)"
* **Categoria:** `Experiência do Usuário (UX)`
* **Camada Alvo:** `Interface Web / Design System`
```gherkin
Cenário: Estudante visualiza o card de Retenção Madura e consulta sua definição pedagógica
  Dado que o estudante acessa a aba "Desempenho"
  Então o card de "Retenção Madura (Nível 4+)" exibe a contagem absoluta e o percentual sobre o total do acervo
  E exibe um botão de ajuda acessível com aria-label="O que é Retenção Madura?" e aria-describedby="tooltip-mature-info"
  Quando o estudante foca ou passa o cursor sobre o botão de ajuda
  Então um microcopy contextual é apresentado explicando: "Perguntas com intervalos de 60, 90 e 180 dias fixadas na sua memória de longo prazo."
  E o leitor de tela anuncia o texto auxiliar através do vínculo semântico de acessibilidade.
```

#### `UC-S04-23`: Estados de Feedback Visual e Acessível na Exportação de Dados LGPD
* **Categoria:** `Experiência do Usuário & Acessibilidade`
* **Camada Alvo:** `Interface Web / Export Controller`
```gherkin
Cenário: Estudante aciona o download de histórico em CSV
  Dado que o estudante está no painel de exportação da aba "Desempenho"
  Quando ele clica no botão "Baixar Histórico (CSV)"
  Então o botão entra temporariamente em estado de carregamento exibindo spinner SVG e texto "Gerando arquivo..."
  E o atributo "aria-busy='true'" é aplicado ao botão para tecnologias assistivas
  E a Live Region anuncia "Preparando arquivo CSV com seu histórico completo..."
  Quando o navegador recebe o stream do arquivo com Content-Disposition attachment
  Então o botão é restaurado ao seu estado inicial habilitado
  E uma mensagem sutil de confirmação "Download iniciado com sucesso!" é exibida e anunciada com aria-live="polite".
```

#### `UC-S04-24`: Estado de Erro com Recuperação Graciosa no Fragmento HTMX (Error State)
* **Categoria:** `Design System & Resiliência de Interface`
* **Camada Alvo:** `Interface Web / HTMX Handlers`
```gherkin
Cenário: Falha de comunicação ou queda temporária de rede ao trocar de página no histórico
  Dado que o estudante tenta navegar para a página 3 do histórico
  Quando a requisição HTMX falha com erro de rede ou HTTP 500
  Então o container "#history-table-container" renderiza um card de erro amigável com role="alert"
  E apresenta a mensagem "Não foi possível carregar os registros de histórico no momento."
  E disponibiliza um botão visível e acessível "Tentar Novamente" com hx-get configurado para a página solicitada
  E nenhum layout shift abrupto é provocado no restante da página.
```

#### `UC-S04-25`: Estado Parcial e Filtro por Matéria sem Resultados (Empty Filter State)
* **Categoria:** `Design System & UX`
* **Camada Alvo:** `Interface Web / Templates`
```gherkin
Cenário: Estudante aplica filtro para uma matéria recém-cadastrada que não possui revisões
  Dado que o estudante possui revisões cadastradas no geral, mas nenhuma na matéria "Direito Marítimo"
  Quando ele seleciona "Direito Marítimo" no filtro de matérias do histórico
  Então a tabela renderiza um estado vazio de filtragem com ícone de busca vazia
  E a mensagem "Nenhuma revisão registrada para a matéria 'Direito Marítimo'."
  E um botão de ação rápida "Limpar Filtro" é disponibilizado
  E ao clicar em "Limpar Filtro", a tabela é restaurada exibindo todos os registros sem recarregar a página inteira.
```

#### `UC-S04-26`: Contraste Estrito (WCAG 2.1 AA) e Redundância Semântica nos Badges
* **Categoria:** `Acessibilidade (WCAG 2.1 AA) & Design System`
* **Camada Alvo:** `Interface Web / Tailwind CSS Tokens`
```gherkin
Cenário: Inspeção de contraste e redundância semântica em badges de transição de nível no Light e Dark Mode
  Dado que o histórico exibe linhas com promoção de nível ("N2 → N3") e regressão de nível ("N6 → N2")
  Quando renderizados nos temas Claro e Escuro
  Então o badge de promoção exibe ícone de seta subindo "↑", texto "Promovido" e contraste de cor >= 4.5:1
  E o badge de regressão exibe ícone de seta descendo "↓", texto "Regredido" e contraste de cor >= 4.5:1
  E o badge de manutenção exibe símbolo "=" e texto "Mantido"
  E a informação de status nunca depende exclusivamente da percepção de cores (WCAG Critério 1.4.1).
```

#### `UC-S04-27`: Estabilidade Dimensional e Prevenção Rígida de Layout Shift (CLS = 0)
* **Categoria:** `Performance Frontend (Core Web Vitals)`
* **Camada Alvo:** `Interface Web / CSS & Templates`
```gherkin
Cenário: Carregamento do Hub de Desempenho sem salto visual durante renderização
  Dado que o estudante acessa "/performance" em qualquer viewport (desktop ou mobile)
  Quando os componentes da tela são carregados e montados
  Então os 4 cards de KPI possuem altura mínima reservada de "min-h-[110px]"
  E os contêineres de gráficos SVG possuem aspect-ratio e altura mínima declaradas ("min-h-[280px]")
  E a área da tabela de histórico possui reserva dimensional de "min-h-[460px]" com skeleton pré-renderizado durante trocas HTMX
  E o índice Cumulative Layout Shift (CLS) medido é estritamente zero (CLS = 0.000).
```

---

### 2.10 Categoria 10: Invariantes do SRS Estrito, Resiliência do Catálogo & Defesas de Arquitetura (Cluster 1)

#### `UC-S04-28`: Penalidade Máxima do SRS Estrito no Nível 6 (Regressão para Nível 2)
* **Categoria:** `Invariante de Domínio & SRS`
* **Camada Alvo:** `Domínio / Aplicação`
```gherkin
Cenário: Pergunta veterana em Nível 6 sofre penalidade severa de regressão ao falhar na revisão
  Dado que o relógio do sistema está fixado em 2026-10-07T10:00:00Z
  E o estudante possui a pergunta "q-600" no Nível 6 (intervalo de 180 dias) com vencimento em 2026-10-07
  Quando o estudante submete uma nota 80 (ou qualquer nota < 100)
  Então o motor SRS penaliza o progresso regredindo-o estritamente para o Nível 2
  E o próximo vencimento é reagendado para 2026-10-22 (hoje + 15 dias do Nível 2)
  E um registro em "review_audit_logs" é persistido com:
    | score | level_before | level_after | is_promoted | is_regressed | review_date |
    | 80    | 6            | 2           | False       | True         | 2026-10-07  |
  E a contagem de perguntas em Retenção Madura (Nível 4+) no inventário ativo do estudante é decrementada em 1.
```

#### `UC-S04-29`: Manutenção de Nível com Reagendamento Estrito (Score Parcial < 100)
* **Categoria:** `Caminho Feliz & SRS`
* **Camada Alvo:** `Domínio / Aplicação`
```gherkin
Cenário: Pergunta no Nível 3 falha em atingir acerto pleno (100%) e mantém o nível atual
  Dado que o relógio do sistema está fixado em 2026-10-07T10:00:00Z
  E a pergunta "q-300" está no Nível 3 (intervalo de 30 dias) com vencimento em 2026-10-07
  Quando o estudante submete a nota 75 (score < 100)
  Então o progresso permanece no Nível 3
  E o próximo vencimento é reagendado estritamente para 2026-11-06 (hoje + 30 dias do Nível 3)
  E o log de auditoria registra:
    | score | level_before | level_after | is_promoted | is_regressed | review_date |
    | 75    | 3            | 3           | False       | False        | 2026-10-07  |
```

#### `UC-S04-30`: Revisão após Inatividade Prolongada (Overdue Extremo e Carimbo Temporal no Dia Efetivo)
* **Categoria:** `Edge Case & Calendário`
* **Camada Alvo:** `Aplicação / Domínio`
```gherkin
Cenário: Pergunta com vencimento atrasado há 90 dias é revisada pelo estudante
  Dado que o relógio do sistema está fixado em 2026-10-07T10:00:00Z
  E a pergunta "q-200" está no Nível 2 com "next_review_date = 2026-07-09" (90 dias de atraso por inatividade do aluno)
  Quando o estudante realiza a revisão hoje obtendo score 100
  Então o progresso é promovido para o Nível 3 com vencimento em 2026-11-06 (calculado a partir de hoje + 30 dias, e NUNCA da data vencida no passado)
  E o log de auditoria grava "review_date = 2026-10-07" carimbando o esforço cognitivo no dia real da execução.
```

#### `UC-S04-31`: Preservação Integral de Histórico após Exclusão Isolada de Tema
* **Categoria:** `Transição de Estado & Histórico`
* **Camada Alvo:** `Persistência / Repositório`
```gherkin
Cenário: O usuário exclui um tema específico sem excluir a matéria mãe
  Dado que o estudante realizou revisões no tema "Recursos Cíveis" (topic_id="top-44") da matéria "Processo Civil" (subject_id="subj-10")
  E o log de auditoria registrou "historical_subject_name = 'Processo Civil'" e "historical_topic_name = 'Recursos Cíveis'"
  Quando o usuário exclui o tema "top-44" do catálogo
  Então a tabela "topics" deleta o registro "top-44"
  E na tabela "review_audit_logs", a chave estrangeira "topic_id" é convertida para NULL via "ON DELETE SET NULL"
  E a chave "subject_id" continua apontando para "subj-10"
  E os campos "historical_subject_name" e "historical_topic_name" permanecem intactos com seus valores originais.
```

#### `UC-S04-32`: Preservação de Histórico e Fallback Acessível após Exclusão Isolada de Pergunta
* **Categoria:** `Transição de Estado & Histórico`
* **Camada Alvo:** `Persistência / Repositório / Web`
```gherkin
Cenário: O usuário exclui uma pergunta específica que já possuía histórico de revisões
  Dado que a pergunta "q-999" possui 5 logs de auditoria gravados
  Quando o usuário remove a pergunta "q-999" do catálogo
  Então a tabela "questions" remove a pergunta
  E na tabela "review_audit_logs", a chave "question_id" sofre "ON DELETE SET NULL"
  E as 5 revisões anteriores continuam contabilizando normalmente para "total_reviews_count" e "retention_rate" do estudante
  E no Hub de Desempenho e na exportação CSV/JSON, a menção à pergunta exibe o texto amigável "[Pergunta Removida do Catálogo]".
```

#### `UC-S04-33`: Imunidade a Renomeações de Matéria e Tema (Snapshot Isolation Dinâmico)
* **Categoria:** `Invariante de Domínio & Histórico`
* **Camada Alvo:** `Aplicação / Domínio`
```gherkin
Cenário: Matéria e tema são renomeados entre revisões sucessivas da mesma pergunta
  Dado que o estudante revisou a pergunta "q-10" quando a matéria chamava "Direito Civil" e o tema "Posse" no dia 2026-10-01
  E o log registrou "historical_subject_name = 'Direito Civil'" e "historical_topic_name = 'Posse'"
  Quando o usuário renomeia a matéria para "Direito das Coisas" e o tema para "Posse e Propriedade"
  E revisa novamente a pergunta "q-10" no dia 2026-10-08
  Então um segundo log é gerado registrando "historical_subject_name = 'Direito das Coisas'" e "historical_topic_name = 'Posse e Propriedade'"
  E o primeiro log gravado no dia 2026-10-01 permanece 100% inalterado com os nomes originais congelados.
```

#### `UC-S04-34`: Garantia de Zero Side-Effects (Sem Logs Fantasmas) em Falha ou Rejeição de Revisão
* **Categoria:** `Validação & Integridade Transacional`
* **Camada Alvo:** `Aplicação / Domínio`
```gherkin
Cenário: Chamada de revisão interceptada por não estar vencida não pode gerar lixo em auditoria
  Dado que a pergunta "q-55" possui vencimento para "amanhã" (2026-10-08)
  Quando um cliente ou requisição maliciosa tenta forçar "POST /questions/study/review" na data 2026-10-07
  Então o caso de uso levanta "QuestionNotDueError"
  E a transação é imediatamente abortada
  E absolutamente nenhum registro é inserido em "review_audit_logs".
```

#### `UC-S04-35`: Proteção Defensiva contra Injeção de Fórmulas em Exportação CSV (Anti-CSV Injection / CWE-1236)
* **Categoria:** `Segurança & LGPD`
* **Camada Alvo:** `Adaptadores / Exportador Web & API`
```gherkin
Cenário: Matéria ou tema contendo caracteres especiais de comando de planilha são exportados com segurança
  Dado que um estudante cadastrou uma matéria com o nome "=cmd|'/C calc'!A0" ou "@SUM(1+1)"
  E realizou revisões nessa matéria gerando logs de auditoria
  Quando ele aciona a exportação "GET /performance/export?format=csv"
  Então as células geradas no CSV contendo os caracteres problemáticos ("=", "+", "-", "@", "\t", "\r") são neutralizadas com apóstrofo prefixado
  E a planilha (Excel / LibreOffice) renderiza o conteúdo como texto puro sem executar comandos ou fórmulas dinâmicas.
```

#### `UC-S04-36`: Agregação Analítica de Alto Desempenho $O(1)$ em Memória via Índices Cobridores
* **Categoria:** `Performance de Banco de Dados & Arquitetura`
* **Camada Alvo:** `Aplicação / Repositório SQL`
```gherkin
Cenário: Estudante com volume massivo de revisões (ex: 20.000 logs) acessa o Hub de Desempenho
  Dado que o estudante possui 20.000 logs de auditoria acumulados ao longo de meses de estudo
  Quando ele requisita "GET /performance"
  Então o repositório executa consulta agregada com contagens escalares suportadas pelo índice "ix_review_audit_user_date"
  E nenhum objeto de entidade individual é carregado em massa na memória RAM do servidor Python ($O(1)$ footprint de memória)
  E a resposta completa de estatísticas é gerada e retornada em menos de 15ms.
```


---

### 2.11 Categoria 11: Governança de Segurança Avançada, Telemetria & Compliance LGPD (Cluster 2)

#### `UC-S04-37`: Isolamento Granular Multi-tenant e Defesa em Profundidade contra IDOR em Filtros de Histórico (CWE-639)
* **Categoria:** `Segurança & Anti-IDOR`
* **Camada Alvo:** `Aplicação / Repositório SQL`
```gherkin
Cenário: Tentativa de filtrar histórico utilizando subject_id pertencente a outro estudante
  Dado um estudante autenticado "user-A"
  E existe no sistema uma matéria "subj-B-999" pertencente privativamente ao estudante "user-B"
  Quando o "user-A" requisita "GET /performance/history?subject_id=subj-B-999" ou via endpoint de API
  Então a consulta SQL impõe cláusula mandatória "WHERE user_id = :session_user_id AND subject_id = :subject_id"
  E nenhuma linha ou dado histórico do "user-B" é retornado
  E o sistema responde com fragmento de tabela vazia (HTTP 200) sem vazar a existência ou detalhes da matéria alheia (CWE-209)
  E nenhum erro de autorização informativo (como HTTP 403 revelando existência) é exposto ao atacante.
```

#### `UC-S04-38`: Cabeçalhos HTTP Defensivos de Download e Prevenção de Cache de Dados Pessoais (OWASP / LGPD / CWE-525)
* **Categoria:** `Segurança & AppSec`
* **Camada Alvo:** `Adaptadores / Web & API`
```gherkin
Cenário: Inspeção de cabeçalhos de segurança em endpoints de download de dados pessoais
  Dado um estudante autenticado solicitando exportação de histórico via JSON ou CSV
  Quando o download é emitido pelo servidor ("GET /performance/export?format=json|csv" ou "/api/v1/performance/export")
  Então a resposta HTTP 200 contém os cabeçalhos de proteção mandatória:
    | Cabeçalho | Valor | Finalidade |
    | X-Content-Type-Options | nosniff | Prevenção de MIME confusion / sniff |
    | X-Frame-Options | DENY | Prevenção de Clickjacking na janela de download |
    | Content-Security-Policy | default-src 'none' | Bloqueio de scripts em visualização direta |
    | Cache-Control | no-store, no-cache, must-revalidate, private | Bloqueio de cache de dados pessoais do titular |
    | Pragma | no-cache | Compatibilidade com proxies legados |
    | Expires | 0 | Expiração imediata de artefatos de dados |
  E o cabeçalho "Content-Disposition" utiliza nome determinístico sem UUIDs de usuário e codificação segura RFC 6266
  E caches intermediários (proxies corporativos, CDNs e disco do browser) são rigorosamente impedidos de armazenar os dados do titular.
```

#### `UC-S04-39`: Prevenção de Exaustão de Recursos (DoS de Memória) via Streaming na Exportação em Lote (CWE-400)
* **Categoria:** `Segurança & Resiliência`
* **Camada Alvo:** `Aplicação / Adaptadores Web & API`
```gherkin
Cenário: Exportação de grande volume de histórico sem sobrecarga de memória no servidor
  Dado que um estudante veterano possui mais de 25.000 logs de revisão registrados em "review_audit_logs"
  Quando ele aciona a exportação em lote ("GET /performance/export?format=csv")
  Então o caso de uso e repositório utilizam cursor paginado ou gerador assíncrono (chunk streaming)
  E os dados são transmitidos em fluxo contínuo via "StreamingResponse" em blocos de até 500 registros
  E o consumo de memória RAM do processo da aplicação permanece estável O(1) sem picos de alocação
  E o download é concluído com integridade sem timeout ou falhas de Out of Memory (OOM).
```

#### `UC-S04-40`: Structured Logging em JSON com Correlation ID e Propagação de W3C Trace Context (traceparent)
* **Categoria:** `Telemetria & Observabilidade`
* **Camada Alvo:** `Infraestrutura / Observabilidade`
```gherkin
Cenário: Rastreabilidade distribuída e emissão de logs estruturados em requisições de desempenho
  Dado que uma requisição HTTP chega ao Hub de Desempenho contendo o cabeçalho W3C "traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
  Quando o controlador processa a agregação de estatísticas ou exportação
  Então o middleware de observabilidade extrai o trace context e gera um "correlation_id" correlacionado
  E todos os logs emitidos durante a transação são formatados em JSON estruturado contendo:
    | Campo | Descrição | Exemplo |
    | timestamp | Data/hora em ISO 8601 UTC | "2026-10-07T05:37:43.000Z" |
    | level | INFO, WARN ou ERROR | "INFO" |
    | service | Nome do microsserviço | "study-reviewer" |
    | correlation_id | Identificador único da requisição | "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c" |
    | traceparent | Contexto W3C propagado | "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01" |
    | user_id_hash | Hash HMAC/SHA-256 do user_id (minimização) | "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" |
    | duration_ms | Tempo de execução da agregação em ms | 12.4 |
    | event | Identificador semântico do evento | "performance_stats_computed" |
  E nenhuma informação pessoal desnecessária (PII em claro) é registrada nos logs de aplicação.
```

#### `UC-S04-41`: Métricas Operacionais de Desempenho e Histogramas de Agregação/Exportação (Prometheus/OpenTelemetry)
* **Categoria:** `Telemetria & Observabilidade`
* **Camada Alvo:** `Infraestrutura / Métricas`
```gherkin
Cenário: Coleta de métricas de telemetria operacional durante a operação do Hub de Desempenho
  Dado que o sistema recebe requisições de revisão, estatísticas e exportação
  Quando as operações são executadas
  Então o coletor de telemetria incrementa e observa as métricas operacionais:
    | Métrica | Tipo | Rótulos | Descrição |
    | study_reviewer_performance_aggregation_duration_seconds | Histograma | status_code, cache_hit | Tempo de cálculo de KPIs |
    | study_reviewer_audit_logs_written_total | Contador | evaluation_mode, outcome | Volume de logs persistidos |
    | study_reviewer_export_requests_total | Contador | format, status | Total de requisições de exportação |
    | study_reviewer_export_duration_seconds | Histograma | format | Tempo de geração de exportações |
    | study_reviewer_export_bytes_total | Contador | format | Volume de bytes trafegados no download |
  E o percentil 95 (P95) do tempo de agregação analítica é monitorado com alerta caso ultrapasse o teto de 50ms.
```

#### `UC-S04-42`: Portabilidade de Dados Estrita sem Vazamento de Metadados de Terceiros (LGPD Art. 18)
* **Categoria:** `Privacidade & LGPD`
* **Camada Alvo:** `Aplicação / Exportador`
```gherkin
Cenário: Estudante que revisou matérias públicas/compartilhadas solicita portabilidade de seus dados
  Dado que o estudante "user-A" estudou perguntas criadas por um professor "teacher-Z" em matéria pública compartilhada
  Quando o "user-A" solicita o download integral de seus dados em JSON ("GET /performance/export?format=json")
  Então o payload gerado inclui exclusivamente o histórico pessoal de revisões, pontuações e notas do "user-A"
  E as informações de terceiros são estritamente sanitizadas:
    - O ID, e-mail e dados de perfil do "teacher-Z" NÃO são incluídos no arquivo
    - Logs de revisões de outros alunos que estudaram a mesma matéria NÃO constam na exportação
    - Metadados internos de infraestrutura ou moderação do sistema são omitidos
  E o titular recebe a portabilidade completa de seus dados pessoais sem comprometer a privacidade de terceiros (LGPD Art. 18, V c/c Art. 6º, VII).
```

#### `UC-S04-43`: Desvinculação Irreversível e Expulso de Dados Descritivos na Exclusão de Conta (LGPD Art. 6º, III e Art. 16, IV)
* **Categoria:** `Privacidade & LGPD`
* **Camada Alvo:** `Persistência / Repositório / LGPD`
```gherkin
Cenário: Exclusão definitiva de conta do estudante com sanitização de nomes congelados privados
  Dado que o titular "user-777" possui histórico de revisões em "review_audit_logs"
  E possui matérias privadas cujos nomes foram inseridos pelo próprio usuário (ex: "Anotações Pessoais do Titular")
  Quando o titular solicita formalmente o direito de eliminação de seus dados (LGPD Art. 18, VI)
  Então a chave estrangeira "user_id" é convertida para NULL via "ON DELETE SET NULL"
  E os campos "historical_subject_name" e "historical_topic_name" de matérias privadas do usuário sofrem higienização irreversível para "[Matéria Anonimizada]" e "[Tema Anonimizado]"
  E qualquer anotação subjetiva ou dado textual potencialmente reidentificável é expurgado
  E os dados puramente estatísticos (score, datas, níveis, modo) são mantidos de forma irreversivelmente desidentificada para fins de calibração algorítmica e estatísticas agregadas (LGPD Art. 16, IV).
```

#### `UC-S04-44`: Rollback Transacional Atômico em Falha na Persistência de Auditoria (ACID)
* **Categoria:** `Concorrência & Transação (ACID)`
* **Camada Alvo:** `Aplicação / Persistência`
```gherkin
Cenário: Falha de banco na gravação do log de auditoria reverte o avanço de progresso do aluno
  Dado que um estudante revisa a pergunta "q-100" no Nível 2 vencida hoje
  E o estudante submete o score 100 visando avanço para o Nível 3
  Quando a camada de persistência falha ao gravar o registro em "review_audit_logs" (ex: queda de conexão ou violação de integridade)
  Então a transação relacional é revertida integralmente via ROLLBACK
  E o progresso da pergunta permanece estritamente no Nível 2 com a data de vencimento inalterada
  E nenhuma linha órfã é persistida em "review_audit_logs"
  E o caso de uso propaga uma exceção de persistência sem corromper o estado do SRS.
```

#### `UC-S04-45`: Exclusão de Entidades do Catálogo com Proteção contra Full Table Scan via FK Indexes
* **Categoria:** `Performance de Banco de Dados & Integridade`
* **Camada Alvo:** `Persistência / DDL`
```gherkin
Cenário: Deleção de matéria ou pergunta com ON DELETE SET NULL veloz em tabela volumosa
  Dado que a tabela "review_audit_logs" possui 500.000 registros indexados nas chaves estrangeiras "subject_id", "question_id" e "topic_id"
  Quando o proprietário de uma matéria a exclui do catálogo
  Então o banco de dados executa a atualização "ON DELETE SET NULL" utilizando o índice específico da FK
  E o comando DELETE conclui em tempo inferior a 50 milissegundos sem realizar Sequential Scan sobre a tabela de logs
  E os campos históricos congelados permanecem íntegros.
```

#### `UC-S04-46`: Paridade Bidirecional de Migração Alembic (PostgreSQL e SQLite)
* **Categoria:** `DevOps & Infraestrutura`
* **Camada Alvo:** `Frameworks & Drivers / Alembic`
```gherkin
Cenário: Execução íntegra de upgrade e downgrade da migração da Sprint 04 em ambos os dialetos
  Dado o arquivo de migração da Sprint 04 contendo a criação de "review_audit_logs" e índices cobridores
  Quando a esteira executa "alembic upgrade head" no PostgreSQL 16 e no SQLite
  Então todas as tabelas, foreign keys e índices (com INCLUDE no PostgreSQL e padrão no SQLite) são criados com sucesso
  E quando a esteira executa "alembic downgrade -1"
  Então todos os objetos criados são completamente removidos sem deixar resíduos ou quebrar tabelas pré-existentes.
```

---

## 3. Matriz de Rastreabilidade de QA Expandida

| ID Caso de Uso | Categoria | Camada | Teste Automatizado Previsto |
| :--- | :--- | :--- | :--- |
| `UC-S04-01` | Caminho Feliz | Aplicação/Domínio | `tests/unit/test_review_question_use_case.py` |
| `UC-S04-02` | Caminho Feliz | Aplicação/Web | `tests/unit/test_get_user_statistics_use_case.py` |
| `UC-S04-03` | Caminho Feliz | Aplicação/Web/API | `tests/unit/test_export_user_data_use_case.py` |
| `UC-S04-04` | Caminho Feliz | Aplicação/Web/API | `tests/unit/test_export_user_data_use_case.py` |
| `UC-S04-05` | Edge Case | Domínio/Web | `tests/unit/test_study_statistics_service.py` |
| `UC-S04-06` | Edge Case | Domínio/Aplicação | `tests/unit/test_study_statistics_service.py` |
| `UC-S04-07` | Edge Case | Domínio Puro | `tests/unit/test_review_audit_log_entity.py` |
| `UC-S04-08` | Validação | Adaptador API | `tests/integration/test_performance_api_controllers.py` |
| `UC-S04-09` | Validação | Adaptador API | `tests/integration/test_performance_api_controllers.py` |
| `UC-S04-10` | Invariante | Domínio/Repo | `tests/unit/test_review_audit_log_entity.py` |
| `UC-S04-11` | Invariante | Domínio Puro | `tests/unit/test_review_audit_log_entity.py` |
| `UC-S04-12` | Histórico/LGPD | Repositório/DB | `tests/integration/test_review_audit_repository.py` |
| `UC-S04-13` | Histórico/LGPD | Repositório/DB | `tests/integration/test_review_audit_repository.py` |
| `UC-S04-14` | Concorrência | Aplicação/Repo | `tests/integration/test_review_question_integration.py` |
| `UC-S04-15` | Busca/Filtros | Adaptador Web | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-16` | Paginação | Adaptador Web | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-17` | Segurança | Aplicação/API | `tests/integration/test_performance_security.py` |
| `UC-S04-18` | Segurança | Web/Auth | `tests/integration/test_performance_security.py` |
| `UC-S04-19` | UX & Mobile | Interface Web/Layout | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-20` | Acessibilidade | Web/A11y (SVG) | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-21` | Acessibilidade | Web/HTMX Foco | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-22` | UX & Microcopy | Web/Componentes | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-23` | UX Feedback | Web/Exportação | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-24` | UI Error State | Web/HTMX Handlers | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-25` | UI Partial State | Web/Filtros | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-26` | UI/A11y Contraste | Web/Tailwind Tokens | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-27` | Core Web Vitals | Web/Layout & CSS | `tests/integration/test_performance_web_controllers.py` |
| `UC-S04-28` | Invariante SRS | Domínio/Aplicação | `tests/unit/test_review_question_use_case.py` |
| `UC-S04-29` | Caminho Feliz SRS | Domínio/Aplicação | `tests/unit/test_review_question_use_case.py` |
| `UC-S04-30` | Calendário/SRS | Aplicação/Domínio | `tests/unit/test_review_question_use_case.py` |
| `UC-S04-31` | Histórico/DB | Repositório/DB | `tests/integration/test_review_audit_repository.py` |
| `UC-S04-32` | Histórico/DB | Repositório/DB | `tests/integration/test_review_audit_repository.py` |
| `UC-S04-33` | Snapshot Isolation | Aplicação/Repo | `tests/integration/test_review_question_integration.py` |
| `UC-S04-34` | Validação/Side-Effects| Aplicação/Repo | `tests/unit/test_review_question_use_case.py` |
| `UC-S04-35` | Segurança/CSV | Adaptador/Web | `tests/unit/test_export_user_data_use_case.py` |
| `UC-S04-36` | Performance/DB | Repositório/DB | `tests/integration/test_review_audit_repository.py` |
| `UC-S04-37` | Segurança/Anti-IDOR | Aplicação/Repo | `tests/integration/test_performance_security.py` |
| `UC-S04-38` | Segurança/Headers | Adaptador Web/API | `tests/integration/test_performance_security.py` |
| `UC-S04-39` | Segurança/Anti-DoS | Adaptador Web/API | `tests/integration/test_performance_export_streaming.py` |
| `UC-S04-40` | Telemetria/Tracing | Infra/Observabilidade | `tests/integration/test_performance_telemetry.py` |
| `UC-S04-41` | Telemetria/Métricas | Infra/Métricas | `tests/integration/test_performance_telemetry.py` |
| `UC-S04-42` | LGPD/Portabilidade | Aplicação/Export | `tests/unit/test_export_user_data_use_case.py` |
| `UC-S04-43` | LGPD/Anonimização | Repositório/DB | `tests/integration/test_review_audit_repository.py` |
| `UC-S04-44` | Atomicidade ACID | Aplicação/Persistência | `tests/integration/test_review_question_integration.py` |
| `UC-S04-45` | Performance FKs | Repositório/DDL | `tests/integration/test_review_audit_repository.py` |
| `UC-S04-46` | DevOps/Alembic | Infra/Migrações | `tests/integration/test_alembic_migrations.py` |

---

### 🛡️ Parecer Técnico Unânime da Bancada dos 13 Especialistas (4 Clusters)

```
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║          AUDITORIA UNÂNIME DA BANCADA DE ESPECIALISTAS — MATRIZ BDD SPRINT 04         ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║  CLUSTER 1: CORE & ARQUITETURA                                                        ║
║    • #1 Produto (PO):                   [APROVADO] Regras SRS e Marco 4 consolidados  ║
║    • #2 QA (Qualidade):                 [APROVADO] 46 cenários determinísticos        ║
║    • #3 Arquiteto:                      [APROVADO] Clean Architecture e Inversão      ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║  CLUSTER 2: SEGURANÇA & COMPLIANCE                                                    ║
║    • #4 Segurança (OWASP/AppSec):       [APROVADO] Anti-IDOR, Anti-CSV Injection      ║
║    • #5 Telemetria & Observabilidade:   [APROVADO] W3C traceparent e métricas         ║
║    • #10 LGPD & Privacidade:            [APROVADO] Art. 18 (JSON/CSV) e Art. 16 IV    ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║  CLUSTER 3: EXPERIÊNCIA & INTERFACE                                                   ║
║    • #6 UX (Experiência):               [APROVADO] Microcopy Retenção Madura (N4+)    ║
║    • #7 UI (Design System):             [APROVADO] 5 Estados de Tela e Tailwind       ║
║    • #9 Acessibilidade (WCAG 2.1 AA):   [APROVADO] Tabelas .sr-only e Contraste >=4.5 ║
║    • #12 Performance Frontend (CWV):    [APROVADO] CLS=0.000 e Zero dependências JS   ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║  CLUSTER 4: ENGENHARIA, DADOS & OPS                                                   ║
║    • #8 DevOps:                         [APROVADO] Paridade Docker e Alembic          ║
║    • #11 Performance Python:            [APROVADO] slots=True, frozen=True e Geradores║
║    • #13 Performance de Banco de Dados: [APROVADO] Transação ACID e Índices em FKs   ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║  STATUS FINAL: APROVADO UNANIMEMENTE COM 46 CASOS DE USO (LIBERADO PARA A SPEC)       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
```



