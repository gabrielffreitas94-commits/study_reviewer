---
name: ux-journey-auditor
description: Audits pull request diff against staging for user journey smoothness, cognitive load, feedback loops, error prevention, and the 5 essential UI/UX states.
---

# UX Journey Auditor (Skill do Especialista de UX)

Esta skill é utilizada pelo **Especialista de UX** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é auditar os fluxos de navegação, templates e interações no diff contra a branch `staging`, garantindo que a aplicação proporcione uma **experiência fluida, sem atrito cognitivo**, com tratamento rigoroso dos estados de interface, feedback visual instantâneo e aderência às melhores práticas de usabilidade e ergonomia digital.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * Templates HTML / Jinja2, componentes de interface, fragmentos HTMX e estilos.
  * Requisitos da Sprint no `PRD.md` e fluxos de usuário especificados.
* **Gatilho de Execução:** Auditoria final de PR para qualquer entrega que envolva templates, componentes ou fluxos de usuário.

---

## 2. Checklist Exaustivo de Auditoria de UX

O Especialista de UX inspeciona o código e os fluxos respondendo a sete dimensões essenciais:

1. **Visibilidade do Status do Sistema e Feedback Imediato:**
   * O usuário recebe feedback perceptível imediatamente após realizar qualquer ação (clique de botão, submissão de formulário, exclusão)?
   * Requisições assíncronas (ex: requisições HTMX) possuem indicadores visuais de progresso (spinners sutis, desativação temporária de botão ou animação de transição) para informar que o sistema está processando?
   * Ações bem-sucedidas são confirmadas de maneira clara e proporcional (sem sobrecarregar o usuário com modais intrusivos quando um feedback inline é mais adequado)?

2. **Tratamento Integral dos 5 Estados de UX (Five States of UI):**
   * **Ideal State:** Quando a tela possui dados típicos cadastrados, as informações são apresentadas com hierarquia visual clara e legível?
   * **Empty State (Estado Vazio):** Quando uma listagem ou recurso não possui dados (ex: zero matérias, zero flashcards):
     * O sistema evita telas frias ou em branco?
     * Há uma mensagem acolhedora explicando o motivo da tela vazia?
     * Existe um botão ou link de ação primária (*Call to Action*) convidando o usuário a dar o próximo passo (ex: *"Cadastrar primeira matéria"* ou *"Adicionar novo flashcard"*)?
   * **Loading State:** Transições de tela e carregamentos de fragmentos HTMX são suaves e não causam saltos bruscos no layout (*Cumulative Layout Shift*)?
   * **Error State:** As mensagens de erro são comunicadas em linguagem humana e acolhedora, explicando o que ocorreu e oferecendo um caminho de resolução ou botão para tentar novamente?
   * **Partial / Boundary State:** A interface se comporta bem quando há apenas 1 item na tela ou quando há muitos itens?

3. **Minimização da Carga Cognitiva e Fricção:**
   * As ações centrais e frequentes do usuário exigem o menor número de cliques e decisões possíveis?
   * A ação primária de cada tela possui destaque visual evidente em relação a ações secundárias ou de cancelamento?
   * O fluxo de tela não exige que o usuário memorize informações de passos anteriores.

4. **Prevenção Ativa de Erros e Recuperação Graciosa:**
   * Botões de submissão são protegidos contra clique duplo ou submissão múltipla acidental durante o envio?
   * Ações irreversíveis ou destrutivas (ex: exclusão de dados) solicitam confirmação prévia inequívoca?
   * Validações de formulário apontam claramente quais campos necessitam de correção de forma contextual e inline, sem limpar os dados já preenchidos corretamente.

5. **Linguagem Natural e Correspondência com o Modelo Mental:**
   * A interface utiliza os termos e conceitos do domínio do usuário, eliminando totalmente jargões técnicos de infraestrutura ou banco de dados (ex: proibido exibir "Erro de integridade referencial", "Objeto nulo", "Constraint violada")?
   * Ícones possuem rótulos textuais ou atributos explicativos acessíveis.

6. **Consistência Visual e Padrões de Interação:**
   * Botões de ação, links, diálogos e cards seguem os mesmos padrões de comportamento e posicionamento em todas as telas da aplicação?

7. **Fluidez e Rapidez em Tarefas Repetitivas:**
   * Em tarefas de revisão ou estudo contínuo, a transição entre um item e o próximo é instantânea e sem recarregamento completo da página, preservando o ritmo e a concentração do usuário?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **6** | **Especialista de UX** | `[APROVADO]` | Experiência do usuário auditada com sucesso. Jornada fluida e sem fricção, feedback visual imediato em todas as ações, tratamento completo dos 5 estados de interface (com empty state acionável e acolhedor) e linguagem 100% natural. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **6** | **Especialista de UX** | `[BLOQUEANTE]` | Falha de experiência do usuário identificada: [descrever se há falta de feedback em ações assíncronas, empty state inexistente, excesso de cliques, mensagens com jargão técnico ou salto brusco de layout]. Correção necessária antes do merge. |
```

### Caso N/A Justificado (Sem impacto de interface):
```markdown
| **6** | **Especialista de UX** | `[N/A JUSTIFICADO]` | Esta PR não introduz nem modifica templates, componentes visuais ou fluxos de usuário; trata-se de escopo puramente backend/infraestrutura sem impacto em UX. |
```
