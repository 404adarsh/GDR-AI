import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_theme.dart';
import '../../state/app_state.dart';
import '../widgets/glass_card.dart';

class StealthScreen extends StatelessWidget {
  const StealthScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final sol = state.stealthSolution;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Stealth Action Bar
          Row(
            children: [
              Expanded(
                flex: 2,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.cyan,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    elevation: 0,
                  ),
                  onPressed: state.isSolving ? null : () => state.triggerStealthSolve(),
                  icon: state.isSolving
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(color: Colors.black, strokeWidth: 2),
                        )
                      : const Icon(Icons.bolt, size: 20),
                  label: Text(
                    state.isSolving ? 'ANALYZING SCREEN...' : '⚡ SOLVE SCREEN NOW',
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, letterSpacing: 0.5),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              _buildToggleButton(
                label: 'AUTO-WATCH',
                isActive: state.autowatchEnabled,
                icon: Icons.remove_red_eye_outlined,
                onTap: () => state.toggleAutoWatch(),
              ),
              const SizedBox(width: 12),
              _buildToggleButton(
                label: 'EARPHONE WHISPER',
                isActive: state.whisperEnabled,
                icon: Icons.headphones_outlined,
                onTap: () => state.toggleWhisper(),
              ),
              const SizedBox(width: 12),
              IconButton(
                tooltip: 'Clear Solution',
                onPressed: () => state.clearStealth(),
                icon: const Icon(Icons.delete_outline, color: AppTheme.textMuted),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Invisibility Status Banner
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              color: state.isCloaked ? const Color(0x1A10B981) : const Color(0x1AEF4444),
              border: Border.all(
                color: state.isCloaked ? AppTheme.green : AppTheme.danger,
                width: 1,
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Icon(
                  state.isCloaked ? Icons.shield_outlined : Icons.warning_amber_rounded,
                  size: 16,
                  color: state.isCloaked ? AppTheme.green : AppTheme.danger,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    state.isCloaked
                        ? '🛡️ Screen-Share Invisibility: ACTIVE (Zoom, Meet, Teams, Discord & OBS cannot capture this window. Viewers see through to your background).'
                        : '⚠️ Screen-Share Cloak is OFF (Window is currently visible to screen capture).',
                    style: TextStyle(
                      color: state.isCloaked ? AppTheme.green : AppTheme.danger,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // Question Detected Card
          GlassCard(
            borderColor: AppTheme.cyan.withOpacity(0.4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('🎯 DETECTED PROBLEM / QUESTION', style: TextStyle(color: AppTheme.cyan, fontSize: 12, fontWeight: FontWeight.bold)),
                    if (sol.timestamp != null)
                      Text(sol.timestamp!.split('T').last.split('.').first, style: AppTheme.mono),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  sol.question,
                  style: const TextStyle(color: AppTheme.textMain, fontSize: 14, height: 1.4, fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Section 1: 🗣️ SAY THIS FIRST
          GlassCard(
            borderColor: AppTheme.green.withOpacity(0.5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Row(
                      children: [
                        Text('🗣️ SAY THIS FIRST', style: TextStyle(color: AppTheme.green, fontSize: 13, fontWeight: FontWeight.bold)),
                        SizedBox(width: 8),
                        Text('(Immediate confident response)', style: TextStyle(color: AppTheme.textMuted, fontSize: 11)),
                      ],
                    ),
                    IconButton(
                      icon: const Icon(Icons.copy, size: 14, color: AppTheme.textMuted),
                      tooltip: 'Copy speaking points',
                      onPressed: () => Clipboard.setData(ClipboardData(text: sol.talkingPoints)),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  sol.talkingPoints.isNotEmpty ? sol.talkingPoints : 'No solution yet. Tap ⚡ Solve Screen Now.',
                  style: const TextStyle(color: AppTheme.textMain, fontSize: 14, height: 1.5),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Section 2: 💡 OPTIMAL APPROACH & BIG-O
          GlassCard(
            borderColor: AppTheme.violet.withOpacity(0.5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('💡 OPTIMAL APPROACH & BIG-O COMPLEXITY', style: TextStyle(color: AppTheme.violet, fontSize: 13, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text(
                  sol.approach.isNotEmpty ? sol.approach : 'Algorithmic approach will appear here.',
                  style: const TextStyle(color: AppTheme.textMain, fontSize: 13, height: 1.5),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Section 3: 💻 SOLUTION CODE
          GlassCard(
            borderColor: AppTheme.cyan.withOpacity(0.5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('💻 SOLUTION CODE', style: TextStyle(color: AppTheme.cyan, fontSize: 13, fontWeight: FontWeight.bold)),
                    IconButton(
                      icon: const Icon(Icons.copy, size: 14, color: AppTheme.textMuted),
                      tooltip: 'Copy Code',
                      onPressed: () => Clipboard.setData(ClipboardData(text: sol.code)),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF03050A),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.white10),
                  ),
                  child: SelectableText(
                    sol.code.isNotEmpty ? sol.code : '# Solution code appears here',
                    style: AppTheme.mono.copyWith(fontSize: 12, height: 1.5, color: const Color(0xFFE2E8F0)),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Section 4: ⚠️ EDGE CASES
          GlassCard(
            borderColor: AppTheme.warning.withOpacity(0.5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('⚠️ EDGE CASES & INTERVIEW TRAPS', style: TextStyle(color: AppTheme.warning, fontSize: 13, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text(
                  sol.edgeCases.isNotEmpty ? sol.edgeCases : 'Edge cases will appear here.',
                  style: const TextStyle(color: AppTheme.textMain, fontSize: 13, height: 1.4),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildToggleButton({
    required String label,
    required bool isActive,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: isActive ? AppTheme.green.withOpacity(0.18) : AppTheme.cardBg,
          border: Border.all(
            color: isActive ? AppTheme.green : AppTheme.cardBorder,
            width: 1,
          ),
          borderRadius: BorderRadius.circular(10),
          boxShadow: isActive ? [const BoxShadow(color: AppTheme.greenGlow, blurRadius: 10)] : null,
        ),
        child: Row(
          children: [
            Icon(icon, size: 16, color: isActive ? AppTheme.green : AppTheme.textMuted),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: isActive ? AppTheme.green : AppTheme.textMuted,
                fontSize: 11,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
