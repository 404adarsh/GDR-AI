import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';
import 'app_typography.dart';

export 'app_colors.dart';
export 'app_typography.dart';

/// App Theme Extension for dynamic token access via `Theme.of(context).extension<BlockBrainThemeExtension>()`
@immutable
class BlockBrainThemeExtension extends ThemeExtension<BlockBrainThemeExtension> {
  final Color surfaceBase;
  final Color surfaceRaised;
  final Color surfaceOverlay;
  final Color surfaceHighlight;
  final Color accentPrimary;
  final Color accentSecondary;
  final Color textPrimary;
  final Color textSecondary;
  final Color textTertiary;
  final Color borderDefault;
  final Color borderSubtle;
  final bool isMinimal;

  const BlockBrainThemeExtension({
    required this.surfaceBase,
    required this.surfaceRaised,
    required this.surfaceOverlay,
    required this.surfaceHighlight,
    required this.accentPrimary,
    required this.accentSecondary,
    required this.textPrimary,
    required this.textSecondary,
    required this.textTertiary,
    required this.borderDefault,
    required this.borderSubtle,
    this.isMinimal = false,
  });

  static const darkStudio = BlockBrainThemeExtension(
    surfaceBase: AppColors.surfaceBase,
    surfaceRaised: AppColors.surfaceRaised,
    surfaceOverlay: AppColors.surfaceOverlay,
    surfaceHighlight: AppColors.surfaceHighlight,
    accentPrimary: AppColors.accentPrimary,
    accentSecondary: AppColors.accentSecondary,
    textPrimary: AppColors.neutral100,
    textSecondary: AppColors.neutral400,
    textTertiary: AppColors.neutral500,
    borderDefault: AppColors.borderDefault,
    borderSubtle: AppColors.borderSubtle,
    isMinimal: false,
  );

  static const darkMinimal = BlockBrainThemeExtension(
    surfaceBase: Color(0xFF090A0E),
    surfaceRaised: Color(0xFF0F1015),
    surfaceOverlay: Color(0xFF14161E),
    surfaceHighlight: Color(0xFF1A1D27),
    accentPrimary: Color(0xFF00B8D9),
    accentSecondary: Color(0xFF7E38B7),
    textPrimary: Color(0xFFE2E8F0),
    textSecondary: Color(0xFF718096),
    textTertiary: Color(0xFF4A5568),
    borderDefault: Color(0xFF1E222D),
    borderSubtle: Color(0x0FFFFFFF),
    isMinimal: true,
  );

  @override
  BlockBrainThemeExtension copyWith({
    Color? surfaceBase,
    Color? surfaceRaised,
    Color? surfaceOverlay,
    Color? surfaceHighlight,
    Color? accentPrimary,
    Color? accentSecondary,
    Color? textPrimary,
    Color? textSecondary,
    Color? textTertiary,
    Color? borderDefault,
    Color? borderSubtle,
    bool? isMinimal,
  }) {
    return BlockBrainThemeExtension(
      surfaceBase: surfaceBase ?? this.surfaceBase,
      surfaceRaised: surfaceRaised ?? this.surfaceRaised,
      surfaceOverlay: surfaceOverlay ?? this.surfaceOverlay,
      surfaceHighlight: surfaceHighlight ?? this.surfaceHighlight,
      accentPrimary: accentPrimary ?? this.accentPrimary,
      accentSecondary: accentSecondary ?? this.accentSecondary,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textTertiary: textTertiary ?? this.textTertiary,
      borderDefault: borderDefault ?? this.borderDefault,
      borderSubtle: borderSubtle ?? this.borderSubtle,
      isMinimal: isMinimal ?? this.isMinimal,
    );
  }

  @override
  BlockBrainThemeExtension lerp(ThemeExtension<BlockBrainThemeExtension>? other, double t) {
    if (other is! BlockBrainThemeExtension) return this;
    return BlockBrainThemeExtension(
      surfaceBase: Color.lerp(surfaceBase, other.surfaceBase, t)!,
      surfaceRaised: Color.lerp(surfaceRaised, other.surfaceRaised, t)!,
      surfaceOverlay: Color.lerp(surfaceOverlay, other.surfaceOverlay, t)!,
      surfaceHighlight: Color.lerp(surfaceHighlight, other.surfaceHighlight, t)!,
      accentPrimary: Color.lerp(accentPrimary, other.accentPrimary, t)!,
      accentSecondary: Color.lerp(accentSecondary, other.accentSecondary, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      textTertiary: Color.lerp(textTertiary, other.textTertiary, t)!,
      borderDefault: Color.lerp(borderDefault, other.borderDefault, t)!,
      borderSubtle: Color.lerp(borderSubtle, other.borderSubtle, t)!,
      isMinimal: other.isMinimal,
    );
  }
}

class AppTheme {
  // Backward compatibility aliases mapped directly to new disciplined design tokens
  static const Color bgDark = AppColors.surfaceBase;
  static const Color cardBg = AppColors.surfaceRaised;
  static const Color cardBorder = AppColors.borderDefault;
  static const Color cardHover = AppColors.surfaceHighlight;

  static const Color cyan = AppColors.accentPrimary;
  static const Color cyanGlow = AppColors.accentPrimaryGlow;
  static const Color violet = AppColors.accentSecondary;
  static const Color violetGlow = AppColors.accentSecondaryMuted;
  static const Color green = AppColors.semanticSuccess;
  static const Color greenGlow = AppColors.semanticSuccessSubtle;
  static const Color danger = AppColors.semanticDanger;
  static const Color dangerDark = Color(0xFF7F1D1D);
  static const Color warning = AppColors.semanticWarning;

  static const Color textMain = AppColors.neutral100;
  static const Color textMuted = AppColors.neutral400;

  static ThemeData get themeData => getTheme(isMinimal: false);

  static ThemeData getTheme({bool isMinimal = false}) {
    final ext = isMinimal ? BlockBrainThemeExtension.darkMinimal : BlockBrainThemeExtension.darkStudio;

    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: ext.surfaceBase,
      primaryColor: ext.accentPrimary,
      extensions: [ext],
      colorScheme: ColorScheme.dark(
        primary: ext.accentPrimary,
        secondary: ext.accentSecondary,
        surface: ext.surfaceRaised,
        error: AppColors.semanticDanger,
      ),
      textTheme: GoogleFonts.interTextTheme(
        ThemeData.dark().textTheme.copyWith(
          headlineMedium: AppTypography.displayMedium,
          titleMedium: AppTypography.titleMedium,
          bodyMedium: AppTypography.bodyMedium,
          bodySmall: AppTypography.bodySmall,
        ),
      ),
      iconTheme: IconThemeData(color: ext.accentPrimary, size: 18),
    );
  }

  static TextStyle get mono => AppTypography.monoMetrics;
}
