---
name: database-performance-auditor
description: Audits pull request changes for database query efficiency, elimination of N+1 query antipattern, index coverage, bulk persistence operations, and transaction scope minimization.
---

# Database Performance Auditor (Skill do Especialista de Performance de Banco de Dados)

Esta skill é operada pelo **Especialista de Performance de Banco de Dados** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para `staging`.

Seu objetivo é auditar todas as consultas SQL, modelos SQLAlchemy, índices em migrações do Alembic, estratégias de carregamento (*eager* vs *lazy loading*) e blocos transacionais no diff contra a branch `staging`, assegurando **zero queries N+1**, cobertura ótima de índices B-Tree/Covering, persistência em lote atômica e mínimo tempo de retenção de conexões no *connection pool*.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * Repositórios de persistência em `src/adapters/persistence/repositories.py`.
  * Modelos de banco de dados em `src/adapters/persistence/models.py`.
  * Mapeadores de persistência em `src/adapters/persistence/mappers.py`.
  * Scripts de migração em `alembic/versions/`.
* **Gatilho de Execução:** Auditoria final de PR para qualquer alteração que toque modelos, repositórios, migrações ou consultas ao banco de dados.

---

## 2. Checklist Exaustivo de Auditoria de Performance de Banco

O especialista inspeciona o subsistema de persistência respondendo a seis dimensões essenciais:

1. **Detecção e Eliminação Ativa de N+1 Queries:**
   * *O código itera sobre modelos e acessa relacionamentos sem carregamento antecipado?* Toda consulta a entidades que possuem coleções ou chaves estrangeiras associadas que serão lidas deve obrigatoriamente utilizar `selectinload()` ou `joinedload()`.
   * *O uso de lazy loading acidental em produção está mitigado?* Relacionamentos que possam ser lidos fora de sessão aberta devem ser prevenidos com estratégias explícitas de eager loading.

2. **Estratégia de Indexação e Cobertura (Covering Indexes):**
   * *Colunas filtradas por `WHERE` ou `JOIN` possuem índices dedicados?* Toda chave estrangeira e campo de busca (ex: `user_id`, `subject_id`, `flashcard_id`, `gap_index`) deve possuir índice B-Tree indexado.
   * *Consultas críticas de leitura utilizam Covering Indexes?* Quando o banco for PostgreSQL, queries frequentes devem aproveitar a cláusula `INCLUDE` para cobrir colunas de projeção no próprio índice, permitindo *Index-Only Scans*.
   * *Ordenações frequentes são suportadas por índices?* Cláusulas `ORDER BY` combinadas com filtros (ex: `WHERE session_id = :id ORDER BY gap_index ASC`) devem possuir índices compostos que correspondam à ordem das colunas.

3. **Persistência em Lote (*Bulk Operations*) e Batching:**
   * *O código persiste coleções de registros via loop de `add()` e `commit()` individuais?* Isso é terminantemente proibido. Deve-se utilizar métodos em lote (`save_all`, bulk insert ou `db.scalars()` em massa).
   * *Transações atômicas:* Operações que envolvem mútiplos registros devem ser encapsuladas em uma única transação atômica (`session.begin()`), evitando commits intermediários parciais.

4. **Projeções Seletivas vs `SELECT *`:**
   * *O código consulta a linha inteira quando precisa apenas verificar existência ou contar?* Verificações de duplicidade ou existência devem usar `select(exists().where(...))` ou `func.count()`, nunca carregar a entidade completa na memória.
   * *Paginação eficiente:* Consultas paginadas devem priorizar paginação baseada em cursor / gap index em vez de `OFFSET` profundo, que degrada o desempenho proporcionalmente ao número de páginas saltadas.

5. **Gerenciamento Enxuto de Transações e Conexões:**
   * *Transações de banco de dados permanecem abertas durante operações de I/O de rede ou disco?* Transações devem ser delimitadas estritamente ao momento da leitura/escrita, liberando a conexão de volta ao pool imediatamente.
   * *Conexões são sempre liberadas no final?* Assegurar uso de context managers (`with Session() as session:`) ou dependências com `yield` no FastAPI.

6. **Paridade Multi-Engine e Versionamento no Alembic:**
   * *Todos os índices estão registrados em migrações Alembic?* Nenhum índice pode ser criado manualmente; todas as alterações estruturais de DDL devem estar registradas em `alembic/versions/`.
   * *Compatibilidade com SQLite em testes e PostgreSQL em produção:* O código não deve utilizar dialetos proprietários incompatíveis sem o devido tratamento de abstração.

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **13** | **Especialista de Performance de Banco** | `[APROVADO]` | Performance de banco de dados auditada com sucesso. Zero ocorrências de N+1 queries via eager loading (selectinload), índices B-tree e covering indexes presentes para filtros e junções frequentes, persistência em lote (bulk) e transações com ciclo de vida enxuto. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **13** | **Especialista de Performance de Banco** | `[BLOQUEANTE]` | Ineficiência de persistência identificada: [descrever se houve query N+1, falta de índice em chave estrangeira, commit em loop ou ausência de migração Alembic]. Correção obrigatória antes do merge. |
```
