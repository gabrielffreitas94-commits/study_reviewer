import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/widgets/flip_card_3d.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/widgets/swipe_gesture_detector.dart';
import 'package:study_reviewer_mobile/features/sync/presentation/widgets/sync_status_badge.dart';

void main() {
  group('FlipCard3D Widget', () {
    testWidgets('renders front child initially and flips to back on tap',
        (tester) async {
      var flipped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: FlipCard3D(
              onFlip: () {
                flipped = true;
              },
              front: const Text('Frente do Card'),
              back: const Text('Verso do Card'),
            ),
          ),
        ),
      );

      expect(find.text('Frente do Card'), findsOneWidget);

      await tester.tap(find.byType(FlipCard3D));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(flipped, isTrue);
      expect(find.text('Verso do Card'), findsOneWidget);
    });

    testWidgets('respects prefers-reduced-motion (disableAnimations)',
        (tester) async {
      await tester.pumpWidget(
        const MediaQuery(
          data: MediaQueryData(disableAnimations: true),
          child: const MaterialApp(
            home: Scaffold(
              body: FlipCard3D(
                front: Text('Frente Reduzida'),
                back: Text('Verso Reduzido'),
              ),
            ),
          ),
        ),
      );

      expect(find.text('Frente Reduzida'), findsOneWidget);

      await tester.tap(find.byType(FlipCard3D));
      await tester.pump(); // Não deve exigir animação gradual

      expect(find.text('Verso Reduzido'), findsOneWidget);
    });
  });

  group('SwipeGestureDetector Widget', () {
    testWidgets('detects swipe left drag and invokes callback', (tester) async {
      var swiped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 200,
                child: SwipeGestureDetector(
                  onSwipeLeft: () {
                    swiped = true;
                  },
                  child: const Text('Arraste-me'),
                ),
              ),
            ),
          ),
        ),
      );

      expect(find.text('Arraste-me'), findsOneWidget);

      // Executa gesto de arrastar para a esquerda
      await tester.drag(find.byType(SwipeGestureDetector), const Offset(-120.0, 0.0));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(swiped, isTrue);
    });
  });

  group('SyncStatusBadge Widget', () {
    testWidgets('renders Synced state with correct label and green style',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SyncStatusBadge(status: SyncStatus.synced),
          ),
        ),
      );

      expect(find.text('Sincronizado'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle_outline), findsOneWidget);
    });

    testWidgets('renders PendingSync state with amber style and pending count',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SyncStatusBadge(
              status: SyncStatus.pendingSync,
              pendingCount: 4,
            ),
          ),
        ),
      );

      expect(find.text('4 pendente(s)'), findsOneWidget);
      expect(find.byIcon(Icons.sync), findsOneWidget);
    });

    testWidgets('renders Offline state with grey style and offline label',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SyncStatusBadge(status: SyncStatus.offline),
          ),
        ),
      );

      expect(find.text('Offline'), findsOneWidget);
      expect(find.byIcon(Icons.cloud_off_outlined), findsOneWidget);
    });
  });
}
