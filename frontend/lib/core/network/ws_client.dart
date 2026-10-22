import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:web_socket_channel/web_socket_channel.dart';

class WsClient {
  final String url;
  WebSocketChannel? _channel;
  final StreamController<Map<String, dynamic>> _controller = StreamController<Map<String, dynamic>>.broadcast();
  bool _isConnected = false;
  Timer? _reconnectTimer;

  WsClient({this.url = 'ws://127.0.0.1:8844/ws'});

  Stream<Map<String, dynamic>> get stream => _controller.stream;
  bool get isConnected => _isConnected;

  String _getAuthenticatedUrl() {
    try {
      final home = Platform.environment['HOME'] ?? '/home/kali';
      final tokenFile = File('$home/.config/blockbrain/session.token');
      if (tokenFile.existsSync()) {
        final token = tokenFile.readAsStringSync().trim();
        if (token.isNotEmpty) {
          final uri = Uri.parse(url);
          return uri.replace(queryParameters: {'token': token}).toString();
        }
      }
    } catch (_) {}
    return url;
  }

  void connect() {
    try {
      final authUrl = _getAuthenticatedUrl();
      _channel = WebSocketChannel.connect(Uri.parse(authUrl));
      _isConnected = true;

      _channel!.stream.listen(
        (data) {
          try {
            final parsed = jsonDecode(data.toString()) as Map<String, dynamic>;
            _controller.add(parsed);
          } catch (_) {}
        },
        onError: (err) {
          _isConnected = false;
          _scheduleReconnect();
        },
        onDone: () {
          _isConnected = false;
          _scheduleReconnect();
        },
      );
    } catch (_) {
      _isConnected = false;
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), () {
      connect();
    });
  }

  void send(Map<String, dynamic> data) {
    if (_isConnected && _channel != null) {
      try {
        _channel!.sink.add(jsonEncode(data));
      } catch (_) {}
    }
  }

  void dispose() {
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _controller.close();
  }
}
