import 'package:flutter/material.dart';

import 'toronto_time.dart';
import 'voice_controller.dart';

Future<void> showScheduledMessagesSheet(
  BuildContext context,
  VoiceController controller,
) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  useSafeArea: true,
  builder: (_) => FractionallySizedBox(
    heightFactor: .94,
    child: ScheduledMessagesSheet(controller: controller),
  ),
);

class ScheduledMessagesSheet extends StatefulWidget {
  const ScheduledMessagesSheet({super.key, required this.controller});
  final VoiceController controller;

  @override
  State<ScheduledMessagesSheet> createState() => _ScheduledMessagesSheetState();
}

class _ScheduledMessagesSheetState extends State<ScheduledMessagesSheet> {
  bool _loading = true;
  bool _saving = false;
  String? _error;
  List<Map<String, dynamic>> _contacts = [];
  List<Map<String, dynamic>> _templates = [];
  List<Map<String, dynamic>> _schedules = [];
  final Set<String> _selectedContacts = {};
  String? _selectedTemplate;
  List<TextEditingController> _parameters = [];
  late DateTime _date;
  late TimeOfDay _time;

  String t(String text) => widget.controller.t(text);

  Map<String, dynamic>? get _template {
    for (final item in _templates) {
      if (_templateKey(item) == _selectedTemplate) return item;
    }
    return null;
  }

  String _templateKey(Map<String, dynamic> item) =>
      '${item['name']}|${item['language']}';

  @override
  void initState() {
    super.initState();
    final initialTorontoTime = TorontoTime.toWallTime(
      DateTime.now().add(const Duration(minutes: 5)),
    );
    _date = DateTime(
      initialTorontoTime.year,
      initialTorontoTime.month,
      initialTorontoTime.day,
    );
    _time = TimeOfDay.fromDateTime(initialTorontoTime);
    _refresh();
  }

  @override
  void dispose() {
    for (final controller in _parameters) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _refresh() async {
    if (!widget.controller.connected) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final values = await Future.wait([
        widget.controller.assistantActivity(),
        widget.controller.approvedScheduleTemplates(),
        widget.controller.scheduledMessages(),
      ]);
      if (!mounted) return;
      final activity = values[0] as Map<String, dynamic>;
      final contacts = (activity['contacts'] as List)
          .cast<Map<String, dynamic>>()
          .where((contact) => contact['consent'] == 'granted')
          .toList();
      final templates = values[1] as List<Map<String, dynamic>>;
      setState(() {
        _contacts = contacts;
        _templates = templates;
        _schedules = values[2] as List<Map<String, dynamic>>;
        if (_selectedTemplate == null && templates.isNotEmpty) {
          _selectTemplate(_templateKey(templates.first));
        } else if (_selectedTemplate != null &&
            !templates.any((item) => _templateKey(item) == _selectedTemplate)) {
          _selectTemplate(templates.isEmpty ? null : _templateKey(templates.first));
        }
      });
    } on FormatException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = t('Could not load scheduled messages.'));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _selectTemplate(String? key) {
    for (final controller in _parameters) {
      controller.dispose();
    }
    final selected = _templates.where((item) => _templateKey(item) == key);
    final count = selected.isEmpty ? 0 : (selected.first['parameter_count'] as num).toInt();
    _parameters = List.generate(count, (_) => TextEditingController());
    _selectedTemplate = key;
  }

  DateTime get _scheduledLocal => DateTime(
    _date.year,
    _date.month,
    _date.day,
    _time.hour,
    _time.minute,
  );

  Future<void> _pickDate() async {
    final now = TorontoTime.toWallTime(DateTime.now());
    final value = await showDatePicker(
      context: context,
      initialDate: _date.isBefore(DateTime(now.year, now.month, now.day))
          ? now
          : _date,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: DateTime(now.year + 2, now.month, now.day),
    );
    if (value != null && mounted) setState(() => _date = value);
  }

  Future<void> _pickTime() async {
    final value = await showTimePicker(context: context, initialTime: _time);
    if (value != null && mounted) setState(() => _time = value);
  }

  Future<void> _create() async {
    final template = _template;
    if (_selectedContacts.isEmpty) {
      setState(() => _error = t('Select at least one contact with recorded permission.'));
      return;
    }
    if (template == null) {
      setState(() => _error = t('Choose an approved WhatsApp template.'));
      return;
    }
    final when = _scheduledLocal;
    String scheduledTime;
    try {
      if (!TorontoTime.isFutureWallTime(
        year: when.year,
        month: when.month,
        day: when.day,
        hour: when.hour,
        minute: when.minute,
        now: DateTime.now(),
      )) {
        setState(() => _error = t('Choose a future date and time.'));
        return;
      }
      scheduledTime = TorontoTime.toIso8601(
        year: when.year,
        month: when.month,
        day: when.day,
        hour: when.hour,
        minute: when.minute,
      );
    } on ArgumentError {
      setState(() => _error = t('Choose a valid Toronto local time.'));
      return;
    }
    final parameters = _parameters.map((item) => item.text.trim()).toList();
    if (parameters.any((value) => value.isEmpty)) {
      setState(() => _error = t('Enter a value for each template parameter.'));
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final recipients = _contacts
          .where((contact) => _selectedContacts.contains(contact['id']))
          .map((contact) => (contact['wa_id'] ?? contact['phone']) as String)
          .toList();
      await widget.controller.createScheduledMessage(
        recipients: recipients,
        templateName: template['name'] as String,
        templateLanguage: template['language'] as String,
        templateParameters: parameters,
        scheduledTime: scheduledTime,
      );
      await _refresh();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(t('Scheduled message saved.'))),
      );
    } on FormatException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) setState(() => _error = t('Could not schedule this message.'));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  String _status(String value) => switch (value) {
    'pending' => t('Pending'),
    'processing' => t('Sending'),
    'submitted' => t('Submitted to WhatsApp'),
    'failed' => t('Failed'),
    'unknown' => t('Outcome unknown · check WhatsApp before retrying'),
    'partial' => t('Partially completed'),
    _ => value,
  };

  String _scheduleDate(String raw) {
    final value = TorontoTime.toWallTime(DateTime.parse(raw));
    final localizations = MaterialLocalizations.of(context);
    return '${localizations.formatMediumDate(value)} · ${localizations.formatTimeOfDay(TimeOfDay.fromDateTime(value))} · America/Toronto';
  }

  @override
  Widget build(BuildContext context) {
    final localizations = MaterialLocalizations.of(context);
    final template = _template;
    final paramCount = template == null
        ? 0
        : (template['parameter_count'] as num).toInt();
    return Scaffold(
      appBar: AppBar(
        title: Text(t('Scheduled messages')),
        leading: IconButton(
          tooltip: t('Close'),
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          IconButton(
            tooltip: t('Refresh scheduled messages'),
            onPressed: _loading ? null : _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _loading && _contacts.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                Text(t('Contacts with recorded permission')),
                const SizedBox(height: 8),
                if (_contacts.isEmpty)
                  Text(t('No contacts with recorded permission are available.'))
                else
                  ..._contacts.map((contact) {
                    final id = contact['id'] as String;
                    final number = (contact['wa_id'] ?? '') as String;
                    return CheckboxListTile(
                      key: ValueKey('schedule-contact-$id'),
                      contentPadding: EdgeInsets.zero,
                      value: _selectedContacts.contains(id),
                      onChanged: _saving
                          ? null
                          : (selected) => setState(() {
                              if (selected == true) {
                                _selectedContacts.add(id);
                              } else {
                                _selectedContacts.remove(id);
                              }
                            }),
                      title: Text(contact['name'] as String? ?? ''),
                      subtitle: Text('••••${number.length <= 4 ? number : number.substring(number.length - 4)}'),
                      controlAffinity: ListTileControlAffinity.leading,
                    );
                  }),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  key: const Key('schedule-template-picker'),
                  initialValue: _templates.any((item) => _templateKey(item) == _selectedTemplate)
                      ? _selectedTemplate
                      : null,
                  decoration: InputDecoration(labelText: t('Approved template')),
                  items: _templates.map((item) => DropdownMenuItem(
                    value: _templateKey(item),
                    child: Text('${item['name']} · ${item['language']}'),
                  )).toList(),
                  onChanged: _saving ? null : (value) => setState(() => _selectTemplate(value)),
                ),
                if (_templates.isEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(t('No supported approved templates were returned by Meta.')),
                  ),
                for (var index = 0; index < paramCount; index++) ...[
                  const SizedBox(height: 10),
                  TextField(
                    key: ValueKey('schedule-template-parameter-$index'),
                    controller: _parameters[index],
                    decoration: InputDecoration(
                      labelText: '${t('Template parameter')} {{${index + 1}}}',
                    ),
                    maxLength: 1024,
                  ),
                ],
                const SizedBox(height: 8),
                Text('${t('Scheduled time zone')}: America/Toronto'),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _saving ? null : _pickDate,
                        icon: const Icon(Icons.calendar_today_outlined),
                        label: Text(localizations.formatMediumDate(_date)),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _saving ? null : _pickTime,
                        icon: const Icon(Icons.schedule),
                        label: Text(localizations.formatTimeOfDay(_time)),
                      ),
                    ),
                  ],
                ),
                if (_error != null) ...[
                  const SizedBox(height: 8),
                  Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ],
                const SizedBox(height: 8),
                FilledButton.icon(
                  key: const Key('schedule-message-submit'),
                  onPressed: _saving || _loading || _templates.isEmpty ? null : _create,
                  icon: _saving
                      ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.send_outlined),
                  label: Text(t('Schedule message')),
                ),
                const Divider(height: 32),
                Row(
                  children: [
                    Expanded(
                      child: Text(t('Scheduled messages'), style: Theme.of(context).textTheme.titleMedium),
                    ),
                    IconButton(
                      tooltip: t('Refresh scheduled messages'),
                      onPressed: _loading ? null : _refresh,
                      icon: const Icon(Icons.refresh),
                    ),
                  ],
                ),
                if (_schedules.isEmpty)
                  Text(t('No scheduled messages yet.'))
                else
                  ..._schedules.map((schedule) {
                    final recipients = (schedule['recipients'] as List)
                        .cast<Map<String, dynamic>>()
                        .map((item) => item['contact_name'] as String? ?? '')
                        .join(', ');
                    return Card(
                      child: ListTile(
                        title: Text('${schedule['template_name']} · ${_status(schedule['status'] as String)}'),
                        subtitle: Text('$recipients\n${_scheduleDate(schedule['scheduled_time'] as String)}'),
                        isThreeLine: true,
                      ),
                    );
                  }),
              ],
            ),
    );
  }
}
