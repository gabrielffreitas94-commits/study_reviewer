---
name: ui-interface-auditor
description: Audits pull request diff against staging for mobile-first responsiveness, design system token consistency, interactive element states, and frontend template clean code.
---

# UI Interface & Components Auditor (Skill do Especialista de UI)

Esta skill é utilizada pelo **Especialista de UI** durante a auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request.

Seu objetivo é auditar os templates, componentes visuais, folhas de estilo e utilitários no diff contra a branch `staging`, garantindo a **excelência estética, responsividade impecável (Mobile-First)**, fidelidade aos tokens do sistema de design, microinterações completas e higiene de código frontend.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * Templates HTML / Jinja2, componentes de interface, fragmentos HTMX e configurações de estilo (Tailwind / CSS).
  * Design tokens e escala visual estabelecida no projeto.
* **Gatilho de Execução:** Auditoria final de PR para qualquer alteração que introduza ou modifique interfaces gráficas.

---

## 2. Checklist Exaustivo de Auditoria de Interface (UI)

O Especialista de UI inspeciona a camada de apresentação através de sete dimensões estruturais:

1. **Responsividade Mobile-First e Ausência de Quebras de Layout:**
   * **Abordagem Mobile-First:** O design foi concebido prioritariamente para telas pequenas e adaptado responsivamente para telas maiores?
   * **Zero Scroll Horizontal:** Em telas estreitas de smartphones (360px a 430px), a interface não gera rolagem horizontal involuntária (`overflow-x`)? Textos longos quebram linhas adequadamente?
   * **Adaptação Fluida:** Em telas médias (tablets: 768px a 1024px) e desktops (1280px+), o layout aproveita o espaço com elegância, sem esticar elementos desproporcionalmente.

2. **Consistência de Tokens do Design System:**
   * **Paleta Cromática Semântica:** Uso disciplinado das cores do projeto (ação primária, superfícies de fundo, cores de texto de alto e baixo contraste, bordas, estados de sucesso e perigo). Proibição de cores arbitrárias fora da escala.
   * **Escala Tipográfica:** Relação hierárquica clara entre títulos (`h1`, `h2`, `h3`), parágrafos, legendas e badges, mantendo legibilidade e peso de fontes consistentes.
   * **Ritmo Espacial:** Uso consistente da escala de espaçamento (padding e margin) entre cards, containers, botões e campos de entrada.
   * **Bordas e Elevações:** Padronização nos raios de arredondamento (*border-radius*) e nas sombras (*box-shadow*).

3. **Estados Interativos Completos dos Elementos:**
   * Todo elemento interativo (botões, links, cards clicáveis, campos de formulário) possui estilos distintos, perceptíveis e semânticos para:
     * **Default:** Estado normal de repouso.
     * **Hover:** Feedback sutil ao passar o cursor (mudança suave de cor ou elevação).
     * **Focus / Focus-visible:** Anel ou contorno de foco evidente para navegação por teclado (ex: `focus:ring-2 focus:outline-none`).
     * **Active:** Resposta tátil ao clique/pressão.
     * **Disabled:** Estado inativo visualmente indiscutível (opacidade reduzida, cursor `not-allowed`, sem disparar ações).

4. **Dinâmica de Atualizações e Swaps de Fragmentos (HTMX / Transições):**
   * As substituições parciais de HTML (via HTMX ou equivalente) ocorrem de maneira suave, sem provocar cintilação de tela (*flicker*) ou recarregamentos pesados.
   * O container de substituição mantém altura ou dimensões estáveis durante o processamento para evitar colapsos temporários de layout.

5. **Semântica HTML e Limpeza Estrutural:**
   * Uso adequado de elementos semânticos estruturais (`<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<aside>`).
   * Proibição de `<div>` ou `<span>` com manipuladores de clique atuando como botões disfarçados; elementos interativos devem ser estritamente `<button>` ou `<a>`.
   * Campos de formulário com rótulos semânticos explicitamente associados (`<label for="...">`).

6. **Ergonomia e Alvos de Toque em Telas Sensíveis ao Toque:**
   * Botões, ícones clicáveis e links em interfaces mobile possuem área de toque confortável (tamanho mínimo recomendado de 44x44px ou 48x48px).
   * Espaçamento adequado entre elementos clicáveis adjacentes para impedir toques acidentais no elemento vizinho.

7. **Qualidade e Otimização de Assets Visuais:**
   * Ícones em formato vetorial (SVG) com viewBox adequado, cores herdadas via `currentColor` e dimensões nítidas.
   * Elementos visuais não pesam desnecessariamente no carregamento ou na renderização do navegador.

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **7** | **Especialista de UI** | `[APROVADO]` | Interface de usuário auditada com sucesso. Responsividade mobile-first impecável (sem scroll horizontal), fidelidade total aos tokens de design system, estados interativos (hover/focus/disabled) implementados e swaps dinâmicos fluidos. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **7** | **Especialista de UI** | `[BLOQUEANTE]` | Falha de interface de usuário identificada: [descrever se há quebra de layout mobile, scroll horizontal involuntário, estilos arbitrários fora do design system, ausência de estado de foco ou elemento interativo sem tag semântica]. Correção necessária antes do merge. |
```

### Caso N/A Justificado (Sem interface gráfica):
```markdown
| **7** | **Especialista de UI** | `[N/A JUSTIFICADO]` | Esta PR não introduz nem modifica templates, componentes visuais ou estilos; trata-se de escopo puramente backend/infraestrutura sem impacto em UI. |
```
