import 'package:flutter/foundation.dart';
import '../state/app_state.dart';

/// Service coordinating editor focus and panel navigation.
/// Repurposed from detached window launcher to the true inline right-sidebar panel architecture.
class EditorWindowService {
  static final EditorWindowService _instance = EditorWindowService._internal();
  factory EditorWindowService() => _instance;
  EditorWindowService._internal();

  AppState? _appState;

  void registerAppState(AppState state) {
    _appState = state;
  }

  /// Focus or open the inline Monaco Editor inside the app's right sidebar.
  void openOrFocusEditor() {
    if (_appState != null) {
      _appState!.switchRightTab('editor');
    } else {
      debugPrint('[EditorWindowService] AppState not registered.');
    }
  }

  void close() {
    _appState?.toggleRightPanel(false);
  }
}
