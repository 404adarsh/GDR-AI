class SystemState {
  final String orbState; // idle | listening | thinking | speaking | alert
  final String currentActivity;
  final double cpuPercent;
  final double ramUsedGb;
  final double ramTotalGb;
  final double vramUsedMb;
  final double vramTotalMb;
  final String agentName;
  final String userName;
  final bool isPanicked;

  SystemState({
    required this.orbState,
    required this.currentActivity,
    required this.cpuPercent,
    required this.ramUsedGb,
    required this.ramTotalGb,
    required this.vramUsedMb,
    required this.vramTotalMb,
    required this.agentName,
    required this.userName,
    required this.isPanicked,
  });

  factory SystemState.initial() {
    return SystemState(
      orbState: 'idle',
      currentActivity: 'Monitoring system and scheduled routines',
      cpuPercent: 12.0,
      ramUsedGb: 6.2,
      ramTotalGb: 15.4,
      vramUsedMb: 940.0,
      vramTotalMb: 3800.0,
      agentName: 'BlockBrain AI',
      userName: 'User',
      isPanicked: false,
    );
  }

  factory SystemState.fromJson(Map<String, dynamic> json) {
    final hw = json['hardware'] ?? {};
    final vram = hw['vram'] ?? {};
    final ram = hw['ram'] ?? {};
    final cpu = hw['cpu'] ?? {};

    return SystemState(
      orbState: json['orb_state'] ?? 'idle',
      currentActivity: json['what_im_doing_now'] ?? 'Standing by',
      cpuPercent: (cpu['percent'] ?? 10.0).toDouble(),
      ramUsedGb: (ram['used_gb'] ?? 5.0).toDouble(),
      ramTotalGb: (ram['total_gb'] ?? 16.0).toDouble(),
      vramUsedMb: (vram['used_mb'] ?? 800.0).toDouble(),
      vramTotalMb: (vram['total_mb'] ?? 3800.0).toDouble(),
      agentName: 'BlockBrain AI',
      userName: 'User',
      isPanicked: json['is_panicked'] == true,
    );
  }
}

class ScheduledTask {
  final int id;
  final String description;
  final String nextRunAt;
  final String scheduleType;

  ScheduledTask({
    required this.id,
    required this.description,
    required this.nextRunAt,
    required this.scheduleType,
  });

  factory ScheduledTask.fromJson(Map<String, dynamic> json) {
    return ScheduledTask(
      id: json['id'] ?? 0,
      description: json['description'] ?? '',
      nextRunAt: json['next_run_at'] ?? '',
      scheduleType: json['schedule_type'] ?? 'once',
    );
  }
}
