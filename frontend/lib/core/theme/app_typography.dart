import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';

/// Deliberate Typography System:
/// - Sans-Serif: Inter with tuned letter-spacing, line-heights, and weights (UI, headers, body)
/// - Monospace: JetBrains Mono with tuned tracking (telemetry, terminal, hotkeys, code)
class AppTypography {
  AppTypography._();

  static TextStyle displayLarge = GoogleFonts.inter(
    fontSize: 22,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.4,
    height: 1.25,
    color: AppColors.neutral100,
  );

  static TextStyle displayMedium = GoogleFonts.inter(
    fontSize: 18,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.2,
    height: 1.3,
    color: AppColors.neutral100,
  );

  static TextStyle titleMedium = GoogleFonts.inter(
    fontSize: 14,
    fontWeight: FontWeight.w600,
    letterSpacing: -0.1,
    height: 1.35,
    color: AppColors.neutral100,
  );

  static TextStyle bodyMedium = GoogleFonts.inter(
    fontSize: 13,
    fontWeight: FontWeight.w400,
    letterSpacing: 0.0,
    height: 1.45,
    color: AppColors.neutral200,
  );

  static TextStyle bodySmall = GoogleFonts.inter(
    fontSize: 12,
    fontWeight: FontWeight.w400,
    letterSpacing: 0.1,
    height: 1.4,
    color: AppColors.neutral400,
  );

  static TextStyle caption = GoogleFonts.inter(
    fontSize: 11,
    fontWeight: FontWeight.w500,
    letterSpacing: 0.2,
    height: 1.3,
    color: AppColors.neutral500,
  );

  // --- Monospace scale for metrics & code ---
  static TextStyle monoMetrics = GoogleFonts.jetBrainsMono(
    fontSize: 11,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.3,
    color: AppColors.accentPrimary,
  );

  static TextStyle monoCode = GoogleFonts.jetBrainsMono(
    fontSize: 12,
    fontWeight: FontWeight.w400,
    letterSpacing: 0.0,
    height: 1.5,
    color: AppColors.neutral200,
  );

  static TextStyle monoBadge = GoogleFonts.jetBrainsMono(
    fontSize: 10,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.5,
    color: AppColors.neutral300,
  );
}
