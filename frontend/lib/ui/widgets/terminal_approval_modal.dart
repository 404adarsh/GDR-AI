import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../state/app_state.dart';

/// Modal dialog presented when a terminal command or critical tool execution requires human approval.
///
/// Features:
/// 1. Un-truncated monospace command viewer with copy-to-clipboard.
/// 2. High-contrast crimson hazard banner for dangerous commands with the detected reason.
/// 3. Allow Once (primary), Allow Always (exact-match, disabled on danger), and Deny.
/// 4. Zero Self-Approval cryptographic nonce handling via AppState.
class TerminalApprovalModal extends StatelessWidget {
  final Map<String, dynamic> approval;

  const TerminalApprovalModal({
    super.key,
    required this.approval,
  });

  @override
  Widget build(BuildContext context) {
    final state = context.read<AppState>();
    final cmd = approval['command'] as String? ?? '';
    final isDangerous = approval['is_dangerous'] == true;
    final dangerReason = approval['danger_reason'] as String? ?? 'Dangerous OS operation detected';
    final approvalId = approval['id'] as String? ?? '';

    return Material(
      color: Colors.black54,
      child: Center(
        child: Container(
          width: 620,
          margin: const EdgeInsets.symmetric(horizontal: 24),
          decoration: BoxDecoration(
            color: AppColors.surfaceRaised,
            borderRadius: BorderRadius.circular(AppColors.radiusLg),
            border: Border.all(
              color: isDangerous ? AppColors.semanticDanger : AppColors.accentPrimaryMuted,
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: (isDangerous ? AppColors.semanticDanger : AppColors.accentPrimary)
                    .withOpacity(0.18),
                blurRadius: 36,
                spreadRadius: 2,
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                decoration: BoxDecoration(
                  color: isDangerous
                      ? AppColors.semanticDangerMuted
                      : AppColors.surfaceHighlight,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(AppColors.radiusLg),
                    topRight: Radius.circular(AppColors.radiusLg),
                  ),
                  border: Border(
                    bottom: BorderSide(
                      color: isDangerous
                          ? AppColors.semanticDanger.withOpacity(0.3)
                          : AppColors.borderDefault,
                    ),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      isDangerous
                          ? Icons.warning_amber_rounded
                          : Icons.security_rounded,
                      size: 20,
                      color: isDangerous ? AppColors.semanticDanger : AppColors.accentPrimary,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            isDangerous
                                ? 'SECURITY HAZARD: DANGEROUS COMMAND DETECTED'
                                : 'TERMINAL ACCESS APPROVAL REQUIRED',
                            style: AppTypography.monoBadge.copyWith(
                              color: isDangerous ? AppColors.semanticDanger : AppColors.neutral100,
                              fontWeight: FontWeight.bold,
                              fontSize: 11,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'Gate ID: $approvalId • Zero Self-Approval Nonce Active',
                            style: AppTypography.caption.copyWith(color: AppColors.neutral400),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Crimson Hazard Banner for dangerous commands
                    if (isDangerous) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.semanticDanger.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(AppColors.radiusMd),
                          border: Border.all(
                            color: AppColors.semanticDanger.withOpacity(0.4),
                            width: 1,
                          ),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              Icons.gpp_bad_rounded,
                              size: 18,
                              color: AppColors.semanticDanger,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                dangerReason,
                                style: AppTypography.bodySmall.copyWith(
                                  color: AppColors.semanticDanger,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],

                    Text(
                      'COMMAND TO EXECUTE:',
                      style: AppTypography.monoBadge.copyWith(
                        color: AppColors.neutral400,
                        fontSize: 10,
                      ),
                    ),
                    const SizedBox(height: 8),

                    // Un-truncated Monospace Command Viewer
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceBase,
                        borderRadius: BorderRadius.circular(AppColors.radiusMd),
                        border: Border.all(color: AppColors.borderDefault, width: 1),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            children: [
                              Text(
                                '\$ (bash / sh)',
                                style: AppTypography.monoCode.copyWith(
                                  color: AppColors.neutral500,
                                  fontSize: 11,
                                ),
                              ),
                              const Spacer(),
                              InkWell(
                                onTap: () {
                                  Clipboard.setData(ClipboardData(text: cmd));
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text('Command copied to clipboard'),
                                      duration: Duration(seconds: 2),
                                    ),
                                  );
                                },
                                borderRadius: BorderRadius.circular(AppColors.radiusSm),
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  child: Row(
                                    children: [
                                      const Icon(Icons.copy_rounded, size: 13, color: AppColors.neutral400),
                                      const SizedBox(width: 4),
                                      Text(
                                        'COPY',
                                        style: AppTypography.monoBadge.copyWith(
                                          color: AppColors.neutral400,
                                          fontSize: 9,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          SelectableText(
                            cmd,
                            style: AppTypography.monoCode.copyWith(
                              color: isDangerous ? AppColors.semanticDanger : AppColors.accentPrimary,
                              fontSize: 13,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 24),

                    // Actions Bar: Allow Once, Allow Always (if safe), Deny
                    Row(
                      children: [
                        // Deny button
                        OutlinedButton.icon(
                          onPressed: () => state.resolvePendingTerminalApproval('deny'),
                          icon: Icon(Icons.close_rounded, size: 16, color: AppColors.semanticDanger),
                          label: Text(
                            'Deny',
                            style: AppTypography.bodySmall.copyWith(
                              color: AppColors.semanticDanger,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          style: OutlinedButton.styleFrom(
                            side: BorderSide(color: AppColors.semanticDanger, width: 1),
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(AppColors.radiusMd),
                            ),
                          ),
                        ),
                        const Spacer(),

                        // Allow Always button (exact match, disabled on dangerous)
                        if (isDangerous)
                          Tooltip(
                            message: 'Dangerous commands cannot be whitelisted to Allow Always',
                            child: ElevatedButton.icon(
                              onPressed: null,
                              icon: const Icon(Icons.lock_rounded, size: 15, color: AppColors.neutral500),
                              label: Text(
                                'Allow Always',
                                style: AppTypography.bodySmall.copyWith(color: AppColors.neutral500),
                              ),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppColors.surfaceHighlight,
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(AppColors.radiusMd),
                                ),
                              ),
                            ),
                          )
                        else
                          OutlinedButton.icon(
                            onPressed: () => state.resolvePendingTerminalApproval('allow_always'),
                            icon: Icon(Icons.all_inclusive_rounded, size: 15, color: AppColors.semanticSuccess),
                            label: Text(
                              'Allow Always',
                              style: AppTypography.bodySmall.copyWith(
                                color: AppColors.semanticSuccess,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            style: OutlinedButton.styleFrom(
                              side: BorderSide(color: AppColors.semanticSuccess, width: 1),
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(AppColors.radiusMd),
                              ),
                            ),
                          ),

                        const SizedBox(width: 10),

                        // Allow Once button (Primary)
                        ElevatedButton.icon(
                          onPressed: () => state.resolvePendingTerminalApproval('allow_once'),
                          icon: const Icon(Icons.check_rounded, size: 16, color: AppColors.neutral950),
                          label: Text(
                            'Allow Once',
                            style: AppTypography.bodySmall.copyWith(
                              color: AppColors.neutral950,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.accentPrimary,
                            foregroundColor: AppColors.neutral950,
                            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(AppColors.radiusMd),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
