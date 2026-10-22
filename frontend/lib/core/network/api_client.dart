import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../models/system_state.dart';
import '../../models/stealth_solution.dart';

class ApiClient {
  final String baseUrl;

  ApiClient({this.baseUrl = 'http://127.0.0.1:8844'});

  Future<SystemState> fetchStatus() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/status')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return SystemState.fromJson(jsonDecode(res.body));
      }
    } catch (_) {}
    return SystemState.initial();
  }

  Future<Map<String, dynamic>> sendChat(String prompt) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'prompt': prompt}),
      ).timeout(const Duration(seconds: 60));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      return {'reply': 'Error reaching brain: $e'};
    }
    return {'reply': 'Error processing query.'};
  }

  Future<StealthSolution> fetchLatestStealth() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/stealth/latest')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return StealthSolution.fromJson(jsonDecode(res.body));
      }
    } catch (_) {}
    return StealthSolution.initial();
  }

  Future<StealthSolution> triggerStealthSolve({String? prompt}) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/stealth/solve'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'prompt': prompt}),
      ).timeout(const Duration(seconds: 30));
      if (res.statusCode == 200) {
        return StealthSolution.fromJson(jsonDecode(res.body));
      }
    } catch (_) {}
    return StealthSolution.initial();
  }

  Future<bool> toggleStealthAutoWatch(bool enable) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/stealth/autowatch'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'enabled': enable, 'interval': 4.0}),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return data['autowatch_enabled'] == true;
      }
    } catch (_) {}
    return false;
  }

  Future<bool> toggleStealthWhisper(bool enable) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/stealth/whisper'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'enabled': enable}),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return data['whisper_enabled'] == true;
      }
    } catch (_) {}
    return false;
  }

  Future<void> clearStealth() async {
    try {
      await http.post(Uri.parse('$baseUrl/api/stealth/clear'));
    } catch (_) {}
  }

  Future<List<ScheduledTask>> fetchTasks() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/tasks')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        final list = jsonDecode(res.body) as List;
        return list.map((e) => ScheduledTask.fromJson(e)).toList();
      }
    } catch (_) {}
    return [];
  }

  Future<bool> addTask(String text) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/tasks'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': text}),
      );
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> captureScreen() async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/screen/capture'));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (_) {}
    return {'success': false};
  }

  Future<Map<String, dynamic>> runTerminalCommand(String command) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/terminal/run'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'command': command}),
      );
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      return {'output': 'Error: $e'};
    }
    return {'output': 'Failed to execute command'};
  }

  Future<bool> triggerPanic({String action = 'toggle'}) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/panic'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'action': action}),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return data['panicked'] == true;
      }
    } catch (_) {}
    return false;
  }

  Future<Map<String, dynamic>> approveTerminalCommand(
    String approvalId,
    String action, {
    String? uiNonce,
  }) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/terminal/approve'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'approval_id': approvalId,
          'action': action,
          'ui_nonce': uiNonce ?? '',
        }),
      );
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      } else {
        try {
          return jsonDecode(res.body);
        } catch (_) {
          return {'output': 'HTTP ${res.statusCode}: ${res.body}', 'exit_code': 1};
        }
      }
    } catch (e) {
      return {'output': 'Error resolving approval: $e', 'exit_code': 1};
    }
  }

  Future<Map<String, dynamic>> fetchPermissions() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/permissions')).timeout(const Duration(seconds: 3));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (_) {}
    return {'mode': 'LIMITED', 'tools': {}};
  }

  Future<bool> setPermissionMode(String mode) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/permissions/mode'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'mode': mode}),
      );
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<bool> setToolToggle(String tool, bool enabled) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/permissions/tool'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'tool': tool, 'enabled': enabled}),
      );
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
