import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'voice_controller.dart';
import 'connection_page.dart';
import 'inbox_page.dart';

void main() => runApp(const VoiceNotesApp());

class VoiceNotesApp extends StatefulWidget {
  const VoiceNotesApp({super.key});

  @override
  State<VoiceNotesApp> createState() => _VoiceNotesAppState();
}

class _VoiceNotesAppState extends State<VoiceNotesApp> {
  final controller = VoiceController();

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: controller,
    builder: (context, _) => MaterialApp(
      title: 'Voice Notes v3',
      debugShowCheckedModeBanner: false,
      locale: Locale(controller.localeCode),
      supportedLocales: const [Locale('en'), Locale('fr'), Locale('ar')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF136D62)),
        scaffoldBackgroundColor: const Color(0xFFF5F6F3),
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
        ),
      ),
      home: VoiceHome(controller: controller),
    ),
  );
}

class VoiceHome extends StatefulWidget {
  const VoiceHome({super.key, required this.controller});
  final VoiceController controller;

  @override
  State<VoiceHome> createState() => _VoiceHomeState();
}

class _VoiceHomeState extends State<VoiceHome> with WidgetsBindingObserver {
  VoiceController get controller => widget.controller;

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
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: controller,
    builder: (context, _) {
      final c = controller;
      final status = switch (c.state) {
        VoiceState.idle => c.t('Ready when you are'),
        VoiceState.uploading => c.t('Transcribing and translating your file…'),
        VoiceState.connecting => c.t('Connecting to live translation…'),
        VoiceState.listening => c.t('Listening · speak naturally'),
        VoiceState.finishing => c.t('Finishing the last words…'),
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
              tooltip: c.t('Connection settings'),
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
            Padding(
              padding: const EdgeInsetsDirectional.only(end: 12),
              child: DropdownButton<String>(
                key: const Key('language-picker'),
                value: c.localeCode,
                underline: const SizedBox.shrink(),
                onChanged: (value) {
                  if (value != null) c.setLocale(value);
                },
                items: const [
                  DropdownMenuItem(value: 'en', child: Text('English')),
                  DropdownMenuItem(value: 'fr', child: Text('Français')),
                  DropdownMenuItem(value: 'ar', child: Text('العربية')),
                ],
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
                                ? c.t('Connected to your server')
                                : c.t('Connect your server to get started'),
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
                                      ? c.t('Connection settings')
                                      : c.t('Connect server'),
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
                                label: Text(c.t('WhatsApp inbox')),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Card(
                    child: SwitchListTile.adaptive(
                      value: c.saveToDatabase,
                      onChanged: !c.connected || c.busy
                          ? null
                          : c.setSaveToDatabase,
                      title: Text(c.t('Save to Database')),
                      subtitle: Text(
                        c.t('Applies to WhatsApp, uploads, and live sessions.'),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    c.t('Your voice, in two languages.'),
                    style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    c.t(
                      'Upload a voice note or speak into your microphone. Read the original words alongside their translation.',
                    ),
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
                          decoration: InputDecoration(
                            labelText: c.t('Translate into'),
                          ),
                          items: [
                            DropdownMenuItem(
                              value: 'fr',
                              child: Text(
                                c.t('French / Français'),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            DropdownMenuItem(
                              value: 'en',
                              child: Text(c.t('English')),
                            ),
                          ],
                          onChanged: c.busy
                              ? null
                              : (value) {
                                  if (value != null) c.setTarget(value);
                                },
                        ),
                      ),
                      Text(
                        c.t(
                          'English and French input · language detected automatically',
                        ),
                        style: TextStyle(color: Color(0xFF58665F)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final upload = _panel(
                        icon: Icons.upload_file_rounded,
                        title: c.t('Upload a voice note'),
                        children: [
                          Text(
                            c
                                .t(
                                  'WhatsApp .ogg / .opus, MP3, WAV, M4A or WebM. Up to {size} MB.',
                                )
                                .replaceAll(
                                  '{size}',
                                  '${c.maxUploadBytes ~/ 1000000}',
                                ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            c.t(
                              'Uploading saves the original audio and transcription on the machine running this backend. It is not automatically synced to your iPhone.',
                            ),
                            style: TextStyle(
                              color: Color(0xFF58665F),
                              fontSize: 12,
                              height: 1.4,
                            ),
                          ),
                          const SizedBox(height: 20),
                          OutlinedButton.icon(
                            onPressed: c.busy ? null : c.pickFile,
                            icon: const Icon(Icons.folder_open),
                            label: Text(c.t('Choose audio file')),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            c.filename ?? c.t('No file selected'),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 20),
                          FilledButton.icon(
                            onPressed: c.busy || !c.hasFile || !c.connected
                                ? null
                                : c.upload,
                            icon: const Icon(Icons.translate),
                            label: Text(c.t('Upload & transcribe')),
                          ),
                        ],
                      );
                      final live = _panel(
                        icon: Icons.mic_none_rounded,
                        title: c.t('Speak live'),
                        children: [
                          Text(
                            c.t(
                              'Allow microphone access, then speak in English or French. Text appears as you talk.',
                            ),
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
                                  ? c.t('Stop & finish')
                                  : c.t('Start speaking'),
                            ),
                          ),
                          const SizedBox(height: 16),
                          Text(
                            c.t(
                              'Live translated text · up to 10 minutes per session\nSmall delays are normal. Keep this page open.',
                            ),
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
                        c.t('Original transcript'),
                        c.transcript,
                        c.t('Your original words will appear here.'),
                      );
                      final translated = _result(
                        c
                            .t('{language} translation')
                            .replaceAll('{language}', c.t(c.targetName)),
                        c.translation,
                        c.t('Your translated text will appear here.'),
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
                  Text(
                    c.t(
                      'Testing with WhatsApp? Save a voice note to your device, then choose it above. Live mode uses this microphone.',
                    ),
                    style: TextStyle(color: Color(0xFF58665F)),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    c.t(
                      'Audio is processed by OpenAI. Uploaded audio and transcripts are stored on the backend machine in its local data folder. WhatsApp inbox results also remain in the app queue.',
                    ),
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
                tooltip: controller.t('Copy text'),
                onPressed: text.isEmpty
                    ? null
                    : () async {
                        await Clipboard.setData(ClipboardData(text: text));
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text(controller.t('Copied'))),
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
