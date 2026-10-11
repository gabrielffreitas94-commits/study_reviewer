import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

/// Constantes de rede e endpoints da API REST do Study Reviewer.
class ApiConstants {
  ApiConstants._();

  /// URL para emulador Android padrão (10.0.2.2 mapeia para o host local).
  static const String androidEmulatorBaseUrl = 'http://10.0.2.2:8000/api/v1';

  /// URL padrão para Web, Desktop e emulador iOS (localhost).
  static const String localhostBaseUrl = 'http://localhost:8000/api/v1';

  /// URL de Staging pública na AWS (Serverless Always Free)
  static const String stagingBaseUrl =
      'https://6xopxyw6z6qmqpbmcvaszuy27m0jsgzh.lambda-url.sa-east-1.on.aws/api/v1';

  /// Determina dinamicamente a URL base correta conforme a plataforma de execução ou flag --dart-define.
  static String get defaultBaseUrl {
    const envUrl = String.fromEnvironment('API_BASE_URL');
    if (envUrl.isNotEmpty) {
      return envUrl;
    }
    if (kIsWeb) {
      return localhostBaseUrl;
    }
    try {
      if (Platform.isAndroid) {
        return androidEmulatorBaseUrl;
      }
    } catch (_) {
      // Plataforma sem suporte a dart:io (fall-through seguro)
    }
    return localhostBaseUrl;
  }

  // Endpoints de Autenticação
  static const String authGoogle = '/auth/google';
  static const String authMe = '/auth/me';
  static const String authLogout = '/auth/logout';
  static const String authAccount = '/auth/account';

  // Endpoints de Perguntas SRS
  static const String questionsDue = '/questions/due';
  static String questionReview(String id) => '/questions/$id/review';
  static String questionEvaluateText(String id) => '/questions/$id/evaluate-text';
  static String questionEvaluateAudio(String id) => '/questions/$id/evaluate-audio';
  static String questionDispute(String id) => '/questions/$id/dispute';
  static const String userTokenBalance = '/users/me/token-balance';

  // Endpoints de Flashcards e Estudo
  static const String studyBatch = '/study/batch';
  static const String studyNext = '/study/next';
  static String studyRead(String cardId) => '/study/read/$cardId';
  static String topicFlashcards(String topicId) => '/topics/$topicId/flashcards';

  // Endpoints de Sincronização Offline
  static const String studySyncAnswers = '/study/sync-answers';

  // Endpoints de Performance e Auditoria
  static const String performanceStatistics = '/performance/statistics';
  static const String performanceAuditLogs = '/performance/audit-logs';
  static const String performanceExport = '/performance/export';


  // Configurações de Timeout (15 segundos)
  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 15);
  static const Duration sendTimeout = Duration(seconds: 15);
}
