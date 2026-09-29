import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_notes/main.dart';

void main() {
  testWidgets('French default and English switch work on a narrow screen', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const VoiceNotesApp());
    await tester.pumpAndSettle();

    expect(find.text('French / Français'), findsOneWidget);
    expect(find.text('Start speaking'), findsOneWidget);
    final upload = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Transcribe & translate'),
    );
    expect(upload.onPressed, isNull);
    expect(tester.takeException(), isNull);

    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('English').last);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('English translation'), 300);
    expect(find.text('English translation'), findsOneWidget);
    expect(tester.takeException(), isNull);

    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
  });
}
