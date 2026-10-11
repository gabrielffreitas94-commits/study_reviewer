---
name: flutter-code-quality-auditor
description: Audits Dart code quality, lifecycle management, leak-free dispose execution, isolate compute offload, Clean Architecture layering, and analysis_options strict compliance.
---

# Flutter Code Quality Auditor (Skill do Especialista Flutter)

Esta skill é operada pelo **Especialista Flutter** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é conduzir uma auditoria rigorosa de **qualidade de engenharia de software em Dart: conformidade estrita com as regras de análise estática, descarte compulsório de recursos em `dispose()` (zero memory leaks), Clean Architecture client-side, imutabilidade e offload de computação pesada para Dart Isolates**.

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Base de código Dart: `mobile/lib/` e suíte de testes `mobile/test/`.
  * Regras de linter: `mobile/analysis_options.yaml`, `mobile/pubspec.yaml`.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para qualquer alteração que adicione, modifique ou refatore código Dart, lógica de domínio mobile, controllers ou suítes de teste.

---

## 2. Checklist Exaustivo de Qualidade de Código Dart & Flutter

O Especialista Flutter avalia o código sob cinco pilares de boas práticas:

1. **Ciclo de Vida Limpo e Descarte Obrigatório em `dispose()` (Zero Leaks):**
   * *Descarte de Controllers:* Todo `StatefulWidget` que crie ou instancie `TextEditingController`, `AnimationController`, `ScrollController` ou `FocusNode` invoca obrigatoriamente o método `.dispose()` no encerramento do widget?
   * *Encerramento de Assinaturas:* Streams e listeners reativos (`StreamSubscription`, `ChangeNotifier`) são explicitamente cancelados em `dispose()` ou gerenciados por wrappers de ciclo de vida automáticos?

2. **Concorrência e Offloading de Tarefas Pesadas (Dart Isolates):**
   * *Thread Principal Desimpedida:* Operações de parsing de JSON de grande porte, rotinas de criptografia, decodificação de áudio ou cálculos de métricas de estudo são transferidos para threads secundárias via `compute()` ou `Isolate.run()`?
   * *Zero I/O Síncrono:* Nenhuma leitura ou escrita síncrona de arquivo (`dart:io` com métodos síncronos) é executada na thread de UI.

3. **Conformidade Estrita com `analysis_options.yaml`:**
   * *Zero Warnings:* O comando `flutter analyze` executa e conclui com 100% de sucesso, sem erros, sem avisos (*warnings*) e sem informações pendentes (*infos*)?
   * *Tipagem Estrita:* O código proíbe chamadas dinâmicas inseguras (`avoid_dynamic_calls`), variáveis de tipo omitido e futures não aguardados (`unawaited_futures`)?

4. **Clean Architecture e Imutabilidade no Client:**
   * *Separação em Camadas:* As regras de negócio do app residem no domínio puro (`mobile/lib/domain/`), sem acoplamento a classes ou widgets do framework Flutter?
   * *Modelagem Imutável:* Entidades e estados utilizam comparação por valor e imutabilidade declarativa via `freezed`, `equatable` ou classes `final` com `copyWith()`.

5. **Testabilidade e Cobertura de Testes Mobile:**
   * *Testes Unitários & Widget Tests:* Use cases e gerenciadores de estado possuem testes unitários e de integração de widgets correspondentes em `mobile/test/`.

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **15** | **Especialista Flutter** | `[APROVADO]` | Boas práticas e qualidade de código Flutter auditadas com sucesso. Ciclo de vida estrito sem memory leaks (todos os controllers descartados em dispose), tarefas pesadas delegadas a Isolates, Clean Architecture respeitada e zero avisos no flutter analyze. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **15** | **Especialista Flutter** | `[BLOQUEANTE]` | Violação de qualidade de código Dart identificada: [descrever se houve controller sem dispose, computação pesada síncrona na UI thread, acoplamento de domínio com widgets ou aviso no flutter analyze]. Correção obrigatória antes do merge. |
```
