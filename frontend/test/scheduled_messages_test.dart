import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:voice_notes/assistant_overlay.dart';
import 'package:voice_notes/voice_controller.dart';

void main() {
  testWidgets('Schedules an approved template for selected contacts and refreshes status', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1200, 1500);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    var status = 'pending';
    Map<String, dynamic>? submittedBody;
    var createCalls = 0;
    var listCalls = 0;
    final controller = VoiceController(
      client: MockClient((request) async {
        expect(request.headers['Authorization'], 'Bearer test-token');
        if (request.url.path == '/api/config') {
          return http.Response(
            jsonEncode({
              'version': '3.3.0',
              'max_upload_bytes': 20000000,
              'whatsapp': {'configured': true},
            }),
            200,
          );
        }
        if (request.url.path == '/api/whatsapp/assistant/activity') {
          return http.Response(
            jsonEncode({
              'contacts': [
                {
                  'id': 'contact-1',
                  'name': 'Test Contact',
                  'wa_id': '14165550123',
                  'phone': '+14165550123',
                  'consent': 'granted',
                },
                {
                  'id': 'contact-2',
                  'name': 'No Permission',
                  'wa_id': '14165550124',
                  'consent': 'unknown',
                },
                {
                  'id': 'contact-3',
                  'name': 'Second Consented Contact',
                  'wa_id': '14165550125',
                  'consent': 'granted',
                },
              ],
              'tasks': [],
              'messages': [],
            }),
            200,
          );
        }
        if (request.url.path == '/api/whatsapp/schedules/templates') {
          return http.Response(
            jsonEncode({
              'templates': [
                {
                  'name': 'hello_world',
                  'language': 'en_US',
                  'parameter_count': 1,
                  'body': 'Hello {{1}}',
                },
                {
                  'name': 'bonjour_template',
                  'language': 'fr_FR',
                  'parameter_count': 1,
                  'body': 'Bonjour {{1}}',
                },
              ],
            }),
            200,
          );
        }
        if (request.url.path == '/api/whatsapp/schedules' &&
            request.method == 'POST') {
          createCalls++;
          submittedBody = jsonDecode(request.body) as Map<String, dynamic>;
          return http.Response(
            jsonEncode({'schedule_id': 'schedule-1', 'status': 'pending'}),
            200,
          );
        }
        if (request.url.path == '/api/whatsapp/schedules') {
          listCalls++;
          return http.Response(
            jsonEncode({
              'schedules': submittedBody == null
                  ? []
                  : [
                      {
                        'schedule_id': 'schedule-1',
                        'template_name': 'hello_world',
                        'template_language': 'en_US',
                        'scheduled_time': submittedBody!['scheduled_time'],
                        'status': status,
                        'recipients': [
                          {
                            'contact_name': 'Test Contact',
                            'status': status,
                            'phone': '+14165550123',
                          },
                        ],
                      },
                    ],
            }),
            200,
          );
        }
        fail('Unexpected request: ${request.method} ${request.url}');
      }),
    );
    expect(
      await controller.connectToBackend(
        'https://voice.example.com',
        'test-token',
      ),
      isTrue,
    );

    final navigator = GlobalKey<NavigatorState>();
    await tester.pumpWidget(
      MaterialApp(
        navigatorKey: navigator,
        home: AssistantOverlay(
          controller: controller,
          navigatorKey: navigator,
          child: const Scaffold(body: Text('Voice Notes')),
        ),
      ),
    );
    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Scheduled messages'));
    await tester.pumpAndSettle();

    expect(find.text('Test Contact'), findsOneWidget);
    expect(find.text('Second Consented Contact'), findsOneWidget);
    expect(find.text('No Permission'), findsNothing);
    await tester.tap(find.byKey(const ValueKey('schedule-contact-contact-1')));
    await tester.tap(find.byKey(const ValueKey('schedule-contact-contact-3')));
    await tester.tap(find.byKey(const Key('schedule-template-picker')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('bonjour_template · fr_FR').last);
    await tester.pumpAndSettle();
    await tester.ensureVisible(
      find.byKey(const ValueKey('schedule-template-parameter-0')),
    );
    // Empty required template parameters must stop locally without a POST.
    await tester.ensureVisible(find.byKey(const Key('schedule-message-submit')));
    await tester.tap(find.byKey(const Key('schedule-message-submit')));
    await tester.pumpAndSettle();
    expect(find.text('Enter a value for each template parameter.'), findsOneWidget);
    expect(createCalls, 0);
    await tester.enterText(
      find.byKey(const ValueKey('schedule-template-parameter-0')),
      'Pat',
    );
    await tester.ensureVisible(find.byKey(const Key('schedule-message-submit')));
    await tester.tap(find.byKey(const Key('schedule-message-submit')));
    await tester.pumpAndSettle();

    expect(submittedBody, isNotNull);
    expect(submittedBody!['recipients'], ['14165550123', '14165550125']);
    expect(submittedBody!['template_name'], 'bonjour_template');
    expect(submittedBody!['template_language'], 'fr_FR');
    expect(submittedBody!['template_parameters'], ['Pat']);
    expect(submittedBody!['timezone'], 'America/Toronto');
    expect(DateTime.parse(submittedBody!['scheduled_time'] as String).isAfter(DateTime.now()), isTrue);
    await tester.ensureVisible(find.textContaining('Pending'));
    expect(find.textContaining('Pending'), findsOneWidget);

    for (final state in {
      'submitted': 'Submitted to WhatsApp',
      'failed': 'Failed',
      'unknown': 'Outcome unknown · check WhatsApp before retrying',
    }.entries) {
      status = state.key;
      await tester.tap(find.byTooltip('Refresh scheduled messages').first);
      await tester.pumpAndSettle();
      expect(find.textContaining(state.value), findsOneWidget);
    }
    expect(createCalls, 1, reason: 'Refreshing the list must never resubmit a job.');
    expect(listCalls, greaterThanOrEqualTo(5));
    expect(tester.takeException(), isNull);

    await tester.pumpWidget(const SizedBox());
    controller.dispose();
    await tester.pumpAndSettle();
  });
}
