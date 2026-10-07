import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/core/theme/app_theme.dart';
import 'package:study_reviewer_mobile/features/auth/presentation/cubit/auth_cubit.dart';
import 'package:study_reviewer_mobile/features/auth/presentation/cubit/auth_state.dart';

/// Tela moderna de Login com Google OAuth2 e acessibilidade completa.
class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      body: SafeArea(
        child: BlocConsumer<AuthCubit, AuthState>(
          listener: (context, state) {
            if (state is AuthError) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(
                    state.message,
                    style: const TextStyle(color: Colors.white),
                  ),
                  backgroundColor: AppTheme.rose600,
                  behavior: SnackBarBehavior.floating,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              );
            }
          },
          builder: (context, state) {
            final isLoading = state is AuthLoading;

            return Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Ícone de Identidade Visual
                      Center(
                        child: Container(
                          width: 80,
                          height: 80,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [AppTheme.indigo500, AppTheme.indigo700],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: [
                              BoxShadow(
                                color: AppTheme.indigo500.withOpacity(0.3),
                                blurRadius: 16,
                                offset: const Offset(0, 8),
                              ),
                            ],
                          ),
                          child: const Icon(
                            Icons.auto_stories_rounded,
                            size: 42,
                            color: Colors.white,
                          ),
                        ),
                      ),
                      const SizedBox(height: 28),

                      // Título e Subtítulo
                      Text(
                        'Study Reviewer',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: isDark ? AppTheme.slate50 : AppTheme.slate900,
                          letterSpacing: -0.5,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Sistema Inteligente de Repetição Espaçada.\nPotencialize sua retenção a longo prazo.',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: isDark ? AppTheme.slate400 : AppTheme.slate600,
                          height: 1.5,
                        ),
                      ),
                      const SizedBox(height: 48),

                      // Card com Botão de Ação Google
                      Container(
                        padding: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          color: isDark ? AppTheme.slate900 : Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: BorderSide(
                            color: isDark ? AppTheme.slate800 : AppTheme.slate200,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(isDark ? 0.2 : 0.04),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Text(
                              'Acesse sua conta',
                              textAlign: TextAlign.center,
                              style: theme.textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.w600,
                                color: isDark ? AppTheme.slate100 : AppTheme.slate800,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Conecte-se com sua conta Google institucional ou pessoal para sincronizar revisões.',
                              textAlign: TextAlign.center,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: isDark ? AppTheme.slate400 : AppTheme.slate500,
                              ),
                            ),
                            const SizedBox(height: 24),

                            // Botão Acessível Google Sign-In (Touch target mínimo 48dp)
                            Semantics(
                              label: 'Entrar com o Google',
                              button: true,
                              enabled: !isLoading,
                              child: SizedBox(
                                height: 50,
                                child: OutlinedButton(
                                  onPressed: isLoading
                                      ? null
                                      : () {
                                          context
                                              .read<AuthCubit>()
                                              .loginWithGoogle();
                                        },
                                  style: OutlinedButton.styleFrom(
                                    minimumSize: AppTheme.minTouchTargetSize,
                                    backgroundColor: isDark
                                        ? AppTheme.slate800
                                        : Colors.white,
                                    side: BorderSide(
                                      color: isDark
                                          ? AppTheme.slate700
                                          : AppTheme.slate300,
                                      width: 1.2,
                                    ),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 16,
                                      vertical: 12,
                                    ),
                                  ),
                                  child: isLoading
                                      ? const SizedBox(
                                          width: 22,
                                          height: 22,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2.2,
                                            valueColor:
                                                AlwaysStoppedAnimation<Color>(
                                              AppTheme.indigo500,
                                            ),
                                          ),
                                        )
                                      : Row(
                                          mainAxisAlignment:
                                              MainAxisAlignment.center,
                                          children: [
                                            const _GoogleGLogo(),
                                            const SizedBox(width: 14),
                                            Text(
                                              'Continuar com o Google',
                                              style: TextStyle(
                                                fontSize: 15,
                                                fontWeight: FontWeight.w600,
                                                color: isDark
                                                    ? AppTheme.slate100
                                                    : AppTheme.slate800,
                                              ),
                                            ),
                                          ],
                                        ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 36),

                      // Rodapé de Privacidade e Termos
                      Text(
                        'Ao continuar, você concorda com nossos Termos de Serviço e Política de Privacidade.',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: isDark ? AppTheme.slate500 : AppTheme.slate400,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

/// Logo vetorial autossuficiente do Google para conformidade visual e acessibilidade.
class _GoogleGLogo extends StatelessWidget {
  const _GoogleGLogo();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 22,
      height: 22,
      alignment: Alignment.center,
      decoration: const BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.white,
      ),
      child: const Text(
        'G',
        style: TextStyle(
          color: Color(0xFF4285F4),
          fontWeight: FontWeight.w900,
          fontSize: 16,
          fontFamily: 'Roboto',
        ),
      ),
    );
  }
}
