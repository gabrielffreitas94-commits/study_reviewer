import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/text_evaluation_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/evaluation_feedback_card.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/question_answer_mode_tabs.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/question_text_input_area.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/score_thumb_selector.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/srs_level_badge.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/subscore_progress_bar.dart';

void main() {
  group('ScoreThumbSelector Widget', () {
    testWidgets('renderiza presets 0%, 25%, 50%, 75%, 100% com touch targets >= 48dp',
        (tester) async {
      int? changedScore;
      var submitted = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ScoreThumbSelector(
              currentScore: 100,
              onScoreChanged: (val) => changedScore = val,
              onSubmit: () => submitted = true,
            ),
          ),
        ),
      );

      expect(find.text('0%'), findsOneWidget);
      expect(find.text('25%'), findsOneWidget);
      expect(find.text('50%'), findsOneWidget);
      expect(find.text('75%'), findsOneWidget);
      expect(find.text('100%'), findsOneWidget);

      // Verifica tamanho mínimo dos touch targets (48x48)
      final presetButtons = find.byType(OutlinedButton);
      expect(presetButtons, findsNWidgets(5));
      for (final btn in presetButtons.evaluate()) {
        final size = tester.getSize(find.byWidget(btn.widget));
        expect(size.height, greaterThanOrEqualTo(48.0));
        expect(size.width, greaterThanOrEqualTo(48.0));
      }

      // Toca no preset 50%
      await tester.tap(find.text('50%'));
      await tester.pump();
      expect(changedScore, 50);

      // Clica em confirmar e avançar
      await tester.tap(find.text('Confirmar e Avançar'));
      await tester.pump();
      expect(submitted, isTrue);
    });
  });

  group('SrsLevelBadge Widget', () {
    testWidgets('renderiza badge de promoção com ícone superior e texto redundante',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SrsLevelBadge(
              type: SrsBadgeType.promotion,
              levelAfter: 3,
            ),
          ),
        ),
      );

      expect(find.text('↑ Nível Superior (Nível 3)'), findsOneWidget);
      expect(find.byIcon(Icons.arrow_upward), findsOneWidget);
    });

    testWidgets('renderiza badge de manutenção com ícone e texto neutro',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SrsLevelBadge(
              type: SrsBadgeType.maintenance,
              levelAfter: 2,
            ),
          ),
        ),
      );

      expect(find.text('= Mantido (Nível 2)'), findsOneWidget);
      expect(find.byIcon(Icons.drag_handle), findsOneWidget);
    });

    testWidgets('renderiza badge de regressão com ícone para baixo e texto explicativo',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SrsLevelBadge(
              type: SrsBadgeType.regression,
              levelAfter: 1,
            ),
          ),
        ),
      );

      expect(find.text('↓ Rebaixado (Nível 1)'), findsOneWidget);
      expect(find.byIcon(Icons.arrow_downward), findsOneWidget);
    });

    testWidgets('construtor fromResult mapeia corretamente os tipos',
        (tester) async {
      final promoBadge = SrsLevelBadge.fromResult(
        isPromoted: true,
        isDemoted: false,
        isMaintained: false,
        levelAfter: 4,
      );
      expect(promoBadge.type, SrsBadgeType.promotion);

      final demoBadge = SrsLevelBadge.fromResult(
        isPromoted: false,
        isDemoted: true,
        isMaintained: false,
        levelAfter: 1,
      );
      expect(demoBadge.type, SrsBadgeType.regression);

      final maintBadge = SrsLevelBadge.fromResult(
        isPromoted: false,
        isDemoted: false,
        isMaintained: true,
        levelAfter: 2,
      );
      expect(maintBadge.type, SrsBadgeType.maintenance);
    });
  });

  group('SubscoreProgressBar Widget', () {
    testWidgets('renderiza rótulo, valor percentual e barra animada',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SubscoreProgressBar(
              label: 'Cobertura Conceitual',
              score: 95,
              icon: Icons.checklist_rtl,
            ),
          ),
        ),
      );

      expect(find.text('Cobertura Conceitual'), findsOneWidget);
      expect(find.text('95%'), findsOneWidget);
      expect(find.byIcon(Icons.checklist_rtl), findsOneWidget);
      expect(find.byType(LinearProgressIndicator), findsOneWidget);
    });
  });

  group('EvaluationFeedbackCard Widget', () {
    final tEvaluation = TextEvaluationResultEntity(
      questionId: 'q-10',
      score: 85,
      feedback: 'Excelente menção à eficácia horizontal e vertical dos direitos.',
      coverageScore: 90,
      accuracyScore: 85,
      depthScore: 80,
      tokensConsumed: 482,
      remainingBalance: 1518,
      ragGroundingApplied: true,
    );

    testWidgets('renderiza nota de domínio, métricas analíticas e feedback pedagógico',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: EvaluationFeedbackCard(evaluation: tEvaluation),
            ),
          ),
        ),
      );

      expect(find.text('85% de Domínio'), findsOneWidget);
      expect(find.text('Cobertura Conceitual'), findsOneWidget);
      expect(find.text('Precisão Técnica'), findsOneWidget);
      expect(find.text('Profundidade da Resposta'), findsOneWidget);
      expect(
        find.text('Excelente menção à eficácia horizontal e vertical dos direitos.'),
        findsOneWidget,
      );
      expect(
        find.text('482 tokens consumidos • Saldo: 1518'),
        findsOneWidget,
      );
      expect(find.text('RAG Ativo'), findsOneWidget);
    });
  });

  group('QuestionAnswerModeTabs Widget', () {
    testWidgets('renderiza as duas abas e dispara callback ao alternar',
        (tester) async {
      int selectedMode = 0;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: QuestionAnswerModeTabs(
              activeMode: selectedMode,
              onModeChanged: (mode) => selectedMode = mode,
            ),
          ),
        ),
      );

      expect(find.text('✍️ Digitar Resposta'), findsOneWidget);
      expect(find.text('💡 Apenas Gabarito'), findsOneWidget);

      await tester.tap(find.text('💡 Apenas Gabarito'));
      await tester.pump();

      expect(selectedMode, 1);
    });
  });

  group('QuestionTextInputArea Widget', () {
    testWidgets('renderiza TextField, contador e botão de submissão',
        (tester) async {
      final controller = TextEditingController(text: 'Minha resposta');
      var submitted = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: QuestionTextInputArea(
                controller: controller,
                isEvaluating: false,
                onSubmit: () => submitted = true,
              ),
            ),
          ),
        ),
      );

      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('14 caracteres'), findsOneWidget);
      expect(find.text('✨ Avaliar com IA'), findsOneWidget);

      await tester.tap(find.text('✨ Avaliar com IA'));
      await tester.pump();

      expect(submitted, isTrue);
    });

    testWidgets('exibe banner de saldo insuficiente com fallback para modo manual',
        (tester) async {
      final controller = TextEditingController(text: 'Resposta curta');
      var manualRevealed = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: QuestionTextInputArea(
                controller: controller,
                isEvaluating: false,
                errorMessage: 'Saldo de tokens insuficiente para avaliação por IA',
                onSubmit: () {},
                onRevealManual: () => manualRevealed = true,
              ),
            ),
          ),
        ),
      );

      expect(
        find.text('Saldo de tokens insuficiente para avaliação por IA'),
        findsOneWidget,
      );
      expect(find.text('Continuar no Modo Manual'), findsOneWidget);

      await tester.tap(find.text('Continuar no Modo Manual'));
      await tester.pump();

      expect(manualRevealed, isTrue);
    });
  });
}
