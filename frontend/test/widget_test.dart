import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:voice_notes/main.dart';

void main() {
  testWidgets('language selector switches the page to Arabic RTL', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const VoiceNotesApp());
    await tester.pumpAndSettle();

    expect(find.text('Your voice, in two languages.'), findsOneWidget);
    expect(find.text('Save to Database'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Start speaking'), 300);
    expect(find.text('Start speaking'), findsOneWidget);
    final upload = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Upload & transcribe'),
    );
    expect(upload.onPressed, isNull);
    expect(tester.takeException(), isNull);

    final picker = tester.widget<DropdownButton<String>>(
      find.byKey(const Key('language-picker')),
    );
    picker.onChanged!('ar');
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView).first, const Offset(0, 3000));
    await tester.pumpAndSettle();
    expect(find.text('صوتك بلغتين.'), findsOneWidget);
    expect(find.text('حفظ في قاعدة البيانات'), findsOneWidget);
    expect(
      Directionality.of(tester.element(find.text('صوتك بلغتين.'))),
      TextDirection.rtl,
    );
    expect(tester.takeException(), isNull);

    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
  });
}
