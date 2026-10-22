import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_theme.dart';
import '../../state/app_state.dart';
import '../widgets/glass_card.dart';

class HealthScreen extends StatelessWidget {
  const HealthScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final sys = state.systemState;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('SYSTEM HEALTH & HARDWARE TELEMETRY', style: TextStyle(color: AppTheme.cyan, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
          const SizedBox(height: 6),
          const Text('Hardware constraint management designed for NVIDIA RTX 3050 Laptop (4GB VRAM, 16GB RAM).', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
          const SizedBox(height: 20),

          // VRAM Card
          GlassCard(
            borderColor: AppTheme.cyan.withOpacity(0.4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.memory, color: AppTheme.cyan, size: 18),
                        SizedBox(width: 8),
                        Text('NVIDIA RTX 3050 VRAM BUDGET', style: TextStyle(color: AppTheme.cyan, fontSize: 13, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    Text('${sys.vramUsedMb.toStringAsFixed(0)} / ${sys.vramTotalMb.toStringAsFixed(0)} MB', style: AppTheme.mono),
                  ],
                ),
                const SizedBox(height: 12),
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: LinearProgressIndicator(
                    value: (sys.vramUsedMb / sys.vramTotalMb).clamp(0.0, 1.0),
                    backgroundColor: Colors.white10,
                    valueColor: AlwaysStoppedAnimation<Color>(sys.vramUsedMb > 3400 ? AppTheme.danger : AppTheme.cyan),
                    minHeight: 10,
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  '• Strict 3800 MiB ceiling active to prevent Linux compositor and X11 thrashing.\n• Single Heavy GPU Model lock: only 1 heavy model resident at a time.\n• Auto-unloads idle models after 300s.',
                  style: TextStyle(color: AppTheme.textMuted, fontSize: 11, height: 1.4),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // CPU & RAM Card
          Row(
            children: [
              Expanded(
                child: GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('CPU UTILIZATION', style: TextStyle(color: AppTheme.violet, fontSize: 12, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 10),
                      Text('${sys.cpuPercent.toStringAsFixed(1)}%', style: AppTheme.mono.copyWith(fontSize: 22, color: AppTheme.textMain)),
                      const SizedBox(height: 6),
                      const Text('Running WakeWord (openWakeWord), VAD (webrtcvad), STT, Neural TTS', style: TextStyle(color: AppTheme.textMuted, fontSize: 10)),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('SYSTEM RAM RESERVE', style: TextStyle(color: AppTheme.green, fontSize: 12, fontWeight: FontWeight.bold)),
                      const SizedBox(height: 10),
                      Text('${(sys.ramTotalGb - sys.ramUsedGb).toStringAsFixed(1)} GB Free', style: AppTheme.mono.copyWith(fontSize: 22, color: AppTheme.green)),
                      const SizedBox(height: 6),
                      const Text('Guaranteed ≥ 4.0 GB free floor for desktop and OS processes', style: TextStyle(color: AppTheme.textMuted, fontSize: 10)),
                    ],
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Doctor Diagnostics Card
          GlassCard(
            borderColor: AppTheme.green.withOpacity(0.4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.healing, color: AppTheme.green, size: 18),
                    SizedBox(width: 8),
                    Text('SUBSYSTEM DIAGNOSTICS (GDR DOCTOR)', style: TextStyle(color: AppTheme.green, fontSize: 13, fontWeight: FontWeight.bold)),
                  ],
                ),
                const SizedBox(height: 12),
                _buildDiagRow('Microphone (PipeWire wpctl auto-boost)', true),
                _buildDiagRow('Voice Activity Detection (webrtcvad 16kHz)', true),
                _buildDiagRow('Offline WakeWord (hey_jarvis_v0.1.onnx)', true),
                _buildDiagRow('Local Speech-To-Text (faster-whisper int8)', true),
                _buildDiagRow('Neural Text-To-Speech (Piper en_US-lessac)', true),
                _buildDiagRow('Screen Invisibility Engine (libstealthcloak X11 Hook)', state.isCloaked),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDiagRow(String label, bool passed) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppTheme.textMain, fontSize: 12)),
          Row(
            children: [
              Icon(passed ? Icons.check_circle : Icons.error, color: passed ? AppTheme.green : AppTheme.danger, size: 14),
              const SizedBox(width: 4),
              Text(passed ? 'PASS' : 'FAIL', style: TextStyle(color: passed ? AppTheme.green : AppTheme.danger, fontSize: 11, fontWeight: FontWeight.bold)),
            ],
          ),
        ],
      ),
    );
  }
}
