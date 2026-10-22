import 'package:flutter/material.dart';
import '../../core/theme/app_colors.dart';

/// Professional Shimmer / Skeleton Loader for async loading states.
/// Free of heavy external dependencies, fully aligned with AppColors tokens.
class SkeletonLoader extends StatefulWidget {
  final double width;
  final double height;
  final double borderRadius;

  const SkeletonLoader({
    super.key,
    required this.width,
    required this.height,
    this.borderRadius = AppColors.radiusMd,
  });

  @override
  State<SkeletonLoader> createState() => _SkeletonLoaderState();
}

class _SkeletonLoaderState extends State<SkeletonLoader> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.borderRadius),
            gradient: LinearGradient(
              begin: Alignment(-1.5 + (_controller.value * 3.0), -0.2),
              end: Alignment(-0.5 + (_controller.value * 3.0), 0.2),
              colors: const [
                AppColors.surfaceRaised,
                AppColors.surfaceHighlight,
                AppColors.surfaceRaised,
              ],
              stops: const [0.0, 0.5, 1.0],
            ),
            border: Border.all(color: AppColors.borderDefault, width: 1),
          ),
        );
      },
    );
  }
}
