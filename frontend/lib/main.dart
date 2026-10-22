import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:window_manager/window_manager.dart';
import 'package:webview_cef/webview_cef.dart';

import 'core/theme/app_theme.dart';
import 'services/editor_window_service.dart';
import 'state/app_state.dart';
import 'ui/chat_platform_scaffold.dart';

void main(List<String> args) async {
  WidgetsFlutterBinding.ensureInitialized();

  if (Platform.isLinux || Platform.isWindows) {
    await windowManager.ensureInitialized();

    const WindowOptions windowOptions = WindowOptions(
      size: Size(1320, 840),
      minimumSize: Size(820, 560),
      center: true,
      backgroundColor: Colors.transparent,
      skipTaskbar: false,
      title: 'blockbrain_hud',
    );

    await windowManager.waitUntilReadyToShow(windowOptions, () async {
      await windowManager.show();
      await windowManager.focus();
    });

    try {
      await WebviewManager().initialize();
    } catch (e) {
      debugPrint('[CEF] WebviewManager initialize exception: $e');
    }
  }

  final appState = AppState();
  EditorWindowService().registerAppState(appState);

  runApp(
    ChangeNotifierProvider<AppState>.value(
      value: appState,
      child: const BlockBrainApp(),
    ),
  );
}

class BlockBrainApp extends StatelessWidget {
  const BlockBrainApp({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return MaterialApp(
      title: 'blockbrain_hud',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.getTheme(isMinimal: state.isMinimalTheme),
      home: const ChatPlatformScaffold(),
    );
  }
}
