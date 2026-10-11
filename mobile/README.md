# Study Reviewer Mobile

Aplicativo móvel em **Flutter** para o sistema **Study Reviewer**, especializado em repetição espaçada inteligente (SRS) e revisão ativa.

---

## 🏛 Arquitetura e Engenharia de Software

O projeto adota os princípios de **Clean Architecture** (Uncle Bob) e **Design System** alinhado ao Tailwind CSS:

```
mobile/
├── android/                   # Configurações nativas Android (API 34, ProGuard/R8, Keystore)
│   ├── app/
│   │   ├── build.gradle       # compileSdkVersion 34, targetSdkVersion 34, minSdkVersion 24
│   │   ├── proguard-rules.pro # Regras de R8/ProGuard para runtime Flutter e plugins
│   │   └── src/main/
│   │       ├── AndroidManifest.xml # Permissões de rede, launch/normal theme
│   │       └── kotlin/com/studyreviewer/app/MainActivity.kt
├── lib/
│   ├── core/                  # Módulos transversais e contratos fundamentais
│   │   ├── constants/         # URLs de emulador/host e endpoints de API REST
│   │   ├── errors/            # Falhas padronizadas (ServerFailure, AuthFailure, etc.)
│   │   ├── network/           # Cliente Dio com timeouts de 15s, AuthInterceptor defensivo
│   │   ├── storage/           # Wrapper do FlutterSecureStorage (Android Keystore / Keychain)
│   │   ├── theme/             # Paleta Tailwind (Indigo/Slate), Dark/Light mode e touch targets (48dp)
│   │   └── usecases/          # Contrato abstrato UseCase<Type, Params>
│   ├── features/
│   │   ├── auth/              # Feature de Autenticação OIDC Google
│   │   │   ├── data/          # Models (UserModel), RemoteDataSource, AuthRepositoryImpl
│   │   │   ├── domain/        # Entidades (UserEntity), Repositórios e UseCases
│   │   │   └── presentation/  # Cubit, States e LoginPage acessível
│   │   └── home/
│   │       └── presentation/  # HomeShellPage com BottomNavigationBar de 4 abas
│   ├── injection_container.dart # Service Locator com GetIt
│   └── main.dart              # Inicialização reativa e AuthGate
└── test/                      # Testes unitários e de integração de Cubits, Repositories e Storage
```

---

## 🔐 Segurança e Gerenciamento de Chaves

- **Android Keystore**: Implementado via `FlutterSecureStorage` com `AndroidOptions(encryptedSharedPreferences: true)`. O MasterKey do Keystore do hardware protege as credenciais de sessão localmente.
- **Defensive Logging**: O interceptor HTTP Dio registra rotas e códigos de status de forma anonimizada, bloqueando o vazamento de cabeçalhos de autenticação (`Authorization: Bearer`), senhas, tokens ou dados pessoais (PII).
- **ProGuard / R8**: Habilitado em builds de release com regras estritas para retenção dos plugins de segurança e Google Sign-In.

---

## 🚀 Como Executar

### Pré-requisitos
- Flutter SDK `>=3.0.0 <4.0.0`
- Android Studio / Android SDK 34
- Backend FastAPI em execução (`http://localhost:8000`)

### Execução no Emulador Android
```bash
flutter pub get
flutter run
```
*No emulador Android, a rota de rede `http://10.0.2.2:8000/api/v1` é mapeada automaticamente pelo `ApiConstants.defaultBaseUrl`.*

### Execução de Testes
```bash
flutter test
```
