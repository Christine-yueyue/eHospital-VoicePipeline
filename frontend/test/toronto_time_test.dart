import 'package:flutter_test/flutter_test.dart';
import 'package:voice_notes/toronto_time.dart';

void main() {
  test('serializes Toronto winter and summer wall times with correct offsets', () {
    expect(
      TorontoTime.toIso8601(year: 2026, month: 1, day: 15, hour: 9, minute: 5),
      '2026-01-15T09:05-05:00',
    );
    expect(
      TorontoTime.toIso8601(year: 2026, month: 7, day: 15, hour: 9, minute: 5),
      '2026-07-15T09:05-04:00',
    );
  });

  test('handles both Toronto DST transitions', () {
    // In 2026 DST begins on March 8; 02:00–02:59 does not exist.
    expect(
      TorontoTime.toIso8601(year: 2026, month: 3, day: 8, hour: 1, minute: 59),
      '2026-03-08T01:59-05:00',
    );
    expect(
      () => TorontoTime.toIso8601(year: 2026, month: 3, day: 8, hour: 2, minute: 30),
      throwsArgumentError,
    );
    expect(
      TorontoTime.toIso8601(year: 2026, month: 3, day: 8, hour: 3, minute: 0),
      '2026-03-08T03:00-04:00',
    );

    // The repeated fall-back hour uses its first occurrence (EDT).
    expect(
      TorontoTime.toIso8601(year: 2026, month: 11, day: 1, hour: 1, minute: 30),
      '2026-11-01T01:30-04:00',
    );
    expect(
      TorontoTime.toIso8601(year: 2026, month: 11, day: 1, hour: 2, minute: 0),
      '2026-11-01T02:00-05:00',
    );
  });

  test('converts UTC instants back to Toronto wall time around DST', () {
    expect(
      TorontoTime.toWallTime(DateTime.parse('2026-03-08T07:00:00Z')),
      DateTime.utc(2026, 3, 8, 3),
    );
    expect(
      TorontoTime.toWallTime(DateTime.parse('2026-11-01T06:00:00Z')),
      DateTime.utc(2026, 11, 1, 1),
    );
  });

  test('rejects past Toronto wall times against an absolute current instant', () {
    final now = DateTime.utc(2026, 7, 15, 14);
    expect(
      TorontoTime.isFutureWallTime(
        year: 2026,
        month: 7,
        day: 15,
        hour: 9,
        minute: 59,
        now: now,
      ),
      isFalse,
    );
    expect(
      TorontoTime.isFutureWallTime(
        year: 2026,
        month: 7,
        day: 15,
        hour: 10,
        minute: 1,
        now: now,
      ),
      isTrue,
    );
  });
}
