import 'package:flutter/material.dart';

/// Centralized Design Token System for BlockBrain HUD.
/// Follows disciplined architectural rules:
/// - Near-black surfaces with intentional subtle depth
/// - Single disciplined primary cyan (#00D9FF)
/// - Single disciplined secondary violet (#9D4EDD)
/// - 11-step neutral scale for genuine text/border hierarchy
/// - Semantic colors with restrained, non-neon tones
/// - Zero hardcoded hex values scattered in widget trees
class AppColors {
  AppColors._();

  // --- 1. Surfaces (Elevation System) ---
  /// Level 0: The deepest application background canvas
  static const Color surfaceBase = Color(0xFF0A0B10);

  /// Level 1: Sidebar, cards, top navigation bar
  static const Color surfaceRaised = Color(0xFF11131A);

  /// Level 2: Popups, dropdowns, floating menus, right canvas panel
  static const Color surfaceOverlay = Color(0xFF171A24);

  /// Level 3: Active text fields, hovered buttons, elevated dialogs
  static const Color surfaceHighlight = Color(0xFF1F2330);

  // --- 2. Primary Accent: Disciplined Cyan ---
  /// Primary action, active states, voice waveforms
  static const Color accentPrimary = Color(0xFF00D9FF);
  static const Color accentPrimaryHover = Color(0xFF33E1FF);
  static const Color accentPrimaryMuted = Color(0x2400D9FF); // ~14% opacity
  static const Color accentPrimarySubtle = Color(0x0F00D9FF); // ~6% opacity
  static const Color accentPrimaryGlow = Color(0x3300D9FF); // ~20% opacity

  // --- 3. Secondary Accent: Disciplined Violet ---
  /// Secondary emphasis, badges, secondary pills (never mixed randomly)
  static const Color accentSecondary = Color(0xFF9D4EDD);
  static const Color accentSecondaryMuted = Color(0x249D4EDD);
  static const Color accentSecondarySubtle = Color(0x0F9D4EDD);

  // --- 4. Neutral Grayscale Scale (11 Steps) ---
  static const Color neutral950 = Color(0xFF08090C); // Deepest void
  static const Color neutral900 = Color(0xFF0F1117);
  static const Color neutral850 = Color(0xFF151821);
  static const Color neutral800 = Color(0xFF1C202C); // Dark card base
  static const Color neutral700 = Color(0xFF2B3142); // Structural borders
  static const Color neutral600 = Color(0xFF3F475D); // Subtle borders & inactive icons
  static const Color neutral500 = Color(0xFF5D6782); // Tertiary metadata & hotkeys
  static const Color neutral400 = Color(0xFF848FA8); // Secondary readable labels
  static const Color neutral300 = Color(0xFFB0B9CF); // Main reading copy
  static const Color neutral200 = Color(0xFFD6DCE8); // Crisp body text
  static const Color neutral100 = Color(0xFFF1F4F9); // Crisp headline & title

  // --- 5. Semantic Colors ---
  static const Color semanticSuccess = Color(0xFF10B981);
  static const Color semanticSuccessSubtle = Color(0x1F10B981);

  static const Color semanticWarning = Color(0xFFF59E0B);
  static const Color semanticWarningSubtle = Color(0x1FF59E0B);

  /// Panic Kill & destructive emergency actions only
  static const Color semanticDanger = Color(0xFFEF4444);
  static const Color semanticDangerMuted = Color(0x26EF4444);
  static const Color semanticDangerGlow = Color(0x33EF4444);

  // --- 6. Borders ---
  static const Color borderSubtle = Color(0x1AFFFFFF); // Low-contrast 10% white
  static const Color borderDefault = Color(0xFF242938); // Neutral structural border
  static const Color borderFocused = Color(0xFF00D9FF); // Primary focus ring

  // --- 7. Radii Hierarchy (Rule 19) ---
  static const double radiusSm = 6.0;   // Chips, tags, small badges
  static const double radiusMd = 10.0;  // Input boxes, buttons, dropdowns
  static const double radiusLg = 16.0;  // Standard cards, message bubbles
  static const double radiusXl = 24.0;  // Floating panels, modals

  // --- 8. Standardized Motion Constants (Part 3) ---
  static const Duration durationFast = Duration(milliseconds: 180);
  static const Duration durationNormal = Duration(milliseconds: 280);
  static const Duration durationSlow = Duration(milliseconds: 400);

  static const Curve curveFast = Curves.easeOutCubic;
  static const Curve curveNormal = Curves.easeInOutCubic;
}
