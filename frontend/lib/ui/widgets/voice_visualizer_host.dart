import 'package:flutter/material.dart';
import 'package:voice_anim_kit/voice_anim_kit.dart';
import '../../core/theme/app_colors.dart';

enum VoiceAnimStyle {
  wave,
  bar,
  circle,
  blob,
  line,
  particle,
  ripple,
  aiGaze,
  glowBar,
}

extension VoiceAnimStyleExt on VoiceAnimStyle {
  String get id {
    switch (this) {
      case VoiceAnimStyle.wave:
        return 'wave';
      case VoiceAnimStyle.bar:
        return 'bar';
      case VoiceAnimStyle.circle:
        return 'circle';
      case VoiceAnimStyle.blob:
        return 'blob';
      case VoiceAnimStyle.line:
        return 'line';
      case VoiceAnimStyle.particle:
        return 'particle';
      case VoiceAnimStyle.ripple:
        return 'ripple';
      case VoiceAnimStyle.aiGaze:
        return 'ai_gaze';
      case VoiceAnimStyle.glowBar:
        return 'glow_bar';
    }
  }

  String get displayName {
    switch (this) {
      case VoiceAnimStyle.wave:
        return 'Sine Wave Glow';
      case VoiceAnimStyle.bar:
        return 'Frequency Equalizer';
      case VoiceAnimStyle.circle:
        return 'Pulse Rings';
      case VoiceAnimStyle.blob:
        return 'Organic Metaball';
      case VoiceAnimStyle.line:
        return 'Telemetry Line';
      case VoiceAnimStyle.particle:
        return 'Kinetic Particles';
      case VoiceAnimStyle.ripple:
        return 'Expanding Ripple';
      case VoiceAnimStyle.aiGaze:
        return 'Neural Gaze';
      case VoiceAnimStyle.glowBar:
        return 'Matrix Glow Bars';
    }
  }

  static VoiceAnimStyle fromId(String? id) {
    switch (id) {
      case 'bar':
        return VoiceAnimStyle.bar;
      case 'circle':
        return VoiceAnimStyle.circle;
      case 'blob':
        return VoiceAnimStyle.blob;
      case 'line':
        return VoiceAnimStyle.line;
      case 'particle':
        return VoiceAnimStyle.particle;
      case 'ripple':
        return VoiceAnimStyle.ripple;
      case 'ai_gaze':
        return VoiceAnimStyle.aiGaze;
      case 'glow_bar':
        return VoiceAnimStyle.glowBar;
      case 'wave':
      default:
        return VoiceAnimStyle.wave;
    }
  }
}

/// A unified host for all 9 voice_anim_kit visualizers.
/// Fully recolored with AppColors design tokens.
class VoiceVisualizerHost extends StatelessWidget {
  final VoiceAnimStyle style;
  final bool isRecording;
  final double amplitude;
  final double size;
  final Color? primaryColor;
  final Color? secondaryColor;

  const VoiceVisualizerHost({
    super.key,
    required this.style,
    required this.isRecording,
    required this.amplitude,
    this.size = 90.0,
    this.primaryColor,
    this.secondaryColor,
  });

  @override
  Widget build(BuildContext context) {
    final effectivePrimary = primaryColor ?? AppColors.accentPrimary;

    Widget visualizer;
    switch (style) {
      case VoiceAnimStyle.wave:
        visualizer = SizedBox(
          width: size * 2.2,
          height: size * 0.7,
          child: WaveVisualizer(
            isRecording: isRecording,
            amplitude: amplitude,
            color: effectivePrimary,
            height: size * 0.7,
          ),
        );
        break;

      case VoiceAnimStyle.bar:
        visualizer = SizedBox(
          width: size * 1.8,
          height: size * 0.7,
          child: BarVisualizer(
            isRecording: isRecording,
            amplitude: amplitude,
            color: effectivePrimary,
            height: size * 0.7,
            barCount: 17,
            barWidth: 3.5,
          ),
        );
        break;

      case VoiceAnimStyle.circle:
        visualizer = SizedBox(
          width: size * 1.4,
          height: size * 1.4,
          child: CircleVisualizer(
            isRecording: isRecording,
            amplitude: amplitude,
            color: effectivePrimary,
            radius: size * 0.6,
          ),
        );
        break;

      case VoiceAnimStyle.blob:
        visualizer = SizedBox(
          width: size * 1.3,
          height: size * 1.3,
          child: BlobVisualizer(
            isRecording: isRecording,
            amplitude: amplitude,
            color: effectivePrimary,
            size: size * 1.1,
          ),
        );
        break;

      case VoiceAnimStyle.line:
        visualizer = SizedBox(
          width: size * 2.0,
          height: size * 0.6,
          child: LineVisualizer(
            isRecording: isRecording,
            amplitude: amplitude,
            color: effectivePrimary,
            height: size * 0.6,
          ),
        );
        break;

      case VoiceAnimStyle.particle:
        visualizer = SizedBox(
          width: size * 1.8,
          height: size * 0.8,
          child: ParticleVisualizer(
            isRecording: isRecording,
            amplitude: amplitude,
            color: effectivePrimary,
            height: size * 0.8,
            particleCount: 18,
          ),
        );
        break;

      case VoiceAnimStyle.ripple:
        visualizer = SizedBox(
          width: size * 1.2,
          height: size * 1.2,
          child: RippleVisualizer(
            isRecording: isRecording,
            amplitude: amplitude,
            color: effectivePrimary,
            radius: size * 0.45,
          ),
        );
        break;

      case VoiceAnimStyle.aiGaze:
        visualizer = SizedBox(
          width: size * 1.3,
          height: size * 1.3,
          child: AIGazeVisualizer(
            isRecording: isRecording,
            amplitude: amplitude,
            color: effectivePrimary,
            size: size * 1.1,
          ),
        );
        break;

      case VoiceAnimStyle.glowBar:
        visualizer = SizedBox(
          width: size * 1.8,
          height: size * 0.8,
          child: GlowBarVisualizer(
            isRecording: isRecording,
            amplitude: amplitude,
            color: effectivePrimary,
            height: size * 0.8,
            barCount: 15,
            barWidth: 4.0,
          ),
        );
        break;
    }

    return AnimatedSwitcher(
      duration: AppColors.durationNormal,
      switchInCurve: AppColors.curveFast,
      switchOutCurve: AppColors.curveFast,
      child: visualizer,
    );
  }
}
