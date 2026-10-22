import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

class GlowingAiOrb extends StatefulWidget {
  final String state; // idle | listening | thinking | speaking | alert
  final double size;
  final VoidCallback? onTap;

  const GlowingAiOrb({
    super.key,
    required this.state,
    this.size = 140,
    this.onTap,
  });

  @override
  State<GlowingAiOrb> createState() => _GlowingAiOrbState();
}

class _GlowingAiOrbState extends State<GlowingAiOrb> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();
  }

  @override
  void didUpdateWidget(GlowingAiOrb oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.state != oldWidget.state) {
      if (widget.state == 'thinking' || widget.state == 'listening') {
        _controller.duration = const Duration(milliseconds: 1000);
      } else {
        _controller.duration = const Duration(seconds: 3);
      }
      _controller.repeat();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color get _primaryColor {
    switch (widget.state) {
      case 'listening':
        return AppTheme.green;
      case 'thinking':
        return AppTheme.violet;
      case 'speaking':
        return const Color(0xFF38BDF8);
      case 'alert':
        return AppTheme.danger;
      case 'idle':
      default:
        return AppTheme.cyan;
    }
  }

  Color get _secondaryColor {
    switch (widget.state) {
      case 'listening':
        return const Color(0xFF047857);
      case 'thinking':
        return const Color(0xFF6B21A8);
      case 'speaking':
        return const Color(0xFF818CF8);
      case 'alert':
        return const Color(0xFF991B1B);
      case 'idle':
      default:
        return AppTheme.violet;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          final t = _controller.value;
          final floatOffset = math.sin(t * math.pi * 2) * 5.0;
          final scalePulse = 1.0 + (math.sin(t * math.pi * 2) * 0.04);

          return Transform.translate(
            offset: Offset(0, floatOffset),
            child: Transform.scale(
              scale: scalePulse,
              child: Container(
                width: widget.size,
                height: widget.size,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    center: const Alignment(-0.3, -0.3),
                    radius: 0.9,
                    colors: [
                      Colors.white,
                      _primaryColor,
                      _secondaryColor,
                      AppTheme.bgDark,
                    ],
                    stops: const [0.0, 0.35, 0.75, 1.0],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: _primaryColor.withOpacity(0.55),
                      blurRadius: 35,
                      spreadRadius: 8,
                    ),
                    BoxShadow(
                      color: _secondaryColor.withOpacity(0.35),
                      blurRadius: 50,
                      spreadRadius: 15,
                    ),
                  ],
                ),
                child: Center(
                  child: Container(
                    width: widget.size * 0.85,
                    height: widget.size * 0.85,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: Colors.white.withOpacity(0.25),
                        width: 1.5,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
