---
name: frontend-performance-auditor
description: Audits pull request changes for Core Web Vitals (LCP, INP, CLS), static asset minification, DOM efficiency, layout thrashing prevention, and optimal HTMX partial swaps.
---

# Frontend Performance Auditor (Skill do Especialista de Performance Frontend)

Esta skill é operada pelo **Especialista de Performance de Frontend** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para `staging`.

Seu objetivo é inspecionar templates HTML/Jinja2, estilos Tailwind CSS, comportamento de scripts e fragmentos HTMX no diff contra a branch `staging`, assegurando **excelência em Core Web Vitals**, ausência de reflows desnecessários no DOM (*layout thrashing*), tempos de resposta de UI ultrarrápidos e tamanho mínimo de download de assets.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
  * Templates e parciais em `src/adapters/web/templates/`.
  * Arquivos de estilo em `src/adapters/web/static/css/` e `tailwind.config.js`.
  * Configuração de empacotamento em `package.json`.
* **Gatilho de Execução:** Auditoria final de PR para qualquer alteração que toque templates, estilos, scripts ou renderização web.

---

## 2. Checklist Exaustivo de Auditoria de Performance Frontend

O especialista inspeciona o frontend respondendo a seis dimensões essenciais:

1. **Conformidade com Core Web Vitals:**
   * **Largest Contentful Paint (LCP $\le 2.5\text{s}$):** Os elementos principais de cada tela (ex: flashcard principal, cabeçalho da matéria) carregam imediatamente sem aguardar folhas de estilo pesadas ou múltiplos scripts encadeados?
   * **Interaction to Next Paint (INP $\le 200\text{ms}$):** Ações imediatas do usuário (ex: atalhos de teclado para virar o card, clique no botão de resposta, digitação de busca) produzem resposta visual perceptível em menos de 100ms?
   * **Cumulative Layout Shift (CLS $\le 0.1$):** Containers dinâmicos possuem altura mínima ou proporções reservadas (ex: `min-h-[...]`, `aspect-ratio`) para que a inserção assíncrona de novos cartões não cause saltos verticais no layout?

2. **Minimização e Purga de Assets Estáticos (Tailwind CSS):**
   * *O bundle CSS foi compilado em modo de produção com `--minify`?* O comando `npm run build:css` deve gerar um único arquivo `tailwind.css` enxuto.
   * *O `tailwind.config.js` rastreia adequadamente todos os arquivos de template?* Todas as classes utilitárias não utilizadas devem ser purgadas do arquivo final.

3. **Eficiência no DOM e Prevenção de Layout Thrashing:**
   * *Paginação e Lazy Rendering no DOM:* Listas extensas (como dezenas de matérias e temas) devem renderizar apenas os elementos visíveis na página/viewport ou paginar o DOM, evitando dezenas de milhares de nós no DOM tree.
   * *Busca Client-side Leve:* A filtragem em tempo real de temas e matérias deve manipular atributos de visibilidade (`hidden` / `classList`) de forma em lote, evitando ler propriedades geométricas (`offsetWidth`, `getBoundingClientRect`) durante mutações contínuas.
   * *Debouncing Obrigatório:* Campos de filtro textual devem usar debounce no evento `input` para não recalcular visibilidade a cada caractere digitado.

4. **Fragmentos HTMX e Custo de Rede:**
   * *Trocas Parciais Mínimas:* As rotas de swap do HTMX (`hx-get`, `hx-post`) devem retornar estritamente os nós que serão substituídos (partials), nunca a página inteira re-renderizada.
   * *Transições Suaves Aceleradas por Hardware:* Animações e flips de cartão devem utilizar propriedades CSS aceleradas por GPU (`transform`, `opacity`), nunca animando propriedades que forcem repaint/reflow (`width`, `height`, `top`, `left`).

5. **Eliminação de Bloqueio de Renderização e FOUC:**
   * *Scripts com Defer:* Scripts não-críticos devem possuir o atributo `defer` ou estar localizados imediatamente antes do fechamento da tag `</body>`.
   * *Prevenção de FOUC:* Scripts críticos de preferência de tema (Dark/Light mode) devem ser inline e ultraenxutos no `<head>`, prevenindo telas brancas rápidas durante o carregamento inicial.

6. **Processamento Isolado de Frontend no CI:**
   * O pipeline de CI deve validar o build de assets frontend em contêiner/ambiente Node isolado, garantindo paridade e ausência de dependência de binários globais.

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **12** | **Especialista de Performance Frontend** | `[APROVADO]` | Performance de frontend validada com louvor. Tailwind CSS estático minificado e purgado, Core Web Vitals otimizados (LCP/INP/CLS), paginação eficiente de DOM sem layout thrashing, fragmentos HTMX enxutos e scripts com execução não-bloqueante. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **12** | **Especialista de Performance Frontend** | `[BLOQUEANTE]` | Gargalo de frontend identificado: [descrever se houve falta de minificação do CSS, alto CLS por ausência de altura fixa, layout thrashing em buscas ou envio de página inteira em swap HTMX]. Otimização obrigatória antes do merge. |
```

### Caso Não Aplicável (Justificado):
```markdown
| **12** | **Especialista de Performance Frontend** | `[N/A JUSTIFICADO]` | Esta PR não introduz nem modifica templates, componentes visuais, estilos ou scripts; trata-se de escopo puramente backend/infraestrutura sem impacto na camada de apresentação frontend. |
```
