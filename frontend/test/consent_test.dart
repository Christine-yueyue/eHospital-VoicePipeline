import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:voice_notes/assistant_overlay.dart';
import 'package:voice_notes/voice_controller.dart';

void main() {
  testWidgets('Consent requires operator selection and evidence; saving never sends', (tester) async {
    tester.view.physicalSize = const Size(1200, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final writes = <http.Request>[];
    final controller = VoiceController(client: MockClient((request) async {
      expect(request.headers['Authorization'], 'Bearer test-token');
      if (request.url.path == '/api/config') {
        return http.Response(jsonEncode({
          'version': '3.3.0', 'max_upload_bytes': 20000000,
          'whatsapp': {'configured': true},
        }), 200);
      }
      if (request.url.path == '/api/whatsapp/assistant/activity') {
        return http.Response('{"messages":[],"tasks":[]}', 200);
      }
      writes.add(request);
      if (request.url.path == '/api/whatsapp/assistant/message') {
        return http.Response(jsonEncode({
          'reply': 'The contact was saved with permission unknown.',
          'action': {
            'type': 'contact_created',
            'item': {'id': 'contact-test', 'name': 'Pat Test',
                     'phone': '+14165550123', 'consent': 'unknown'},
          },
        }), 200);
      }
      expect(request.url.path, '/api/whatsapp/contacts/consent');
      return http.Response('{"success":true}', 200);
    }));
    await controller.connectToBackend('https://voice.example.com', 'test-token');
    final navigator = GlobalKey<NavigatorState>();
    await tester.pumpWidget(MaterialApp(
      navigatorKey: navigator,
      home: AssistantOverlay(
        controller: controller, navigatorKey: navigator,
        child: const Scaffold(body: Text('Voice Notes')),
      ),
    ));
    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Add Pat Test');
    await tester.testTextInput.receiveAction(TextInputAction.send);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Record permission'));
    await tester.tap(find.text('Record permission'));
    await tester.pumpAndSettle();
    FilledButton saveButton() => tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Save permission'),
    );
    expect(saveButton().onPressed, isNull);
    await tester.tap(find.text('Choose permission status'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Agreed to WhatsApp messages').last);
    await tester.pumpAndSettle();
    expect(saveButton().onPressed, isNull);
    final evidence = find.descendant(of: find.byType(AlertDialog), matching: find.byType(TextField));
    await tester.enterText(evidence, 'Signed intake form');
    await tester.pumpAndSettle();
    expect(saveButton().onPressed, isNotNull);
    expect(writes.length, 1);
    await tester.tap(find.text('Save permission'));
    await tester.pumpAndSettle();
    expect(writes.length, 2);
    expect(jsonDecode(writes.last.body), {
      'id': 'contact-test', 'consent': 'granted', 'source': 'Signed intake form',
    });
    expect(writes.any((request) => request.url.path.endsWith('/followups/send')), isFalse);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
    await tester.pumpAndSettle();
  });
}
