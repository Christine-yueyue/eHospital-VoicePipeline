import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:voice_notes/connection_page.dart';
import 'package:voice_notes/inbox_page.dart';
import 'package:voice_notes/voice_controller.dart';

const config = {
  'version': '4.0.0',
  'max_upload_bytes': 20000000,
  'whatsapp': {'configured': true, 'target_language': 'fr'},
};

void main() {
  test('Only HTTPS or local debug addresses accepted', () {
    expect(
      VoiceController.validateAddress('https://voice.example.com'),
      isNull,
    );
    expect(VoiceController.validateAddress('http://127.0.0.1:8000'), isNull);
    expect(VoiceController.validateAddress('http://192.168.1.20:8004'), isNull);
    for (final address in [
      'http://public.example.com',
      'https://user:pass@voice.example.com',
      'https://voice.example.com/api',
      'https://voice.example.com?token=secret',
      'bad address',
    ]) {
      expect(VoiceController.validateAddress(address), isNotNull);
    }
  });

  testWidgets(
    'Connect authenticates without embedding token in URL; disconnect clears state',
    (tester) async {
      final requests = <http.Request>[];
      final controller = VoiceController(
        client: MockClient((request) async {
          requests.add(request);
          return http.Response(jsonEncode(config), 200);
        }),
      );
      expect(
        await controller.connectToBackend(
          'https://voice.example.com',
          'app-secret',
        ),
        isTrue,
      );
      expect(requests.single.headers['Authorization'], 'Bearer app-secret');
      expect(
        requests.single.url.toString(),
        'https://voice.example.com/api/config',
      );
      expect(controller.connected, isTrue);
      controller.transcript = 'private';
      controller.disconnect();
      expect(controller.connected, isFalse);
      expect(controller.transcript, isEmpty);
      controller.dispose();
      await tester.pumpAndSettle();
    },
  );

  testWidgets('Wrong token leaves app disconnected and shows a useful error', (
    tester,
  ) async {
    final controller = VoiceController(
      client: MockClient(
        (request) async => http.Response(
          jsonEncode({'error': 'Enter the correct app access token.'}),
          401,
        ),
      ),
    );
    await tester.pumpWidget(
      MaterialApp(home: ConnectionPage(controller: controller)),
    );
    await tester.enterText(
      find.byType(TextField).at(0),
      'https://voice.example.com',
    );
    await tester.enterText(find.byType(TextField).at(1), 'wrong');
    await tester.tap(find.text('Connect'));
    await tester.pumpAndSettle();
    expect(find.text('Enter the correct app access token.'), findsOneWidget);
    expect(controller.connected, isFalse);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
    await tester.pumpAndSettle();
  });

  testWidgets('Rejects v2 before enabling app actions', (tester) async {
    final controller = VoiceController(
      client: MockClient(
        (request) async =>
            http.Response(jsonEncode({'max_upload_bytes': 20000000}), 200),
      ),
    );
    expect(
      await controller.connectToBackend('https://voice.example.com', 'test'),
      isFalse,
    );
    expect(controller.error, contains('v4 backend'));
    controller.dispose();
    await tester.pumpAndSettle();
  });

  testWidgets(
    'Inbox displays transcript and translation and deletes after confirmation',
    (tester) async {
      tester.view.physicalSize = const Size(390, 1100);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      var deleted = false;
      final controller = VoiceController(
        client: MockClient((request) async {
          expect(request.headers['Authorization'], 'Bearer app-secret');
          if (request.url.path == '/api/config') {
            return http.Response(jsonEncode(config), 200);
          }
          if (request.url.path == '/api/whatsapp/delete') {
            expect(jsonDecode(request.body)['id'], 'wamid.test');
            deleted = true;
            return http.Response('{"success":true}', 200);
          }
          return http.Response(
            jsonEncode({
              'whatsapp': config['whatsapp'],
              'messages': deleted
                  ? []
                  : [
                      {
                        'id': 'wamid.test',
                        'sender': '…0123',
                        'target': 'fr',
                        'created': 1790000000,
                        'status': 'completed',
                        'transcript': 'Friday at three.',
                        'translation': 'Vendredi à quinze heures.',
                        'error': '',
                      },
                    ],
            }),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }),
      );
      await controller.connectToBackend(
        'https://voice.example.com',
        'app-secret',
      );
      await tester.pumpWidget(
        MaterialApp(home: InboxPage(controller: controller)),
      );
      await tester.pumpAndSettle();
      expect(controller.connected, isTrue);
      expect(find.text('Friday at three.'), findsOneWidget);
      expect(find.text('Vendredi à quinze heures.'), findsOneWidget);
      await tester.ensureVisible(find.text('Delete'));
      await tester.tap(find.text('Delete'));
      await tester.pumpAndSettle();
      expect(deleted, isFalse);
      await tester.tap(find.widgetWithText(FilledButton, 'Delete'));
      await tester.pumpAndSettle();
      expect(deleted, isTrue);
      expect(find.text('No calls or voice messages yet.'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      controller.dispose();
      await tester.pumpAndSettle();
    },
  );
}
