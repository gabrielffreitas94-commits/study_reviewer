import 'package:equatable/equatable.dart';

/// Entidade de domínio representando o resultado de uma revisão de Pergunta Aberta pelo motor SRS.
class ReviewResultEntity extends Equatable {
  final String questionId;
  final int score;
  final int levelBefore;
  final int levelAfter;
  final DateTime nextReviewDate;
  final bool isPromoted;
  final bool isDemoted;
  final bool isMaintained;
  final int intervalDays;

  const ReviewResultEntity({
    required this.questionId,
    required this.score,
    required this.levelBefore,
    required this.levelAfter,
    required this.nextReviewDate,
    required this.isPromoted,
    required this.isDemoted,
    required this.isMaintained,
    this.intervalDays = 1,
  });

  @override
  List<Object?> get props => [
        questionId,
        score,
        levelBefore,
        levelAfter,
        nextReviewDate,
        isPromoted,
        isDemoted,
        isMaintained,
        intervalDays,
      ];
}
