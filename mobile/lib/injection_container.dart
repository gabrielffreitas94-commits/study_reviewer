import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:get_it/get_it.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:study_reviewer_mobile/core/network/api_client.dart';
import 'package:study_reviewer_mobile/core/storage/secure_storage_service.dart';
import 'package:study_reviewer_mobile/features/auth/data/datasources/auth_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/auth/data/repositories/auth_repository_impl.dart';
import 'package:study_reviewer_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:study_reviewer_mobile/features/auth/domain/usecases/get_current_user_usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/usecases/login_with_google_usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/usecases/logout_usecase.dart';
import 'package:study_reviewer_mobile/features/auth/presentation/cubit/auth_cubit.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/datasources/flashcard_local_data_source.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/datasources/flashcard_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/flashcards/data/repositories/flashcard_repository_impl.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/repositories/flashcard_repository.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/get_next_card_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/get_study_batch_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/list_topic_flashcards_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/domain/usecases/mark_card_read_usecase.dart';
import 'package:study_reviewer_mobile/features/flashcards/presentation/cubit/flashcard_cubit.dart';
import 'package:study_reviewer_mobile/features/sync/data/datasources/sync_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/datasources/question_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/srs_questions/data/repositories/question_repository_impl.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/repositories/question_repository.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/get_due_questions_usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/domain/usecases/review_question_usecase.dart';
import 'package:study_reviewer_mobile/features/srs_questions/presentation/cubit/question_srs_cubit.dart';
import 'package:study_reviewer_mobile/features/performance/data/datasources/performance_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/performance/data/repositories/performance_repository_impl.dart';
import 'package:study_reviewer_mobile/features/performance/domain/repositories/performance_repository.dart';
import 'package:study_reviewer_mobile/features/performance/domain/usecases/get_user_statistics_usecase.dart';
import 'package:study_reviewer_mobile/features/performance/presentation/cubit/performance_cubit.dart';
import 'package:study_reviewer_mobile/features/settings/data/datasources/settings_remote_data_source.dart';
import 'package:study_reviewer_mobile/features/settings/data/repositories/settings_repository_impl.dart';
import 'package:study_reviewer_mobile/features/settings/domain/repositories/settings_repository.dart';
import 'package:study_reviewer_mobile/features/settings/domain/usecases/delete_account_usecase.dart';
import 'package:study_reviewer_mobile/features/settings/presentation/cubit/settings_cubit.dart';

final sl = GetIt.instance;


/// Inicializa e registra as dependências do Service Locator (GetIt) para Core e Features.
Future<void> initInjection() async {
  // ----------------------------------------------------
  // Core & External
  // ----------------------------------------------------
  sl.registerLazySingleton<SecureStorageService>(
    () => SecureStorageService(
      storage: const FlutterSecureStorage(
        aOptions: AndroidOptions(encryptedSharedPreferences: true),
        iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
      ),
    ),
  );

  sl.registerLazySingleton<GoogleSignIn>(
    () => GoogleSignIn(
      scopes: ['email', 'profile'],
    ),
  );

  sl.registerLazySingleton<Dio>(
    () => ApiClient.createDioClient(
      secureStorageService: sl<SecureStorageService>(),
      onUnauthorized: () {
        if (sl.isRegistered<AuthCubit>()) {
          sl<AuthCubit>().forceUnauthenticated();
        }
      },
    ),
  );

  // ----------------------------------------------------
  // Feature: Auth
  // ----------------------------------------------------
  // Data Sources
  sl.registerLazySingleton<AuthRemoteDataSource>(
    () => AuthRemoteDataSourceImpl(dio: sl<Dio>()),
  );

  // Repositories
  sl.registerLazySingleton<AuthRepository>(
    () => AuthRepositoryImpl(
      remoteDataSource: sl<AuthRemoteDataSource>(),
      secureStorageService: sl<SecureStorageService>(),
      googleSignIn: sl<GoogleSignIn>(),
    ),
  );

  // Use Cases
  sl.registerLazySingleton(
    () => LoginWithGoogleUseCase(sl<AuthRepository>()),
  );
  sl.registerLazySingleton(
    () => GetCurrentUserUseCase(sl<AuthRepository>()),
  );
  sl.registerLazySingleton(
    () => LogoutUseCase(sl<AuthRepository>()),
  );

  // Cubits (Factory ou LazySingleton)
  sl.registerFactory(
    () => AuthCubit(
      loginWithGoogleUseCase: sl<LoginWithGoogleUseCase>(),
      getCurrentUserUseCase: sl<GetCurrentUserUseCase>(),
      logoutUseCase: sl<LogoutUseCase>(),
    ),
  );

  // ----------------------------------------------------
  // Feature: Flashcards & Offline Sync
  // ----------------------------------------------------
  // Data Sources
  sl.registerLazySingleton<FlashcardRemoteDataSource>(
    () => FlashcardRemoteDataSourceImpl(client: sl<Dio>()),
  );
  sl.registerLazySingleton<FlashcardLocalDataSource>(
    () => FlashcardLocalDataSourceImpl(),
  );
  sl.registerLazySingleton<SyncRemoteDataSource>(
    () => SyncRemoteDataSourceImpl(client: sl<Dio>()),
  );

  // Repositories
  sl.registerLazySingleton<FlashcardRepository>(
    () => FlashcardRepositoryImpl(
      remoteDataSource: sl<FlashcardRemoteDataSource>(),
      localDataSource: sl<FlashcardLocalDataSource>(),
    ),
  );

  // Use Cases
  sl.registerLazySingleton(
    () => GetStudyBatchUseCase(sl<FlashcardRepository>()),
  );
  sl.registerLazySingleton(
    () => GetNextCardUseCase(sl<FlashcardRepository>()),
  );
  sl.registerLazySingleton(
    () => MarkCardReadUseCase(sl<FlashcardRepository>()),
  );
  sl.registerLazySingleton(
    () => ListTopicFlashcardsUseCase(sl<FlashcardRepository>()),
  );

  // Cubit
  sl.registerFactory(
    () => FlashcardCubit(
      getStudyBatchUseCase: sl<GetStudyBatchUseCase>(),
      getNextCardUseCase: sl<GetNextCardUseCase>(),
      markCardReadUseCase: sl<MarkCardReadUseCase>(),
    ),
  );

  // ----------------------------------------------------
  // Feature: SRS Questions
  // ----------------------------------------------------
  // Data Sources
  sl.registerLazySingleton<QuestionRemoteDataSource>(
    () => QuestionRemoteDataSourceImpl(client: sl<Dio>()),
  );

  // Repositories
  sl.registerLazySingleton<QuestionRepository>(
    () => QuestionRepositoryImpl(
      remoteDataSource: sl<QuestionRemoteDataSource>(),
    ),
  );

  // Use Cases
  sl.registerLazySingleton(
    () => GetDueQuestionsUseCase(repository: sl<QuestionRepository>()),
  );
  sl.registerLazySingleton(
    () => ReviewQuestionUseCase(repository: sl<QuestionRepository>()),
  );

  // Cubit
  sl.registerFactory(
    () => QuestionSrsCubit(
      getDueQuestionsUseCase: sl<GetDueQuestionsUseCase>(),
      reviewQuestionUseCase: sl<ReviewQuestionUseCase>(),
    ),
  );

  // ----------------------------------------------------
  // Feature: Performance Hub
  // ----------------------------------------------------
  // Data Sources
  sl.registerLazySingleton<PerformanceRemoteDataSource>(
    () => PerformanceRemoteDataSourceImpl(client: sl<Dio>()),
  );

  // Repositories
  sl.registerLazySingleton<PerformanceRepository>(
    () => PerformanceRepositoryImpl(
      remoteDataSource: sl<PerformanceRemoteDataSource>(),
    ),
  );

  // Use Cases
  sl.registerLazySingleton(
    () => GetUserStatisticsUseCase(repository: sl<PerformanceRepository>()),
  );

  // Cubit
  sl.registerFactory(
    () => PerformanceCubit(
      getUserStatisticsUseCase: sl<GetUserStatisticsUseCase>(),
    ),
  );

  // ----------------------------------------------------
  // Feature: Settings & LGPD Account Deletion
  // ----------------------------------------------------
  // Data Sources
  sl.registerLazySingleton<SettingsRemoteDataSource>(
    () => SettingsRemoteDataSourceImpl(client: sl<Dio>()),
  );

  // Repositories
  sl.registerLazySingleton<SettingsRepository>(
    () => SettingsRepositoryImpl(
      remoteDataSource: sl<SettingsRemoteDataSource>(),
    ),
  );

  // Use Cases
  sl.registerLazySingleton(
    () => DeleteAccountUseCase(repository: sl<SettingsRepository>()),
  );

  // Cubit
  sl.registerFactory(
    () => SettingsCubit(
      deleteAccountUseCase: sl<DeleteAccountUseCase>(),
      secureStorageService: sl<SecureStorageService>(),
    ),
  );
}

