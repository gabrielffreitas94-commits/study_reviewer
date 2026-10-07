import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_cubit.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_state.dart';

/// Tela de Configurações, Aparência e Conformidade LGPD (Exclusão de Conta).
class SettingsPage extends StatelessWidget {
  final VoidCallback? onAccountDeleted;

  const SettingsPage({
    super.key,
    this.onAccountDeleted,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Configurações'),
        centerTitle: true,
      ),
      body: BlocConsumer<SettingsCubit, SettingsState>(
        listener: (context, state) {
          if (state.errorMessage != null && state.errorMessage!.isNotEmpty) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(state.errorMessage!),
                backgroundColor: Colors.redAccent,
              ),
            );
          }

          if (state.isAccountDeleted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text(
                  'Sua conta e dados pessoais foram excluídos definitivamente.',
                ),
                backgroundColor: Color(0xFF059669),
                duration: Duration(seconds: 4),
              ),
            );

            // Redireciona para a tela de autenticação / login
            if (onAccountDeleted != null) {
              onAccountDeleted!();
            } else {
              Navigator.of(context).pushNamedAndRemoveUntil(
                '/login',
                (route) => false,
              );
            }
          }
        },
        builder: (context, state) {
          return SingleChildScrollView(
            padding: const EdgeInsets.symmetric(
              horizontal: 16.0,
              vertical: 20.0,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 1. Seção de Aparência
                _buildAppearanceSection(context, state),
                const SizedBox(height: 24.0),

                // 2. Seção de Dados e Privacidade (LGPD & Google Play)
                _buildPrivacySection(context),
                const SizedBox(height: 24.0),

                // 3. Seção da Zona de Perigo (Exclusão de Conta)
                _buildDangerZoneSection(context, state),
                const SizedBox(height: 32.0),
              ],
            ),
          );
        },
      ),
    );
  }

  /// 1. Seção de Aparência (Dark / Light / Sistema)
  Widget _buildAppearanceSection(BuildContext context, SettingsState state) {
    final theme = Theme.of(context);

    return Card(
      elevation: 1.5,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16.0),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.palette_outlined,
                  color: theme.colorScheme.primary,
                  size: 24.0,
                ),
                const SizedBox(width: 8.0),
                Text(
                  'Aparência',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12.0),
            Text(
              'Escolha a forma como o Study Reviewer se apresenta:',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 12.0),
            SegmentedButton<ThemeMode>(
              segments: const <ButtonSegment<ThemeMode>>[
                ButtonSegment<ThemeMode>(
                  value: ThemeMode.light,
                  icon: Icon(Icons.light_mode_outlined),
                  label: Text('Claro'),
                ),
                ButtonSegment<ThemeMode>(
                  value: ThemeMode.dark,
                  icon: Icon(Icons.dark_mode_outlined),
                  label: Text('Escuro'),
                ),
                ButtonSegment<ThemeMode>(
                  value: ThemeMode.system,
                  icon: Icon(Icons.settings_brightness_outlined),
                  label: Text('Sistema'),
                ),
              ],
              selected: <ThemeMode>{state.themeMode},
              onSelectionChanged: (Set<ThemeMode> newSelection) {
                if (newSelection.isNotEmpty) {
                  context.read<SettingsCubit>().setThemeMode(newSelection.first);
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  /// 2. Seção de Dados e Privacidade (LGPD Art. 18 e Google Play Data Safety)
  Widget _buildPrivacySection(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      elevation: 1.5,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16.0),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.privacy_tip_outlined,
                  color: Color(0xFF0284C7),
                  size: 24.0,
                ),
                const SizedBox(width: 8.0),
                Text(
                  'Dados e Privacidade',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12.0),
            Text(
              'Seus dados acadêmicos e registros de estudo são processados sob princípios estritos de segurança e privacidade (LGPD).',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 16.0),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.description_outlined, color: Color(0xFF0284C7)),
              title: const Text(
                'Política de Privacidade Completa',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              subtitle: const Text(
                'Consulte as finalidades, direitos do titular e prazos de retenção',
                style: TextStyle(fontSize: 12.0),
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => _showPrivacyPolicyModal(context),
            ),
          ],
        ),
      ),
    );
  }

  /// 3. Seção da Zona de Perigo: Exclusão de Conta com Confirmação em Duas Etapas
  Widget _buildDangerZoneSection(BuildContext context, SettingsState state) {
    final theme = Theme.of(context);

    return Card(
      elevation: 2.0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16.0),
        side: const BorderSide(color: Color(0xFFDC2626), width: 1.2),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(
                  Icons.warning_amber_rounded,
                  color: Color(0xFFDC2626),
                  size: 24.0,
                ),
                SizedBox(width: 8.0),
                Text(
                  'Zona de Perigo (LGPD Art. 18)',
                  style: TextStyle(
                    color: Color(0xFFDC2626),
                    fontWeight: FontWeight.bold,
                    fontSize: 16.0,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12.0),
            Text(
              'A exclusão da conta é definitiva e irreversível. Todos os seus cartões, perguntas abertas, histórico SRS e dados pessoais serão purgados imediatamente.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: Colors.grey.shade700,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 16.0),

            // Botão "Excluir Minha Conta" com Touch Target >= 48x48dp
            ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48.0),
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFDC2626),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12.0),
                    ),
                    elevation: 1.0,
                  ),
                  onPressed: state.isDeletingAccount
                      ? null
                      : () => _confirmAccountDeletionStep1(context),
                  icon: state.isDeletingAccount
                      ? const SizedBox(
                          width: 20.0,
                          height: 20.0,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            valueColor:
                                AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : const Icon(Icons.delete_forever_outlined),
                  label: Text(
                    state.isDeletingAccount
                        ? 'Excluindo conta...'
                        : 'Excluir Minha Conta',
                    style: const TextStyle(
                      fontSize: 15.0,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Etapa 1 da Confirmação em Duas Etapas
  void _confirmAccountDeletionStep1(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (dialogCtx) {
        return AlertDialog(
          title: const Row(
            children: [
              Icon(Icons.report_problem_outlined, color: Color(0xFFDC2626)),
              SizedBox(width: 8.0),
              Flexible(child: Text('Excluir Conta?')),
            ],
          ),
          content: const Text(
            'Você está prestes a iniciar a exclusão da sua conta no Study Reviewer.\n\n'
            'Esta ação acarretará a eliminação permanente de:\n'
            '• Todo o histórico de revisões e repetição espaçada (SRS);\n'
            '• Todos os cartões e perguntas cadastradas;\n'
            '• Dados de perfil e sessão associados ao seu e-mail.\n\n'
            'Deseja prosseguir para a etapa final de confirmação?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(),
              child: const Text('Cancelar'),
            ),
            ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48.0),
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFDC2626),
                  foregroundColor: Colors.white,
                ),
                onPressed: () {
                  Navigator.of(dialogCtx).pop();
                  _confirmAccountDeletionStep2(context);
                },
                child: const Text('Continuar para Exclusão'),
              ),
            ),
          ],
        );
      },
    );
  }

  /// Etapa 2 da Confirmação em Duas Etapas (Definitiva)
  void _confirmAccountDeletionStep2(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (dialogCtx) {
        return AlertDialog(
          title: const Text(
            'Atenção: Confirmação Final',
            style: TextStyle(
              color: Color(0xFFDC2626),
              fontWeight: FontWeight.bold,
            ),
          ),
          content: const Text(
            'Esta operação NÃO poderá ser desfeita sob hipótese alguma.\n\n'
            'Tem certeza absoluta de que deseja excluir permanentemente sua conta agora?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogCtx).pop(),
              child: const Text('Voltar'),
            ),
            ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48.0),
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF991B1B), // Vermelho escuro
                  foregroundColor: Colors.white,
                ),
                onPressed: () {
                  Navigator.of(dialogCtx).pop();
                  context.read<SettingsCubit>().deleteAccount();
                },
                child: const Text(
                  'Sim, Excluir Minha Conta',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  /// Exibe modal com a política de privacidade e conformidade com a LGPD
  void _showPrivacyPolicyModal(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20.0)),
      ),
      builder: (modalCtx) {
        return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.75,
          maxChildSize: 0.95,
          minChildSize: 0.5,
          builder: (_, scrollController) {
            return Padding(
              padding: const EdgeInsets.all(20.0),
              child: ListView(
                controller: scrollController,
                children: [
                  Center(
                    child: Container(
                      width: 40.0,
                      height: 4.0,
                      decoration: BoxDecoration(
                        color: Colors.grey.shade300,
                        borderRadius: BorderRadius.circular(2.0),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16.0),
                  Text(
                    'Política de Privacidade e Proteção de Dados',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 12.0),
                  const Text(
                    'Conformidade com a LGPD (Lei nº 13.709/2018) e Google Play Data Safety.',
                    style: TextStyle(fontStyle: FontStyle.italic),
                  ),
                  const Divider(height: 24.0),
                  const Text(
                    '1. Dados Pessoais Coletados',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16.0),
                  ),
                  const SizedBox(height: 6.0),
                  const Text(
                    'Coletamos apenas o seu endereço de e-mail e identificador fornecido pelo Google OAuth2 '
                    'para autenticação e salvaguarda do seu progresso de estudos.',
                  ),
                  const SizedBox(height: 16.0),
                  const Text(
                    '2. Finalidade do Tratamento',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16.0),
                  ),
                  const SizedBox(height: 6.0),
                  const Text(
                    'Os dados são utilizados exclusivamente para calcular os intervalos de repetição espaçada (SRS), '
                    'gerar as métricas do Hub de Desempenho e sincronizar seus flashcards.',
                  ),
                  const SizedBox(height: 16.0),
                  const Text(
                    '3. Direitos do Titular (Art. 18 LGPD)',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16.0),
                  ),
                  const SizedBox(height: 6.0),
                  const Text(
                    'Você possui o direito de confirmar a existência de tratamento, acessar seus dados, '
                    'corrigir dados incompletos ou requerer a eliminação total e definitiva dos dados pessoais tratados, '
                    'o que pode ser feito diretamente na seção "Zona de Perigo" desta tela.',
                  ),
                  const SizedBox(height: 16.0),
                  const Text(
                    '4. Armazenamento e Segurança',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16.0),
                  ),
                  const SizedBox(height: 6.0),
                  const Text(
                    'Os tokens são armazenados com criptografia de ponta no Android Keystore ou iOS Keychain. '
                    'Nenhuma credencial é compartilhada com terceiros para fins de marketing ou publicidade.',
                  ),
                  const SizedBox(height: 24.0),
                  ElevatedButton(
                    onPressed: () => Navigator.of(modalCtx).pop(),
                    child: const Text('Fechar'),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}
