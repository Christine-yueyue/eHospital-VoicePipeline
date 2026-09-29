import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:voice_notes/inbox_page.dart';
import 'package:voice_notes/voice_controller.dart';

const config = {
  'version': '4.0.0',
  'max_upload_bytes': 20000000,
  'whatsapp': {'configured': true, 'target_language': 'fr'},
};

Map<String, dynamic> callResult() => {
  'id': 'call:wacid.test',
  'kind': 'call_transcript',
  'call_id': 'wacid.test',
  'sender': '…0123',
  'target': 'fr',
  'created': 1790000000,
  'status': 'completed',
  'stage': '',
  'transcript': '[Business] Your table is booked. [Customer] Thank you.',
  'translation': '[Business] Votre table est réservée. [Customer] Merci.',
  'error': '',
  'details': {
    'language': 'en',
    'duration': 12.5,
    'segments': [
      {
        'speaker': 'Business',
        'start': 0.4,
        'end': 2.7,
        'text': 'Your table is booked.',
      },
      {'speaker': 'Customer', 'start': 3.2, 'end': 4.8, 'text': 'Thank you.'},
    ],
  },
};

void main() {
  testWidgets('v4 rejects the v3 backend to keep the versions separate', (
    tester,
  ) async {
    final controller = VoiceController(
      client: MockClient(
        (request) async =>
            http.Response(jsonEncode({...config, 'version': '3.0.0'}), 200),
      ),
    );
    expect(
      await controller.connectToBackend('https://voice.example.com', 'test'),
      isFalse,
    );
    expect(controller.error, contains('v4 backend'));
    expect(controller.connected, isFalse);
    controller.dispose();
    await tester.pumpAndSettle();
  });

  testWidgets(
    'call transcript, translation and speaker timeline fit an iPhone',
    (tester) async {
      tester.view.physicalSize = const Size(390, 1100);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final row = callResult();
      final controller = VoiceController(
        client: MockClient((request) async {
          expect(request.headers['Authorization'], 'Bearer app-test');
          return http.Response(
            jsonEncode(
              request.url.path == '/api/config'
                  ? config
                  : {
                      'whatsapp': config['whatsapp'],
                      'messages': [row],
                    },
            ),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }),
      );
      await controller.connectToBackend(
        'https://voice.example.com',
        'app-test',
      );
      await tester.pumpWidget(
        MaterialApp(home: InboxPage(controller: controller)),
      );
      await tester.pumpAndSettle();
      expect(find.text('Call transcript · Meta'), findsOneWidget);
      expect(
        find.text('Detected language: en · Duration: 0:12'),
        findsOneWidget,
      );
      expect(find.text(row['transcript'] as String), findsOneWidget);
      expect(find.text(row['translation'] as String), findsOneWidget);
      await tester.ensureVisible(find.text('Speaker timeline (2)'));
      await tester.tap(find.text('Speaker timeline (2)'));
      await tester.pumpAndSettle();
      expect(find.text('Business · 0:00–0:02'), findsOneWidget);
      expect(find.text('Customer · 0:03–0:04'), findsOneWidget);
      expect(find.text('Thank you.'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      controller.dispose();
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'call progress polls and partial translation retry uses the call ID',
    (tester) async {
      var row = callResult()
        ..addAll({
          'status': 'processing',
          'stage': 'fetching_transcript',
          'transcript': '',
          'translation': '',
          'details': <String, dynamic>{},
        });
      var retried = false;
      final controller = VoiceController(
        client: MockClient((request) async {
          if (request.url.path == '/api/config') {
            return http.Response(jsonEncode(config), 200);
          }
          if (request.url.path == '/api/whatsapp/retry') {
            expect(jsonDecode(request.body)['id'], 'call:wacid.test');
            retried = true;
            row = callResult();
            return http.Response('{"success":true}', 200);
          }
          return http.Response(
            jsonEncode({
              'whatsapp': config['whatsapp'],
              'messages': [row],
            }),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }),
      );
      await controller.connectToBackend(
        'https://voice.example.com',
        'app-test',
      );
      await tester.pumpWidget(
        MaterialApp(home: InboxPage(controller: controller)),
      );
      await tester.pump();
      await tester.pump();
      expect(find.text('Fetching Meta transcript…'), findsOneWidget);
      row = callResult()
        ..addAll({
          'status': 'partial',
          'translation': '',
          'error': 'Translation failed',
        });
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();
      expect(
        find.text('Transcript ready · translation needs retry'),
        findsOneWidget,
      );
      expect(find.text(row['transcript'] as String), findsOneWidget);
      await tester.ensureVisible(find.text('Retry'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(retried, isTrue);
      expect(find.text('Ready'), findsOneWidget);
      expect(find.text(row['translation'] as String), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      controller.dispose();
      await tester.pumpAndSettle();
    },
  );
}
