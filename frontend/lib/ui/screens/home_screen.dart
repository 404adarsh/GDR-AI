import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_theme.dart';
import '../../state/app_state.dart';
import '../widgets/glass_card.dart';
import '../widgets/glowing_ai_orb.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final TextEditingController _promptController = TextEditingController();

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  void _submitPrompt(AppState state) {
    final text = _promptController.text.trim();
    if (text.isNotEmpty) {
      _promptController.clear();
      state.sendChatMessage(text);
      state.setScreen(2); // Switch to Chat Screen to see response
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final sys = state.systemState;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Centerpiece Orb Card
          GlassCard(
            padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 24),
            child: Column(
              children: [
                GlowingAiOrb(
                  state: sys.orbState,
                  size: 150,
                  onTap: () {
                    // Tap orb to solve screen or trigger voice prompt
                    state.triggerStealthSolve();
                  },
                ),
                const SizedBox(height: 20),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
                  decoration: BoxDecoration(
                    color: AppTheme.cyan.withOpacity(0.12),
                    border: Border.all(color: AppTheme.cyan, width: 1),
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: const [
                      BoxShadow(color: AppTheme.cyanGlow, blurRadius: 10),
                    ],
                  ),
                  child: Text(
                    sys.orbState.toUpperCase(),
                    style: const TextStyle(
                      color: AppTheme.cyan,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 2,
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  sys.currentActivity,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: AppTheme.textMuted,
                    fontSize: 13,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // Telemetry Row: Hardware & VRAM Budget (RTX 3050 Constraint)
          Row(
            children: [
              Expanded(
                child: GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('GPU VRAM (RTX 3050)', style: TextStyle(color: AppTheme.cyan, fontSize: 12, fontWeight: FontWeight.bold)),
                          Text('${sys.vramUsedMb.toStringAsFixed(0)} / ${sys.vramTotalMb.toStringAsFixed(0)} MB', style: AppTheme.mono),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: (sys.vramUsedMb / sys.vramTotalMb).clamp(0.0, 1.0),
                          backgroundColor: Colors.white10,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            (sys.vramUsedMb > 3400) ? AppTheme.danger : AppTheme.cyan,
                          ),
                          minHeight: 6,
                        ),
                      ),
                      const SizedBox(height: 6),
                      const Text('< 3.8 GB Ceiling Lock active to prevent compositor thrashing', style: TextStyle(color: AppTheme.textMuted, fontSize: 10)),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('SYSTEM RAM', style: TextStyle(color: AppTheme.violet, fontSize: 12, fontWeight: FontWeight.bold)),
                          Text('${sys.ramUsedGb.toStringAsFixed(1)} / ${sys.ramTotalGb.toStringAsFixed(1)} GB', style: AppTheme.mono),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: (sys.ramUsedGb / sys.ramTotalGb).clamp(0.0, 1.0),
                          backgroundColor: Colors.white10,
                          valueColor: const AlwaysStoppedAnimation<Color>(AppTheme.violet),
                          minHeight: 6,
                        ),
                      ),
                      const SizedBox(height: 6),
                      const Text('CPU Offloaded: WakeWord, VAD, STT, Neural TTS', style: TextStyle(color: AppTheme.textMuted, fontSize: 10)),
                    ],
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Quick Action Cards
          const Text('QUICK COMMANDS', style: TextStyle(color: AppTheme.cyan, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _buildQuickPill('⚡ Solve Current Screen Question', () => state.triggerStealthSolve()),
              _buildQuickPill('📅 Schedule Task ("in 15m water break")', () {
                state.api.addTask('in 15m stretch and drink water');
                state.refreshData();
              }),
              _buildQuickPill('🎙️ Whispering Earphone Mode', () => state.toggleWhisper()),
              _buildQuickPill('🤖 Check System Diagnostics', () => state.setScreen(6)),
            ],
          ),

          const SizedBox(height: 24),

          // Bottom Prompt Bar
          GlassCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                const Icon(Icons.terminal, color: AppTheme.cyan),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: _promptController,
                    onSubmitted: (_) => _submitPrompt(state),
                    style: const TextStyle(color: Colors.white, fontSize: 14),
                    decoration: const InputDecoration(
                      hintText: 'Ask BlockBrain anything, or enter a natural command...',
                      hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 13),
                      border: InputBorder.none,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: () => _submitPrompt(state),
                  icon: const Icon(Icons.arrow_forward_rounded, color: AppTheme.cyan),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickPill(String title, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: AppTheme.cardBg,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppTheme.cardBorder, width: 1),
        ),
        child: Text(
          title,
          style: const TextStyle(color: AppTheme.textMain, fontSize: 12, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}
