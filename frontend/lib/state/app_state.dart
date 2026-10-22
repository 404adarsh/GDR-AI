import 'dart:async';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/network/api_client.dart';
import '../core/network/ws_client.dart';
import '../models/system_state.dart';
import '../models/stealth_solution.dart';
import '../ui/widgets/voice_visualizer_host.dart';

class ChatMessage {
  final String role; // 'user' | 'assistant'
  final String text;
  final String? attachmentB64;
  final String time;
  final String? toolName;
  final String? toolDesc;
  final String? toolStatus;
  final bool isApprovalRequired;
  final String? approvalAction;

  ChatMessage({
    required this.role,
    required this.text,
    this.attachmentB64,
    required this.time,
    this.toolName,
    this.toolDesc,
    this.toolStatus,
    this.isApprovalRequired = false,
    this.approvalAction,
  });
}

class AppState extends ChangeNotifier {
  final ApiClient api = ApiClient();
  final WsClient ws = WsClient();

  // Layout states
  bool isSidebarCollapsed = false;
  bool isRightPanelOpen = false;
  String activeRightTab = 'copilot'; // 'copilot' | 'terminal' | 'tasks' | 'memory'
  String activeMode = 'chat'; // 'chat' | 'copilot' | 'tasks' | 'approvals' | 'memory' | 'terminal' | 'settings'

  // Resizable Right Sidebar State
  double? customRightPanelWidth;
  bool isDraggingRightPanel = false;

  double get effectiveRightPanelWidth {
    if (customRightPanelWidth != null) {
      return customRightPanelWidth!.clamp(320.0, 880.0);
    }
    return activeRightTab == 'editor' ? 640.0 : 460.0;
  }

  void startDraggingRightPanel() {
    isDraggingRightPanel = true;
    notifyListeners();
  }

  void updateRightPanelWidth(double delta, double maxWidth) {
    final current = effectiveRightPanelWidth;
    final newWidth = (current - delta).clamp(320.0, maxWidth);
    customRightPanelWidth = newWidth;
    isDraggingRightPanel = true;
    notifyListeners();
  }

  void stopDraggingRightPanel() {
    isDraggingRightPanel = false;
    notifyListeners();
    persistRightPanelWidth();
  }

  Future<void> persistRightPanelWidth() async {
    if (customRightPanelWidth == null) return;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setDouble('blockbrain_right_panel_width', customRightPanelWidth!);
    } catch (_) {}
  }

  // Model & Chat states
  String currentChatTitle = 'New Conversation';
  String selectedModel = 'Sarvam 105B';
  String? attachedScreenshotB64;
  bool isStreaming = false;
  bool isMessagesLoading = false;

  // Voice Animation & Audio Pipeline State (voice_anim_kit)
  VoiceAnimStyle voiceStyle = VoiceAnimStyle.wave;
  double voiceAmplitude = 0.35;
  bool isVoiceActive = false;
  bool isMinimalTheme = false;

  SystemState systemState = SystemState.initial();
  StealthSolution stealthSolution = StealthSolution.initial();
  bool isSolving = false;
  bool autowatchEnabled = false;
  bool whisperEnabled = false;
  bool isCloaked = true; // Screen-share invisibility active by default

  List<ChatMessage> messages = [];
  List<Map<String, dynamic>> conversations = [
    {
      'id': 'conv_init',
      'title': 'Welcome to BlockBrain',
      'time': 'Just now',
    }
  ];

  List<ScheduledTask> tasks = [];
  String terminalHistory = 'BlockBrain Shell Console ready.\nType bash commands or click Run on code blocks.\n';
  Timer? _pollingTimer;

  // Section 9 & 10: Terminal Approval Gate & Permissions State
  Map<String, dynamic>? pendingTerminalApproval;
  String permissionMode = 'LIMITED'; // 'READ_ONLY' | 'LIMITED' | 'TRUSTED'
  Map<String, bool> toolToggles = {
    'filesystem': true,
    'terminal': true,
    'github': false,
    'browser': false,
    'google_workspace': false,
    'n8n': false,
  };

  AppState() {
    init();
  }

  void init() {
    ws.connect();
    ws.stream.listen((event) {
      final type = event['type'];
      final data = event['data'] ?? {};

      if (type == 'init') {
        final stealth = data['stealth'] ?? {};
        autowatchEnabled = stealth['autowatch_enabled'] == true;
        whisperEnabled = stealth['whisper_enabled'] == true;
        if (data['latest_solution'] != null) {
          stealthSolution = StealthSolution.fromJson(data['latest_solution']);
        }
        notifyListeners();
      } else if (type == 'stealth_solution') {
        stealthSolution = StealthSolution.fromJson(data);
        isSolving = false;
        notifyListeners();
      } else if (type == 'orb_update') {
        notifyListeners();
      } else if (type == 'terminal_approval_required') {
        pendingTerminalApproval = Map<String, dynamic>.from(data);
        notifyListeners();
      } else if (type == 'terminal_approved_executed' || type == 'terminal_denied') {
        if (pendingTerminalApproval?['id'] == data['id']) {
          pendingTerminalApproval = null;
          notifyListeners();
        }
      }
    });

    refreshData();
    fetchPermissions();
    _loadPersistedSettings();
    _pollingTimer = Timer.periodic(const Duration(seconds: 4), (_) => refreshData());
  }

  Future<void> _loadPersistedSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final styleId = prefs.getString('voice_anim_style');
      if (styleId != null) {
        voiceStyle = VoiceAnimStyleExt.fromId(styleId);
      }
      isMinimalTheme = prefs.getBool('theme_is_minimal') ?? false;
      final savedWidth = prefs.getDouble('blockbrain_right_panel_width');
      if (savedWidth != null && savedWidth >= 320.0 && savedWidth <= 880.0) {
        customRightPanelWidth = savedWidth;
      } else {
        customRightPanelWidth = 460.0;
      }
      notifyListeners();
    } catch (_) {}
  }

  Future<void> setVoiceStyle(VoiceAnimStyle s) async {
    voiceStyle = s;
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('voice_anim_style', s.id);
    } catch (_) {}
  }

  Future<void> toggleMinimalTheme() async {
    isMinimalTheme = !isMinimalTheme;
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('theme_is_minimal', isMinimalTheme);
    } catch (_) {}
  }

  void setVoiceActive(bool active, [double? amp]) {
    isVoiceActive = active;
    if (amp != null) voiceAmplitude = amp.clamp(0.0, 1.0);
    notifyListeners();
  }

  void toggleSidebar() {
    isSidebarCollapsed = !isSidebarCollapsed;
    notifyListeners();
  }

  void toggleRightPanel([bool? force]) {
    isRightPanelOpen = force ?? !isRightPanelOpen;
    notifyListeners();
  }

  void switchRightTab(String tab) {
    activeRightTab = tab;
    isRightPanelOpen = true;
    notifyListeners();
  }

  void switchMode(String mode) {
    activeMode = mode;
    if (mode == 'copilot') {
      switchRightTab('copilot');
    } else if (mode == 'tasks') {
      switchRightTab('tasks');
    } else if (mode == 'terminal') {
      switchRightTab('terminal');
    } else if (mode == 'memory') {
      switchRightTab('memory');
    }
    notifyListeners();
  }

  void startNewChat() {
    messages.clear();
    currentChatTitle = 'New Conversation';
    attachedScreenshotB64 = null;
    notifyListeners();
  }

  Future<void> attachScreen() async {
    final res = await api.captureScreen();
    if (res['success'] == true && res['image_b64'] != null) {
      attachedScreenshotB64 = res['image_b64'];
      notifyListeners();
    }
  }

  void clearAttachment() {
    attachedScreenshotB64 = null;
    notifyListeners();
  }

  Future<void> refreshData() async {
    final s = await api.fetchStatus();
    systemState = s;

    final sol = await api.fetchLatestStealth();
    if (sol.timestamp != null) {
      stealthSolution = sol;
    }

    final t = await api.fetchTasks();
    tasks = t;
    notifyListeners();
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty && attachedScreenshotB64 == null) return;

    final userAttachment = attachedScreenshotB64;
    attachedScreenshotB64 = null;

    messages.add(
      ChatMessage(
        role: 'user',
        text: text,
        attachmentB64: userAttachment,
        time: 'Now',
      ),
    );

    if (messages.length == 1 && currentChatTitle == 'New Conversation') {
      currentChatTitle = text.length > 28 ? '${text.substring(0, 28)}...' : text;
      conversations.insert(0, {
        'id': 'conv_${DateTime.now().millisecondsSinceEpoch}',
        'title': currentChatTitle,
        'time': 'Just now',
      });
    }

    isStreaming = true;
    notifyListeners();

    // Check for inline tool intents
    String lower = text.toLowerCase();
    if (lower.contains('screen') || lower.contains('solve')) {
      messages.add(
        ChatMessage(
          role: 'assistant',
          text: '',
          time: 'Now',
          toolName: 'Screen Reflection',
          toolDesc: 'Analyzing active window context & OCR...',
          toolStatus: 'done',
        ),
      );
    }

    final res = await api.sendChat(text);
    final reply = res['reply'] ?? 'Standing by.';

    messages.add(
      ChatMessage(
        role: 'assistant',
        text: reply,
        time: 'Just now',
      ),
    );

    isStreaming = false;
    notifyListeners();
    refreshData();
  }

  Future<void> triggerTerminal(String cmd) async {
    terminalHistory += '\n> $cmd\n';
    notifyListeners();
    final res = await api.runTerminalCommand(cmd);
    if (res['status'] == 'requires_approval' && res['approval'] != null) {
      pendingTerminalApproval = Map<String, dynamic>.from(res['approval']);
      terminalHistory += '⚠️ Approval required for: $cmd\n';
    } else {
      terminalHistory += '${res['output'] ?? ''}\n';
    }
    notifyListeners();
  }

  Future<void> resolvePendingTerminalApproval(String action) async {
    if (pendingTerminalApproval == null) return;
    final id = pendingTerminalApproval!['id'] as String;
    final nonce = pendingTerminalApproval!['ui_nonce'] as String?;
    final cmd = pendingTerminalApproval!['command'] as String? ?? '';
    final res = await api.approveTerminalCommand(id, action, uiNonce: nonce);
    pendingTerminalApproval = null;
    terminalHistory += '\n[Terminal Gate: $action] $cmd\n${res['output'] ?? ''}\n';
    notifyListeners();
  }

  Future<void> fetchPermissions() async {
    try {
      final data = await api.fetchPermissions();
      if (data['mode'] != null) {
        permissionMode = data['mode'];
      }
      if (data['tools'] != null && data['tools'] is Map) {
        toolToggles = Map<String, bool>.from(data['tools']);
      }
      notifyListeners();
    } catch (_) {}
  }

  Future<void> setPermissionMode(String mode) async {
    permissionMode = mode;
    notifyListeners();
    await api.setPermissionMode(mode);
  }

  Future<void> setToolToggle(String tool, bool enabled) async {
    toolToggles[tool] = enabled;
    notifyListeners();
    await api.setToolToggle(tool, enabled);
  }

  Future<void> triggerStealthSolve() async {
    isSolving = true;
    notifyListeners();
    final sol = await api.triggerStealthSolve();
    stealthSolution = sol;
    isSolving = false;
    switchRightTab('copilot');
    notifyListeners();
  }

  Future<void> toggleAutoWatch() async {
    autowatchEnabled = !autowatchEnabled;
    notifyListeners();
    final res = await api.toggleStealthAutoWatch(autowatchEnabled);
    autowatchEnabled = res;
    notifyListeners();
  }

  Future<void> toggleWhisper() async {
    whisperEnabled = !whisperEnabled;
    notifyListeners();
    final res = await api.toggleStealthWhisper(whisperEnabled);
    whisperEnabled = res;
    notifyListeners();
  }

  Future<void> clearStealth() async {
    await api.clearStealth();
    stealthSolution = StealthSolution.initial();
    notifyListeners();
  }

  Future<void> triggerPanic() async {
    await api.triggerPanic();
    await refreshData();
  }

  void toggleCloak() {
    isCloaked = !isCloaked;
    switchRightTab('copilot');
    notifyListeners();
  }

  void selectModel(String model) {
    selectedModel = model;
    notifyListeners();
  }

  // Backward-compatible properties & methods for legacy screens
  int currentScreenIndex = 0;
  void setScreen(int idx) {
    currentScreenIndex = idx;
    notifyListeners();
  }

  List<Map<String, String>> get chatMessages => messages.map((m) => {
    'role': m.role,
    'text': m.text,
    'time': m.time,
  }).toList();

  Future<void> sendChatMessage(String text) async {
    await sendMessage(text);
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    ws.dispose();
    super.dispose();
  }
}
