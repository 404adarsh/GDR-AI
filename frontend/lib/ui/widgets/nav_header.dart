import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_theme.dart';
import '../../state/app_state.dart';
import 'blockbrain_brand_icon.dart';

class NavHeader extends StatelessWidget {
  const NavHeader({super.key});

  static const List<String> screens = [
    '⚡ Command Center',
    '🕵️ Stealth Copilot',
    '💬 AI Chat',
    '📅 Tasks',
    '🛡️ Approvals',
    '🧠 Memory',
    '💻 System & VRAM',
    '⚙️ Settings',
  ];

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xE6070A13),
        border: const Border(
          bottom: BorderSide(color: AppTheme.cardBorder, width: 1),
        ),
      ),
      child: Row(
        children: [
          // Brand Logo
          Row(
            children: [
              const BlockBrainBrandIcon(
                size: 26,
                showGlow: true,
              ),
              const SizedBox(width: 10),
              const Text(
                'BLOCKBRAIN',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 15,
                  letterSpacing: 1.5,
                  color: AppTheme.cyan,
                  shadows: [Shadow(color: AppTheme.cyanGlow, blurRadius: 12)],
                ),
              ),
            ],
          ),
          const SizedBox(width: 16),

          // Stealth Cloak Indicator Pill
          InkWell(
            onTap: () => state.toggleCloak(),
            borderRadius: BorderRadius.circular(12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: state.isCloaked ? const Color(0x2610B981) : const Color(0x2694A3B8),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: state.isCloaked ? AppTheme.green : AppTheme.textMuted,
                  width: 1,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    state.isCloaked ? Icons.visibility_off : Icons.visibility,
                    size: 13,
                    color: state.isCloaked ? AppTheme.green : AppTheme.textMuted,
                  ),
                  const SizedBox(width: 5),
                  Text(
                    state.isCloaked ? 'CLOAK ACTIVE (Screen-Share Invisible)' : 'CLOAK OFF',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: state.isCloaked ? AppTheme.green : AppTheme.textMuted,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(width: 20),

          // Nav Tabs
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: List.generate(screens.length, (idx) {
                  final active = state.currentScreenIndex == idx;
                  return Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(8),
                      onTap: () => state.setScreen(idx),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: active ? AppTheme.cyan : Colors.transparent,
                          borderRadius: BorderRadius.circular(8),
                          boxShadow: active
                              ? [const BoxShadow(color: AppTheme.cyanGlow, blurRadius: 12)]
                              : null,
                        ),
                        child: Text(
                          screens[idx],
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: active ? Colors.black : AppTheme.textMuted,
                          ),
                        ),
                      ),
                    ),
                  );
                }),
              ),
            ),
          ),

          const SizedBox(width: 12),

          // Panic Button
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.dangerDark,
              foregroundColor: Colors.white,
              elevation: 0,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: const BorderSide(color: AppTheme.danger, width: 1),
              ),
            ),
            onPressed: () => state.triggerPanic(),
            icon: const Icon(Icons.warning_amber_rounded, size: 14, color: Colors.white),
            label: const Text(
              'PANIC KILL',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 0.8),
            ),
          ),
        ],
      ),
    );
  }
}
