---
name: a11y-wcag-auditor
description: Audits pull request diff against staging for WCAG 2.1 AA accessibility compliance, keyboard navigability, WAI-ARIA semantics, color contrast, and assistive tech support.
---

# Accessibility WCAG Auditor (Skill do Especialista de Acessibilidade)

Esta skill é utilizada pelo **Especialista de Acessibilidade** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é auditar os templates, componentes, formulários e folhas de estilo no diff contra a branch `staging`, assegurando **conformidade rigorosa com as diretrizes internacionais WCAG 2.1 nível AA**, navegabilidade total por teclado, semântica assistiva correta com WAI-ARIA e inclusão universal de usuários com deficiência.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * Templates HTML / Jinja2, componentes de interface, fragmentos dinâmicos e estilos.
  * Diretrizes de design e padrões de acessibilidade WCAG 2.1 AA.
* **Gatilho de Execução:** Auditoria final de PR para qualquer alteração que introduza ou modifique interfaces, formulários ou componentes de usuário.

---

## 2. Checklist Exaustivo de Acessibilidade (WCAG 2.1 AA)

O Especialista de Acessibilidade inspeciona o código respondendo a sete dimensões essenciais:

1. **Operabilidade e Navegação Exclusiva por Teclado:**
   * **Alcance e Acionamento:** Todos os elementos interativos (botões, links, campos de entrada, modais) são alcançáveis via `Tab` e acionáveis via `Enter` ou barra de `Espaço`?
   * **Indicadores de Foco Nítidos:** Todos os elementos focáveis possuem anel de foco visualmente evidente (`focus-visible`)? É terminantemente proibido o uso de `outline: none` sem um anel de foco substituto (ex: `focus:ring-2 focus:ring-offset-2`).
   * **Ordem Lógica de Foco:** A tabulação segue a ordem lógica e visual de leitura do documento, sem uso de `tabindex` positivo arbitrário?
   * **Gestão de Foco em Modais e Diálogos:** Quando um modal ou menu sobreposto se abre, o foco é transferido para dentro dele e mantido enclausurado até o fechamento, sendo devolvido ao botão disparador de origem ao fechar?

2. **Semântica HTML Nativa e WAI-ARIA Disciplinado:**
   * **Primeira Regra do ARIA:** Elementos interativos utilizam tags nativas (`<button>`, `<a href="...">`, `<input>`, `<select>`) em vez de `<div>` com cliques artificiais simulando botões?
   * **Ícones Decorativos:** Ícones puramente visuais e decorativos possuem expressamente o atributo `aria-hidden="true"` para não poluir o leitor de telas?
   * **Botões de Apenas Ícone:** Botões que contêm apenas ícones gráficos possuem `aria-label` descritivo da ação (ex: `<button aria-label="Avançar para o próximo card">`)?
   * **Componentes Expansíveis:** Menus e seções recolhíveis indicam seu estado via `aria-expanded="true/false"` e identificação do alvo via `aria-controls`?

3. **Regiões Dinâmicas e Atualizações Assíncronas (Live Regions):**
   * Em telas com atualizações parciais assíncronas (ex: HTMX swaps de flashcards, carregamento de novas perguntas ou contadores):
     * O container ou anúncio de feedback utiliza `aria-live="polite"` e `aria-atomic="true"` para que os leitores de tela notifiquem a atualização sem interromper o usuário bruscamente?
     * Notificações críticas ou mensagens de erro utilizam `role="alert"` ou `aria-live="assertive"`?

4. **Acessibilidade e Rótulos em Formulários:**
   * Todo campo de entrada (`<input>`, `<textarea>`, `<select>`) possui um elemento `<label>` programaticamente associado via `for="id_do_campo"`?
   * Mensagens de erro de validação de formulário são vinculadas ao campo correspondente através de `aria-describedby="id_do_erro"` e o campo recebe `aria-invalid="true"` quando houver falha?
   * Campos obrigatórios possuem o atributo nativo `required` ou `aria-required="true"`?

5. **Contraste Cromático e Independência de Cor:**
   * **Taxa de Contraste Mínima:** Todos os textos normais atingem no mínimo 4.5:1 de relação de contraste contra a cor de fundo (calculado segundo as regras da WCAG AA)?
   * **Textos Grandes e Elementos Gráficos:** Textos de grande porte (18pt+ ou 14pt negrito) e bordas de componentes ativos atingem no mínimo 3.0:1?
   * **Independência de Cor:** O sistema nunca comunica status, erro ou sucesso exclusivamente através de cores; a cor deve estar sempre acompanhada de texto explícito ou ícone semântico?

6. **Hierarquia de Títulos e Marcos Estruturais (Landmarks):**
   * A página possui um único `<h1>` que sintetiza o propósito principal da tela, seguido por uma estrutura hierárquica coerente de `<h2>` e `<h3>`, sem pular níveis?
   * Os marcos semânticos principais (`<header>`, `<nav>`, `<main>`, `<footer>`) estão presentes e identificam as regiões estruturais do documento?

7. **Movimento Reduzido e Escalabilidade de Zoom:**
   * Animações, transições e efeitos visuais respeitam a preferência do usuário por movimento reduzido (`@media (prefers-reduced-motion: reduce)` ou utilitários `motion-reduce:...`)?
   * A interface suporta ampliação de zoom de até 200% no navegador sem quebrar o layout, sobrepor textos ou inviabilizar o uso?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **9** | **Especialista de Acessibilidade** | `[APROVADO]` | Acessibilidade auditada com sucesso conforme WCAG 2.1 AA. Navegação 100% operável por teclado com anéis de foco evidentes, semântica HTML nativa com WAI-ARIA correto, contraste cromático superior a 4.5:1 e anúncios em regiões dinâmicas (aria-live). |
```

### Caso Reprovado / Bloqueante:
```markdown
| **9** | **Especialista de Acessibilidade** | `[BLOQUEANTE]` | Falha de acessibilidade identificada: [descrever se há falta de foco visível, elementos interativos sem tag nativa/aria-label, contraste insuficiente, formulário sem label associado ou ausência de aria-live em swap dinâmico]. Correção necessária antes do merge. |
```

### Caso N/A Justificado (Sem interface gráfica):
```markdown
| **9** | **Especialista de Acessibilidade** | `[N/A JUSTIFICADO]` | Esta PR não introduz nem modifica templates, componentes visuais ou interfaces; trata-se de escopo puramente backend/infraestrutura sem impacto em acessibilidade. |
```
