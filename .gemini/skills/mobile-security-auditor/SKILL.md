---
name: mobile-security-auditor
description: Audits mobile application security, hardware-backed storage (KeyStore/Keychain), zero plaintext credentials, release obfuscation, and manifest permissions.
---

# Mobile Security Auditor (Skill do Especialista Mobile)

Esta skill é operada pelo **Especialista Mobile** durante a fase de auditoria final da Sprint, imediatamente antes da abertura ou aprovação da Pull Request para a branch `staging`.

Seu objetivo é auditar exaustivamente a **segurança de armazenamento local, proteção de credenciais em cofres criptográficos de hardware, integridade do aplicativo e minimização de permissões de sistema** de acordo com os padrões OWASP MASVS (Mobile Application Security Verification Standard).

---

## 1. Entrada e Gatilho
* **Arquivos e Artefatos Base:**
  * Camada de armazenamento e autenticação mobile: `mobile/lib/data/datasources/`, `mobile/lib/core/security/`.
  * Manifestos e configurações de build: `mobile/android/app/src/main/AndroidManifest.xml`, `mobile/ios/Runner/Info.plist`, `mobile/android/app/build.gradle*`.
  * Git diff da branch da sprint contra a branch `staging` (`git diff staging...HEAD`).
* **Gatilho de Execução:** Auditoria de PR para alterações que envolvam login, persistência de tokens, permissões nativas, builds de release ou chamadas de segurança local.

---

## 2. Checklist Exaustivo de Auditoria de Segurança Mobile

O Especialista Mobile audita o código avaliando os seguintes requisitos de segurança:

1. **Armazenamento Seguro em Hardware (OWASP MASVS-STORAGE):**
   * *Zero Plaintext Storage:* Tokens JWT, segredos de autenticação e dados pessoais sensíveis são persistidos exclusivamente através de cofres de hardware seguro (*Android KeyStore* com criptografia AES e *iOS Keychain* via `flutter_secure_storage`)?
   * *Proibição em SharedPreferences:* O uso de *SharedPreferences* ou *UserDefaults* é restrito estritamente a configurações não sensíveis de UI (ex: tema claro/escuro)?

2. **Ofuscação de Binários e Remoção de Metadados:**
   * *R8 / ProGuard:* O build de release do Android possui regras ativas de minificação e ofuscação de símbolos (`minifyEnabled true`, `shrinkResources true`)?
   * *Flutter Obfuscate:* O pipeline de empacotamento utiliza a flag `--obfuscate` com `--split-debug-info` para prevenir engenharia reversa das regras de negócio?

3. **Proteção de Telas e Dados em Multitarefa:**
   * *Prevenção de Gravação de Tela Indevida:* Telas que manipulam credenciais ou dados pessoais ativam flags de proteção de tela (`FLAG_SECURE` no Android / overlay seguro no iOS) para impedir screenshots e visualização no alternador de apps do SO?

4. **Permissões Mínimas nos Manifestos (Privilégio Mínimo):**
   * *AndroidManifest.xml & Info.plist:* Apenas as permissões estritamente essenciais para o escopo do app estão declaradas? Permissões de risco (acesso a contatos, localização em background, microfone sem uso) estão banidas se não justificadas no PRD?

---

## 3. Emissão de Parecer na PR

A skill gera a saída formal padronizada para inclusão na tabela de especialistas da Pull Request:

### Caso Aprovado:
```markdown
| **14** | **Especialista Mobile** | `[APROVADO]` | Segurança mobile auditada com sucesso. Armazenamento seguro de tokens via hardware KeyStore/Keychain, zero credenciais em texto plano, ofuscação de release ativa e manifestos com privilégio mínimo de permissões. |
```

### Caso Reprovado / Bloqueante:
```markdown
| **14** | **Especialista Mobile** | `[BLOQUEANTE]` | Vulnerabilidade de segurança mobile identificada: [descrever se houve gravação de token em SharedPreferences desprotegido, ausência de ofuscação no build de release ou permissão abusiva no manifesto]. Correção obrigatória antes do merge. |
```
