import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../state/app_state.dart';
import 'voice_visualizer_host.dart';

/// Section 7: Agent's Own Canvas
/// Dedicated visual surface inside the BlockBrain HUD for:
/// 1. Implementation Plan & Live Todo Tracking (Pending / In-Progress / Completed).
/// 2. Live Animation Preview (VoiceVisualizerHost).
/// 3. Architecture & Security System Overview.
class AgentCanvasView extends StatefulWidget {
  const AgentCanvasView({super.key});

  @override
  State<AgentCanvasView> createState() => _AgentCanvasViewState();
}

class _AgentCanvasViewState extends State<AgentCanvasView> {
  // Built-in reactive plan tracker
  final List<Map<String, dynamic>> _planTasks = [
    {
      'title': 'Audit & Architecture Hardening',
      'desc': 'Audit tiers.py, shell.py, and setup SHA-256 Merkle audit chaining',
      'status': 'completed',
    },
    {
      'title': 'Zero Self-Approval Nonce Gate',
      'desc': '256-bit cryptographic nonces with strict Allow Always exact matching',
      'status': 'completed',
    },
    {
      'title': 'Threading & Event Loop Bridge',
      'desc': 'asyncio.to_thread offload with threadsafe WebSocket event bridge',
      'status': 'completed',
    },
    {
      'title': 'Terminal Access Modal & Visual Surface',
      'desc': 'Monospace un-truncated command viewer with crimson hazard banner',
      'status': 'in_progress',
    },
    {
      'title': 'Granular 3-Tier Permissions UI',
      'desc': 'Read-Only / Limited / Trusted selectors with per-tool MCP switches',
      'status': 'pending',
    },
    {
      'title': 'Full End-to-End Build & Self-Verification',
      'desc': '11 automated unit tests + flutter analyze + screenshot capture',
      'status': 'pending',
    },
  ];

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Canvas Header
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.surfaceRaised,
            borderRadius: BorderRadius.circular(AppColors.radiusMd),
            border: Border.all(color: AppColors.borderDefault, width: 1),
          ),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: AppColors.accentPrimarySubtle,
                  borderRadius: BorderRadius.circular(AppColors.radiusSm),
                ),
                child: const Icon(Icons.dashboard_customize_rounded, size: 16, color: AppColors.accentPrimary),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'AGENT CANVAS & EXECUTION SURFACE',
                      style: AppTypography.monoBadge.copyWith(
                        color: AppColors.neutral100,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Live plan tracking, architecture status, and voice animation studio',
                      style: AppTypography.caption.copyWith(color: AppColors.neutral400),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.surfaceHighlight,
                  borderRadius: BorderRadius.circular(AppColors.radiusSm),
                  border: Border.all(color: AppColors.accentPrimaryMuted, width: 1),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: AppColors.semanticSuccess,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'LIVE SYNC',
                      style: AppTypography.monoBadge.copyWith(
                        color: AppColors.neutral200,
                        fontSize: 9,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 14),

        // Live Animation Studio Preview Card
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.surfaceRaised,
            borderRadius: BorderRadius.circular(AppColors.radiusMd),
            border: Border.all(color: AppColors.borderDefault, width: 1),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.graphic_eq_rounded, size: 15, color: AppColors.accentPrimary),
                  const SizedBox(width: 8),
                  Text(
                    'LIVE VOICE ANIMATION PREVIEW',
                    style: AppTypography.monoBadge.copyWith(
                      color: AppColors.neutral100,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    state.voiceStyle.name.toUpperCase(),
                    style: AppTypography.monoBadge.copyWith(
                      color: AppColors.accentPrimary,
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Container(
                height: 100,
                decoration: BoxDecoration(
                  color: AppColors.surfaceBase,
                  borderRadius: BorderRadius.circular(AppColors.radiusSm),
                  border: Border.all(color: AppColors.borderDefault),
                ),
                child: Center(
                  child: VoiceVisualizerHost(
                    style: state.voiceStyle,
                    isRecording: true,
                    amplitude: 0.65,
                    size: 80,
                  ),
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 14),

        // Implementation Plan & Todo Tracking Section
        Text(
          'IMPLEMENTATION PLAN & TASK PIPELINE',
          style: AppTypography.monoBadge.copyWith(
            color: AppColors.neutral400,
            fontSize: 10,
          ),
        ),
        const SizedBox(height: 8),

        ..._planTasks.map((task) => _buildTaskItem(task)),
      ],
    );
  }

  Widget _buildTaskItem(Map<String, dynamic> task) {
    final status = task['status'] as String;
    Color statusColor;
    IconData statusIcon;
    String statusLabel;

    if (status == 'completed') {
      statusColor = AppColors.semanticSuccess;
      statusIcon = Icons.check_circle_rounded;
      statusLabel = 'DONE';
    } else if (status == 'in_progress') {
      statusColor = AppColors.accentPrimary;
      statusIcon = Icons.hourglass_top_rounded;
      statusLabel = 'ACTIVE';
    } else {
      statusColor = AppColors.neutral500;
      statusIcon = Icons.radio_button_unchecked_rounded;
      statusLabel = 'QUEUED';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceRaised,
        borderRadius: BorderRadius.circular(AppColors.radiusMd),
        border: Border.all(
          color: status == 'in_progress' ? AppColors.accentPrimaryMuted : AppColors.borderDefault,
          width: 1,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(statusIcon, size: 16, color: statusColor),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  task['title'] as String,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutral100,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  task['desc'] as String,
                  style: AppTypography.caption.copyWith(color: AppColors.neutral400),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: statusColor.withOpacity(0.12),
              borderRadius: BorderRadius.circular(AppColors.radiusSm),
              border: Border.all(color: statusColor.withOpacity(0.3), width: 1),
            ),
            child: Text(
              statusLabel,
              style: AppTypography.monoBadge.copyWith(
                color: statusColor,
                fontSize: 9,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
