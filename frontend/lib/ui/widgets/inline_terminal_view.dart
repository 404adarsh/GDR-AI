import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:xterm/xterm.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';

/// Studio-grade BlockBrain Terminal Palette
const blockbrainTerminalTheme = TerminalTheme(
  cursor: AppColors.accentPrimary,
  selection: Color(0x4000F2FE),
  foreground: AppColors.neutral200,
  background: AppColors.surfaceBase,
  black: Color(0xFF1E222D),
  red: AppColors.semanticDanger,
  green: AppColors.semanticSuccess,
  yellow: AppColors.semanticWarning,
  blue: Color(0xFF82AAFF),
  magenta: Color(0xFFC792EA),
  cyan: AppColors.accentPrimary,
  white: AppColors.neutral100,
  brightBlack: Color(0xFF546E7A),
  brightRed: Color(0xFFFF5370),
  brightGreen: Color(0xFF38EF7D),
  brightYellow: Color(0xFFFFD54F),
  brightBlue: Color(0xFF82AAFF),
  brightMagenta: Color(0xFFD670D6),
  brightCyan: Color(0xFF4DD0E1),
  brightWhite: Color(0xFFFFFFFF),
  searchHitBackground: Color(0xFF32474B),
  searchHitBackgroundCurrent: Color(0xFF00F2FE),
  searchHitForeground: Color(0xFF000000),
);

class TerminalTabSession {
  final String id;
  final String title;
  final bool isAgent;
  final Terminal terminal;
  final FocusNode focusNode;
  WebSocketChannel? channel;
  StreamSubscription? subscription;
  bool isConnected = false;
  bool isConnecting = false;

  TerminalTabSession({
    required this.id,
    required this.title,
    this.isAgent = false,
  })  : terminal = Terminal(maxLines: 10000),
        focusNode = FocusNode();

  void dispose() {
    subscription?.cancel();
    channel?.sink.close();
    focusNode.dispose();
  }
}

/// Multi-tab genuine PTY OS Terminal widget connected to backend /ws/terminal.
class InlineTerminalView extends StatefulWidget {
  const InlineTerminalView({super.key});

  @override
  State<InlineTerminalView> createState() => _InlineTerminalViewState();
}

class _InlineTerminalViewState extends State<InlineTerminalView> {
  final List<TerminalTabSession> _tabs = [];
  int _activeTabIndex = 0;
  int _bashCounter = 1;

  @override
  void initState() {
    super.initState();
    // 1. Dedicated Agent Terminal Tab (Permanent, streams approved agent actions)
    final agentTab = TerminalTabSession(
      id: 'agent',
      title: 'Agent',
      isAgent: true,
    );
    _tabs.add(agentTab);

    // 2. Default Interactive User Bash Tab
    final userTab = TerminalTabSession(
      id: 'bash_1',
      title: 'bash (1)',
      isAgent: false,
    );
    _tabs.add(userTab);
    _activeTabIndex = 1; // Default to interactive bash for user

    // Connect both sessions
    _connectSession(agentTab);
    _connectSession(userTab);
  }

  @override
  void dispose() {
    for (final tab in _tabs) {
      tab.dispose();
    }
    super.dispose();
  }

  String _getSessionToken() {
    try {
      final envToken = Platform.environment['HUD_SESSION_TOKEN'];
      if (envToken != null && envToken.isNotEmpty) {
        return envToken.trim();
      }
      final home = Platform.environment['HOME'] ?? '/home/kali';
      final tokenFile = File('$home/.config/blockbrain/session.token');
      if (tokenFile.existsSync()) {
        return tokenFile.readAsStringSync().trim();
      }
    } catch (_) {}
    return '';
  }

  void _connectSession(TerminalTabSession session) {
    if (session.isConnecting) return;
    session.isConnecting = true;

    final token = _getSessionToken();
    final uri = Uri.parse('ws://127.0.0.1:8844/ws/terminal').replace(
      queryParameters: {
        'token': token,
        'session_id': session.id,
        'cols': '100',
        'rows': '30',
      },
    );

    try {
      final channel = WebSocketChannel.connect(uri);
      session.channel = channel;

      session.subscription = channel.stream.listen(
        (data) {
          if (!session.isConnected) {
            setState(() {
              session.isConnected = true;
              session.isConnecting = false;
            });
          }
          try {
            final parsed = jsonDecode(data.toString()) as Map<String, dynamic>;
            final text = parsed['data']?.toString() ?? '';
            if (text.isNotEmpty) {
              session.terminal.write(text);
            }
          } catch (_) {
            session.terminal.write(data.toString());
          }
        },
        onError: (err) {
          if (mounted) {
            setState(() {
              session.isConnected = false;
              session.isConnecting = false;
            });
          }
        },
        onDone: () {
          if (mounted) {
            setState(() {
              session.isConnected = false;
              session.isConnecting = false;
            });
          }
        },
      );

      // Wire terminal output to WebSocket
      session.terminal.onOutput = (output) {
        if (session.isConnected && session.channel != null) {
          session.channel!.sink.add(jsonEncode({
            'type': 'input',
            'data': output,
          }));
        }
      };

      // Wire resize events
      session.terminal.onResize = (width, height, pw, ph) {
        if (session.isConnected && session.channel != null) {
          session.channel!.sink.add(jsonEncode({
            'type': 'resize',
            'cols': width,
            'rows': height,
          }));
        }
      };
    } catch (e) {
      session.isConnecting = false;
      session.isConnected = false;
    }
  }

  void _addNewTab() {
    _bashCounter++;
    final newTab = TerminalTabSession(
      id: 'bash_$_bashCounter',
      title: 'bash ($_bashCounter)',
      isAgent: false,
    );
    setState(() {
      _tabs.add(newTab);
      _activeTabIndex = _tabs.length - 1;
    });
    _connectSession(newTab);
  }

  void _closeTab(int index) {
    if (index <= 0 || index >= _tabs.length) return; // Cannot close agent tab
    final tab = _tabs[index];

    // Inform backend to terminate PTY
    if (tab.isConnected && tab.channel != null) {
      try {
        tab.channel!.sink.add(jsonEncode({'type': 'close'}));
      } catch (_) {}
    }
    tab.dispose();

    setState(() {
      _tabs.removeAt(index);
      if (_activeTabIndex >= _tabs.length) {
        _activeTabIndex = _tabs.length - 1;
      }
    });
  }

  void _reconnectActiveTab() {
    if (_activeTabIndex < 0 || _activeTabIndex >= _tabs.length) return;
    final tab = _tabs[_activeTabIndex];
    tab.subscription?.cancel();
    tab.channel?.sink.close();
    tab.isConnected = false;
    tab.isConnecting = false;
    _connectSession(tab);
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    if (_tabs.isEmpty) {
      return const SizedBox.shrink();
    }
    final activeTab = _tabs[_activeTabIndex];

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surfaceBase,
        borderRadius: BorderRadius.circular(AppColors.radiusMd),
        border: Border.all(color: AppColors.borderDefault, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Tab Bar & Controls (28px height standard)
          Container(
            height: 36,
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            decoration: const BoxDecoration(
              color: AppColors.surfaceOverlay,
              borderRadius: BorderRadius.vertical(top: Radius.circular(AppColors.radiusMd)),
              border: Border(bottom: BorderSide(color: AppColors.borderDefault, width: 1)),
            ),
            child: Row(
              children: [
                // Tabs List
                Expanded(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: List.generate(_tabs.length, (idx) {
                        final tab = _tabs[idx];
                        final isActive = idx == _activeTabIndex;
                        return _buildTabHeader(tab, idx, isActive);
                      }),
                    ),
                  ),
                ),

                const SizedBox(width: 4),

                // Spawn New Shell Tab Button (+)
                _buildActionBtn(
                  icon: Icons.add_rounded,
                  tooltip: 'New Terminal Tab',
                  onTap: _addNewTab,
                ),

                const SizedBox(width: 4),

                // Reconnect / Refresh Button
                _buildActionBtn(
                  icon: Icons.refresh_rounded,
                  tooltip: 'Reconnect Session',
                  onTap: _reconnectActiveTab,
                ),

                const SizedBox(width: 6),

                // Status Indicator
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: activeTab.isConnected
                        ? AppColors.semanticSuccess
                        : (activeTab.isConnecting ? AppColors.semanticWarning : AppColors.semanticDanger),
                    boxShadow: [
                      BoxShadow(
                        color: (activeTab.isConnected
                                ? AppColors.semanticSuccess
                                : AppColors.semanticDanger)
                            .withOpacity(0.4),
                        blurRadius: 4,
                      )
                    ],
                  ),
                ),
                const SizedBox(width: 6),
              ],
            ),
          ),

          // 2. Terminal Viewport
          Expanded(
            child: ClipRRect(
              borderRadius: const BorderRadius.vertical(bottom: Radius.circular(AppColors.radiusMd)),
              child: Stack(
                children: [
                  TerminalView(
                    activeTab.terminal,
                    key: ValueKey('term_${activeTab.id}'),
                    theme: blockbrainTerminalTheme,
                    textStyle: const TerminalStyle(
                      fontSize: 12.0,
                      fontFamily: 'monospace',
                    ),
                    padding: const EdgeInsets.all(10),
                    autoResize: true,
                    focusNode: activeTab.focusNode,
                    autofocus: true,
                    readOnly: activeTab.isAgent,
                  ),

                  // Disconnected Overlay
                  if (!activeTab.isConnected && !activeTab.isConnecting)
                    Positioned(
                      top: 10,
                      right: 12,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceOverlay.withOpacity(0.9),
                          borderRadius: BorderRadius.circular(AppColors.radiusSm),
                          border: Border.all(color: AppColors.semanticDanger.withOpacity(0.6), width: 1),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.error_outline_rounded, size: 12, color: AppColors.semanticDanger),
                            const SizedBox(width: 6),
                            Text(
                              'Disconnected',
                              style: AppTypography.monoBadge.copyWith(
                                color: AppColors.semanticDanger,
                                fontSize: 10,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabHeader(TerminalTabSession tab, int index, bool isActive) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () {
          setState(() {
            _activeTabIndex = index;
          });
          tab.focusNode.requestFocus();
        },
        child: Container(
          height: 28,
          margin: const EdgeInsets.only(right: 4),
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(
            color: isActive ? AppColors.surfaceBase : AppColors.surfaceHighlight.withOpacity(0.5),
            borderRadius: BorderRadius.circular(AppColors.radiusSm),
            border: Border.all(
              color: isActive ? AppColors.accentPrimary.withOpacity(0.6) : AppColors.borderDefault,
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                tab.isAgent ? Icons.smart_toy_outlined : Icons.terminal_rounded,
                size: 13,
                color: isActive
                    ? (tab.isAgent ? const Color(0xFFC792EA) : AppColors.accentPrimary)
                    : AppColors.neutral400,
              ),
              const SizedBox(width: 6),
              Text(
                tab.title,
                style: AppTypography.caption.copyWith(
                  color: isActive ? AppColors.neutral100 : AppColors.neutral300,
                  fontWeight: isActive ? FontWeight.w600 : FontWeight.w500,
                  fontSize: 11,
                ),
              ),
              if (!tab.isAgent) ...[
                const SizedBox(width: 6),
                MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => _closeTab(index),
                    child: Container(
                      padding: const EdgeInsets.all(2),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.transparent,
                      ),
                      child: const Icon(
                        Icons.close_rounded,
                        size: 12,
                        color: AppColors.neutral400,
                      ),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionBtn({
    required IconData icon,
    required String tooltip,
    required VoidCallback onTap,
  }) {
    return Tooltip(
      message: tooltip,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: onTap,
          child: Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: AppColors.surfaceHighlight,
              borderRadius: BorderRadius.circular(AppColors.radiusSm),
              border: Border.all(color: AppColors.borderDefault, width: 1),
            ),
            child: Icon(icon, size: 14, color: AppColors.neutral200),
          ),
        ),
      ),
    );
  }
}
