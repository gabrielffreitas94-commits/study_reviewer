# Casos de Uso e Matriz de Edge Cases — Sprint 07
## Base de Conhecimento RAG, Chunking Semântico & Validação de Questões

---

## 1. Casos de Uso de Negócio (BDD / Gherkin)

### UC-KNOW-01: Ingestão de Material Didático por Tema
**Como** Estudante ou Professor  
**Quero** fazer upload de um resumo, texto de lei ou capítulo de livro em um Tema de estudo  
**Para que** o sistema construa uma base vetorial canônica para validação de questões e correções automáticas.

```gherkin
Cenário: Ingestão bem-sucedida de material em texto
  Dado que o usuário proprietário da matéria possui o tema "Direito Constitucional"
  Quando ele envia um documento com título "Controle de Constitucionalidade" e conteúdo de 4.000 caracteres
  Então o sistema deve criar uma entidade KnowledgeSource com status ativo
  E deve fragmentar o texto em KnowledgeChunks de até 512 tokens com 10% de overlap
  E deve gerar os embeddings vetoriais para cada chunk
  E deve persistir os chunks associados estritamente ao topic_id do tema.

Cenário: Rejeição de material vazio ou excessivamente curto
  Dado que o usuário tenta cadastrar uma fonte de conhecimento
  Quando o conteúdo possui menos de 20 caracteres úteis após sanitização
  Então o sistema deve lançar EmptyKnowledgeContentError
  E nenhum chunk ou fonte deve ser persistido.
```

### UC-KNOW-02: Isolamento Estrito Multi-Tenant entre Temas
**Como** Estudante revisando um Tema específico  
**Quero** que a busca vetorial consulte exclusivamente os documentos daquele Tema  
**Para que** não ocorra vazamento de conceitos ou contaminação cruzada de informações entre matérias diferentes.

```gherkin
Cenário: Garantia de isolamento entre temas distintos
  Dado que existem dois temas: Tema A ("Direito Penal") e Tema B ("Biologia Celular")
  E o Tema A possui chunks contendo "Habeas Corpus" e "Prescrição Penal"
  E o Tema B possui chunks contendo "Mitose" e "Meiose"
  Quando uma busca por similaridade é executada no Tema A com a query "processo de divisão celular"
  Então a busca deve retornar apenas chunks do Tema A (com score baixo)
  E nunca deve retornar nenhum chunk pertencente ao Tema B.
```

### UC-KNOW-03: Validação de Questão com Base no Conhecimento do Tema
**Como** Estudante ou Criador de Conteúdo  
**Quero** validar o enunciado e o gabarito de uma pergunta aberta contra os textos do Tema  
**Para que** eu tenha certeza de que a questão é factualmente correta e fundamentada na literatura de estudo.

```gherkin
Cenário: Questão com respaldo integral na literatura cadastrada
  Dado que o Tema possui chunks que explicam que "O recurso extraordinário é cabível em decisão de única ou última instância quando a decisão recorrida contrariar a Constituição"
  Quando o usuário submete para validação uma questão com o enunciado "Quando cabe recurso extraordinário?" e o respectivo gabarito correto
  Então o serviço de validação deve retornar is_grounded = True
  E confidence_score >= 0.85
  E deve elencar os chunks de evidência recuperados com citações do texto.

Cenário: Questão com contradição factual ou sem respaldo
  Dado que o Tema trata de "Farmacologia Cardíaca"
  Quando o usuário submete uma questão cujo gabarito afirma que "A aspirina é um antibiótico potente contra bactérias gram-positivas"
  Então o serviço de validação deve retornar is_grounded = False
  E confidence_score < 0.50
  E deve apontar no reasoning que a afirmação contraria a literatura do tema.
```

---

## 2. Matriz Exaustiva de Edge Cases da Sprint 07

| ID | Cenário de Borda | Condição | Comportamento Esperado do Sistema |
| :--- | :--- | :--- | :--- |
| **EC-01** | Texto de entrada com ruídos e tags HTML maliciosas | O usuário insere texto com `<script>` ou HTML quebrado | Sanitização prévia via `nh3` e normalização de espaços antes do chunking. |
| **EC-02** | Texto com quebras de linha artificiais ou OCR quebrado | Linhas quebradas a cada 4 palavras | O `SemanticChunkerService` agrupa frases completas e normaliza `\n` redundantes. |
| **EC-03** | Documento gigantesco (> 500.000 caracteres) | Upload de livro inteiro | Validação de limite máximo de tamanho por fonte (máx 200.000 caracteres por fonte) e paginação de chunks. |
| **EC-04** | Tema sem nenhuma fonte cadastrada (Cold Start) | Chamada de validação de questão sem chunks no tema | Retorna resultado gracioso `is_grounded = False`, com mensagem indicando ausência de material didático cadastrado no tema. |
| **EC-05** | Vetor de embedding com dimensionalidade incorreta | Provedor de embedding falha ou retorna vetor nulo | Validação de invariante no domínio: lança `InvalidEmbeddingError` se vetor for vazio ou não contiver floats válidos. |
| **EC-06** | Exclusão de fonte com chunks ativos | Usuário exclui um livro/resumo | Exclusão atômica e em cascata de todos os `KnowledgeChunks` vinculados àquela fonte. |
| **EC-07** | Tentativa de acesso a fontes de tema pertencente a outro usuário (IDOR) | Usuário B tenta consultar ou excluir fontes do Tema do Usuário A | Bloqueio de autorização com `HTTP 403 Forbidden` ou `SubjectForbiddenError`. |
