import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../state/app_state.dart';
import 'screens/settings_screen.dart';
import 'widgets/skeleton_loader.dart';
import 'widgets/voice_visualizer_host.dart';
import 'widgets/terminal_approval_modal.dart';
import 'widgets/agent_canvas_view.dart';
import 'widgets/blockbrain_brand_icon.dart';
import 'widgets/inline_monaco_editor.dart';
import 'widgets/inline_terminal_view.dart';
import '../../services/editor_window_service.dart';

/// Primary Workspace Viewport & Conversational Platform for BlockBrain HUD.
/// Refactored for studio-grade visual polish:
/// - 0 emojis in UI chrome (vector icons only)
/// - Single disciplined color token system (AppColors)
/// - Deliberate typography hierarchy (AppTypography)
/// - Real-time Voice Animation Kit integration (9 styles)
/// - Shimmer skeleton loaders for async operations
/// - Strict physical surface elevations & radius hierarchy
class ChatPlatformScaffold extends StatefulWidget {
  const ChatPlatformScaffold({super.key});

  @override
  State<ChatPlatformScaffold> createState() => _ChatPlatformScaffoldState();
}

class _ChatPlatformScaffoldState extends State<ChatPlatformScaffold> {
  final TextEditingController _promptController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _showSlashPopup = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        EditorWindowService().registerAppState(context.read<AppState>());
      }
    });
  }

  @override
  void dispose() {
    _promptController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: AppColors.durationNormal,
          curve: AppColors.curveFast,
        );
      }
    });
  }

  void _sendMessage(AppState state) {
    final text = _promptController.text.trim();
    if (text.isNotEmpty || state.attachedScreenshotB64 != null) {
      _promptController.clear();
      setState(() => _showSlashPopup = false);
      state.sendMessage(text);
      _scrollToBottom();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return Scaffold(
      backgroundColor: AppColors.surfaceBase,
      body: Stack(
        children: [
          Container(
            color: AppColors.surfaceBase,
            child: Row(
              children: [
                // 1. LEFT SIDEBAR
                _buildSidebar(state),

                // 2. CENTER VIEWPORT
                Expanded(
                  child: Column(
                    children: [
                      // Top Navigation Bar
                      _buildTopBar(state),

                      // Center Viewport (Conversation or Settings)
                      Expanded(
                        child: state.activeMode == 'settings'
                            ? const SettingsScreen()
                            : Stack(
                                children: [
                                  // Conversation Scroll
                                  Positioned.fill(
                                    child: SingleChildScrollView(
                                      controller: _scrollController,
                                      padding: const EdgeInsets.fromLTRB(24, 20, 24, 140),
                                      child: Center(
                                        child: ConstrainedBox(
                                          constraints: const BoxConstraints(maxWidth: 820),
                                          child: state.isMessagesLoading
                                              ? _buildLoadingSkeleton()
                                              : (state.messages.isEmpty
                                                  ? _buildEmptyStateHero(state)
                                                  : _buildMessageList(state)),
                                        ),
                                      ),
                                    ),
                                  ),

                                  // Bottom Floating Composer
                                  Positioned(
                                    left: 24,
                                    right: 24,
                                    bottom: 16,
                                    child: Center(
                                      child: ConstrainedBox(
                                        constraints: const BoxConstraints(maxWidth: 820),
                                        child: _buildComposer(state),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                      ),
                    ],
                  ),
                ),

                // 3. RIGHT CANVAS / ARTIFACTS PANEL
                if (state.isRightPanelOpen) ...[
                  _buildRightPanelResizer(state),
                  _buildRightPanel(state),
                ],
              ],
            ),
          ),

          // 4. TERMINAL ACCESS / PERMISSION GATE MODAL OVERLAY
          if (state.pendingTerminalApproval != null)
            Positioned.fill(
              child: TerminalApprovalModal(
                approval: state.pendingTerminalApproval!,
              ),
            ),
        ],
      ),
    );
  }

  // ==============================================================================
  // 1. LEFT SIDEBAR (Level 1 Elevation)
  // ==============================================================================
  Widget _buildSidebar(AppState state) {
    final collapsed = state.isSidebarCollapsed;

    return AnimatedContainer(
      duration: AppColors.durationNormal,
      curve: AppColors.curveFast,
      width: collapsed ? 68 : 260,
      decoration: const BoxDecoration(
        color: AppColors.surfaceRaised,
        border: Border(
          right: BorderSide(color: AppColors.borderDefault, width: 1),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Branding Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            child: Row(
              children: [
                const BlockBrainBrandIcon(
                  size: 28,
                  showGlow: true,
                ),
                if (!collapsed) ...[
                  const SizedBox(width: 10),
                  Text(
                    'BLOCKBRAIN',
                    style: AppTypography.titleMedium.copyWith(
                      letterSpacing: 1.0,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
                const Spacer(),
                IconButton(
                  icon: Icon(
                    collapsed ? Icons.chevron_right_rounded : Icons.chevron_left_rounded,
                    size: 18,
                    color: AppColors.neutral400,
                  ),
                  tooltip: collapsed ? 'Expand Sidebar' : 'Collapse Sidebar',
                  onPressed: () => state.toggleSidebar(),
                ),
              ],
            ),
          ),

          // New Chat Button
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            child: InkWell(
              borderRadius: BorderRadius.circular(AppColors.radiusMd),
              onTap: () => state.startNewChat(),
              child: Container(
                padding: EdgeInsets.symmetric(
                  horizontal: collapsed ? 0 : 12,
                  vertical: 9,
                ),
                decoration: BoxDecoration(
                  color: AppColors.surfaceHighlight,
                  borderRadius: BorderRadius.circular(AppColors.radiusMd),
                  border: Border.all(color: AppColors.borderDefault, width: 1),
                ),
                child: Row(
                  mainAxisAlignment: collapsed ? MainAxisAlignment.center : MainAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.add_rounded,
                      size: 16,
                      color: AppColors.accentPrimary,
                    ),
                    if (!collapsed) ...[
                      const SizedBox(width: 8),
                      Text(
                        'New Session',
                        style: AppTypography.caption.copyWith(
                          color: AppColors.neutral100,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),

          const SizedBox(height: 8),

          // Session History Section Header
          if (!collapsed)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Text(
                'ACTIVE SESSIONS',
                style: AppTypography.monoBadge.copyWith(
                  color: AppColors.neutral500,
                ),
              ),
            ),

          // Chat History List
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              itemCount: state.conversations.length,
              itemBuilder: (context, idx) {
                final c = state.conversations[idx];
                final isSelected = idx == 0;

                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(AppColors.radiusSm),
                    onTap: () {
                      state.currentChatTitle = c['title'] ?? 'Session';
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                      decoration: BoxDecoration(
                        color: isSelected ? AppColors.accentPrimarySubtle : Colors.transparent,
                        borderRadius: BorderRadius.circular(AppColors.radiusSm),
                        border: isSelected
                            ? Border.all(color: AppColors.accentPrimaryMuted, width: 1)
                            : null,
                      ),
                      child: Row(
                        children: [
                          Icon(
                            Icons.chat_bubble_outline_rounded,
                            size: 14,
                            color: isSelected ? AppColors.accentPrimary : AppColors.neutral400,
                          ),
                          if (!collapsed) ...[
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                c['title'] ?? 'Session',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: AppTypography.caption.copyWith(
                                  color: isSelected ? AppColors.accentPrimary : AppColors.neutral200,
                                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          ),

          // Bottom Mode Switcher (Level 1 Surface)
          Container(
            padding: const EdgeInsets.all(8),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppColors.borderDefault, width: 1)),
            ),
            child: Column(
              children: [
                _buildModeItem(state, 'Chat Platform', Icons.chat_outlined, 'chat', collapsed),
                _buildModeItem(state, 'Stealth Copilot', Icons.visibility_outlined, 'copilot', collapsed),
                _buildModeItem(state, 'Tasks & Cron', Icons.task_alt_outlined, 'tasks', collapsed),
                _buildModeItem(state, 'Terminal Shell', Icons.terminal_rounded, 'terminal', collapsed),
                _buildEditorLauncherItem(state, collapsed),
                _buildModeItem(state, 'Memory Store', Icons.psychology_outlined, 'memory', collapsed),
                _buildModeItem(state, 'Voice & Settings', Icons.tune_rounded, 'settings', collapsed),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModeItem(AppState state, String label, IconData icon, String mode, bool collapsed) {
    final active = state.activeMode == mode;

    return InkWell(
      onTap: () => state.switchMode(mode),
      borderRadius: BorderRadius.circular(AppColors.radiusSm),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: active ? AppColors.accentPrimarySubtle : Colors.transparent,
          borderRadius: BorderRadius.circular(AppColors.radiusSm),
          border: active ? Border.all(color: AppColors.accentPrimaryMuted, width: 1) : null,
        ),
        child: Row(
          mainAxisAlignment: collapsed ? MainAxisAlignment.center : MainAxisAlignment.start,
          children: [
            Icon(
              icon,
              size: 15,
              color: active ? AppColors.accentPrimary : AppColors.neutral400,
            ),
            if (!collapsed) ...[
              const SizedBox(width: 10),
              Text(
                label,
                style: AppTypography.caption.copyWith(
                  color: active ? AppColors.accentPrimary : AppColors.neutral300,
                  fontWeight: active ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildEditorLauncherItem(AppState state, bool collapsed) {
    final active = state.isRightPanelOpen && state.activeRightTab == 'editor';

    return InkWell(
      onTap: () {
        state.switchRightTab('editor');
        EditorWindowService().openOrFocusEditor();
      },
      borderRadius: BorderRadius.circular(AppColors.radiusSm),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: active ? AppColors.accentPrimarySubtle : Colors.transparent,
          borderRadius: BorderRadius.circular(AppColors.radiusSm),
          border: active ? Border.all(color: AppColors.accentPrimaryMuted, width: 1) : null,
        ),
        child: Row(
          mainAxisAlignment: collapsed ? MainAxisAlignment.center : MainAxisAlignment.start,
          children: [
            const Icon(
              Icons.code_rounded,
              size: 15,
              color: AppColors.accentPrimary,
            ),
            if (!collapsed) ...[
              const SizedBox(width: 10),
              Text(
                'Code Studio',
                style: AppTypography.caption.copyWith(
                  color: AppColors.neutral200,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                decoration: BoxDecoration(
                  color: AppColors.accentPrimarySubtle,
                  borderRadius: BorderRadius.circular(3),
                  border: Border.all(color: AppColors.accentPrimaryMuted, width: 1),
                ),
                child: Text(
                  'MONACO',
                  style: AppTypography.monoBadge.copyWith(
                    fontSize: 9,
                    color: AppColors.accentPrimary,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  // ==============================================================================
  // 2. TOP NAVIGATION BAR (Disciplined Telemetry & Controls)
  // ==============================================================================
  Widget _buildTopBar(AppState state) {
    final sys = state.systemState;

    return Container(
      height: 52,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      decoration: const BoxDecoration(
        color: AppColors.surfaceRaised,
        border: Border(
          bottom: BorderSide(color: AppColors.borderDefault, width: 1),
        ),
      ),
      child: Row(
        children: [
          // Current Chat Title
          Flexible(
            child: Text(
              state.currentChatTitle,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.titleMedium.copyWith(
                color: AppColors.neutral100,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: 14),

          // Model Dropdown Pill
          PopupMenuButton<String>(
            color: AppColors.surfaceOverlay,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppColors.radiusMd),
              side: const BorderSide(color: AppColors.borderDefault, width: 1),
            ),
            initialValue: state.selectedModel,
            onSelected: (m) => state.selectModel(m),
            itemBuilder: (context) => [
              _buildModelMenuItem('Sarvam 105B', 'Primary local agentic model'),
              _buildModelMenuItem('DeepSeek R1', 'Low VRAM reasoning profile'),
              _buildModelMenuItem('Qwen 2.5 7B', 'High-speed desktop control'),
            ],
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: AppColors.surfaceHighlight,
                borderRadius: BorderRadius.circular(AppColors.radiusSm),
                border: Border.all(color: AppColors.borderDefault, width: 1),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    state.selectedModel,
                    style: AppTypography.caption.copyWith(
                      color: AppColors.accentPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Icon(
                    Icons.arrow_drop_down,
                    size: 14,
                    color: AppColors.neutral400,
                  ),
                ],
              ),
            ),
          ),

          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              reverse: true,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Invisibility Badge (Option 3 Physical Screen Isolation)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: AppColors.semanticSuccessSubtle,
                      borderRadius: BorderRadius.circular(AppColors.radiusSm),
                      border: Border.all(color: AppColors.semanticSuccess.withOpacity(0.4), width: 1),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.shield_outlined,
                          size: 13,
                          color: AppColors.semanticSuccess,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          'CLOAK: OPTION 3 READY',
                          style: AppTypography.monoBadge.copyWith(
                            color: AppColors.semanticSuccess,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Telemetry Gauge: RTX 3050 VRAM
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceHighlight,
                      borderRadius: BorderRadius.circular(AppColors.radiusSm),
                      border: Border.all(color: AppColors.borderDefault, width: 1),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'VRAM: ',
                          style: AppTypography.monoBadge.copyWith(color: AppColors.neutral400),
                        ),
                        Text(
                          '${sys.vramUsedMb.toInt()} / ${sys.vramTotalMb.toInt()} MB',
                          style: AppTypography.monoMetrics,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Single-Click Red Panic Kill Button (Deliberate high-visibility emergency control)
                  MouseRegion(
                    cursor: SystemMouseCursors.click,
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: () => state.triggerPanic(),
                      child: Container(
                        height: 30,
                        padding: const EdgeInsets.symmetric(horizontal: 10),
                        decoration: BoxDecoration(
                          color: AppColors.semanticDangerMuted,
                          borderRadius: BorderRadius.circular(AppColors.radiusSm),
                          border: Border.all(color: AppColors.semanticDanger, width: 1.2),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.semanticDanger.withOpacity(0.25),
                              blurRadius: 6,
                              spreadRadius: 0,
                            ),
                          ],
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.emergency_rounded, size: 14, color: AppColors.semanticDanger),
                            const SizedBox(width: 6),
                            Text(
                              'PANIC KILL',
                              style: AppTypography.monoBadge.copyWith(
                                color: AppColors.neutral100,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 0.8,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Code Studio Launcher Button
                  MouseRegion(
                    cursor: SystemMouseCursors.click,
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: () {
                        state.toggleRightPanel(true);
                        state.switchRightTab('editor');
                        EditorWindowService().openOrFocusEditor();
                      },
                      child: Container(
                        height: 30,
                        padding: const EdgeInsets.symmetric(horizontal: 10),
                        decoration: BoxDecoration(
                          color: (state.isRightPanelOpen && state.activeRightTab == 'editor')
                              ? AppColors.accentPrimary.withOpacity(0.15)
                              : AppColors.surfaceHighlight,
                          borderRadius: BorderRadius.circular(AppColors.radiusSm),
                          border: Border.all(
                            color: (state.isRightPanelOpen && state.activeRightTab == 'editor')
                                ? AppColors.accentPrimary
                                : AppColors.accentPrimaryMuted,
                            width: 1,
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.code_rounded, size: 14, color: AppColors.accentPrimary),
                            const SizedBox(width: 6),
                            Text(
                              'CODE STUDIO',
                              style: AppTypography.monoBadge.copyWith(
                                color: AppColors.accentPrimary,
                                letterSpacing: 0.6,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),

                  // Right Canvas / Copilot Toggle
                  IconButton(
                    icon: Icon(
                      Icons.view_sidebar_outlined,
                      size: 18,
                      color: state.isRightPanelOpen ? AppColors.accentPrimary : AppColors.neutral400,
                    ),
                    tooltip: 'Toggle Canvas / Copilot',
                    onPressed: () => state.toggleRightPanel(),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  PopupMenuItem<String> _buildModelMenuItem(String title, String subtitle) {
    return PopupMenuItem<String>(
      value: title,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppTypography.caption.copyWith(color: AppColors.neutral100, fontWeight: FontWeight.bold)),
          const SizedBox(height: 2),
          Text(subtitle, style: AppTypography.caption.copyWith(color: AppColors.neutral500, fontSize: 10)),
        ],
      ),
    );
  }

  // ==============================================================================
  // 3. CENTER CONVERSATION AREA
  // ==============================================================================
  Widget _buildEmptyStateHero(AppState state) {
    return Column(
      children: [
        const SizedBox(height: 36),

        // Live Voice Animation Kit Host (Part 4 Integration)
        MouseRegion(
          cursor: SystemMouseCursors.click,
          child: GestureDetector(
            onTap: () {
              // Toggle live voice listening mode or solve screen
              state.setVoiceActive(!state.isVoiceActive);
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              decoration: BoxDecoration(
                color: AppColors.surfaceRaised,
                borderRadius: BorderRadius.circular(AppColors.radiusXl),
                border: Border.all(
                  color: state.isVoiceActive ? AppColors.accentPrimary : AppColors.borderDefault,
                  width: 1,
                ),
              ),
              child: Column(
                children: [
                  VoiceVisualizerHost(
                    style: state.voiceStyle,
                    isRecording: true,
                    amplitude: state.isVoiceActive ? 0.85 : 0.35,
                    size: 96,
                    primaryColor: AppColors.accentPrimary,
                    secondaryColor: AppColors.accentSecondary,
                  ),
                  const SizedBox(height: 10),
                  Text(
                    state.isVoiceActive
                        ? 'LISTENING ACTIVE • TAP TO PAUSE'
                        : '${state.voiceStyle.displayName.toUpperCase()} • TAP FOR VOICE',
                    style: AppTypography.monoBadge.copyWith(
                      color: state.isVoiceActive ? AppColors.accentPrimary : AppColors.neutral500,
                      letterSpacing: 0.8,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),

        const SizedBox(height: 24),
        Text(
          'Workspace AI Control Center',
          style: AppTypography.displayLarge,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        Text(
          'Private screen context extraction, scheduled task automation, and neural copilot.',
          textAlign: TextAlign.center,
          style: AppTypography.bodySmall.copyWith(color: AppColors.neutral400),
        ),
        const SizedBox(height: 28),

        // 4 Starter Cards (Adaptive grid to prevent overflow on resize)
        LayoutBuilder(
          builder: (context, constraints) {
            final isNarrow = constraints.maxWidth < 460;
            final card1 = _buildStarterCard(
              icon: Icons.screenshot_monitor_outlined,
              title: 'Screen Context Solver',
              desc: 'Analyze active window, extract technical questions, and formulate solutions.',
              onTap: () => state.triggerStealthSolve(),
            );
            final card2 = _buildStarterCard(
              icon: Icons.schedule_outlined,
              title: 'Scheduled Automation',
              desc: 'Dispatch background cron jobs, water breaks, and persistent SQLite alarms.',
              onTap: () {
                _promptController.text = 'Schedule task: in 15 minutes remind me to commit changes';
                _sendMessage(state);
              },
            );
            final card3 = _buildStarterCard(
              icon: Icons.headset_mic_outlined,
              title: 'Whisper Channel',
              desc: 'Relay synthesized answers directly to Bluetooth earpiece without meeting leak.',
              onTap: () => state.toggleWhisper(),
            );
            final card4 = _buildStarterCard(
              icon: Icons.memory_outlined,
              title: 'Hardware Diagnostics',
              desc: 'Inspect audio gain, faster-whisper STT, Piper TTS, and RTX 3050 VRAM load.',
              onTap: () {
                _promptController.text = 'Run hardware doctor diagnostics';
                _sendMessage(state);
              },
            );

            if (isNarrow) {
              return Column(
                children: [
                  card1,
                  const SizedBox(height: 10),
                  card2,
                  const SizedBox(height: 10),
                  card3,
                  const SizedBox(height: 10),
                  card4,
                ],
              );
            }

            return Column(
              children: [
                Row(
                  children: [
                    Expanded(child: card1),
                    const SizedBox(width: 12),
                    Expanded(child: card2),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(child: card3),
                    const SizedBox(width: 12),
                    Expanded(child: card4),
                  ],
                ),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildStarterCard({
    required IconData icon,
    required String title,
    required String desc,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppColors.radiusLg),
      child: Container(
        padding: const EdgeInsets.all(16),
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
                Icon(icon, size: 16, color: AppColors.accentPrimary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.caption.copyWith(
                      color: AppColors.neutral100,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              desc,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.neutral400,
                height: 1.35,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingSkeleton() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: const [
        SizedBox(height: 24),
        SkeletonLoader(width: 220, height: 48),
        SizedBox(height: 16),
        SkeletonLoader(width: double.infinity, height: 110),
        SizedBox(height: 16),
        SkeletonLoader(width: 380, height: 72),
      ],
    );
  }

  Widget _buildMessageList(AppState state) {
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: state.messages.length,
      itemBuilder: (context, idx) {
        final m = state.messages[idx];
        final isUser = m.role == 'user';

        if (isUser) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Flexible(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceHighlight,
                      border: Border.all(color: AppColors.borderDefault, width: 1),
                      borderRadius: const BorderRadius.only(
                        topLeft: Radius.circular(AppColors.radiusLg),
                        topRight: Radius.circular(AppColors.radiusLg),
                        bottomLeft: Radius.circular(AppColors.radiusLg),
                        bottomRight: Radius.circular(AppColors.radiusSm),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        if (m.attachmentB64 != null) ...[
                          ClipRRect(
                            borderRadius: BorderRadius.circular(AppColors.radiusSm),
                            child: Image.memory(
                              base64Decode(m.attachmentB64!.split(',').last),
                              height: 140,
                              fit: BoxFit.cover,
                            ),
                          ),
                          const SizedBox(height: 8),
                        ],
                        Text(
                          m.text,
                          style: AppTypography.bodyMedium.copyWith(color: AppColors.neutral100),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          );
        } else {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const BlockBrainBrandIcon(
                      size: 20,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'BLOCKBRAIN',
                      style: AppTypography.monoBadge.copyWith(
                        color: AppColors.accentPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      m.time,
                      style: AppTypography.caption.copyWith(color: AppColors.neutral500, fontSize: 10),
                    ),
                  ],
                ),
                const SizedBox(height: 8),

                // Tool Card if present
                if (m.toolName != null)
                  Container(
                    margin: const EdgeInsets.only(left: 28, bottom: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceRaised,
                      borderRadius: BorderRadius.circular(AppColors.radiusSm),
                      border: Border.all(color: AppColors.borderDefault, width: 1),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.settings_input_component_outlined, color: AppColors.accentPrimary, size: 14),
                        const SizedBox(width: 6),
                        Text(
                          '${m.toolName}: ${m.toolDesc}',
                          style: AppTypography.caption.copyWith(color: AppColors.neutral300),
                        ),
                      ],
                    ),
                  ),

                // Assistant Message Body
                Padding(
                  padding: const EdgeInsets.only(left: 28),
                  child: SelectableText(
                    m.text,
                    style: AppTypography.bodyMedium.copyWith(height: 1.5),
                  ),
                ),
                const SizedBox(height: 4),

                // Action controls
                Padding(
                  padding: const EdgeInsets.only(left: 28),
                  child: Row(
                    children: [
                      IconButton(
                        icon: const Icon(Icons.content_copy_rounded, size: 13, color: AppColors.neutral400),
                        tooltip: 'Copy reply',
                        onPressed: () => Clipboard.setData(ClipboardData(text: m.text)),
                      ),
                      IconButton(
                        icon: const Icon(Icons.volume_up_outlined, size: 14, color: AppColors.neutral400),
                        tooltip: 'Read aloud',
                        onPressed: () => state.api.sendChat(m.text),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        }
      },
    );
  }

  // ==============================================================================
  // 4. BOTTOM COMPOSER (Level 2 Elevation with Focused Input)
  // ==============================================================================
  Widget _buildComposer(AppState state) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Slash Command Suggestions
        if (_showSlashPopup)
          Container(
            margin: const EdgeInsets.only(bottom: 6),
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: AppColors.surfaceOverlay,
              borderRadius: BorderRadius.circular(AppColors.radiusMd),
              border: Border.all(color: AppColors.borderDefault, width: 1),
            ),
            child: Column(
              children: [
                _buildSlashRow('/screen', 'Capture active screen context for analysis', () {
                  _promptController.text = '/screen';
                  setState(() => _showSlashPopup = false);
                }),
                _buildSlashRow('/task ', 'Schedule future task ("in 15m water break")', () {
                  _promptController.text = '/task ';
                  setState(() => _showSlashPopup = false);
                }),
                _buildSlashRow('/terminal ', 'Run bash shell command directly', () {
                  _promptController.text = '/terminal ';
                  setState(() => _showSlashPopup = false);
                }),
                _buildSlashRow('/cloak', 'Toggle Option 3 off-screen stealth mode', () {
                  _promptController.text = '/cloak';
                  setState(() => _showSlashPopup = false);
                }),
              ],
            ),
          ),

        // Attachment Preview
        if (state.attachedScreenshotB64 != null)
          Container(
            margin: const EdgeInsets.only(bottom: 6),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.surfaceRaised,
              borderRadius: BorderRadius.circular(AppColors.radiusSm),
              border: Border.all(color: AppColors.borderDefault, width: 1),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: Image.memory(
                    base64Decode(state.attachedScreenshotB64!.split(',').last),
                    width: 32,
                    height: 24,
                    fit: BoxFit.cover,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  'Screen context attached',
                  style: AppTypography.caption.copyWith(color: AppColors.neutral200),
                ),
                const SizedBox(width: 6),
                InkWell(
                  onTap: () => state.clearAttachment(),
                  child: const Icon(Icons.close_rounded, size: 14, color: AppColors.neutral400),
                ),
              ],
            ),
          ),

        // Input Field Box
        Container(
          padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
          decoration: BoxDecoration(
            color: AppColors.surfaceOverlay,
            borderRadius: BorderRadius.circular(AppColors.radiusLg),
            border: Border.all(color: AppColors.borderDefault, width: 1),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: _promptController,
                maxLines: 4,
                minLines: 1,
                style: AppTypography.bodyMedium.copyWith(color: AppColors.neutral100),
                decoration: InputDecoration(
                  hintText: 'Ask BlockBrain anything, type / for commands, or speak...',
                  hintStyle: AppTypography.bodyMedium.copyWith(color: AppColors.neutral500),
                  border: InputBorder.none,
                  isDense: true,
                  contentPadding: EdgeInsets.zero,
                ),
                onChanged: (val) {
                  if (val.startsWith('/') && !_showSlashPopup) {
                    setState(() => _showSlashPopup = true);
                  } else if (!val.startsWith('/') && _showSlashPopup) {
                    setState(() => _showSlashPopup = false);
                  }
                },
                onSubmitted: (_) => _sendMessage(state),
              ),
              const SizedBox(height: 8),

              // Action Toolbar
              Row(
                children: [
                  // Attach Screen Button
                  IconButton(
                    icon: const Icon(Icons.screenshot_monitor_outlined, size: 17, color: AppColors.neutral400),
                    tooltip: 'Attach active screen reflection',
                    onPressed: () => state.attachScreen(),
                  ),

                  // Mic Audio Button with Voice Animation indicator
                  IconButton(
                    icon: Icon(
                      state.isVoiceActive ? Icons.mic_rounded : Icons.mic_none_rounded,
                      size: 17,
                      color: state.isVoiceActive ? AppColors.accentPrimary : AppColors.neutral400,
                    ),
                    tooltip: state.isVoiceActive ? 'Voice active' : 'Start voice mode',
                    onPressed: () => state.setVoiceActive(!state.isVoiceActive),
                  ),

                  const Spacer(),

                  // Send Action Pill
                  InkWell(
                    borderRadius: BorderRadius.circular(AppColors.radiusXl),
                    onTap: () => _sendMessage(state),
                    child: Container(
                      width: 32,
                      height: 32,
                      decoration: const BoxDecoration(
                        color: AppColors.accentPrimary,
                        shape: BoxShape.circle,
                      ),
                      child: const Center(
                        child: Icon(Icons.arrow_upward_rounded, size: 18, color: AppColors.surfaceBase),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSlashRow(String cmd, String desc, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppColors.radiusSm),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 5, horizontal: 8),
        child: Row(
          children: [
            Text(
              cmd,
              style: AppTypography.monoMetrics.copyWith(
                color: AppColors.accentPrimary,
                fontSize: 11,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              desc,
              style: AppTypography.caption.copyWith(color: AppColors.neutral400),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRightPanelResizer(AppState state) {
    return MouseRegion(
      cursor: SystemMouseCursors.resizeColumn,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onHorizontalDragStart: (_) {
          state.startDraggingRightPanel();
        },
        onHorizontalDragUpdate: (details) {
          final screenWidth = MediaQuery.of(context).size.width;
          final sidebarWidth = state.isSidebarCollapsed ? 68.0 : 260.0;
          final maxAllowed = (screenWidth - sidebarWidth - 440.0).clamp(320.0, 1200.0);
          state.updateRightPanelWidth(details.delta.dx, maxAllowed);
        },
        onHorizontalDragEnd: (_) {
          state.stopDraggingRightPanel();
        },
        onHorizontalDragCancel: () {
          state.stopDraggingRightPanel();
        },
        child: Container(
          width: 10,
          color: state.isDraggingRightPanel
              ? AppColors.accentPrimary.withOpacity(0.3)
              : Colors.transparent,
          child: Center(
            child: Container(
              width: 2,
              height: 36,
              decoration: BoxDecoration(
                color: state.isDraggingRightPanel
                    ? AppColors.accentPrimary
                    : AppColors.borderDefault,
                borderRadius: BorderRadius.circular(1),
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ==============================================================================
  // 5. RIGHT CANVAS PANEL (Level 2 Elevation with Tabs & Resizing)
  // ==============================================================================
  Widget _buildRightPanel(AppState state) {
    final screenWidth = MediaQuery.of(context).size.width;
    final sidebarWidth = state.isSidebarCollapsed ? 68.0 : 260.0;
    final maxAllowed = (screenWidth - sidebarWidth - 440.0).clamp(320.0, 1200.0);
    final effectiveWidth = state.effectiveRightPanelWidth.clamp(320.0, maxAllowed);

    final isEditor = state.activeRightTab == 'editor';
    final isTerminal = state.activeRightTab == 'terminal';

    return AnimatedContainer(
      duration: state.isDraggingRightPanel ? Duration.zero : AppColors.durationNormal,
      curve: AppColors.curveFast,
      width: effectiveWidth,
      decoration: const BoxDecoration(
        color: AppColors.surfaceOverlay,
        border: Border(left: BorderSide(color: AppColors.borderDefault, width: 1)),
      ),
      child: Column(
        children: [
          // Header Tabs (standard 28px height tabs with icons & glow)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            child: Row(
              children: [
                _buildRightTabBtn(state, 'Copilot', 'copilot', Icons.auto_awesome_rounded),
                const SizedBox(width: 4),
                _buildRightTabBtn(state, 'Canvas', 'canvas', Icons.art_track_rounded),
                const SizedBox(width: 4),
                _buildRightTabBtn(state, 'Editor', 'editor', Icons.code_rounded),
                const SizedBox(width: 4),
                _buildRightTabBtn(state, 'Terminal', 'terminal', Icons.terminal_rounded),
                const SizedBox(width: 4),
                _buildRightTabBtn(state, 'Tasks', 'tasks', Icons.checklist_rounded),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 16, color: AppColors.neutral400),
                  onPressed: () => state.toggleRightPanel(false),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  splashRadius: 14,
                ),
              ],
            ),
          ),

          // Tab Content
          Expanded(
            child: isEditor
                ? const Padding(
                    padding: EdgeInsets.fromLTRB(12, 0, 12, 12),
                    child: InlineMonacoEditor(),
                  )
                : (isTerminal
                    ? const Padding(
                        padding: EdgeInsets.fromLTRB(12, 0, 12, 12),
                        child: InlineTerminalView(),
                      )
                    : SingleChildScrollView(
                        padding: const EdgeInsets.all(14),
                        child: state.activeRightTab == 'copilot'
                            ? _buildCopilotTab(state)
                            : (state.activeRightTab == 'canvas'
                                ? const AgentCanvasView()
                                : _buildTasksTab(state)),
                      )),
          ),
        ],
      ),
    );
  }

  Widget _buildRightTabBtn(AppState state, String label, String tab, IconData icon) {
    final active = state.activeRightTab == tab;

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => state.switchRightTab(tab),
        child: Container(
          height: 28,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(
            color: active ? AppColors.accentPrimary : AppColors.surfaceHighlight,
            borderRadius: BorderRadius.circular(AppColors.radiusSm),
            border: Border.all(
              color: active ? AppColors.accentPrimary : AppColors.borderDefault,
              width: 1,
            ),
            boxShadow: active
                ? [
                    BoxShadow(
                      color: AppColors.accentPrimary.withOpacity(0.3),
                      blurRadius: 6,
                      spreadRadius: 0,
                    )
                  ]
                : null,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 13,
                color: active ? AppColors.surfaceBase : AppColors.neutral300,
              ),
              const SizedBox(width: 5),
              Text(
                label,
                style: AppTypography.caption.copyWith(
                  color: active ? AppColors.surfaceBase : AppColors.neutral300,
                  fontWeight: FontWeight.w600,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCopilotTab(AppState state) {
    final sol = state.stealthSolution;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Option 3 Prompter Card
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.surfaceRaised,
            border: Border.all(color: AppColors.borderDefault, width: 1),
            borderRadius: BorderRadius.circular(AppColors.radiusMd),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.phone_android_rounded, color: AppColors.accentPrimary, size: 14),
                  const SizedBox(width: 6),
                  Text(
                    'OPTION 3: PHYSICAL OLED PROMPTER',
                    style: AppTypography.monoBadge.copyWith(
                      color: AppColors.accentPrimary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                'Open on secondary phone or tablet placed on desk. 100% invisible to Google Meet desktop stream.',
                style: AppTypography.caption.copyWith(color: AppColors.neutral400, height: 1.35),
              ),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.surfaceBase,
                  borderRadius: BorderRadius.circular(AppColors.radiusSm),
                  border: Border.all(color: AppColors.borderDefault, width: 1),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('http://127.0.0.1:8844/stealth', style: AppTypography.monoCode.copyWith(fontSize: 10)),
                    IconButton(
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                      icon: const Icon(Icons.content_copy_rounded, size: 12, color: AppColors.accentPrimary),
                      onPressed: () {
                        Clipboard.setData(const ClipboardData(text: 'http://127.0.0.1:8844/stealth'));
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Option 3 Prompter URL Copied')),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 16),
        Text('ACTIVE SCREEN QUESTION', style: AppTypography.monoBadge.copyWith(color: AppColors.neutral400)),
        const SizedBox(height: 6),
        Text(sol.question, style: AppTypography.bodySmall.copyWith(color: AppColors.neutral200)),

        const SizedBox(height: 14),
        Row(
          children: [
            const Icon(Icons.record_voice_over_outlined, size: 13, color: AppColors.semanticSuccess),
            const SizedBox(width: 6),
            Text('TALKING POINTS', style: AppTypography.monoBadge.copyWith(color: AppColors.semanticSuccess)),
          ],
        ),
        const SizedBox(height: 6),
        Text(sol.talkingPoints, style: AppTypography.bodySmall.copyWith(color: AppColors.neutral200)),

        const SizedBox(height: 14),
        Row(
          children: [
            const Icon(Icons.code_rounded, size: 13, color: AppColors.accentPrimary),
            const SizedBox(width: 6),
            Text('SOLUTION IMPLEMENTATION', style: AppTypography.monoBadge.copyWith(color: AppColors.accentPrimary)),
          ],
        ),
        const SizedBox(height: 6),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.surfaceBase,
            borderRadius: BorderRadius.circular(AppColors.radiusSm),
            border: Border.all(color: AppColors.borderDefault, width: 1),
          ),
          child: SelectableText(
            sol.code,
            style: AppTypography.monoCode.copyWith(fontSize: 11),
          ),
        ),
      ],
    );
  }


  Widget _buildTasksTab(AppState state) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('SCHEDULED ROUTINES', style: AppTypography.monoBadge.copyWith(color: AppColors.neutral400)),
        const SizedBox(height: 8),
        if (state.tasks.isEmpty)
          Text('No active scheduled routines.', style: AppTypography.bodySmall.copyWith(color: AppColors.neutral500))
        else
          ...state.tasks.map(
            (t) => Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.surfaceRaised,
                borderRadius: BorderRadius.circular(AppColors.radiusSm),
                border: Border.all(color: AppColors.borderDefault, width: 1),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(t.description, style: AppTypography.caption.copyWith(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Text('Next: ${t.nextRunAt}', style: AppTypography.monoBadge.copyWith(color: AppColors.neutral500)),
                ],
              ),
            ),
          ),
      ],
    );
  }
}
