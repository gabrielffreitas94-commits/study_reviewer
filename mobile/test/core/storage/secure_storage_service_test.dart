import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:study_reviewer_mobile/core/errors/failures.dart';
import 'package:study_reviewer_mobile/core/storage/secure_storage_service.dart';

class MockFlutterSecureStorage extends Mock implements FlutterSecureStorage {}

void main() {
  late MockFlutterSecureStorage mockStorage;
  late SecureStorageService secureStorageService;

  setUp(() {
    mockStorage = MockFlutterSecureStorage();
    secureStorageService = SecureStorageService(storage: mockStorage);
  });

  group('SecureStorageService', () {
    const tKey = 'test_key';
    const tValue = 'test_value';

    test('deve invocar write com sucesso no storage seguro', () async {
      when(() => mockStorage.write(key: tKey, value: tValue))
          .thenAnswer((_) async {});

      await secureStorageService.write(key: tKey, value: tValue);

      verify(() => mockStorage.write(key: tKey, value: tValue)).called(1);
    });

    test('deve lançar StorageFailure quando write falhar', () async {
      when(() => mockStorage.write(key: tKey, value: tValue))
          .thenThrow(Exception('Keystore locked'));

      expect(
        () => secureStorageService.write(key: tKey, value: tValue),
        throwsA(isA<StorageFailure>()),
      );
    });

    test('deve invocar read e retornar o valor armazenado', () async {
      when(() => mockStorage.read(key: tKey))
          .thenAnswer((_) async => tValue);

      final result = await secureStorageService.read(key: tKey);

      expect(result, tValue);
      verify(() => mockStorage.read(key: tKey)).called(1);
    });

    test('deve invocar delete e remover item com sucesso', () async {
      when(() => mockStorage.delete(key: tKey))
          .thenAnswer((_) async {});

      await secureStorageService.delete(key: tKey);

      verify(() => mockStorage.delete(key: tKey)).called(1);
    });

    test('deve invocar deleteAll e limpar todas as chaves', () async {
      when(() => mockStorage.deleteAll())
          .thenAnswer((_) async {});

      await secureStorageService.deleteAll();

      verify(() => mockStorage.deleteAll()).called(1);
    });

    test('deve verificar containsKey corretamente', () async {
      when(() => mockStorage.containsKey(key: tKey))
          .thenAnswer((_) async => true);

      final result = await secureStorageService.containsKey(key: tKey);

      expect(result, isTrue);
      verify(() => mockStorage.containsKey(key: tKey)).called(1);
    });
  });
}
