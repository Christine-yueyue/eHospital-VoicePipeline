import 'dart:async';
import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:record/record.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

enum VoiceState { idle, uploading, connecting, listening, finishing }

class VoiceController extends ChangeNotifier {
  VoiceController({String? backendUrl, http.Client? client})
    : baseUrl =
          backendUrl ??
          const String.fromEnvironment(
            'API_BASE_URL',
            defaultValue: 'http://127.0.0.1:8003',
          ),
      _http = client ?? http.Client();

  String baseUrl;
  String _accessToken = '';
  bool connected = false;
  Map<String, dynamic> whatsapp = {};
  final AudioRecorder _recorder = AudioRecorder();
  final http.Client _http;
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _events;
  StreamSubscription<Uint8List>? _audio;
  Completer<void>? _ready;
  Completer<void>? _microphoneDone;
  Timer? _finishTimer;
  Timer? _audioWatchdog;
  Future<void>? _closing;
  int _session = 0;
  int _audioBytesSent = 0;
  bool _disposed = false;

  VoiceState state = VoiceState.idle;
  String targetLanguage = 'fr';
  String transcript = '';
  String translation = '';
  // The provider may omit a no-op English -> English result. While waiting
  // for a real translation event, show the source text as a reversible
  // fallback; a later translation delta replaces it.
  bool _translationFallback = false;
  String? error;
  String? filename;
  Uint8List? _fileBytes;
  int maxUploadBytes = 20000000;

  bool get busy => state != VoiceState.idle;
  bool get hasFile => _fileBytes != null;
  String get targetName => targetLanguage == 'fr' ? 'French' : 'English';

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  void setTarget(String value) {
    if (busy) return;
    targetLanguage = value;
    // Results belong to the previous language choice.
    transcript = '';
    translation = '';
    _translationFallback = false;
    error = null;
    _notify();
  }

  Uri _url(String path) => Uri.parse(baseUrl).resolve(path);

  Map<String, String> get _headers => {'Authorization': 'Bearer $_accessToken'};

  static String? validateAddress(String address) {
    final uri = Uri.tryParse(address.trim());
    if (uri == null ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        (uri.path != '' && uri.path != '/')) {
      return 'Enter a server address such as https://voice.example.com.';
    }
    final local =
        uri.host == 'localhost' ||
        uri.host == '127.0.0.1' ||
        uri.host == '::1' ||
        uri.host.endsWith('.local');
    final privateIpv4 = _isPrivateIpv4(uri.host);
    if (uri.scheme != 'https' &&
        !(kDebugMode && (local || privateIpv4) && uri.scheme == 'http')) {
      return 'Use HTTPS for your server. Debug builds also allow localhost, private LAN IPs, or a .local address.';
    }
    return null;
  }

  static bool _isPrivateIpv4(String host) {
    final parts = host.split('.');
    if (parts.length != 4) return false;
    final values = <int>[];
    for (final part in parts) {
      final value = int.tryParse(part);
      if (value == null || value < 0 || value > 255) return false;
      values.add(value);
    }
    return values[0] == 10 ||
        (values[0] == 172 && values[1] >= 16 && values[1] <= 31) ||
        (values[0] == 192 && values[1] == 168);
  }

  Future<bool> connectToBackend(String address, String accessToken) async {
    if (busy) return false;
    final problem = validateAddress(address);
    if (problem != null || accessToken.trim().isEmpty) {
      error = problem ?? 'Enter your app access token.';
      _notify();
      return false;
    }
    try {
      final response = await _http
          .get(
            Uri.parse(address.trim()).resolve('/api/config'),
            headers: {'Authorization': 'Bearer ${accessToken.trim()}'},
          )
          .timeout(const Duration(seconds: 10));
      final body = _responseBody(response);
      if (_disposed) return false;
      if (body['version'] != '3.0.0') {
        throw const FormatException(
          'Connect to the v3 backend. This server uses another version.',
        );
      }
      baseUrl = address.trim();
      _accessToken = accessToken.trim();
      connected = true;
      maxUploadBytes = (body['max_upload_bytes'] as num).toInt();
      whatsapp = body['whatsapp'] as Map<String, dynamic>;
      transcript = '';
      translation = '';
      _translationFallback = false;
      error = null;
      _notify();
      return true;
    } on FormatException catch (e) {
      error = e.message;
    } catch (_) {
      error =
          'Cannot connect. Check the server address, HTTPS certificate and network.';
    }
    _notify();
    return false;
  }

  Map<String, dynamic> _responseBody(http.Response response) {
    Map<String, dynamic> body;
    try {
      body = jsonDecode(response.body) as Map<String, dynamic>;
    } catch (_) {
      throw const FormatException(
        'The server returned an unreadable response. Check its address.',
      );
    }
    if (response.statusCode != 200) {
      throw FormatException(body['error'] as String? ?? 'The request failed.');
    }
    return body;
  }

  Future<Map<String, dynamic>> fetchInbox() async => _responseBody(
    await _http
        .get(_url('/api/whatsapp/messages'), headers: _headers)
        .timeout(const Duration(seconds: 15)),
  );

  Future<void> inboxAction(String action, String id) async {
    _responseBody(
      await _http
          .post(
            _url('/api/whatsapp/$action'),
            headers: {..._headers, 'Content-Type': 'application/json'},
            body: jsonEncode({'id': id}),
          )
          .timeout(const Duration(seconds: 15)),
    );
  }

  void disconnect() {
    if (busy) return;
    _accessToken = '';
    connected = false;
    whatsapp = {};
    _fileBytes = null;
    filename = null;
    transcript = '';
    translation = '';
    _translationFallback = false;
    error = null;
    _notify();
  }

  Future<void> loadConfig() async {
    if (!connected) return;
    try {
      final response = await _http
          .get(_url('/api/config'), headers: _headers)
          .timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        maxUploadBytes = (jsonDecode(response.body)['max_upload_bytes'] as num)
            .toInt();
        _notify();
      }
    } catch (_) {
      // Picking a file still works offline. Upload gives a visible connection error.
    }
  }

  Future<void> pickFile() async {
    if (busy) return;
    try {
      final file = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: ['ogg', 'opus', 'mp3', 'wav', 'm4a', 'webm'],
      );
      if (file == null || _disposed) return;
      final size = await file.length();
      if (size == null || size <= 0 || size > maxUploadBytes) {
        throw FormatException(
          'Choose a nonempty audio file under ${maxUploadBytes ~/ 1000000} MB.',
        );
      }
      final bytes = await file.readAsBytes();
      if (bytes.isEmpty || bytes.length > maxUploadBytes) {
        throw const FormatException('This audio file is empty or too large.');
      }
      _fileBytes = bytes;
      filename = file.name;
      transcript = '';
      translation = '';
      _translationFallback = false;
      error = null;
    } on FormatException catch (e) {
      error = e.message;
    } catch (_) {
      error =
          'Could not read the file. Try exporting the original voice note again.';
    }
    _notify();
  }

  Future<void> upload() async {
    if (busy || _fileBytes == null || !connected) return;
    state = VoiceState.uploading;
    transcript = '';
    translation = '';
    _translationFallback = false;
    error = null;
    _notify();
    try {
      final request = http.MultipartRequest('POST', _url('/api/transcribe'))
        ..headers.addAll(_headers)
        ..fields['target_language'] = targetLanguage
        ..files.add(
          http.MultipartFile.fromBytes('file', _fileBytes!, filename: filename),
        );
      final response = await _http
          .send(request)
          .then(http.Response.fromStream)
          .timeout(const Duration(minutes: 4));
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode != 200 || body['success'] != true) {
        throw FormatException(body['error'] as String? ?? 'The upload failed.');
      }
      transcript = body['transcript'] as String? ?? '';
      translation = body['translation'] as String? ?? '';
      if (targetLanguage == 'en' && translation.trim().isEmpty) {
        translation = transcript;
      }
      _translationFallback = false;
      error = body['translation_error'] as String?;
    } on FormatException catch (e) {
      error = e.message;
    } on TimeoutException {
      error = 'The upload timed out. Try a shorter recording.';
    } catch (_) {
      error =
          'Cannot reach the backend at $baseUrl. Start FastAPI and check the address.';
    } finally {
      state = VoiceState.idle;
      _notify();
    }
  }

  Future<void> start() async {
    if (busy || !connected) return;
    await _closing;
    final current = ++_session;
    state = VoiceState.connecting;
    transcript = '';
    translation = '';
    _translationFallback = false;
    error = null;
    _notify();
    try {
      if (!await _recorder.hasPermission()) {
        throw const FormatException(
          'Microphone permission was denied. Allow it in your browser or device settings.',
        );
      }
      if (_disposed || current != _session) return;
      final uri = _url('/api/live').replace(
        scheme: Uri.parse(baseUrl).scheme == 'https' ? 'wss' : 'ws',
        queryParameters: {'target_language': targetLanguage},
      );
      final channel = WebSocketChannel.connect(uri);
      _channel = channel;
      await channel.ready.timeout(const Duration(seconds: 15));
      channel.sink.add(jsonEncode({'type': 'auth', 'token': _accessToken}));
      final ready = Completer<void>();
      _ready = ready;
      _events = channel.stream.listen(
        (raw) {
          if (_disposed || current != _session) return;
          try {
            final event = jsonDecode(raw as String) as Map<String, dynamic>;
            switch (event['type']) {
              case 'ready':
                if (!ready.isCompleted) ready.complete();
                break;
              case 'source.delta':
                transcript += event['delta'] as String? ?? '';
                if (targetLanguage == 'en' &&
                    (_translationFallback || translation.trim().isEmpty)) {
                  translation = transcript;
                  _translationFallback = true;
                }
                break;
              case 'source.final':
                // The provider can revise partial words when it commits the
                // audio turn. Replace the incremental value with that final
                // transcript so the original panel stays accurate.
                transcript = event['transcript'] as String? ?? transcript;
                if (targetLanguage == 'en' &&
                    (_translationFallback || translation.trim().isEmpty)) {
                  translation = transcript;
                  _translationFallback = true;
                }
                break;
              case 'translation.delta':
                if (_translationFallback) {
                  translation = '';
                  _translationFallback = false;
                }
                translation += event['delta'] as String? ?? '';
                break;
              case 'error':
                _fail(
                  event['message'] as String? ?? 'Live translation failed.',
                );
                break;
              case 'done':
                if (targetLanguage == 'en' &&
                    translation.trim().isEmpty &&
                    transcript.trim().isNotEmpty) {
                  translation = transcript;
                }
                unawaited(_close());
                break;
            }
            _notify();
          } catch (_) {
            _fail('Received an invalid live response. Please start again.');
          }
        },
        onError: (Object _) {
          _fail('Live connection failed. Check the backend and start again.');
        },
        onDone: () {
          if (current == _session && busy) {
            _fail(
              'The connection ended before processing finished. Your displayed text is kept.',
            );
          }
        },
      );
      await ready.future.timeout(const Duration(seconds: 30));
      if (_disposed || current != _session) return;
      final stream = await _recorder.startStream(
        const RecordConfig(
          encoder: AudioEncoder.pcm16bits,
          sampleRate: 24000,
          numChannels: 1,
          autoGain: true,
          echoCancel: true,
          noiseSuppress: true,
        ),
      );
      if (_disposed || current != _session) {
        await _recorder.stop();
        return;
      }
      final microphoneDone = Completer<void>();
      _microphoneDone = microphoneDone;
      _audioBytesSent = 0;
      _audio = stream.listen(
        (chunk) {
          // Keep silence: the interpreter needs phrase boundaries too.
          if (current != _session) return;
          if (chunk.isNotEmpty) {
            _audioBytesSent += chunk.length;
            _audioWatchdog?.cancel();
            _audioWatchdog = null;
          }
          for (var offset = 0; offset < chunk.length; offset += 4800) {
            final end = offset + 4800 < chunk.length
                ? offset + 4800
                : chunk.length;
            channel.sink.add(Uint8List.sublistView(chunk, offset, end));
          }
        },
        onError: (Object _) {
          _fail(
            'The microphone stream failed. Check microphone permissions and retry.',
          );
        },
        onDone: () {
          if (!microphoneDone.isCompleted) microphoneDone.complete();
          if (current == _session && state == VoiceState.listening) {
            _fail('The microphone stopped unexpectedly. Please start again.');
          }
        },
      );
      state = VoiceState.listening;
      _audioWatchdog = Timer(const Duration(seconds: 5), () {
        if (current == _session &&
            state == VoiceState.listening &&
            _audioBytesSent == 0) {
          _fail(
            'No microphone audio was captured. On iOS Simulator choose Features > Audio Input > Mac, or check microphone permission.',
          );
        }
      });
      _notify();
    } on FormatException catch (e) {
      _fail(e.message);
    } on TimeoutException {
      _fail(
        'Live translation took too long to connect. Check the backend and API access.',
      );
    } catch (_) {
      if (error == null) {
        _fail(
          'Could not start live translation. Check microphone access and the backend.',
        );
      }
    }
  }

  Future<void> stop() async {
    if (state != VoiceState.listening) return;
    state = VoiceState.finishing;
    _notify();
    try {
      await _recorder.stop();
      await _microphoneDone?.future.timeout(const Duration(seconds: 5));
      await _audio?.cancel();
      _audio = null;
      if (state != VoiceState.finishing) return;
      _channel?.sink.add(jsonEncode({'type': 'stop'}));
      _finishTimer = Timer(const Duration(seconds: 35), () {
        _fail(
          'The last words could not be confirmed. Your displayed text is kept.',
        );
      });
    } catch (_) {
      _fail('Could not finish the recording. Your displayed text is kept.');
    }
  }

  Future<void> suspend() async {
    if (state == VoiceState.connecting) {
      _fail('Recording was interrupted. Return to the app and start again.');
    } else {
      await stop();
    }
  }

  void _fail(String message) {
    error = message;
    final ready = _ready;
    if (ready != null && !ready.isCompleted) {
      ready.completeError(FormatException(message));
    }
    unawaited(_close());
    _notify();
  }

  Future<void> _close() {
    if (_closing != null) return _closing!;
    _session++;
    _finishTimer?.cancel();
    _audioWatchdog?.cancel();
    _audioWatchdog = null;
    final audio = _audio;
    final events = _events;
    final channel = _channel;
    _audio = null;
    _events = null;
    _channel = null;
    _ready = null;
    _closing =
        () async {
          try {
            await _recorder.stop();
          } catch (_) {
            /* Already stopped. */
          }
          await audio?.cancel();
          await events?.cancel();
          await channel?.sink.close();
          state = VoiceState.idle;
          _notify();
        }().whenComplete(() {
          _closing = null;
        });
    return _closing!;
  }

  @override
  void dispose() {
    _disposed = true;
    _http.close();
    unawaited(_close().whenComplete(_recorder.dispose));
    super.dispose();
  }
}
