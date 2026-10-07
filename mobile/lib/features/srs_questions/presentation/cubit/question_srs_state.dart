import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';

abstract class QuestionSrsState extends Equatable {
  const QuestionSrsState();

  @override
  List<Object?> get props => [];
}

class QuestionSrsInitial extends QuestionSrsState {
  const QuestionSrsInitial();
}

class QuestionSrsLoading extends QuestionSrsState {
  const QuestionSrsLoading();
}

class QuestionSrsEmpty extends QuestionSrsState {
  final String message;

  const QuestionSrsEmpty({
    this.message = 'Parabéns! Todas as perguntas do dia já foram revisadas.',
  });

  @override
  List<Object?> get props => [message];
}

class QuestionSrsLoaded extends QuestionSrsState {
  final List<DueQuestionEntity> questions;
  final int currentIndex;
  final bool isAnswerRevealed;
  final int selectedScore;
  final ReviewResultEntity? lastReviewResult;
  final bool isSubmitting;
  final bool isSessionCompleted;

  const QuestionSrsLoaded({
    required this.questions,
    this.currentIndex = 0,
    this.isAnswerRevealed = false,
    this.selectedScore = 100,
    this.lastReviewResult,
    this.isSubmitting = false,
    this.isSessionCompleted = false,
  });

  DueQuestionEntity? get currentQuestion {
    if (currentIndex >= 0 && currentIndex < questions.length) {
      return questions[currentIndex];
    }
    return null;
  }

  int get totalQuestions => questions.length;

  QuestionSrsLoaded copyWith({
    List<DueQuestionEntity>? questions,
    int? currentIndex,
    bool? isAnswerRevealed,
    int? selectedScore,
    ReviewResultEntity? lastReviewResult,
    bool clearLastReviewResult = false,
    bool? isSubmitting,
    bool? isSessionCompleted,
  }) {
    return QuestionSrsLoaded(
      questions: questions ?? this.questions,
      currentIndex: currentIndex ?? this.currentIndex,
      isAnswerRevealed: isAnswerRevealed ?? this.isAnswerRevealed,
      selectedScore: selectedScore ?? this.selectedScore,
      lastReviewResult: clearLastReviewResult
          ? null
          : (lastReviewResult ?? this.lastReviewResult),
      isSubmitting: isSubmitting ?? this.isSubmitting,
      isSessionCompleted: isSessionCompleted ?? this.isSessionCompleted,
    );
  }

  @override
  List<Object?> get props => [
        questions,
        currentIndex,
        isAnswerRevealed,
        selectedScore,
        lastReviewResult,
        isSubmitting,
        isSessionCompleted,
      ];
}

class QuestionSrsError extends QuestionSrsState {
  final String message;

  const QuestionSrsError(this.message);

  @override
  List<Object?> get props => [message];
}
