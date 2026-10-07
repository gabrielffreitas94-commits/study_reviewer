import 'package:equatable/equatable.dart';

/// Contrato genérico de Caso de Uso (Use Case) na Clean Architecture.
abstract class UseCase<Type, Params> {
  Future<Type> call(Params params);
}

/// Parâmetro nulo para UseCases que não demandam argumentos de entrada.
class NoParams extends Equatable {
  const NoParams();

  @override
  List<Object?> get props => [];
}
