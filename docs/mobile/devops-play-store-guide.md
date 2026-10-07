# Guia de Engenharia de Release e Publicação na Google Play Store
## Study Reviewer Mobile — DevOps, CI/CD e Play Store Compliance

> **Documento:** `docs/mobile/devops-play-store-guide.md`  
> **Responsável:** Especialista de DevOps & CI/CD (#8)  
> **Status:** Ativo / Aprovado pela Bancada dos 13 Especialistas  
> **Versão:** 1.0 — Sprint 05 (Marco 5)  
> **Aderência:** [Especificação da Sprint 05](file:///c:/Users/Pichau/Desktop/study_reviewer/docs/specs/sprint-05-mobile-app-google-play-spec.md) e [PRD v7.0](file:///c:/Users/Pichau/Desktop/study_reviewer/PRD.md#L268-L285).

---

## 1. Visão Geral e Princípios de Release Engineering

A publicação e distribuição do aplicativo **Study Reviewer Mobile (Flutter/Android)** na **Google Play Store** seguem os mais estritos princípios de segurança operacional, automação declarativa e conformidade regulatória.

### Pilares Fundamentais:
1. **Segurança de Segredos (Zero Trust):** Nenhum certificado criptográfico (`*.jks`, `*.keystore`) ou arquivo com credenciais em texto puro (`key.properties`, `local.properties`) jamais é versionado no Git.
2. **Empacotamento Moderno (Android App Bundle - `.aab`):** Distribuição exclusiva via formato AAB com o Google Play App Signing, viabilizando compilações otimizadas (Dynamic Delivery, split APKs por densidade de tela e ABI).
3. **Ofuscação e Minificação com R8/ProGuard:** Redução do binário final, otimização de bytecode e proteção do código proprietário contra engenharia reversa.
4. **Conformidade Estrita com Políticas da Google Play:** Total alinhamento com a seção de **Data Safety**, obrigatoriedade de exclusão de conta in-app/web e classificação etária IARC.

---

## 2. Geração da Keystore Criptográfica de Upload

O Google Play App Signing opera com duas chaves:
- **Chave de Upload:** Gerada pela equipe de engenharia e utilizada para assinar os `.aab` enviados ao Google Play Console.
- **Chave de Assinatura do App:** Gerada e custodiada com segurança pela infraestrutura do Google para assinar os APKs finais entregues aos dispositivos dos usuários.

### 2.1 Comando de Geração via `keytool`
Utilize o utilitário `keytool` empacotado no JDK 17 (OpenJDK / Temurin) para gerar uma keystore criptográfica moderna no padrão PKCS12:

```bash
keytool -genkeypair -v \
  -keystore upload-keystore.jks \
  -storetype PKCS12 \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -alias upload \
  -storepass "<SENHA_FORTE_DA_KEYSTORE>" \
  -keypass "<SENHA_FORTE_DA_CHAVE>" \
  -dname "CN=Study Reviewer DevOps, OU=Engineering, O=Study Reviewer, L=Sao Paulo, ST=SP, C=BR"
```

> [!IMPORTANT]
> - **Validade:** 10.000 dias (~27 anos) garante que o certificado não expire durante o ciclo de vida do aplicativo.
> - **Storetype:** `PKCS12` é o padrão industrial recomendado pelo Android Gradle Plugin moderno.
> - **Guarda do Arquivo:** O arquivo binário `upload-keystore.jks` original deve ser armazenado com criptografia em repouso no cofre corporativo de senhas (1Password / Bitwarden / HashiCorp Vault) com acesso restrito a administradores.

---

## 3. Configuração Local do Gradle (`android/key.properties`)

Para permitir builds assinados em ambiente de desenvolvimento local sem expor credenciais ao repositório Git, o projeto utiliza um arquivo desacoplado `android/key.properties`.

### 3.1 Estrutura de `android/key.properties`
Crie o arquivo local em `mobile/android/key.properties`:

```properties
storePassword=SENHA_FORTE_DA_KEYSTORE
keyPassword=SENHA_FORTE_DA_CHAVE
keyAlias=upload
storeFile=/caminho/absoluto/ou/relativo/para/upload-keystore.jks
```

### 3.2 Proteção no `.gitignore`
Assegure que os seguintes padrões constam explicitamente no `.gitignore` raiz do projeto:

```gitignore
# Android & Flutter Mobile Secrets & Artifacts
*.jks
*.keystore
android/key.properties
android/local.properties
.dart_tool/
.flutter-plugins
.flutter-plugins-dependencies
.packages
.pub-cache/
.pub/
mobile/build/
build/
*.aab
*.apk
```

### 3.3 Integração no `android/app/build.gradle`
Configure a leitura segura do `key.properties` no Gradle:

```groovy
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    ...
    signingConfigs {
        release {
            if (keystorePropertiesFile.exists()) {
                keyAlias keystoreProperties['keyAlias']
                keyPassword keystoreProperties['keyPassword']
                storeFile file(keystoreProperties['storeFile'])
                storePassword keystoreProperties['storePassword']
            }
        }
    }

    buildTypes {
        release {
            signingConfig signingConfigs.release
            ...
        }
    }
}
```

---

## 4. Injeção Segura de Segredos no GitHub Actions

Em ambientes de Integração Contínua (CI/CD), a assinatura do artefato de produção deve ser realizada dinamicamente através de **GitHub Actions Secrets**, sem qualquer persistência estática de segredos no disco do runner após o encerramento do job.

### 4.1 Codificação da Keystore em Base64
Converta o arquivo binário `upload-keystore.jks` em uma string Base64 de linha única:

```bash
# No Linux / macOS:
base64 -w 0 upload-keystore.jks > upload-keystore.jks.base64

# No Windows (PowerShell):
[Convert]::ToBase64String([IO.File]::ReadAllBytes("upload-keystore.jks")) | Out-File -Encoding ascii upload-keystore.jks.base64
```

### 4.2 Catálogo de Secrets do Repositório
No repositório do GitHub, configure em **Settings > Secrets and variables > Actions**:

| Secret Name | Conteúdo | Descrição |
| :--- | :--- | :--- |
| `ANDROID_KEYSTORE_BASE64` | `MIIK...==` | Conteúdo codificado em Base64 da keystore binária |
| `KEYSTORE_PASSWORD` | `<secret>` | Senha de proteção do arquivo de keystore |
| `KEY_ALIAS` | `upload` | Alias da chave gerada no `keytool` |
| `KEY_PASSWORD` | `<secret>` | Senha específica da chave de assinatura |

### 4.3 Pipeline de Release: Decodificação e Limpeza Segura
Snippet de workflow para build assinado em produção (`cd-mobile-release.yml`):

```yaml
      - name: Reconstitute Android Keystore and Properties
        env:
          KEYSTORE_BASE64: ${{ secrets.ANDROID_KEYSTORE_BASE64 }}
          KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
          KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
          KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
        run: |
          mkdir -p mobile/android
          echo "$KEYSTORE_BASE64" | base64 --decode > mobile/android/upload-keystore.jks
          cat <<EOF > mobile/android/key.properties
          storePassword=$KEYSTORE_PASSWORD
          keyPassword=$KEY_PASSWORD
          keyAlias=$KEY_ALIAS
          storeFile=upload-keystore.jks
          EOF
          chmod 600 mobile/android/upload-keystore.jks mobile/android/key.properties

      - name: Build Production Android App Bundle
        working-directory: mobile
        run: flutter build appbundle --release

      - name: Shred Ephemeral Signing Secrets
        if: always()
        run: |
          shred -u mobile/android/upload-keystore.jks 2>/dev/null || rm -f mobile/android/upload-keystore.jks
          shred -u mobile/android/key.properties 2>/dev/null || rm -f mobile/android/key.properties
```

---

## 5. Regras de Compilação R8/ProGuard no `build.gradle`

O compilador R8 executa três tarefas primordiais:
1. **Shrinking (Redução de Código e Recursos):** Descarta classes, métodos e recursos XML/drawables não referenciados.
2. **Optimization (Otimização):** Inlining de métodos curtos, simplificação de fluxos e remoção de instruções mortas.
3. **Obfuscation (Ofuscação):** Renomeia classes e campos públicos/privados para sequências alfanuméricas mínimas (`a`, `b`, `c`), inibindo engenharia reversa.

### 5.1 Configuração no `android/app/build.gradle`

```groovy
android {
    compileSdkVersion 34

    defaultConfig {
        applicationId "com.studyreviewer.app"
        minSdkVersion 24        // Android 7.0 (Nougat) ou superior
        targetSdkVersion 34     // Android 14 (Obrigatório pela Google Play)
        versionCode 1
        versionName "1.0.0"
        testInstrumentationRunner "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            signingConfig signingConfigs.release
            
            // Habilitação da minificação e otimização de bytecode via R8
            minifyEnabled true
            shrinkResources true
            
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
        debug {
            minifyEnabled false
            shrinkResources false
        }
    }
}
```

*(Caso utilize o formato moderno Kotlin DSL `build.gradle.kts`):*
```kotlin
buildTypes {
    release {
        signingConfig = signingConfigs.getByName("release")
        isMinifyEnabled = true
        isShrinkResources = true
        proguardFiles(
            getDefaultProguardFile("proguard-android-optimize.txt"),
            "proguard-rules.pro"
        )
    }
}
```

### 5.2 Regras Personalizadas em `android/app/proguard-rules.pro`
O Flutter exige regras específicas para garantir que classes invocadas via reflexão ou canais de plataforma (`Platform Channels`) não sofram remoção inadvertida:

```proguard
# ====================================================================
# ProGuard / R8 Rules — Study Reviewer Mobile
# ====================================================================

# 1. Preservação do Flutter Engine e Platform Channels
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.**  { *; }
-keep class io.flutter.util.**  { *; }
-keep class io.flutter.view.**  { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }

# 2. Preservação de atributos para Stack Traces legíveis no Play Console
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile

# 3. Modelos de dados serializados (JSON / DTOs)
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}
-keepattributes Signature
-keepattributes *Annotation*

# 4. Plugins nativos essenciais (Flutter Secure Storage & SQLite)
-keep class com.it_nomads.fluttersecurestorage.** { *; }
-keep class com.tekartik.sqflite.** { *; }

# 5. Supressão de warnings de pacotes terceiros conhecidos
-dontwarn io.flutter.embedding.**
-dontwarn okio.**
```

### 5.3 Mapeamento de Símbolos (`mapping.txt`)
Durante a compilação do release, o R8 gera o arquivo de desobfuscação em:
`mobile/build/app/outputs/mapping/release/mapping.txt`

Esse arquivo deve ser enviado ao **Google Play Console** na seção de **Arquivos de desobfuscação** para permitir que relatórios de travamento (ANRs e Crashes) exibam stack traces com nomes originais de métodos e linhas de código.

---

## 6. Checklist de Conformidade do Google Play Console

### 6.1 Formulário de Segurança dos Dados (Data Safety)
A Google Play exige declaração detalhada sobre coleta, compartilhamento e tratamento de dados:

| Categoria do Dado | Tipo Declarado | Finalidade | Coletado / Compartilhado | Criptografia em Trânsito |
| :--- | :--- | :--- | :--- | :--- |
| **Informações Pessoais** | Nome e E-mail | Gerenciamento de conta, autenticação e comunicação | Coletado (Não compartilhado com terceiros) | Sim (HTTPS / TLS 1.3) |
| **Atividade no App** | Interações e progresso (respostas SRS, tempo de revisão) | Funcionalidade do aplicativo e análise de retenção | Coletado (Não compartilhado com terceiros) | Sim (HTTPS / TLS 1.3) |
| **Desempenho e Diagnóstico** | Logs de erro e métricas de latência | Manutenção da qualidade e estabilidade técnica | Coletado (Desidentificado / Agregado) | Sim (HTTPS / TLS 1.3) |

#### Requisitos de Exclusão de Dados:
- **Exclusão In-App:** O app possui botão explícito em `Configurações > Minha Conta > Excluir Conta` que consome o endpoint `DELETE /api/v1/auth/account`.
- **Exclusão Web Externa:** Usuários que desinstalaram o app podem solicitar a exclusão de seus dados através da URL pública:  
  `https://studyreviewer.com/privacy/account-deletion-request`
- **Retenção & Desidentificação:** Em conformidade com a LGPD (Art. 16, IV), os dados pessoais do usuário são apagados de imediato, e as métricas históricas de estudo são irreversivelmente anonimizadas (`ON DELETE SET NULL`).

---

### 6.2 Classificação Etária IARC (International Age Rating Coalition)
O preenchimento do questionário da IARC para o Study Reviewer resulta na classificação indicativa mais favorável:

- **Categoria do App:** Aplicativo Utilitário / Educacional / Produtividade.
- **Conteúdo Violento / Obsceno / Sensível:** Não contém.
- **Compras Digitais no App:** Não contém (ou desativadas nesta versão).
- **Compartilhamento de Localização Física em Tempo Real:** Não.
- **Comunicação Não Moderada entre Usuários:** Não.
- **Resultado Classificatório:**
  - **Brasil (Classificação Indicativa):** **Livre** (para todos os públicos).
  - **EUA (ESRB):** **Everyone (E)**.
  - **Europa (PEGI):** **PEGI 3**.

---

### 6.3 Checklist Operacional Pré-Submissão

- [ ] **SDK Target:** `targetSdkVersion` atualizado para **34** ou superior.
- [ ] **Artefato AAB:** Formato `.aab` gerado com compilação `--release` assinado com a chave de upload oficial.
- [ ] **Tamanho do Pacote:** Tamanho de download inicial inferior a 25MB (garantido pelo R8 e compressão de assets).
- [ ] **URL de Privacidade:** `https://studyreviewer.com/privacy` acessível publicamente com certificados TLS válidos.
- [ ] **Kit Gráfico de Loja:**
  - Ícone de alta resolução: `512 x 512 px`, PNG 32 bits sem transparência.
  - Imagem de recurso / Banner de destaque: `1024 x 500 px`, PNG ou JPEG.
  - Capturas de tela (Screenshots): Mínimo de 4 imagens em `1080 x 1920 px` demonstrando Login, Flashcards 3D, Fila SRS e Gráfico de Desempenho.
- [ ] **Credenciais de Teste para Revisores da Google:** Usuário de teste (`google-reviewer@studyreviewer.com`) cadastrado no banco com senha ativa para a equipe de revisão do Google Play acessar todas as telas autenticadas.

---

## 7. Troubleshooting e Resolução de Problemas Frequentes

### 7.1 Erro `Keystore was tampered with, or password was incorrect`
- **Causa:** Senha incorreta ou formato corrompido durante a conversão base64 no CI.
- **Solução:** No runner Linux, certifique-se de que a variável não contenha quebras de linha (`echo -n "$KEYSTORE_BASE64" | base64 --decode`).

### 7.2 Erro de Minificação R8: `ClassNotFoundException` em Runtime
- **Causa:** Uma classe instanciada por reflexão foi removida pelo R8 por parecer não utilizada.
- **Solução:** Adicione a regra correspondente em `proguard-rules.pro` com a diretiva `-keep class nome.do.pacote.** { *; }`.

### 7.3 Falha `Upload a new Android App Bundle with targetSdkVersion 34 or higher`
- **Causa:** `targetSdkVersion` desatualizado em `android/app/build.gradle`.
- **Solução:** Defina explicitamente `targetSdkVersion 34` e recompile com `flutter build appbundle --release`.
