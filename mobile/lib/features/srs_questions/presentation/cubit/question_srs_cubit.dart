import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/get_due_questions_usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/review_question_usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_state.dart';

/// Cubit responsável pelo gerenciamento de estado da sessão de revisão SRS de perguntas abertas.
class QuestionSrsCubit extends Cubit<QuestionSrsState> {
  final GetDueQuestionsUseCase getDueQuestionsUseCase;
  final ReviewQuestionUseCase reviewQuestionUseCase;

  QuestionSrsCubit({
    required this.getDueQuestionsUseCase,
    required this.reviewQuestionUseCase,
  }) : super(const QuestionSrsInitial());

  /// Carrega a fila de perguntas abertas vencidas para revisão.
  Future<void> loadDueQuestions({
    String? subjectId,
    int limit = 50,
  }) async {
    emit(const QuestionSrsLoading());
    try {
      final questions = await getDueQuestionsUseCase(
        GetDueQuestionsParams(subjectId: subjectId, limit: limit),
      );

      if (questions.isEmpty) {
        emit(const QuestionSrsEmpty());
      } else {
        emit(QuestionSrsLoaded(
          questions: questions,
          currentIndex: 0,
          isAnswerRevealed: false,
          selectedScore: 100,
        ));
      }
    } on Failure catch (failure) {
      emit(QuestionSrsError(failure.message));
    } catch (e) {
      emit(QuestionSrsError('Erro ao carregar perguntas vencidas: $e'));
    }
  }

  /// Revela o gabarito / resposta esperada da pergunta corrente.
  void revealAnswer() {
    final currentState = state;
    if (currentState is QuestionSrsLoaded && !currentState.isAnswerRevealed) {
      emit(currentState.copyWith(isAnswerRevealed: true));
    }
  }

  /// Atualiza a nota de autoavaliação (0 a 100) selecionada pelo estudante.
  void updateScore(int score) {
    final currentState = state;
    if (currentState is QuestionSrsLoaded && !currentState.isSubmitting) {
      emit(currentState.copyWith(selectedScore: score.clamp(0, 100)));
    }
  }

  /// Submete a autoavaliação para processamento pelo algoritmo de repetição espaçada.
  Future<void> submitReview() async {
    final currentState = state;
    if (currentState is! QuestionSrsLoaded || currentState.isSubmitting) {
      return;
    }

    final currentQuestion = currentState.currentQuestion;
    if (currentQuestion == null) return;

    emit(currentState.copyWith(isSubmitting: true));

    try {
      final result = await reviewQuestionUseCase(
        ReviewQuestionParams(
          questionId: currentQuestion.id,
          score: currentState.selectedScore,
        ),
      );

      emit(currentState.copyWith(
        isSubmitting: false,
        lastReviewResult: result,
      ));
    } on Failure catch (failure) {
      emit(currentState.copyWith(isSubmitting: false));
      // Reemite erro mantendo o estado anterior se possível ou transiciona para error
      emit(QuestionSrsError(failure.message));
    } catch (e) {
      emit(currentState.copyWith(isSubmitting: false));
      emit(QuestionSrsError('Falha ao processar revisão: $e'));
    }
  }

  /// Avança para a próxima pergunta da fila ou finaliza a sessão se for a última.
  void nextQuestion() {
    final currentState = state;
    if (currentState is! QuestionSrsLoaded) return;

    final nextIndex = currentState.currentIndex + 1;
    if (nextIndex < currentState.questions.length) {
      emit(currentState.copyWith(
        currentIndex: nextIndex,
        isAnswerRevealed: false,
        selectedScore: 100,
        clearLastReviewResult: true,
      ));
    } else {
      emit(currentState.copyWith(isSessionCompleted: true));
    }
  }

  /// Reinicia o estado para inicial.
  void reset() {
    emit(const QuestionSrsInitial());
  }
}
