import 'package:flutter/material.dart';

/// Tipo de transição ou status de repetição espaçada (SRS).
enum SrsBadgeType {
  promotion,
  maintenance,
  regression,
  levelIndicator,
}

/// Badge acessível com contraste elevado (>= 4.5:1) e semântica redundante (ícone + texto).
///
/// Implementa as diretrizes do Especialista em Acessibilidade:
/// - Promoção: verde esmeralda com "↑ Nível Superior"
/// - Manutenção: cinza ardósia com "= Mantido"
/// - Regressão: rosa carmim com "↓ Rebaixado (Nível X)"
class SrsLevelBadge extends StatelessWidget {
  final SrsBadgeType type;
  final int? levelAfter;
  final int? levelBefore;
  final String? customText;

  const SrsLevelBadge({
    super.key,
    required this.type,
    this.levelAfter,
    this.levelBefore,
    this.customText,
  });

  /// Construtor de conveniência a partir de flags booleanas de resultado SRS.
  factory SrsLevelBadge.fromResult({
    required bool isPromoted,
    required bool isDemoted,
    required bool isMaintained,
    int? levelAfter,
    int? levelBefore,
  }) {
    if (isPromoted) {
      return SrsLevelBadge(
        type: SrsBadgeType.promotion,
        levelAfter: levelAfter,
        levelBefore: levelBefore,
      );
    } else if (isDemoted) {
      return SrsLevelBadge(
        type: SrsBadgeType.regression,
        levelAfter: levelAfter,
        levelBefore: levelBefore,
      );
    } else {
      return SrsLevelBadge(
        type: SrsBadgeType.maintenance,
        levelAfter: levelAfter,
        levelBefore: levelBefore,
      );
    }
  }

  /// Construtor de conveniência para indicar apenas o nível atual (ex: "Nível 3").
  factory SrsLevelBadge.currentLevel(int level) {
    return SrsLevelBadge(
      type: SrsBadgeType.levelIndicator,
      levelAfter: level,
      customText: 'Nível $level',
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    Color backgroundColor;
    Color borderColor;
    Color textColor;
    IconData icon;
    String labelText;

    switch (type) {
      case SrsBadgeType.promotion:
        backgroundColor = isDark ? const Color(0xFF064E3B) : const Color(0xFFD1FAE5);
        borderColor = const Color(0xFF059669);
        textColor = isDark ? const Color(0xFF6EE7B7) : const Color(0xFF065F46);
        icon = Icons.arrow_upward;
        labelText = levelAfter != null
            ? '↑ Nível Superior (Nível $levelAfter)'
            : '↑ Nível Superior';
        break;

      case SrsBadgeType.maintenance:
        backgroundColor = isDark ? const Color(0xFF1E293B) : const Color(0xFFF1F5F9);
        borderColor = const Color(0xFF64748B);
        textColor = isDark ? const Color(0xFFCBD5E1) : const Color(0xFF334155);
        icon = Icons.drag_handle;
        labelText = levelAfter != null
            ? '= Mantido (Nível $levelAfter)'
            : '= Mantido';
        break;

      case SrsBadgeType.regression:
        backgroundColor = isDark ? const Color(0xFF4C0519) : const Color(0xFFFFE4E6);
        borderColor = const Color(0xFFE11D48);
        textColor = isDark ? const Color(0xFFFDA4AF) : const Color(0xFF9F1239);
        icon = Icons.arrow_downward;
        labelText = levelAfter != null
            ? '↓ Rebaixado (Nível $levelAfter)'
            : '↓ Rebaixado';
        break;

      case SrsBadgeType.levelIndicator:
        final lvl = levelAfter ?? 0;
        backgroundColor = isDark ? const Color(0xFF1E1B4B) : const Color(0xFFEEF2FF);
        borderColor = const Color(0xFF6366F1);
        textColor = isDark ? const Color(0xFFA5B4FC) : const Color(0xFF3730A3);
        icon = Icons.layers_outlined;
        labelText = customText ?? 'Nível $lvl';
        break;
    }

    return Semantics(
      label: 'Status SRS: $labelText',
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 6.0),
        decoration: BoxDecoration(
          color: backgroundColor,
          borderRadius: BorderRadius.circular(20.0),
          border: Border.all(color: borderColor, width: 1.2),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 16.0,
              color: textColor,
            ),
            const SizedBox(width: 6.0),
            Text(
              labelText,
              style: TextStyle(
                color: textColor,
                fontSize: 13.0,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.2,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
