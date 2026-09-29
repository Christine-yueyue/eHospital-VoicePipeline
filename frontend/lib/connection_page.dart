import 'package:flutter/material.dart';
import 'voice_controller.dart';

class ConnectionPage extends StatefulWidget {
  const ConnectionPage({super.key, required this.controller});
  final VoiceController controller;

  @override
  State<ConnectionPage> createState() => _ConnectionPageState();
}

class _ConnectionPageState extends State<ConnectionPage> {
  late final address = TextEditingController(text: widget.controller.baseUrl);
  final token = TextEditingController(
    text: const String.fromEnvironment('APP_ACCESS_TOKEN'),
  );
  bool connecting = false;

  @override
  void dispose() {
    address.dispose();
    token.dispose();
    super.dispose();
  }

  Future<void> connect() async {
    setState(() => connecting = true);
    final success = await widget.controller.connectToBackend(
      address.text,
      token.text,
    );
    if (!mounted) return;
    setState(() => connecting = false);
    if (success) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Connection settings')),
    body: Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const Text(
              'Connect your app',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 12),
            const Text(
              'Enter your Voice Notes server address and app access token. Your OpenAI and WhatsApp keys stay on the server.',
            ),
            const SizedBox(height: 24),
            TextField(
              controller: address,
              enabled: !connecting,
              keyboardType: TextInputType.url,
              autocorrect: false,
              enableSuggestions: false,
              decoration: const InputDecoration(
                labelText: 'Server address',
                hintText: 'https://voice.example.com',
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: token,
              enabled: !connecting,
              obscureText: true,
              autocorrect: false,
              enableSuggestions: false,
              decoration: const InputDecoration(labelText: 'App access token'),
              onSubmitted: (_) {
                if (!connecting) connect();
              },
            ),
            const SizedBox(height: 12),
            const Text(
              'For this personal prototype, the app keeps this token in memory until you disconnect or close the app.',
              style: TextStyle(fontSize: 12),
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: connecting ? null : connect,
              child: Text(connecting ? 'Connecting…' : 'Connect'),
            ),
            if (widget.controller.connected)
              TextButton(
                onPressed: connecting
                    ? null
                    : () {
                        widget.controller.disconnect();
                        Navigator.pop(context);
                      },
                child: const Text('Disconnect and clear results'),
              ),
            if (widget.controller.error != null) ...[
              const SizedBox(height: 16),
              Text(
                widget.controller.error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
          ],
        ),
      ),
    ),
  );
}
