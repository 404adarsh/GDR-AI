import 'dart:io';
import 'package:flutter/material.dart';
import 'package:webview_cef/webview_cef.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';

/// Embedded inline Monaco Editor pane powered by Chromium Embedded Framework (CEF).
/// Renders off-screen frames directly to a Flutter hardware Texture widget,
/// living natively inside the right sidebar panel alongside Copilot, Canvas, and Terminal.
class InlineMonacoEditor extends StatefulWidget {
  final double? width;
  final double? height;

  const InlineMonacoEditor({
    super.key,
    this.width,
    this.height,
  });

  @override
  State<InlineMonacoEditor> createState() => _InlineMonacoEditorState();
}

class _InlineMonacoEditorState extends State<InlineMonacoEditor> {
  WebViewController? _controller;
  bool _isInitializing = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _initCefEditor();
  }

  Future<void> _initCefEditor() async {
    setState(() {
      _isInitializing = true;
      _errorMessage = null;
    });

    try {
      // 1. Ensure CEF engine is initialized
      if (!WebviewManager().value) {
        await WebviewManager().initialize();
      }

      // 2. Read local session token for authenticated communication
      final home = Platform.environment['HOME'] ?? '';
      final tokenFile = File('$home/.config/blockbrain/session.token');
      final token = tokenFile.existsSync() ? tokenFile.readAsStringSync().trim() : '';

      // 3. Configure preload scripts to inject session authentication
      final userScripts = InjectUserScripts()
        ..add(UserScript(
          'window.__BLOCKBRAIN_SESSION_TOKEN = "$token";'
          'localStorage.setItem("blockbrain_session_token", "$token");',
          ScriptInjectTime.LOAD_START,
        ));

      // 4. Create CEF WebView controller
      final controller = WebviewManager().createWebView(
        injectUserScripts: userScripts,
        loading: _buildLoadingState(),
      );

      _controller = controller;

      // 5. Initialize navigation to local Monaco Studio
      await controller.initialize('http://127.0.0.1:8844/editor');

      if (mounted) {
        setState(() {
          _isInitializing = false;
        });
      }
    } catch (e) {
      debugPrint('[InlineMonacoEditor] Failed to initialize CEF Monaco: $e');
      if (mounted) {
        setState(() {
          _isInitializing = false;
          _errorMessage = e.toString();
        });
      }
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Widget _buildLoadingState() {
    return Container(
      color: AppColors.surfaceBase,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 28,
              height: 28,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                valueColor: AlwaysStoppedAnimation<Color>(AppColors.accentPrimary),
              ),
            ),
            const SizedBox(height: 14),
            Text(
              'INITIALIZING MONACO TEXTURE ENGINE...',
              style: AppTypography.monoBadge.copyWith(
                color: AppColors.neutral400,
                letterSpacing: 0.8,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState() {
    return Container(
      color: AppColors.surfaceBase,
      padding: const EdgeInsets.all(20),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline_rounded, color: AppColors.semanticDanger, size: 36),
            const SizedBox(height: 12),
            Text(
              'CEF EMBED FAILED',
              style: AppTypography.titleMedium.copyWith(color: AppColors.neutral100),
            ),
            const SizedBox(height: 8),
            Text(
              _errorMessage ?? 'Unknown error initializing Chromium engine.',
              style: AppTypography.caption.copyWith(color: AppColors.neutral400),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: _initCefEditor,
              icon: const Icon(Icons.refresh_rounded, size: 14, color: AppColors.accentPrimary),
              label: Text('RETRY INITIALIZATION', style: AppTypography.monoBadge),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: AppColors.accentPrimaryMuted),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_errorMessage != null) {
      return _buildErrorState();
    }

    if (_isInitializing || _controller == null) {
      return _buildLoadingState();
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(AppColors.radiusMd),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surfaceBase,
          border: Border.all(color: AppColors.borderDefault, width: 1),
        ),
        child: _controller!.webviewWidget,
      ),
    );
  }
}
