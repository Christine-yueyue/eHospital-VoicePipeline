import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'voice_controller.dart';

class InboxPage extends StatefulWidget {
  const InboxPage({super.key, required this.controller});
  final VoiceController controller;

  @override
  State<InboxPage> createState() => _InboxPageState();
}

class _InboxPageState extends State<InboxPage> with WidgetsBindingObserver {
  Timer? timer;
  bool loading = false;
  String? error;
  List<Map<String, dynamic>> messages = [];
  Map<String, dynamic> settings = {};
  final Set<String> pendingActions = {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    unawaited(refresh());
    startTimer();
  }

  void startTimer() {
    timer?.cancel();
    timer = Timer.periodic(const Duration(seconds: 5), (_) => refresh());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      unawaited(refresh());
      startTimer();
    } else {
      timer?.cancel();
    }
  }

  @override
  void dispose() {
    timer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  Future<void> refresh() async {
    if (loading) return;
    setState(() => loading = true);
    try {
      final data = await widget.controller.fetchInbox();
      if (!mounted) return;
      setState(() {
        messages = (data['messages'] as List).cast<Map<String, dynamic>>();
        settings = data['whatsapp'] as Map<String, dynamic>;
        error = null;
      });
    } on FormatException catch (e) {
      if (mounted) setState(() => error = e.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => error =
              'Cannot refresh your inbox. Check the connection and try again.',
        );
      }
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> action(String action, String id) async {
    if (pendingActions.contains(id)) return;
    setState(() => pendingActions.add(id));
    try {
      await widget.controller.inboxAction(action, id);
      if (!mounted) return;
      await refresh();
    } catch (_) {
      if (mounted) {
        setState(
          () => error =
              'The message could not be updated. Refresh and try again.',
        );
      }
    } finally {
      if (mounted) setState(() => pendingActions.remove(id));
    }
  }

  Future<void> delete(String id) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete this result?'),
        content: const Text(
          'This removes the saved transcript and translation from your Voice Notes inbox.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) await action('delete', id);
  }

  Widget result(String title, String value) => Padding(
    padding: const EdgeInsets.only(top: 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                title,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
            IconButton(
              tooltip: 'Copy $title',
              onPressed: () async {
                await Clipboard.setData(ClipboardData(text: value));
                if (!mounted) return;
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(const SnackBar(content: Text('Copied')));
              },
              icon: const Icon(Icons.copy_outlined, size: 18),
            ),
          ],
        ),
        SelectableText(
          value,
          style: const TextStyle(fontSize: 16, height: 1.5),
        ),
      ],
    ),
  );

  Widget messageCard(Map<String, dynamic> message) {
    final id = message['id'] as String;
    final status = message['status'] as String;
    final isCall = message['kind'] == 'call_transcript';
    final details = (message['details'] as Map<String, dynamic>?) ?? {};
    final segments = (details['segments'] as List?) ?? [];
    final processingLabel = switch (message['stage']) {
      'fetching_transcript' => 'Fetching Meta transcript…',
      'parsing_transcript' => 'Reading call transcript…',
      'translating' => 'Translating…',
      _ =>
        isCall
            ? 'Processing call transcript…'
            : 'Transcribing and translating…',
    };
    final statusLabel = switch (status) {
      'queued' => 'Waiting to process',
      'processing' => processingLabel,
      'completed' => 'Ready',
      'partial' => 'Transcript ready · translation needs retry',
      _ => 'Processing failed',
    };
    final date = DateTime.fromMillisecondsSinceEpoch(
      ((message['created'] as num) * 1000).toInt(),
    );
    final formattedDate = MaterialLocalizations.of(
      context,
    ).formatShortDate(date.toLocal());
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(
                  isCall ? Icons.call_outlined : Icons.mic_none_outlined,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    isCall ? 'Call transcript · Meta' : 'Voice message',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${isCall ? 'Participant' : 'From'} ${message['sender']} · $formattedDate',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(statusLabel),
            if (isCall && details.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                [
                  if ((details['language'] as String? ?? '').isNotEmpty)
                    'Detected language: ${details['language']}',
                  if (details['duration'] is num)
                    'Duration: ${timestamp(details['duration'] as num)}',
                ].join(' · '),
              ),
            ],
            if (status == 'queued' || status == 'processing') ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(),
            ],
            if ((message['transcript'] as String).isNotEmpty)
              result('Original transcript', message['transcript'] as String),
            if (isCall && segments.isNotEmpty)
              ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text('Speaker timeline (${segments.length})'),
                children: [
                  for (final segment in segments)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            '${segment['speaker']} · ${timestamp(segment['start'] as num)}–${timestamp(segment['end'] as num)}',
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          SelectableText(segment['text'] as String),
                        ],
                      ),
                    ),
                ],
              ),
            if ((message['translation'] as String).isNotEmpty)
              result(
                message['target'] == 'fr'
                    ? 'French translation'
                    : 'English translation',
                message['translation'] as String,
              ),
            if ((message['error'] as String).isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                message['error'] as String,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              children: [
                if (status == 'failed' || status == 'partial')
                  OutlinedButton.icon(
                    onPressed: pendingActions.contains(id)
                        ? null
                        : () => action('retry', id),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retry'),
                  ),
                TextButton.icon(
                  onPressed: pendingActions.contains(id)
                      ? null
                      : () => delete(id),
                  icon: const Icon(Icons.delete_outline),
                  label: const Text('Delete'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String timestamp(num seconds) {
    final total = seconds.floor();
    return '${total ~/ 60}:${(total % 60).toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('WhatsApp inbox'),
      actions: [
        IconButton(
          tooltip: 'Refresh inbox',
          onPressed: loading ? null : refresh,
          icon: const Icon(Icons.refresh),
        ),
      ],
    ),
    body: Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 800),
        child: RefreshIndicator(
          onRefresh: refresh,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(24),
            children: [
              const Text(
                'Calls and voice messages, translated.',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 12),
              const Text(
                'After a WhatsApp business call with transcription enabled ends, its Meta transcript and translation appear here. Voice messages are also supported.',
              ),
              const SizedBox(height: 12),
              Text(
                'Results are kept for 24 hours. Refreshes every 5 seconds while this screen is open. Translation: ${settings['target_language'] == 'en' ? 'English' : 'French'}.',
              ),
              const SizedBox(height: 24),
              if (settings.isNotEmpty && settings['configured'] != true)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                      'WhatsApp setup is still needed on your server. Complete the Meta configuration, then refresh.',
                    ),
                  ),
                ),
              if (error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Text(
                    error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              if (loading && messages.isEmpty) const LinearProgressIndicator(),
              if (!loading && messages.isEmpty && error == null)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 40),
                  child: Center(child: Text('No calls or voice messages yet.')),
                ),
              ...messages.map(messageCard),
            ],
          ),
        ),
      ),
    ),
  );
}
