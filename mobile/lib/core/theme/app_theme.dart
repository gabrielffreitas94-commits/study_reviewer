import 'package:flutter/material.dart';

/// Design System baseado na paleta moderna do Tailwind CSS (Indigo & Slate)
/// com suporte total a Light/Dark Mode e garantia de touch targets mínimos de 48x48dp.
class AppTheme {
  AppTheme._();

  // Cores Tailwind Indigo
  static const Color indigo50 = Color(0xFFEEF2FF);
  static const Color indigo100 = Color(0xFFE0E7FF);
  static const Color indigo200 = Color(0xFFC7D2FE);
  static const Color indigo500 = Color(0xFF6366F1);
  static const Color indigo600 = Color(0xFF4F46E5);
  static const Color indigo700 = Color(0xFF4338CA);

  // Cores Tailwind Slate
  static const Color slate50 = Color(0xFFF8FAFC);
  static const Color slate100 = Color(0xFFF1F5F9);
  static const Color slate200 = Color(0xFFE2E8F0);
  static const Color slate300 = Color(0xFFCBD5E1);
  static const Color slate400 = Color(0xFF94A3B8);
  static const Color slate500 = Color(0xFF64748B);
  static const Color slate600 = Color(0xFF475569);
  static const Color slate700 = Color(0xFF334155);
  static const Color slate800 = Color(0xFF1E293B);
  static const Color slate900 = Color(0xFF0F172A);
  static const Color slate950 = Color(0xFF020617);

  // Cores Semânticas
  static const Color emerald500 = Color(0xFF10B981);
  static const Color rose500 = Color(0xFFF43F5E);
  static const Color rose600 = Color(0xFFE11D48);
  static const Color amber500 = Color(0xFFF59E0B);

  // Dimensão mínima para acessibilidade de toque (WCAG 2.1 & Material Design)
  static const Size minTouchTargetSize = Size(48, 48);

  /// Tema Claro (Light Mode)
  static ThemeData get lightTheme {
    final colorScheme = ColorScheme.light(
      primary: indigo600,
      onPrimary: Colors.white,
      primaryContainer: indigo50,
      onPrimaryContainer: indigo700,
      secondary: slate700,
      onSecondary: Colors.white,
      surface: Colors.white,
      onSurface: slate900,
      surfaceVariant: slate100,
      onSurfaceVariant: slate600,
      outline: slate200,
      error: rose600,
      onError: Colors.white,
      background: slate50,
      onBackground: slate900,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: slate50,
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.white,
        foregroundColor: slate900,
        elevation: 0,
        centerTitle: true,
        surfaceTintColor: Colors.transparent,
      ),
      cardTheme: CardTheme(
        color: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: slate200, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: minTouchTargetSize,
          backgroundColor: indigo600,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: minTouchTargetSize,
          foregroundColor: slate800,
          side: const BorderSide(color: slate300, width: 1),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          minimumSize: minTouchTargetSize,
          foregroundColor: indigo600,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          minimumSize: minTouchTargetSize,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: slate300),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: slate200),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: indigo600, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: rose600),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Colors.white,
        selectedItemColor: indigo600,
        unselectedItemColor: slate500,
        selectedLabelStyle: TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
        unselectedLabelStyle: TextStyle(fontWeight: FontWeight.w500, fontSize: 12),
        type: BottomNavigationBarType.fixed,
        elevation: 8,
      ),
    );
  }

  /// Tema Escuro (Dark Mode)
  static ThemeData get darkTheme {
    final colorScheme = ColorScheme.dark(
      primary: indigo500,
      onPrimary: Colors.white,
      primaryContainer: const Color(0xFF1E1B4B), // Indigo 950
      onPrimaryContainer: indigo200,
      secondary: slate300,
      onSecondary: slate900,
      surface: slate900,
      onSurface: slate50,
      surfaceVariant: slate800,
      onSurfaceVariant: slate400,
      outline: slate700,
      error: rose500,
      onError: Colors.white,
      background: slate950,
      onBackground: slate50,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: slate950,
      appBarTheme: const AppBarTheme(
        backgroundColor: slate900,
        foregroundColor: slate50,
        elevation: 0,
        centerTitle: true,
        surfaceTintColor: Colors.transparent,
      ),
      cardTheme: CardTheme(
        color: slate900,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: slate800, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: minTouchTargetSize,
          backgroundColor: indigo500,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: minTouchTargetSize,
          foregroundColor: slate200,
          side: const BorderSide(color: slate700, width: 1),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          minimumSize: minTouchTargetSize,
          foregroundColor: indigo500,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          minimumSize: minTouchTargetSize,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: slate900,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: slate700),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: slate800),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: indigo500, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: rose500),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: slate900,
        selectedItemColor: indigo500,
        unselectedItemColor: slate400,
        selectedLabelStyle: TextStyle(fontWeight: FontWeight.w600, fontSize: 12),
        unselectedLabelStyle: TextStyle(fontWeight: FontWeight.w500, fontSize: 12),
        type: BottomNavigationBarType.fixed,
        elevation: 8,
      ),
    );
  }
}
