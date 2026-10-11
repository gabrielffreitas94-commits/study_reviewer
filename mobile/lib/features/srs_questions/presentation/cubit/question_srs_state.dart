import 'package:equatable/equatable.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/due_question_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/review_result_entity.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/entities/text_evaluation_result_entity.dart';

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
  final bool isEvaluatingText;
  final TextEvaluationResultEntity? textEvaluationResult;
  final String? textEvaluationError;
  final int activeAnswerMode; // 0 = Digitar, 1 = Gabarito Manual

  const QuestionSrsLoaded({
    required this.questions,
    this.currentIndex = 0,
    this.isAnswerRevealed = false,
    this.selectedScore = 100,
    this.lastReviewResult,
    this.isSubmitting = false,
    this.isSessionCompleted = false,
    this.isEvaluatingText = false,
    this.textEvaluationResult,
    this.textEvaluationError,
    this.activeAnswerMode = 0,
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
    bool? isEvaluatingText,
    TextEvaluationResultEntity? textEvaluationResult,
    bool clearTextEvaluationResult = false,
    String? textEvaluationError,
    bool clearTextEvaluationError = false,
    int? activeAnswerMode,
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
      isEvaluatingText: isEvaluatingText ?? this.isEvaluatingText,
      textEvaluationResult: clearTextEvaluationResult
          ? null
          : (textEvaluationResult ?? this.textEvaluationResult),
      textEvaluationError: clearTextEvaluationError
          ? null
          : (textEvaluationError ?? this.textEvaluationError),
      activeAnswerMode: activeAnswerMode ?? this.activeAnswerMode,
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
        isEvaluatingText,
        textEvaluationResult,
        textEvaluationError,
        activeAnswerMode,
      ];
}

class QuestionSrsError extends QuestionSrsState {
  final String message;

  const QuestionSrsError(this.message);

  @override
  List<Object?> get props => [message];
}
