import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../state/app_state.dart';
import '../widgets/voice_visualizer_host.dart';

/// Settings & System Configuration Screen.
/// - Full Voice Animation Kit Style Picker (9 styles with live preview & persistence)
/// - Theme Style Toggle (Dark Studio vs Dark Minimal)
/// - Anti-Capture Cloaking & Neural Provider Pipeline details
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('SYSTEM SETTINGS & VOICE PREFERENCES', style: AppTypography.monoBadge.copyWith(color: AppColors.accentPrimary)),
          const SizedBox(height: 6),
          Text(
            'Configure real-time voice visualizers, theme contrast levels, and hardware execution options.',
            style: AppTypography.bodySmall.copyWith(color: AppColors.neutral400),
          ),
          const SizedBox(height: 24),

          // 1. Voice Animation Kit 9-Style Picker (Part 4)
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surfaceRaised,
              borderRadius: BorderRadius.circular(AppColors.radiusLg),
              border: Border.all(color: AppColors.borderDefault, width: 1),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.graphic_eq_rounded, size: 16, color: AppColors.accentPrimary),
                    const SizedBox(width: 8),
                    Text(
                      'VOICE VISUALIZER ARCHITECTURE (9 MODES)',
                      style: AppTypography.monoBadge.copyWith(color: AppColors.neutral100, fontWeight: FontWeight.bold),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppColors.accentPrimarySubtle,
                        borderRadius: BorderRadius.circular(AppColors.radiusSm),
                        border: Border.all(color: AppColors.accentPrimaryMuted, width: 1),
                      ),
                      child: Text(
                        'voice_anim_kit v0.3.0',
                        style: AppTypography.monoBadge.copyWith(color: AppColors.accentPrimary, fontSize: 9),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  'Select the primary reactive visualizer for voice prompts, listening mode, and speech output. Choices are persisted automatically.',
                  style: AppTypography.caption.copyWith(color: AppColors.neutral400),
                ),
                const SizedBox(height: 16),

                // 9-Style Selection Grid (3x3)
                LayoutBuilder(
                  builder: (context, constraints) {
                    final itemWidth = (constraints.maxWidth - 20) / 3;
                    return Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: VoiceAnimStyle.values.map((s) {
                        final isSelected = state.voiceStyle == s;
                        return InkWell(
                          onTap: () => state.setVoiceStyle(s),
                          borderRadius: BorderRadius.circular(AppColors.radiusMd),
                          child: Container(
                            width: itemWidth,
                            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
                            decoration: BoxDecoration(
                              color: isSelected ? AppColors.surfaceHighlight : AppColors.surfaceBase,
                              borderRadius: BorderRadius.circular(AppColors.radiusMd),
                              border: Border.all(
                                color: isSelected ? AppColors.accentPrimary : AppColors.borderDefault,
                                width: isSelected ? 1.5 : 1.0,
                              ),
                            ),
                            child: Column(
                              children: [
                                SizedBox(
                                  height: 48,
                                  child: Center(
                                    child: VoiceVisualizerHost(
                                      style: s,
                                      isRecording: true,
                                      amplitude: 0.45,
                                      size: 40,
                                      primaryColor: isSelected ? AppColors.accentPrimary : AppColors.neutral400,
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  s.displayName,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  textAlign: TextAlign.center,
                                  style: AppTypography.caption.copyWith(
                                    color: isSelected ? AppColors.accentPrimary : AppColors.neutral200,
                                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                                    fontSize: 11,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      }).toList(),
                    );
                  },
                ),
              ],
            ),
          ),

          const SizedBox(height: 18),

          // 2. Theme Appearance Variant (Dark Studio vs Dark Minimal)
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surfaceRaised,
              borderRadius: BorderRadius.circular(AppColors.radiusLg),
              border: Border.all(color: AppColors.borderDefault, width: 1),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('THEME VARIANT: DARK MINIMAL', style: AppTypography.titleMedium.copyWith(fontSize: 13)),
                    const SizedBox(height: 4),
                    Text(
                      'Reduces surface glow and uses matte neutral borders for high-focus sessions.',
                      style: AppTypography.caption.copyWith(color: AppColors.neutral400),
                    ),
                  ],
                ),
                Switch(
                  value: state.isMinimalTheme,
                  onChanged: (_) => state.toggleMinimalTheme(),
                  activeColor: AppColors.accentPrimary,
                  inactiveTrackColor: AppColors.surfaceBase,
                ),
              ],
            ),
          ),

          const SizedBox(height: 18),

          // 3. Screen-Share Invisibility & Cloaking
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surfaceRaised,
              borderRadius: BorderRadius.circular(AppColors.radiusLg),
              border: Border.all(
                color: state.isCloaked ? AppColors.semanticSuccess : AppColors.borderDefault,
                width: 1,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('SCREEN-SHARE INVISIBILITY (OPTION 3 ACTIVE)', style: AppTypography.titleMedium.copyWith(fontSize: 13)),
                    Switch(
                      value: state.isCloaked,
                      onChanged: (_) => state.toggleCloak(),
                      activeColor: AppColors.semanticSuccess,
                      inactiveTrackColor: AppColors.surfaceBase,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Physical Screen Isolation (Option 3): Runs as an independent OLED prompter on your phone or tablet on your desk, guaranteeing zero desktop compositor capture on Google Meet or Zoom.\n\n'
                  'Native X11 Interception Hook (Option 1): libstealthcloak.so intercepts XGetImage / XShmGetImage to exclude window pixels.',
                  style: AppTypography.caption.copyWith(color: AppColors.neutral400, height: 1.4),
                ),
              ],
            ),
          ),

          const SizedBox(height: 18),

          // 4. Granular 3-Tier Permission System & Tool Toggles (Section 10)
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surfaceRaised,
              borderRadius: BorderRadius.circular(AppColors.radiusLg),
              border: Border.all(color: AppColors.borderDefault, width: 1),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.shield_rounded, size: 16, color: AppColors.accentPrimary),
                    const SizedBox(width: 8),
                    Text(
                      'GRANULAR PERMISSION TIERS & TOOL ACCESS',
                      style: AppTypography.monoBadge.copyWith(
                        color: AppColors.neutral100,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceHighlight,
                        borderRadius: BorderRadius.circular(AppColors.radiusSm),
                        border: Border.all(color: AppColors.accentPrimaryMuted, width: 1),
                      ),
                      child: Text(
                        'MODE: ${state.permissionMode.toUpperCase()}',
                        style: AppTypography.monoBadge.copyWith(
                          color: AppColors.accentPrimary,
                          fontSize: 9,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  'Select the global safety tier. Dangerous commands and destructive actions are always gated regardless of the selected level.',
                  style: AppTypography.caption.copyWith(color: AppColors.neutral400),
                ),
                const SizedBox(height: 16),

                // 3-Tier Selector Buttons
                Row(
                  children: [
                    _buildTierButton(
                      context,
                      state,
                      title: 'Read-Only',
                      desc: 'Observation only. Terminal blocked.',
                      tierValue: 'read_only',
                      icon: Icons.visibility_rounded,
                      activeColor: AppColors.neutral300,
                    ),
                    const SizedBox(width: 10),
                    _buildTierButton(
                      context,
                      state,
                      title: 'Limited (Default)',
                      desc: 'Safe auto-run. Gate dangerous.',
                      tierValue: 'limited',
                      icon: Icons.lock_clock_rounded,
                      activeColor: AppColors.accentPrimary,
                    ),
                    const SizedBox(width: 10),
                    _buildTierButton(
                      context,
                      state,
                      title: 'Trusted',
                      desc: 'Full autonomy. Gated hazards.',
                      tierValue: 'trusted',
                      icon: Icons.verified_user_rounded,
                      activeColor: AppColors.semanticSuccess,
                    ),
                  ],
                ),

                const SizedBox(height: 20),
                const Divider(color: AppColors.borderDefault, height: 1),
                const SizedBox(height: 16),

                Text(
                  'SUBSYSTEM & TOOL ACCESS TOGGLES',
                  style: AppTypography.monoBadge.copyWith(
                    color: AppColors.neutral400,
                    fontSize: 10,
                  ),
                ),
                const SizedBox(height: 10),

                // Tool Switches Grid
                Wrap(
                  spacing: 12,
                  runSpacing: 10,
                  children: [
                    'filesystem',
                    'terminal',
                    'github',
                    'browser',
                    'google_workspace',
                    'n8n',
                  ].map((toolKey) {
                    final isEnabled = state.toolToggles[toolKey] ?? true;
                    return Container(
                      width: 250,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceBase,
                        borderRadius: BorderRadius.circular(AppColors.radiusMd),
                        border: Border.all(color: AppColors.borderDefault),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              toolKey.replaceAll('_', ' ').toUpperCase(),
                              style: AppTypography.monoBadge.copyWith(
                                color: isEnabled ? AppColors.neutral100 : AppColors.neutral500,
                                fontSize: 10,
                              ),
                            ),
                          ),
                          Switch(
                            value: isEnabled,
                            onChanged: (val) => state.setToolToggle(toolKey, val),
                            activeColor: AppColors.accentPrimary,
                            inactiveTrackColor: AppColors.surfaceHighlight,
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
              ],
            ),
          ),

          const SizedBox(height: 18),

          // 4. AI Provider Pipeline Details
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppColors.surfaceRaised,
              borderRadius: BorderRadius.circular(AppColors.radiusLg),
              border: Border.all(color: AppColors.borderDefault, width: 1),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('AI INFERENCE PIPELINE', style: AppTypography.titleMedium.copyWith(fontSize: 13)),
                const SizedBox(height: 12),
                _buildConfigItem('Primary Provider', 'Sarvam AI (sarvam-105b)'),
                _buildConfigItem('Local Fallback Provider', 'Ollama (Local CPU/GPU)'),
                _buildConfigItem('Cloud Fallback', 'Anthropic Claude 3.5 Sonnet'),
                _buildConfigItem('Keyring Storage', 'Linux SecretStorage (keyring)'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConfigItem(String key, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(
            width: 180,
            child: Text(key, style: AppTypography.caption.copyWith(color: AppColors.neutral400)),
          ),
          Expanded(
            child: Text(value, style: AppTypography.caption.copyWith(color: AppColors.neutral100, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }

  Widget _buildTierButton(
    BuildContext context,
    AppState state, {
    required String title,
    required String desc,
    required String tierValue,
    required IconData icon,
    required Color activeColor,
  }) {
    final isSelected = state.permissionMode == tierValue;

    return Expanded(
      child: InkWell(
        onTap: () => state.setPermissionMode(tierValue),
        borderRadius: BorderRadius.circular(AppColors.radiusMd),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.surfaceHighlight : AppColors.surfaceBase,
            borderRadius: BorderRadius.circular(AppColors.radiusMd),
            border: Border.all(
              color: isSelected ? activeColor : AppColors.borderDefault,
              width: isSelected ? 1.5 : 1.0,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, size: 16, color: isSelected ? activeColor : AppColors.neutral400),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      title,
                      style: AppTypography.bodySmall.copyWith(
                        color: isSelected ? AppColors.neutral100 : AppColors.neutral300,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                desc,
                style: AppTypography.caption.copyWith(
                  color: isSelected ? AppColors.neutral300 : AppColors.neutral500,
                  fontSize: 10,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
