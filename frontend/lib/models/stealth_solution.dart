class StealthSolution {
  final String? timestamp;
  final String question;
  final String talkingPoints;
  final String approach;
  final String code;
  final String edgeCases;
  final String status;
  final bool whispered;

  StealthSolution({
    this.timestamp,
    required this.question,
    required this.talkingPoints,
    required this.approach,
    required this.code,
    required this.edgeCases,
    required this.status,
    required this.whispered,
  });

  factory StealthSolution.fromJson(Map<String, dynamic> json) {
    return StealthSolution(
      timestamp: json['timestamp'] as String?,
      question: json['question'] ?? 'Stealth Copilot standing by...',
      talkingPoints: json['talking_points'] ?? '',
      approach: json['approach'] ?? '',
      code: json['code'] ?? '',
      edgeCases: json['edge_cases'] ?? '',
      status: json['status'] ?? 'ready',
      whispered: json['whispered'] == true,
    );
  }

  factory StealthSolution.initial() {
    return StealthSolution(
      question: 'Stealth Copilot standing by. Waiting for question on screen...',
      talkingPoints: 'I\'m monitoring your screen invisibly. As soon as a question or problem appears, your speaking points and optimal solution will appear right here.',
      approach: 'System is synchronized with your display. You can click ⚡ Solve Screen Now at any time or enable Auto-Watch.',
      code: '# Code solution will appear here\ndef solution():\n    pass',
      edgeCases: '• Null or empty inputs\n• Single element arrays\n• Boundary conditions',
      status: 'ready',
      whispered: false,
    );
  }
}
