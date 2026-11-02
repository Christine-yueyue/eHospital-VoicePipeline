import 'dart:async';

import 'package:flutter/material.dart';
import 'connection_page.dart';
import 'voice_controller.dart';

class AssistantOverlay extends StatefulWidget {
  const AssistantOverlay({
    super.key,
    required this.controller,
    required this.navigatorKey,
    required this.child,
  });
  final VoiceController controller;
  final GlobalKey<NavigatorState> navigatorKey;
  final Widget child;

  @override
  State<AssistantOverlay> createState() => _AssistantOverlayState();
}

class _AssistantOverlayState extends State<AssistantOverlay> {
  static const _green = Color(0xFF136D62);
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<_ChatEntry> _entries = [];
  Timer? _poll;
  Timer? _recordingTimer;
  bool _recording = false;
  bool _transcribing = false;
  int _recordingSeconds = 0;
  bool _open = false;
  bool _sending = false;
  bool _loadingActivity = false;
  int _unread = 0;

  String t(String english) {
    final locale = widget.controller.localeCode;
    return switch (locale) {
      'fr' => _french[english] ?? english,
      'ar' => _arabic[english] ?? english,
      _ => english,
    };
  }

  static const _french = <String, String>{
    'WhatsApp assistant': 'Assistant WhatsApp',
    'Close assistant': 'Fermer l’assistant',
    'Connected': 'Connecté',
    'Connect your server to use the assistant.':
        'Connectez votre serveur pour utiliser l’assistant.',
    'Connect server': 'Connecter le serveur',
    'WhatsApp setup is incomplete. Follow-up sending needs Meta settings and an approved template.':
        'La configuration WhatsApp est incomplète. L’envoi nécessite Meta et un modèle approuvé.',
    'Hello! I can help you manage WhatsApp contacts and voice follow-ups.':
        'Bonjour ! Je peux gérer vos contacts WhatsApp et vos suivis vocaux.',
    'Create a follow-up': 'Créer un suivi',
    'Show pending replies': 'Voir les réponses en attente',
    'Add a contact': 'Ajouter un contact',
    'Message the assistant…': 'Écrivez à l’assistant…',
    'Send': 'Envoyer',
    'Cancel recording': 'Annuler l’enregistrement',
    'Recording': 'Enregistrement',
    'Stop recording': 'Arrêter l’enregistrement',
    'Transcribing…': 'Transcription…',
    'Record voice message': 'Enregistrer un message vocal',
    'Could not start recording. Check microphone permission.':
        'Impossible de démarrer l’enregistrement. Vérifiez l’autorisation du microphone.',
    'No speech was recognized. Please try again.':
        'Aucune parole reconnue. Veuillez réessayer.',
    'Transcription failed. Check the connection and try again.':
        'La transcription a échoué. Vérifiez la connexion et réessayez.',
    'Please wait…': 'Veuillez patienter…',
    'Task': 'Tâche',
    'Recipient': 'Destinataire',
    'WhatsApp template preview': 'Aperçu du modèle WhatsApp',
    'The contact has not confirmed permission to receive WhatsApp messages.':
        'Le contact n’a pas confirmé son accord pour recevoir des messages WhatsApp.',
    'WhatsApp setup or approved template is missing.':
        'La configuration WhatsApp ou le modèle approuvé est manquant.',
    'Confirm and send': 'Confirmer et envoyer',
    'This only marks the internal follow-up complete. It sends no message.':
        'Cela termine uniquement le suivi interne. Aucun message ne sera envoyé.',
    'Mark complete': 'Marquer comme terminé',
    'Contact': 'Contact',
    'Permission': 'Autorisation',
    'Add this contact': 'Ajouter ce contact',
    'Choose this contact': 'Choisir ce contact',
    'Follow-up': 'Suivi',
    'View follow-up': 'Voir le suivi',
    'Invitation submitted. Waiting for WhatsApp delivery confirmation.':
        'Invitation envoyée. En attente de confirmation WhatsApp.',
    'Follow-up marked complete.': 'Suivi marqué comme terminé.',
    'Could not reach the assistant. Check the server and try again.':
        'Impossible de joindre l’assistant. Vérifiez le serveur et réessayez.',
    'Could not send the invitation. Check WhatsApp settings and try again.':
        'Impossible d’envoyer l’invitation. Vérifiez WhatsApp et réessayez.',
    'Could not update the follow-up. Refresh and try again.':
        'Impossible de mettre à jour le suivi. Actualisez et réessayez.',
    'Saved': 'Enregistré',
    'Needs permission': 'Autorisation nécessaire',
    'Waiting for reply': 'En attente de réponse',
    'Needs review': 'À consulter',
    'Draft': 'Brouillon',
    'Completed': 'Terminé',
    'Cancelled': 'Annulé',
    'Reply received': 'Réponse reçue',
    'Voice reply': 'Réponse vocale',
    'Transcript': 'Transcription',
    'Translation': 'Traduction',
    'No reply content is saved. Check the WhatsApp inbox before the temporary result expires.':
        'Aucun contenu de réponse n’est enregistré. Consultez la boîte WhatsApp avant l’expiration du résultat temporaire.',
    'Hello {name}, this is the Voice Notes team. We would like to hear how you are doing. When convenient, please reply with a voice message in this chat. Thank you.':
        'Bonjour {name}, ici l’équipe Voice Notes. Nous aimerions savoir comment vous allez. Quand vous le souhaitez, répondez par un message vocal dans cette discussion. Merci.',
  };
  static const _arabic = <String, String>{
    'WhatsApp assistant': 'مساعد واتساب',
    'Close assistant': 'إغلاق المساعد',
    'Connected': 'متصل',
    'Connect your server to use the assistant.':
        'اتصل بالخادم لاستخدام المساعد.',
    'Connect server': 'الاتصال بالخادم',
    'Hello! I can help you manage WhatsApp contacts and voice follow-ups.':
        'مرحبًا! يمكنني مساعدتك في إدارة جهات اتصال واتساب والمتابعة الصوتية.',
    'Create a follow-up': 'إنشاء متابعة',
    'Show pending replies': 'عرض الردود المعلّقة',
    'Add a contact': 'إضافة جهة اتصال',
    'Message the assistant…': 'أرسل رسالة إلى المساعد…',
    'Send': 'إرسال',
    'Cancel recording': 'إلغاء التسجيل',
    'Recording': 'جارٍ التسجيل',
    'Stop recording': 'إيقاف التسجيل',
    'Transcribing…': 'جارٍ تحويل الصوت إلى نص…',
    'Record voice message': 'تسجيل رسالة صوتية',
    'Could not start recording. Check microphone permission.':
        'تعذر بدء التسجيل. تحقق من إذن الميكروفون.',
    'No speech was recognized. Please try again.':
        'لم يتم التعرف على الكلام. حاول مرة أخرى.',
    'Transcription failed. Check the connection and try again.':
        'فشل تحويل الصوت إلى نص. تحقق من الاتصال وحاول مرة أخرى.',
    'Task': 'المهمة',
    'Recipient': 'المستلم',
    'Confirm and send': 'تأكيد وإرسال',
    'Mark complete': 'تحديد كمكتملة',
    'Contact': 'جهة الاتصال',
    'Permission': 'الإذن',
    'Waiting for reply': 'بانتظار الرد',
    'Needs review': 'بانتظار المراجعة',
    'Draft': 'مسودة',
    'Completed': 'مكتملة',
    'Cancelled': 'ملغاة',
    'Reply received': 'تم استلام الرد',
    'Voice reply': 'رد صوتي',
    'Transcript': 'النص',
    'Translation': 'الترجمة',
    'Needs permission': 'الإذن مطلوب',
  };

  @override
  void initState() {
    super.initState();
    _poll = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _refreshActivity(),
    );
  }

  @override
  void dispose() {
    _poll?.cancel();
    _recordingTimer?.cancel();
    if (_recording) unawaited(widget.controller.cancelAssistantRecording());
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _startChatRecording() async {
    if (_sending || _recording || _transcribing) return;
    try {
      await widget.controller.startAssistantRecording();
      if (!mounted) return;
      setState(() {
        _recording = true;
        _recordingSeconds = 0;
      });
      _recordingTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
        if (!mounted || !_recording) return timer.cancel();
        setState(() => _recordingSeconds++);
        if (_recordingSeconds >= 60) unawaited(_stopChatRecording());
      });
    } on FormatException catch (e) {
      _notice(e.message);
    } catch (_) {
      _notice('Could not start recording. Check microphone permission.');
    }
  }

  Future<void> _stopChatRecording() async {
    if (!_recording) return;
    _recordingTimer?.cancel();
    setState(() {
      _recording = false;
      _transcribing = true;
    });
    try {
      final wav = await widget.controller.stopAssistantRecording();
      final text = await widget.controller.transcribeAssistantRecording(wav);
      if (mounted && text.trim().isNotEmpty) {
        final existing = _input.text.trimRight();
        _input.text = existing.isEmpty
            ? text.trim()
            : '$existing ${text.trim()}';
        _input.selection = TextSelection.collapsed(offset: _input.text.length);
      } else if (mounted) {
        _notice('No speech was recognized. Please try again.');
      }
    } on FormatException catch (e) {
      _notice(e.message);
    } catch (_) {
      _notice('Transcription failed. Check the connection and try again.');
    } finally {
      if (mounted) setState(() => _transcribing = false);
    }
  }

  Future<void> _cancelChatRecording() async {
    _recordingTimer?.cancel();
    await widget.controller.cancelAssistantRecording();
    if (mounted) setState(() => _recording = false);
  }

  void _notice(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _refreshActivity() async {
    if (!widget.controller.connected || _loadingActivity) return;
    _loadingActivity = true;
    try {
      final data = await widget.controller.assistantActivity();
      if (!mounted) return;
      final tasks = (data['tasks'] as List).cast<Map<String, dynamic>>();
      final messages = (data['messages'] as List).cast<Map<String, dynamic>>();
      setState(() {
        _unread = tasks.where((task) => task['status'] == 'review').length;
        if (_open) _appendRecentReplies(messages);
      });
      if (_open) _scrollToEnd();
    } catch (_) {
      // The original inbox remains available when the assistant is offline.
    } finally {
      _loadingActivity = false;
    }
  }

  void _appendRecentReplies(List<Map<String, dynamic>> messages) {
    for (final message in messages.where(
      (item) => item['direction'] == 'inbound',
    )) {
      final id = message['id']?.toString() ?? '';
      if (id.isEmpty || _entries.any((entry) => entry.messageId == id)) {
        continue;
      }
      final transcript = message['transcript'] as String? ?? '';
      final body = message['body'] as String? ?? '';
      final translation = message['translation'] as String? ?? '';
      final display = transcript.isNotEmpty
          ? '${t('Voice reply')} · ${message['contact_name'] ?? ''}\n${t('Transcript')}: $transcript${translation.isEmpty ? '' : '\n${t('Translation')}: $translation'}'
          : body.isNotEmpty
          ? '${t('Reply received')} · ${message['contact_name'] ?? ''}\n$body'
          : '${t('Reply received')} · ${message['contact_name'] ?? ''}\n${t('No reply content is saved. Check the WhatsApp inbox before the temporary result expires.')}';
      _entries.add(_ChatEntry(role: 'assistant', text: display, messageId: id));
    }
  }

  void _setOpen(bool value) {
    setState(() {
      _open = value;
      if (value && _entries.isEmpty) {
        _entries.add(
          _ChatEntry(
            role: 'assistant',
            text: t(
              'Hello! I can help you manage WhatsApp contacts and voice follow-ups.',
            ),
          ),
        );
      }
    });
    if (value) unawaited(_refreshActivity());
  }

  Future<void> _send([String? suggestion]) async {
    final text = (suggestion ?? _input.text).trim();
    if (text.isEmpty || _sending) return;
    final history = _entries
        .where(
          (entry) =>
              entry.messageId == null &&
              (entry.role == 'user' || entry.role == 'assistant'),
        )
        .toList()
        .reversed
        .take(8)
        .toList()
        .reversed
        .map((entry) => {'role': entry.role, 'content': entry.text})
        .toList();
    setState(() {
      _entries.add(_ChatEntry(role: 'user', text: text));
      _input.clear();
      _sending = true;
    });
    _scrollToEnd();
    if (!widget.controller.connected) {
      setState(() {
        _entries.add(
          _ChatEntry(
            role: 'assistant',
            text: t('Connect your server to use the assistant.'),
          ),
        );
        _sending = false;
      });
      return;
    }
    try {
      final result = await widget.controller.assistantMessage(text, history);
      if (!mounted) return;
      setState(() {
        _entries.add(
          _ChatEntry(
            role: 'assistant',
            text: result['reply'] as String? ?? '',
            action: result['action'] as Map<String, dynamic>?,
          ),
        );
        _sending = false;
      });
      _scrollToEnd();
    } on FormatException catch (error) {
      if (!mounted) return;
      setState(() {
        _entries.add(_ChatEntry(role: 'assistant', text: error.message));
        _sending = false;
      });
      _scrollToEnd();
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _entries.add(
          _ChatEntry(
            role: 'assistant',
            text: t(
              'Could not reach the assistant. Check the server and try again.',
            ),
          ),
        );
        _sending = false;
      });
    }
  }

  void _scrollToEnd() => WidgetsBinding.instance.addPostFrameCallback((_) {
    if (_scroll.hasClients) {
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
      );
    }
  });

  Future<void> _confirmSend(String taskId) async {
    if (_sending) return;
    setState(() {
      _sending = true;
      _entries.add(_ChatEntry(role: 'user', text: t('Confirm and send')));
    });
    _scrollToEnd();
    try {
      await widget.controller.sendFollowup(taskId);
      if (!mounted) return;
      setState(() {
        _entries.add(
          _ChatEntry(
            role: 'assistant',
            text: t(
              'Invitation submitted. Waiting for WhatsApp delivery confirmation.',
            ),
          ),
        );
        _sending = false;
      });
      unawaited(_refreshActivity());
    } on FormatException catch (error) {
      if (!mounted) return;
      setState(() {
        _entries.add(_ChatEntry(role: 'assistant', text: error.message));
        _sending = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _entries.add(
          _ChatEntry(
            role: 'assistant',
            text: t(
              'Could not send the invitation. Check WhatsApp settings and try again.',
            ),
          ),
        );
        _sending = false;
      });
    }
    _scrollToEnd();
  }

  Future<void> _confirmComplete(String taskId) async {
    if (_sending) return;
    setState(() {
      _sending = true;
      _entries.add(_ChatEntry(role: 'user', text: t('Mark complete')));
    });
    try {
      await widget.controller.completeFollowup(taskId);
      if (!mounted) return;
      setState(() {
        _entries.add(
          _ChatEntry(role: 'assistant', text: t('Follow-up marked complete.')),
        );
        _sending = false;
      });
      unawaited(_refreshActivity());
    } on FormatException catch (error) {
      if (!mounted) return;
      setState(() {
        _entries.add(_ChatEntry(role: 'assistant', text: error.message));
        _sending = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _entries.add(
          _ChatEntry(
            role: 'assistant',
            text: t('Could not update the follow-up. Refresh and try again.'),
          ),
        );
        _sending = false;
      });
    }
    _scrollToEnd();
  }

  Future<void> _recordConsent(Map<String, dynamic> contact) async {
    if (_sending) return;
    final decision = await showDialog<Map<String, String>>(
      context: context,
      builder: (_) => _ConsentDialog(contact: contact),
    );
    if (decision == null || !mounted || _sending) return;
    setState(() => _sending = true);
    var message =
        'Permission saved. Create a fresh follow-up to review its recipient and template.';
    try {
      await widget.controller.recordContactConsent(
        contact['id'] as String,
        decision['consent']!,
        decision['source']!,
      );
      contact['consent'] = decision['consent'];
    } on FormatException catch (error) {
      message = error.message;
    } catch (_) {
      message = 'Could not save permission. Refresh and try again.';
    }
    if (!mounted) return;
    setState(() {
      _sending = false;
      _entries.add(_ChatEntry(role: 'assistant', text: message));
    });
    _scrollToEnd();
  }

  Widget _actionCard(Map<String, dynamic>? action) {
    if (action == null) return const SizedBox.shrink();
    final type = action['type'];
    if (type == 'draft') {
      final task = action['task'] as Map<String, dynamic>;
      final contact = action['contact'] as Map<String, dynamic>;
      final templatePreview = action['template_preview'] as String? ?? '';
      final canSend = action['can_send'] == true && templatePreview.isNotEmpty;
      final blockedReason = action['reason'] as String? ?? '';
      return _CardBox(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '${t('Task')}: ${task['title']}',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(
              '${t('Recipient')}: ${contact['name']} · +••••${(contact['wa_id'] as String).substring((contact['wa_id'] as String).length - 4)}',
            ),
            const SizedBox(height: 10),
            Text(
              t('WhatsApp template preview'),
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 5),
            Text(
              templatePreview.isNotEmpty
                  ? templatePreview
                  : t(
                      'No verified template preview is available. Create a fresh draft after checking WhatsApp settings.',
                    ),
            ),
            if (!canSend) ...[
              const SizedBox(height: 8),
              Text(
                blockedReason.isNotEmpty
                    ? t(blockedReason)
                    : contact['consent'] != 'granted'
                    ? t(
                        'The contact has not confirmed permission to receive WhatsApp messages.',
                      )
                    : t('WhatsApp setup or approved template is missing.'),
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 10),
            FilledButton(
              onPressed: canSend && !_sending
                  ? () => _confirmSend(task['id'] as String)
                  : null,
              child: Text(t('Confirm and send')),
            ),
            if (contact['consent'] != 'granted')
              TextButton(
                onPressed: _sending ? null : () => _recordConsent(contact),
                child: const Text('Record permission'),
              ),
          ],
        ),
      );
    }
    if (type == 'complete_confirmation') {
      final task = action['task'] as Map<String, dynamic>;
      return _CardBox(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '${t('Follow-up')}: ${task['contact_name']} · ${task['title']}',
            ),
            const SizedBox(height: 6),
            Text(
              t(
                'This only marks the internal follow-up complete. It sends no message.',
              ),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: _sending
                  ? null
                  : () => _confirmComplete(task['id'] as String),
              child: Text(t('Mark complete')),
            ),
          ],
        ),
      );
    }
    if (type == 'contact_created' || type == 'consent_confirmation') {
      final contact = action['item'] as Map<String, dynamic>;
      return _CardBox(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${t('Contact')}: ${contact['name']} · ${t('Permission')}: ${contact['consent']}',
            ),
            TextButton(
              onPressed: _sending ? null : () => _recordConsent(contact),
              child: const Text('Record permission'),
            ),
          ],
        ),
      );
    }
    if (type == 'contact_updated') {
      final contact = action['item'] as Map<String, dynamic>;
      final status = contact['consent'] == 'granted'
          ? t('Saved')
          : t('Needs permission');
      return _CardBox(
        child: Text('${t('Contact')}: ${contact['name']} · $status'),
      );
    }
    if (type == 'contact_choices') {
      final items = (action['items'] as List).cast<Map<String, dynamic>>();
      if (items.isEmpty) return const SizedBox.shrink();
      return _CardBox(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ...items.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: OutlinedButton(
                  onPressed: () =>
                      _send('${t('Create a follow-up')} for ${item['name']}'),
                  child: Text(
                    '${item['name']} · ••••${(item['wa_id'] as String).substring((item['wa_id'] as String).length - 4)}',
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    }
    if (type == 'tasks' || type == 'contacts') {
      final items = (action['items'] as List).cast<Map<String, dynamic>>();
      if (items.isEmpty) return const SizedBox.shrink();
      return _CardBox(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: items.take(8).map((item) {
            if (type == 'tasks') {
              return Padding(
                padding: const EdgeInsets.only(bottom: 7),
                child: Text(
                  '${item['contact_name']} · ${item['title']} · ${t(_taskStatus(item['status'] as String? ?? 'draft'))}',
                ),
              );
            }
            return Padding(
              padding: const EdgeInsets.only(bottom: 7),
              child: Text(
                '${item['name']} · ••••${(item['wa_id'] as String).substring((item['wa_id'] as String).length - 4)}',
              ),
            );
          }).toList(),
        ),
      );
    }
    return const SizedBox.shrink();
  }

  String _taskStatus(String status) => switch (status) {
    'waiting' => 'Waiting for reply',
    'review' => 'Needs review',
    'done' => 'Completed',
    'cancelled' => 'Cancelled',
    _ => 'Draft',
  };

  Widget _panel(
    BuildContext context, {
    required bool mobile,
    required double maxHeight,
  }) {
    final config = widget.controller.whatsapp;
    final waReady =
        config['configured'] == true &&
        config['followup_template_configured'] == true;
    return Material(
      color: Theme.of(context).colorScheme.surface,
      elevation: mobile ? 0 : 12,
      borderRadius: mobile
          ? const BorderRadius.vertical(top: Radius.circular(24))
          : BorderRadius.circular(20),
      clipBehavior: Clip.antiAlias,
      child: SizedBox(
        height: maxHeight,
        width: mobile ? double.infinity : 410,
        child: Column(
          children: [
            Container(
              color: _green,
              padding: const EdgeInsetsDirectional.fromSTEB(16, 12, 8, 12),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 19,
                    backgroundColor: Colors.white.withValues(alpha: .16),
                    child: const Icon(
                      Icons.forum_rounded,
                      color: Colors.white,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          t('WhatsApp assistant'),
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Text(
                          widget.controller.connected
                              ? t('Connected')
                              : t('Connect server'),
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: .8),
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: t('Close assistant'),
                    onPressed: () => _setOpen(false),
                    icon: const Icon(Icons.close, color: Colors.white),
                  ),
                ],
              ),
            ),
            if (!widget.controller.connected)
              Container(
                width: double.infinity,
                color: Theme.of(context).colorScheme.tertiaryContainer,
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 8,
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        t('Connect your server to use the assistant.'),
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                    TextButton(
                      onPressed: _connect,
                      child: Text(t('Connect server')),
                    ),
                  ],
                ),
              )
            else if (!waReady)
              Container(
                width: double.infinity,
                color: Theme.of(context).colorScheme.tertiaryContainer,
                padding: const EdgeInsets.all(9),
                child: Text(
                  t(
                    'WhatsApp setup is incomplete. Follow-up sending needs Meta settings and an approved template.',
                  ),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(12, 14, 12, 8),
                controller: _scroll,
                children: [
                  for (final entry in _entries) _bubble(entry),
                  if (_sending)
                    Align(
                      alignment: AlignmentDirectional.centerStart,
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        child: SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: _green,
                          ),
                        ),
                      ),
                    ),
                  if (!_entries.any((entry) => entry.role == 'user') &&
                      _entries.length == 1)
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        _suggestion(
                          'Create a follow-up',
                          'Create a follow-up for Marie, ask how she is doing, and invite her to reply by voice.',
                        ),
                        _suggestion(
                          'Show pending replies',
                          'Show pending WhatsApp follow-up replies.',
                        ),
                        _suggestion('Add a contact', 'Add a WhatsApp contact.'),
                      ],
                    ),
                ],
              ),
            ),
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    if (_recording) ...[
                      IconButton(
                        tooltip: t('Cancel recording'),
                        onPressed: _cancelChatRecording,
                        icon: const Icon(Icons.close_rounded),
                      ),
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.only(bottom: 14),
                          child: Text(
                            '${t('Recording')} · 00:${_recordingSeconds.toString().padLeft(2, '0')} / 01:00',
                          ),
                        ),
                      ),
                      IconButton.filled(
                        tooltip: t('Stop recording'),
                        onPressed: _stopChatRecording,
                        style: IconButton.styleFrom(
                          backgroundColor: _green,
                          foregroundColor: Colors.white,
                        ),
                        icon: const Icon(Icons.stop_rounded),
                      ),
                    ] else ...[
                      Expanded(
                        child: TextField(
                          controller: _input,
                          minLines: 1,
                          maxLines: 4,
                          textInputAction: TextInputAction.send,
                          onSubmitted: (_) => _send(),
                          decoration: InputDecoration(
                            hintText: t('Message the assistant…'),
                            isDense: true,
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 14,
                              vertical: 12,
                            ),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(24),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        tooltip: _transcribing
                            ? t('Transcribing…')
                            : t('Record voice message'),
                        onPressed: _sending || _transcribing
                            ? null
                            : _startChatRecording,
                        icon: _transcribing
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.mic_none_rounded),
                      ),
                      IconButton.filled(
                        onPressed: _sending || _transcribing || _recording
                            ? null
                            : () => _send(),
                        style: IconButton.styleFrom(
                          backgroundColor: _green,
                          foregroundColor: Colors.white,
                        ),
                        tooltip: t('Send'),
                        icon: const Icon(Icons.arrow_upward_rounded),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _bubble(_ChatEntry entry) {
    final isUser = entry.role == 'user';
    final color = isUser
        ? const Color(0xFFE1F1EA)
        : Theme.of(context).colorScheme.surfaceContainerHighest;
    return Align(
      alignment: isUser
          ? AlignmentDirectional.centerEnd
          : AlignmentDirectional.centerStart,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        constraints: const BoxConstraints(maxWidth: 340),
        child: Column(
          crossAxisAlignment: isUser
              ? CrossAxisAlignment.end
              : CrossAxisAlignment.start,
          children: [
            Container(
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(16),
              ),
              padding: const EdgeInsets.all(11),
              child: SelectableText(entry.text),
            ),
            if (entry.action != null)
              Padding(
                padding: const EdgeInsetsDirectional.only(top: 6),
                child: _actionCard(entry.action),
              ),
          ],
        ),
      ),
    );
  }

  Widget _suggestion(String label, String prompt) => ActionChip(
    label: Text(t(label)),
    onPressed: _sending ? null : () => _send(prompt),
  );

  void _connect() => widget.navigatorKey.currentState?.push(
    MaterialPageRoute<void>(
      builder: (_) => ConnectionPage(controller: widget.controller),
    ),
  );

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final mobile = constraints.maxWidth < 600;
      final media = MediaQuery.of(context);
      final safeBottom = media.padding.bottom;
      final keyboard = media.viewInsets.bottom;
      final available =
          (constraints.maxHeight - media.padding.top - safeBottom - keyboard)
              .clamp(240.0, 900.0)
              .toDouble();
      final panelHeight = mobile
          ? (available - 14).clamp(300.0, 680.0).toDouble()
          : available.clamp(360.0, 640.0).toDouble();
      return Stack(
        fit: StackFit.expand,
        children: [
          widget.child,
          if (_open && mobile)
            Positioned.fill(
              child: GestureDetector(
                onTap: () => _setOpen(false),
                child: ColoredBox(color: Colors.black.withValues(alpha: .26)),
              ),
            ),
          if (_open)
            if (mobile)
              Positioned(
                left: 0,
                right: 0,
                bottom: safeBottom + keyboard,
                child: _panel(context, mobile: true, maxHeight: panelHeight),
              )
            else
              Positioned(
                right: 16,
                bottom: safeBottom + 12,
                child: _panel(context, mobile: false, maxHeight: panelHeight),
              ),
          if (!_open)
            Positioned(
              right: 16,
              bottom: safeBottom + keyboard + 16,
              child: Semantics(
                button: true,
                label: t(_open ? 'Close assistant' : 'WhatsApp assistant'),
                child: Stack(
                  clipBehavior: Clip.none,
                  children: [
                    FloatingActionButton(
                      onPressed: () => _setOpen(!_open),
                      backgroundColor: _green,
                      foregroundColor: Colors.white,
                      heroTag: 'whatsapp-assistant-fab',
                      tooltip: t('WhatsApp assistant'),
                      child: Icon(
                        _open ? Icons.close_rounded : Icons.forum_rounded,
                        size: 25,
                      ),
                    ),
                    if (!_open && _unread > 0)
                      Positioned(
                        right: -3,
                        top: -3,
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.error,
                            border: Border.all(
                              color: Theme.of(context).colorScheme.surface,
                              width: 2,
                            ),
                            shape: BoxShape.circle,
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(5),
                            child: Text(
                              '$_unread',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
        ],
      );
    },
  );
}

class _ConsentDialog extends StatefulWidget {
  const _ConsentDialog({required this.contact});
  final Map<String, dynamic> contact;

  @override
  State<_ConsentDialog> createState() => _ConsentDialogState();
}

class _ConsentDialogState extends State<_ConsentDialog> {
  final _source = TextEditingController();
  String? _decision;

  @override
  void dispose() {
    _source.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Record WhatsApp permission'),
    content: SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('${widget.contact['name']} · ${widget.contact['phone']}'),
          const SizedBox(height: 12),
          const Text(
            'Record the contact’s actual permission. Saving this record does not send a message.',
          ),
          DropdownButton<String>(
            value: _decision,
            hint: const Text('Choose permission status'),
            isExpanded: true,
            items: const [
              DropdownMenuItem(
                value: 'granted',
                child: Text('Agreed to WhatsApp messages'),
              ),
              DropdownMenuItem(value: 'revoked', child: Text('Opted out')),
              DropdownMenuItem(value: 'unknown', child: Text('Unknown')),
            ],
            onChanged: (value) => setState(() => _decision = value),
          ),
          TextField(
            controller: _source,
            maxLength: 240,
            decoration: const InputDecoration(
              labelText: 'Permission source (required for agreement)',
            ),
            onChanged: (_) => setState(() {}),
          ),
        ],
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      FilledButton(
        onPressed:
            _decision == null ||
                (_decision == 'granted' && _source.text.trim().isEmpty)
            ? null
            : () => Navigator.pop(context, {
                'consent': _decision!,
                'source': _source.text.trim(),
              }),
        child: const Text('Save permission'),
      ),
    ],
  );
}

class _ChatEntry {
  const _ChatEntry({
    required this.role,
    required this.text,
    this.action,
    this.messageId,
  });
  final String role;
  final String text;
  final Map<String, dynamic>? action;
  final String? messageId;
}

class _CardBox extends StatelessWidget {
  const _CardBox({required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) => Card(
    color: Theme.of(context).colorScheme.surface,
    margin: EdgeInsets.zero,
    child: Padding(padding: const EdgeInsets.all(12), child: child),
  );
}
