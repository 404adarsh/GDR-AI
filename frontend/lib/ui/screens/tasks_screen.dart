import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_theme.dart';
import '../../state/app_state.dart';
import '../widgets/glass_card.dart';

class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key});

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  final TextEditingController _taskController = TextEditingController();

  void _addTask(AppState state) async {
    final text = _taskController.text.trim();
    if (text.isNotEmpty) {
      _taskController.clear();
      await state.api.addTask(text);
      await state.refreshData();
    }
  }

  @override
  void dispose() {
    _taskController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('NATURAL LANGUAGE TASK SCHEDULER', style: TextStyle(color: AppTheme.cyan, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 1.2)),
          const SizedBox(height: 6),
          const Text('Schedule recurring cron routines, reminders, and future AI actions using plain English.', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
          const SizedBox(height: 16),

          // Add Task Card
          GlassCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                const Icon(Icons.add_task, color: AppTheme.cyan),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: _taskController,
                    onSubmitted: (_) => _addTask(state),
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    decoration: const InputDecoration(
                      hintText: 'e.g. "in 15 minutes stretch and drink water" or "every weekday 9am summarize email"',
                      hintStyle: TextStyle(color: AppTheme.textMuted, fontSize: 12),
                      border: InputBorder.none,
                    ),
                  ),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.cyan,
                    foregroundColor: Colors.black,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: () => _addTask(state),
                  child: const Text('SCHEDULE', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11)),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Active Tasks List
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('ACTIVE ROUTINES & REMINDERS', style: TextStyle(color: AppTheme.textMain, fontSize: 13, fontWeight: FontWeight.bold)),
              IconButton(
                onPressed: () => state.refreshData(),
                icon: const Icon(Icons.refresh, size: 18, color: AppTheme.cyan),
              ),
            ],
          ),
          const SizedBox(height: 10),

          if (state.tasks.isEmpty)
            GlassCard(
              padding: const EdgeInsets.all(24),
              child: const Center(
                child: Text('No active scheduled tasks. Add one above!', style: TextStyle(color: AppTheme.textMuted, fontSize: 12)),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: state.tasks.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final task = state.tasks[index];
                return GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppTheme.cyan.withOpacity(0.12),
                          border: Border.all(color: AppTheme.cyan.withOpacity(0.4), width: 1),
                        ),
                        child: const Icon(Icons.schedule, color: AppTheme.cyan, size: 16),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(task.description, style: const TextStyle(color: AppTheme.textMain, fontSize: 13, fontWeight: FontWeight.w600)),
                            const SizedBox(height: 4),
                            Text('Next Run: ${task.nextRunAt}  •  Type: ${task.scheduleType}', style: AppTheme.mono.copyWith(fontSize: 11, color: AppTheme.textMuted)),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppTheme.green.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AppTheme.green.withOpacity(0.4), width: 1),
                        ),
                        child: Text(
                          'ACTIVE',
                          style: TextStyle(color: AppTheme.green, fontSize: 10, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
