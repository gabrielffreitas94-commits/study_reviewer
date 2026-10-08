---
name: mobile-usability-auditor
description: Audits mobile application usability, touch targets ergonomics, safe areas insets, keyboard overflow prevention, and offline-first study experience.
---

# Mobile Usability Auditor (Skill do Especialista Mobile)

Esta skill é operada pelo **Especialista Mobile** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é conduzir uma auditoria técnica detalhada na **ergonomia de toque, navegação com uma só mão, proteção de áreas seguras (*safe areas*), responsividade de viewport sob abertura de teclado e resiliência de uso offline** no aplicativo mobile.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Componentes e telas mobile: `mobile/lib/presentation/`, `mobile/lib/widgets/`.
  * Layouts, temas e dimensões visuais.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para qualquer alteração que introduza ou modifique telas, formulários, botões, modais ou fluxos de interação touch no mobile.

---

## 2. Checklist Exaustivo de Auditoria de Usabilidade Mobile

O Especialista Mobile avalia os seguintes pontos de usabilidade e ergonomia:

1. **Touch Targets e Área de Toque Ergonômica:**
   * *Dimensão Mínima de Toque:* Todos os botões, ícones acionáveis, flashcards e opções de resposta possuem área interativa mínima de $48 \times 48$ dp?
   * *Espaçamento Entre Controles:* Existe espaçamento de pelo menos $8$ dp entre elementos clicáveis adjacentes para evitar toques acidentais (*fat-finger errors*)?

2. **Thumb Zone e Safe Areas:**
   * *Zona de Alcance Natural do Polegar:* As ações mais frequentes do usuário (virar card, marcar acerto/erro, avançar) estão posicionadas na metade inferior da tela (*thumb zone*)?
   * *Proteção de Insets do Sistema:* Todas as telas utilizam `SafeArea` ou consideram `MediaQuery.of(context).padding` para evitar sobreposição por entalhes (*notches*), furos de câmera e barras de gestos do sistema operacional?

3. **Adaptação de Viewport e Prevenção de Overflow por Teclado:**
   * *Zero Overflow com Teclado Aberto:* Telas contendo campos de texto (`TextField`, `TextFormField`) utilizam `SingleChildScrollView` ou layout rolável equivalente com `resizeToAvoidBottomInset: true`?
   * *Foco Visível:* O campo de texto em edição permanece visível e centralizado na viewport quando o teclado virtual é exibido?

4. **Experiência Offline-First e Feedback de Sincronização:**
   * *Continuidade Offline:* O estudante consegue navegar e responder a rodadas de flashcards sem conexão ativa com a internet?
   * *Feedback Não-Intrusivo:* Estados de sincronização pendente são exibidos de forma sutil e não-bloqueante (ex: indicador discreto no cabeçalho), sem emitir alertas modais obstrutivos durante o estudo?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **14** | **Especialista Mobile** | `[APROVADO]` | Usabilidade mobile auditada com sucesso. Touch targets ergonômicos (>= 48dp), safe areas respeitadas em todos os layouts, prevenção de overflow na abertura de teclado e suporte a fluxo de estudo offline. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **14** | **Especialista Mobile** | `[BLOQUEANTE]` | Falha de usabilidade mobile identificada: [descrever se houve touch target inferior a 48dp, tarja amarela de overflow visual com teclado aberto ou corte de elementos pelo notch]. Correção obrigatória antes do merge. |
```
