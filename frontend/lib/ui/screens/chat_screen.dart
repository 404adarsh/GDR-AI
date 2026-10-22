import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_theme.dart';
import '../../state/app_state.dart';
import '../widgets/glass_card.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  void _send(AppState state) {
    final text = _controller.text.trim();
    if (text.isNotEmpty) {
      _controller.clear();
      state.sendChatMessage(text);
      Future.delayed(const Duration(milliseconds: 100), () {
        if (_scrollController.hasClients) {
          _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          // Header info
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'NEURAL DIALOGUE STREAM (Sarvam 105B / Claude / Ollama)',
                style: TextStyle(color: AppTheme.cyan, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1),
              ),
              Text(
                '${state.chatMessages.length} messages',
                style: AppTheme.mono.copyWith(fontSize: 11, color: AppTheme.textMuted),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Messages List
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              itemCount: state.chatMessages.length,
              itemBuilder: (context, index) {
                final msg = state.chatMessages[index];
                final isUser = msg['role'] == 'user';

                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Row(
                    mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (!isUser) ...[
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppTheme.cyan.withOpacity(0.15),
                            border: Border.all(color: AppTheme.cyan, width: 1),
                          ),
                          child: const Icon(Icons.smart_toy_outlined, color: AppTheme.cyan, size: 14),
                        ),
                        const SizedBox(width: 10),
                      ],
                      Flexible(
                        child: GlassCard(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          borderColor: isUser ? AppTheme.violet.withOpacity(0.5) : AppTheme.cardBorder,
                          child: Column(
                            crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                            children: [
                              Text(
                                isUser ? 'YOU' : 'BLOCKBRAIN AI',
                                style: TextStyle(
                                  color: isUser ? AppTheme.violet : AppTheme.cyan,
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                  letterSpacing: 0.8,
                                ),
                              ),
                              const SizedBox(height: 6),
                              SelectableText(
                                msg['text'] ?? '',
                                style: const TextStyle(color: AppTheme.textMain, fontSize: 13, height: 1.4),
                              ),
                            ],
                          ),
                        ),
                      ),
                      if (isUser) ...[
                        const SizedBox(width: 10),
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppTheme.violet.withOpacity(0.15),
                            border: Border.all(color: AppTheme.violet, width: 1),
                          ),
                          child: const Icon(Icons.person_outline, color: AppTheme.violet, size: 14),
                        ),
                      ],
                    ],
                  ),
                );
              },
            ),
          ),

          const SizedBox(height: 12),

          // Chat Input Box
          GlassCard(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    onSubmitted: (_) => _send(state),
                    style: const TextStyle(color: Colors.white, fontSize: 14),
                    decoration: const InputDecoration(
                      hintText: 'Type your instruction or conversation...',
                      hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 13),
                      border: InputBorder.none,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: () => _send(state),
                  icon: const Icon(Icons.send_rounded, color: AppTheme.cyan, size: 20),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
