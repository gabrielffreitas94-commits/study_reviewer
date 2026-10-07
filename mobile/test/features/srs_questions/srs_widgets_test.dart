import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/score_thumb_selector.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/widgets/srs_level_badge.dart';

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
}
