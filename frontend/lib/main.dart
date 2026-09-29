import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'voice_controller.dart';
import 'connection_page.dart';
import 'inbox_page.dart';

void main() => runApp(const VoiceNotesApp());

class VoiceNotesApp extends StatelessWidget {
  const VoiceNotesApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Voice Notes v3',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF136D62)),
      scaffoldBackgroundColor: const Color(0xFFF5F6F3),
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
      ),
    ),
    home: const VoiceHome(),
  );
}

class VoiceHome extends StatefulWidget {
  const VoiceHome({super.key});

  @override
  State<VoiceHome> createState() => _VoiceHomeState();
}

class _VoiceHomeState extends State<VoiceHome> with WidgetsBindingObserver {
  final controller = VoiceController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Local demo builds can pass APP_ACCESS_TOKEN with --dart-define. This
    // keeps the token out of source control while allowing the simulator demo
    // to start connected. Production builds leave this empty and use the
    // connection form instead.
    const demoToken = String.fromEnvironment('APP_ACCESS_TOKEN');
    if (demoToken.isNotEmpty) {
      unawaited(controller.connectToBackend(controller.baseUrl, demoToken));
    } else {
      unawaited(controller.loadConfig());
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.detached) {
      unawaited(controller.suspend());
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: controller,
    builder: (context, _) {
      final c = controller;
      final status = switch (c.state) {
        VoiceState.idle => 'Ready when you are',
        VoiceState.uploading => 'Transcribing and translating your file…',
        VoiceState.connecting => 'Connecting to live translation…',
        VoiceState.listening => 'Listening · speak naturally',
        VoiceState.finishing => 'Finishing the last words…',
      };
      return Scaffold(
        appBar: AppBar(
          backgroundColor: const Color(0xFFF5F6F3),
          title: const Row(
            children: [
              Icon(Icons.graphic_eq_rounded, color: Color(0xFF136D62)),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Voice Notes v3',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          actions: [
            IconButton(
              tooltip: 'Connection settings',
              onPressed: c.busy
                  ? null
                  : () => Navigator.push(
                      context,
                      MaterialPageRoute<void>(
                        builder: (_) => ConnectionPage(controller: c),
                      ),
                    ),
              icon: const Icon(Icons.settings_outlined),
            ),
            const Padding(
              padding: EdgeInsets.only(right: 24),
              child: Text(
                'EN / FR',
                style: TextStyle(fontSize: 13, color: Color(0xFF58665F)),
              ),
            ),
          ],
        ),
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1100),
              child: ListView(
                padding: const EdgeInsets.all(24),
                children: [
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            c.connected
                                ? 'Connected to your server'
                                : 'Connect your server to get started',
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 12,
                            runSpacing: 8,
                            children: [
                              OutlinedButton.icon(
                                onPressed: c.busy
                                    ? null
                                    : () => Navigator.push(
                                        context,
                                        MaterialPageRoute<void>(
                                          builder: (_) =>
                                              ConnectionPage(controller: c),
                                        ),
                                      ),
                                icon: const Icon(Icons.link),
                                label: Text(
                                  c.connected
                                      ? 'Connection settings'
                                      : 'Connect server',
                                ),
                              ),
                              FilledButton.tonalIcon(
                                onPressed: !c.connected || c.busy
                                    ? null
                                    : () => Navigator.push(
                                        context,
                                        MaterialPageRoute<void>(
                                          builder: (_) =>
                                              InboxPage(controller: c),
                                        ),
                                      ),
                                icon: const Icon(Icons.inbox_outlined),
                                label: const Text('WhatsApp inbox'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Your voice, in two languages.',
                    style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Upload a voice note or speak into your microphone. Read the original words alongside their translation.',
                    style: TextStyle(fontSize: 17, height: 1.5),
                  ),
                  const SizedBox(height: 28),
                  Wrap(
                    spacing: 24,
                    runSpacing: 16,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      SizedBox(
                        width: 250,
                        child: DropdownButtonFormField<String>(
                          isExpanded: true,
                          initialValue: c.targetLanguage,
                          decoration: const InputDecoration(
                            labelText: 'Translate into',
                          ),
                          items: const [
                            DropdownMenuItem(
                              value: 'fr',
                              child: Text(
                                'French / Français',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            DropdownMenuItem(
                              value: 'en',
                              child: Text('English'),
                            ),
                          ],
                          onChanged: c.busy
                              ? null
                              : (value) {
                                  if (value != null) c.setTarget(value);
                                },
                        ),
                      ),
                      const Text(
                        'English and French input · language detected automatically',
                        style: TextStyle(color: Color(0xFF58665F)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final upload = _panel(
                        icon: Icons.upload_file_rounded,
                        title: 'Upload a voice note',
                        children: [
                          Text(
                            'WhatsApp .ogg / .opus, MP3, WAV, M4A or WebM. Up to ${c.maxUploadBytes ~/ 1000000} MB.',
                          ),
                          const SizedBox(height: 20),
                          OutlinedButton.icon(
                            onPressed: c.busy ? null : c.pickFile,
                            icon: const Icon(Icons.folder_open),
                            label: const Text('Choose audio file'),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            c.filename ?? 'No file selected',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 20),
                          FilledButton.icon(
                            onPressed: c.busy || !c.hasFile || !c.connected
                                ? null
                                : c.upload,
                            icon: const Icon(Icons.translate),
                            label: const Text('Transcribe & translate'),
                          ),
                        ],
                      );
                      final live = _panel(
                        icon: Icons.mic_none_rounded,
                        title: 'Speak live',
                        children: [
                          const Text(
                            'Allow microphone access, then speak in English or French. Text appears as you talk.',
                          ),
                          const SizedBox(height: 20),
                          FilledButton.icon(
                            onPressed: c.state == VoiceState.listening
                                ? c.stop
                                : c.busy || !c.connected
                                ? null
                                : c.start,
                            icon: Icon(
                              c.state == VoiceState.listening
                                  ? Icons.stop_rounded
                                  : Icons.mic_rounded,
                            ),
                            label: Text(
                              c.state == VoiceState.listening
                                  ? 'Stop & finish'
                                  : 'Start speaking',
                            ),
                          ),
                          const SizedBox(height: 16),
                          const Text(
                            'Live translated text · up to 10 minutes per session\nSmall delays are normal. Keep this page open.',
                            style: TextStyle(
                              color: Color(0xFF58665F),
                              height: 1.5,
                            ),
                          ),
                        ],
                      );
                      if (constraints.maxWidth < 720) {
                        return Column(
                          children: [upload, const SizedBox(height: 16), live],
                        );
                      }
                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(child: upload),
                          const SizedBox(width: 16),
                          Expanded(child: live),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      if (c.busy)
                        const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      else
                        const Icon(
                          Icons.check_circle_outline,
                          size: 18,
                          color: Color(0xFF136D62),
                        ),
                      const SizedBox(width: 10),
                      Expanded(child: Text(status)),
                    ],
                  ),
                  if (c.error != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.errorContainer,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: SelectableText(c.error!),
                    ),
                  ],
                  const SizedBox(height: 24),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final original = _result(
                        'Original transcript',
                        c.transcript,
                        'Your original words will appear here.',
                      );
                      final translated = _result(
                        '${c.targetName} translation',
                        c.translation,
                        'Your translated text will appear here.',
                      );
                      if (constraints.maxWidth < 720) {
                        return Column(
                          children: [
                            original,
                            const SizedBox(height: 16),
                            translated,
                          ],
                        );
                      }
                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(child: original),
                          const SizedBox(width: 16),
                          Expanded(child: translated),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 24),
                  const Text(
                    'Testing with WhatsApp? Save a voice note to your device, then choose it above. Live mode uses this microphone.',
                    style: TextStyle(color: Color(0xFF58665F)),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Audio is processed by OpenAI. Upload and live results stay in this app session. WhatsApp results stay on your server for 24 hours; audio is deleted after processing.',
                    style: TextStyle(color: Color(0xFF58665F), fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    },
  );

  Widget _panel({
    required IconData icon,
    required String title,
    required List<Widget> children,
  }) => Card(
    margin: EdgeInsets.zero,
    elevation: 0,
    color: Colors.white,
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(icon, color: const Color(0xFF136D62)),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          ...children,
        ],
      ),
    ),
  );

  Widget _result(String title, String text, String placeholder) => Card(
    margin: EdgeInsets.zero,
    elevation: 0,
    color: Colors.white,
    child: Container(
      constraints: const BoxConstraints(minHeight: 210),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              IconButton(
                tooltip: 'Copy text',
                onPressed: text.isEmpty
                    ? null
                    : () async {
                        await Clipboard.setData(ClipboardData(text: text));
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Copied')),
                          );
                        }
                      },
                icon: const Icon(Icons.copy_outlined, size: 20),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SelectableText(
            text.isEmpty ? placeholder : text,
            style: TextStyle(
              fontSize: 17,
              height: 1.6,
              color: text.isEmpty
                  ? const Color(0xFF7B8580)
                  : const Color(0xFF1A2923),
            ),
          ),
        ],
      ),
    ),
  );
}
