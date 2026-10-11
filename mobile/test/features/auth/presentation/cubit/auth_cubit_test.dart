import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/core/usecases/usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:study_reviewer_mobile/features/auth/domain/usecases/get_current_user_usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/usecases/login_with_google_usecase.dart';
import 'package:study_reviewer_mobile/features/auth/domain/usecases/logout_usecase.dart';
import 'package:study_reviewer_mobile/features/auth/presentation/cubit/auth_cubit.dart';
import 'package:study_reviewer_mobile/features/auth/presentation/cubit/auth_state.dart';

class MockLoginWithGoogleUseCase extends Mock implements LoginWithGoogleUseCase {}
class MockGetCurrentUserUseCase extends Mock implements GetCurrentUserUseCase {}
class MockLogoutUseCase extends Mock implements LogoutUseCase {}

void main() {
  late MockLoginWithGoogleUseCase mockLoginWithGoogleUseCase;
  late MockGetCurrentUserUseCase mockGetCurrentUserUseCase;
  late MockLogoutUseCase mockLogoutUseCase;
  late AuthCubit authCubit;

  const tUser = UserEntity(
    id: 1,
    email: 'test@studyreviewer.com',
    name: 'Test User',
    avatarUrl: null,
  );

  setUp(() {
    mockLoginWithGoogleUseCase = MockLoginWithGoogleUseCase();
    mockGetCurrentUserUseCase = MockGetCurrentUserUseCase();
    mockLogoutUseCase = MockLogoutUseCase();

    authCubit = AuthCubit(
      loginWithGoogleUseCase: mockLoginWithGoogleUseCase,
      getCurrentUserUseCase: mockGetCurrentUserUseCase,
      logoutUseCase: mockLogoutUseCase,
    );
  });

  tearDown(() {
    authCubit.close();
  });

  test('estado inicial deve ser AuthInitial', () {
    expect(authCubit.state, const AuthInitial());
  });

  group('checkAuthStatus', () {
    blocTest<AuthCubit, AuthState>(
      'deve emitir [AuthLoading, Authenticated] quando usuário autenticado for retornado',
      build: () {
        when(() => mockGetCurrentUserUseCase(const NoParams()))
            .thenAnswer((_) async => tUser);
        return authCubit;
      },
      act: (cubit) => cubit.checkAuthStatus(),
      expect: () => [
        const AuthLoading(),
        const Authenticated(tUser),
      ],
      verify: (_) {
        verify(() => mockGetCurrentUserUseCase(const NoParams())).called(1);
      },
    );

    blocTest<AuthCubit, AuthState>(
      'deve emitir [AuthLoading, Unauthenticated] quando nenhum usuário for retornado',
      build: () {
        when(() => mockGetCurrentUserUseCase(const NoParams()))
            .thenAnswer((_) async => null);
        return authCubit;
      },
      act: (cubit) => cubit.checkAuthStatus(),
      expect: () => [
        const AuthLoading(),
        const Unauthenticated(),
      ],
    );
  });

  group('loginWithGoogle', () {
    blocTest<AuthCubit, AuthState>(
      'deve emitir [AuthLoading, Authenticated] quando login for bem-sucedido',
      build: () {
        when(() => mockLoginWithGoogleUseCase(const NoParams()))
            .thenAnswer((_) async => tUser);
        return authCubit;
      },
      act: (cubit) => cubit.loginWithGoogle(),
      expect: () => [
        const AuthLoading(),
        const Authenticated(tUser),
      ],
    );

    blocTest<AuthCubit, AuthState>(
      'deve emitir [AuthLoading, AuthError, Unauthenticated] quando login falhar',
      build: () {
        when(() => mockLoginWithGoogleUseCase(const NoParams()))
            .thenThrow(const AuthFailure(message: 'Login cancelado'));
        return authCubit;
      },
      act: (cubit) => cubit.loginWithGoogle(),
      expect: () => [
        const AuthLoading(),
        const AuthError('Login cancelado'),
        const Unauthenticated(),
      ],
    );
  });

  group('logout', () {
    blocTest<AuthCubit, AuthState>(
      'deve emitir [AuthLoading, Unauthenticated] quando logout for executado',
      build: () {
        when(() => mockLogoutUseCase(const NoParams()))
            .thenAnswer((_) async {});
        return authCubit;
      },
      act: (cubit) => cubit.logout(),
      expect: () => [
        const AuthLoading(),
        const Unauthenticated(),
      ],
      verify: (_) {
        verify(() => mockLogoutUseCase(const NoParams())).called(1);
      },
    );
  });
}
