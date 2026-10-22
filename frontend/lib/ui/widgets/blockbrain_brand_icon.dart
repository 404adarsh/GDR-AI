import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';

/// Official Brand Icon for BlockBrain HUD
/// Renders the isometric multi-cube neural architecture mark with cyan glow.
class BlockBrainBrandIcon extends StatelessWidget {
  final double size;
  final bool showGlow;
  final BorderRadius? borderRadius;

  const BlockBrainBrandIcon({
    super.key,
    this.size = 24.0,
    this.showGlow = false,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveRadius = borderRadius ?? BorderRadius.circular(size * 0.22);

    Widget iconWidget = ClipRRect(
      borderRadius: effectiveRadius,
      child: Image.asset(
        'assets/branding/blockbrain_icon.png',
        width: size,
        height: size,
        fit: BoxFit.contain,
        filterQuality: FilterQuality.medium,
        errorBuilder: (context, error, stackTrace) {
          // Fallback if asset is missing
          return Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              color: AppColors.accentPrimarySubtle,
              borderRadius: effectiveRadius,
              border: Border.all(color: AppColors.accentPrimaryMuted, width: 1),
            ),
            child: Icon(
              Icons.view_in_ar_rounded,
              size: size * 0.6,
              color: AppColors.accentPrimary,
            ),
          );
        },
      ),
    );

    if (showGlow) {
      return Container(
        decoration: BoxDecoration(
          borderRadius: effectiveRadius,
          boxShadow: [
            BoxShadow(
              color: AppColors.accentPrimary.withOpacity(0.35),
              blurRadius: size * 0.4,
              spreadRadius: 1,
            ),
          ],
        ),
        child: iconWidget,
      );
    }

    return iconWidget;
  }
}

/// Official Full Brand Logo with Neural Net Circuit
class BlockBrainBrandLogo extends StatelessWidget {
  final double width;
  final double? height;
  final bool showGlow;

  const BlockBrainBrandLogo({
    super.key,
    this.width = 160.0,
    this.height,
    this.showGlow = false,
  });

  @override
  Widget build(BuildContext context) {
    Widget logoWidget = Image.asset(
      'assets/branding/blockbrain_logo.png',
      width: width,
      height: height ?? width,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
      errorBuilder: (context, error, stackTrace) {
        return BlockBrainBrandIcon(size: width * 0.3);
      },
    );

    if (showGlow) {
      return Container(
        decoration: BoxDecoration(
          boxShadow: [
            BoxShadow(
              color: AppColors.accentPrimary.withOpacity(0.2),
              blurRadius: width * 0.15,
            ),
          ],
        ),
        child: logoWidget,
      );
    }

    return logoWidget;
  }
}
