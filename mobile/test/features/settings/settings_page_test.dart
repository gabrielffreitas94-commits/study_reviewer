import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_cubit.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_state.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/pages/settings_page.dart';

class MockSettingsCubit extends Mock implements SettingsCubit {}

void main() {
  late MockSettingsCubit mockSettingsCubit;

  setUp(() {
    mockSettingsCubit = MockSettingsCubit();
  });

  Widget buildTestableWidget(Widget child) {
    return MaterialApp(
      home: BlocProvider<SettingsCubit>.value(
        value: mockSettingsCubit,
        child: child,
      ),
    );
  }

  testWidgets('renderiza seções de Aparência, Privacidade e Zona de Perigo',
      (tester) async {
    when(() => mockSettingsCubit.state).thenReturn(const SettingsState());
    when(() => mockSettingsCubit.stream)
        .thenAnswer((_) => const Stream<SettingsState>.empty());

    await tester.pumpWidget(buildTestableWidget(const SettingsPage()));

    expect(find.text('Aparência'), findsOneWidget);
    expect(find.text('Dados e Privacidade'), findsOneWidget);
    expect(find.text('Zona de Perigo (LGPD Art. 18)'), findsOneWidget);
    expect(find.text('Excluir Minha Conta'), findsOneWidget);
  });

  testWidgets('clicar em Excluir Minha Conta abre diálogo de confirmação em duas etapas',
      (tester) async {
    when(() => mockSettingsCubit.state).thenReturn(const SettingsState());
    when(() => mockSettingsCubit.stream)
        .thenAnswer((_) => const Stream<SettingsState>.empty());
    when(() => mockSettingsCubit.deleteAccount()).thenAnswer((_) async {});

    await tester.pumpWidget(buildTestableWidget(const SettingsPage()));

    // 1. Clica no botão Excluir Minha Conta
    final deleteButton = find.text('Excluir Minha Conta');
    await tester.ensureVisible(deleteButton);
    await tester.tap(deleteButton);
    await tester.pumpAndSettle();

    // Diálogo Etapa 1 exibido
    expect(find.text('Excluir Conta?'), findsOneWidget);
    expect(find.text('Continuar para Exclusão'), findsOneWidget);

    // 2. Clica em Continuar para Exclusão (avança para Etapa 2)
    await tester.tap(find.text('Continuar para Exclusão'));
    await tester.pumpAndSettle();

    // Diálogo Etapa 2 (Confirmação Final)
    expect(find.text('Atenção: Confirmação Final'), findsOneWidget);
    expect(find.text('Sim, Excluir Minha Conta'), findsOneWidget);

    // 3. Clica na confirmação definitiva
    await tester.tap(find.text('Sim, Excluir Minha Conta'));
    await tester.pumpAndSettle();

    verify(() => mockSettingsCubit.deleteAccount()).called(1);
  });
}
