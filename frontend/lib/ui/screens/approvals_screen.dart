import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../widgets/glass_card.dart';

class ApprovalsScreen extends StatelessWidget {
  const ApprovalsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('NIGHT SHIFT APPROVAL QUEUE', style: TextStyle(color: AppTheme.cyan, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
          const SizedBox(height: 6),
          const Text('Sensitive overnight actions (sending emails, form submissions, deleting files) intercepted for your review.', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
          const SizedBox(height: 20),

          GlassCard(
            padding: const EdgeInsets.all(32),
            child: Column(
              children: [
                Icon(Icons.verified_user_outlined, size: 48, color: AppTheme.green.withOpacity(0.8)),
                const SizedBox(height: 14),
                const Text('ALL ACTIONS NOMINAL', style: TextStyle(color: AppTheme.green, fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 1)),
                const SizedBox(height: 8),
                const Text('No pending actions require human authorization at this moment.', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
