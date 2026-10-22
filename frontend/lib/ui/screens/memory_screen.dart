import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';
import '../widgets/glass_card.dart';

class MemoryScreen extends StatelessWidget {
  const MemoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('LONG-TERM EPISODIC & SEMANTIC MEMORY', style: TextStyle(color: AppTheme.cyan, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
          const SizedBox(height: 6),
          const Text('Vector and key-value memory store indexed across past user interactions and preferences.', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
          const SizedBox(height: 20),

          GlassCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('USER PROFILE & PREFERENCES', style: TextStyle(color: AppTheme.violet, fontSize: 13, fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                _buildMemoryItem('User Name', 'GDR / Kali User'),
                _buildMemoryItem('Primary Machine', 'Kali Linux (NVIDIA RTX 3050 Laptop)'),
                _buildMemoryItem('Timezone', 'Asia/Kolkata (IST)'),
                _buildMemoryItem('Primary LLM', 'Sarvam AI 105B (Indian Languages / English)'),
                _buildMemoryItem('Fallback LLM', 'Ollama (Qwen2.5 / DeepSeek) & Claude 3.5 Sonnet'),
                _buildMemoryItem('TTS Voice', 'Piper Neural (en_US-lessac-medium) + Sarvam Bulbul'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMemoryItem(String key, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 150,
            child: Text(key, style: const TextStyle(color: AppTheme.textMuted, fontSize: 12)),
          ),
          Expanded(
            child: Text(value, style: const TextStyle(color: AppTheme.textMain, fontSize: 12, fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}
