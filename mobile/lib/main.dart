import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/core/theme/app_theme.dart';
import 'package:study_reviewer_mobile/features/auth/presentation/cubit/auth_cubit.dart';
import 'package:study_reviewer_mobile/features/auth/presentation/cubit/auth_state.dart';
import 'package:study_reviewer_mobile/features/auth/presentation/pages/login_page.dart';
import 'package:study_reviewer_mobile/features/home/presentation/pages/home_shell_page.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_cubit.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_state.dart';
import 'package:study_reviewer_mobile/injection_container.dart' as di;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Inicializa o Service Locator GetIt
  await di.initInjection();

  runApp(const StudyReviewerApp());
}

/// Aplicação raiz com suporte a tema reativo (Light / Dark) e roteamento de autenticação.
class StudyReviewerApp extends StatelessWidget {
  const StudyReviewerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [
        BlocProvider<AuthCubit>(
          create: (_) => di.sl<AuthCubit>()..checkAuthStatus(),
        ),
        BlocProvider<SettingsCubit>(
          create: (_) => di.sl<SettingsCubit>(),
        ),
      ],
      child: BlocBuilder<SettingsCubit, SettingsState>(
        builder: (context, settingsState) {
          return MaterialApp(
            title: 'Study Reviewer',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.lightTheme,
            darkTheme: AppTheme.darkTheme,
            themeMode: settingsState.themeMode,
            routes: {
              '/login': (_) => const LoginPage(),
            },
            home: const AuthGate(),
          );
        },
      ),
    );
  }
}


/// Portão de autenticação que direciona o usuário conforme o estado emitido pelo AuthCubit.
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<AuthCubit, AuthState>(
      builder: (context, state) {
        if (state is Authenticated) {
          return HomeShellPage(user: state.user);
        } else if (state is Unauthenticated || state is AuthError) {
          return const LoginPage();
        }

        // Estado inicial de carregamento / splash screen
        return const _SplashScreen();
      },
    );
  }
}

/// Tela de splash exibida durante a verificação de sessão criptografada no Keystore.
class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? AppTheme.slate950 : AppTheme.slate50,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [AppTheme.indigo500, AppTheme.indigo700],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(18),
              ),
              child: const Icon(
                Icons.auto_stories_rounded,
                size: 38,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Study Reviewer',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: isDark ? AppTheme.slate100 : AppTheme.slate900,
              ),
            ),
            const SizedBox(height: 24),
            const SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                valueColor: AlwaysStoppedAnimation<Color>(AppTheme.indigo500),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
