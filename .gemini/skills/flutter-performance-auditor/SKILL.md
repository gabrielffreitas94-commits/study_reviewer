---
name: flutter-performance-auditor
description: Audits Flutter rendering performance, widget tree rebuild minimization, const constructor enforcement, virtualized lists, image caching, and 60/120 FPS frame budget.
---

# Flutter Performance Auditor (Skill do Especialista Flutter)

Esta skill é operada pelo **Especialista Flutter** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é auditar exaustivamente a **performance do pipeline de renderização do Flutter: eliminação de rebuilds redundantes na árvore de widgets, uso de construtores const, virtualização de listas, dimensionamento de bitmaps na memória gráfica e garantia de frame budget de 60/120 FPS sem jank**.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Componentes e widgets visuais: `mobile/lib/presentation/`.
  * Gerenciamento de estado de tela: Blocs, Cubits, ValueNotifiers.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para alterações que adicionem, alterem ou refatorem widgets Flutter, telas de estudo, listas ou animações.

---

## 2. Checklist Exaustivo de Auditoria de Performance Flutter

O Especialista Flutter avalia o código sob os seguintes critérios de performance visual:

1. **Minimização de Rebuilds e Construtores Const:**
   * *Uso Sistemático de `const`:* Todos os widgets que possuem argumentos estáticos declaram o construtor `const` para que o framework reutilize as instâncias da Element Tree sem reconstruí-las?
   * *Isolamento Reativo:* A reatividade de estado é delimitada no nó mais folha da árvore de widgets? O código utiliza construtores granulares (`ValueListenableBuilder`, `BlocBuilder` com `buildWhen`, `Selector`) em vez de reconstruir o corpo da tela inteiro?
   * *Proibição de `setState()` no Topo:* Proibido o acionamento de `setState()` no nível de `Scaffold` ou na raiz da tela.

2. **Virtualização Eficiente de Listas e Coleções:**
   * *`ListView.builder` & `SliverList`:* Listas dinâmicas ou potencialmente longas (cards, matérias, tópicos) utilizam virtualização com `.builder` em vez de colunas com filhos pré-instanciados em lista fixa?
   * *`itemExtent` / `prototypeItem`:* Listas com itens de altura uniforme declaram `itemExtent` explícito para permitir que o Flutter calcule o offset de rolagem em $\mathcal{O}(1)$ sem layout síncrono prévio?

3. **Otimização de Bitmaps e Imagens na Memória:**
   * *`cacheWidth` & `cacheHeight`:* Imagens renderizadas através de `ResizeImage`, `Image.asset` ou `Image.network` especificam restrições de decodificação de dimensões compatíveis com o tamanho de exibição na tela, prevenindo desperdício massivo de heap gráfico?

4. **Frame Budget e Ausência de Jank (60/120 FPS):**
   * *Raster & UI Threads:* O código evita criar layouts complexos em loops contínuos de animação que excedam o limite de $16.6\text{ms}$ por quadro ($8.3\text{ms}$ em 120Hz)?
   * *Clipping Eficiente:* O uso de `ClipRRect` e `BackdropFilter` é mantido estritamente moderado, evitando passagens excessivas de offscreen rendering na GPU?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **15** | **Especialista Flutter** | `[APROVADO]` | Performance Flutter auditada com sucesso. Árvore de widgets otimizada com construtores const, reatividade isolada no nível folha, listas virtuais com itemExtent e dimensionamento correto de bitmaps sem frame drops. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **15** | **Especialista Flutter** | `[BLOQUEANTE]` | Ineficiência de renderização Flutter identificada: [descrever se houve rebuild redundante de tela na raiz, ListView com filhos estáticos sem virtualização ou imagem sem cacheWidth estourando a memória]. Correção obrigatória antes do merge. |
```
