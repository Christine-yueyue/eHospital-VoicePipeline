/// Converts a Toronto wall-clock time to an ISO-8601 value with its explicit
/// America/Toronto UTC offset. The scheduling form only allows dates up to two
/// years ahead, so the post-2007 North American DST rules apply.
class TorontoTime {
  TorontoTime._();

  /// Returns the UTC offset for a Toronto wall-clock date and time.
  ///
  /// The spring-forward gap (02:00–02:59) is rejected. During the repeated
  /// fall-back hour, the first occurrence (EDT, UTC-04:00) is selected.
  static Duration utcOffsetForWallTime({
    required int year,
    required int month,
    required int day,
    required int hour,
    required int minute,
  }) {
    final wall = DateTime.utc(year, month, day, hour, minute);
    if (wall.year != year || wall.month != month || wall.day != day ||
        wall.hour != hour || wall.minute != minute) {
      throw ArgumentError('Invalid Toronto wall-clock date or time.');
    }

    final springDay = _nthSunday(year, 3, 2);
    final fallDay = _nthSunday(year, 11, 1);
    final afterSpringGap = month > 3 || (month == 3 &&
        (day > springDay || (day == springDay && hour >= 3)));
    final beforeFallTransition = month < 11 || (month == 11 &&
        (day < fallDay || (day == fallDay && hour < 1)));

    if (month == 3 && day == springDay && hour == 2) {
      throw ArgumentError('That local time does not exist in America/Toronto.');
    }
    final daylight = afterSpringGap && beforeFallTransition ||
        month == 11 && day == fallDay && hour == 1;
    return Duration(hours: daylight ? -4 : -5);
  }

  /// Serializes the wall-clock components with the corresponding Toronto
  /// offset, independent of the device's configured time zone.
  static String toIso8601({
    required int year,
    required int month,
    required int day,
    required int hour,
    required int minute,
  }) {
    final offset = utcOffsetForWallTime(
      year: year,
      month: month,
      day: day,
      hour: hour,
      minute: minute,
    );
    final sign = offset.isNegative ? '-' : '+';
    final minutes = offset.inMinutes.abs();
    final hoursText = (minutes ~/ 60).toString().padLeft(2, '0');
    final minutesText = (minutes % 60).toString().padLeft(2, '0');
    final date = DateTime.utc(year, month, day, hour, minute);
    final wallText = date.toIso8601String().substring(0, 16);
    return '$wallText$sign$hoursText:$minutesText';
  }

  static bool isFutureWallTime({
    required int year,
    required int month,
    required int day,
    required int hour,
    required int minute,
    required DateTime now,
  }) => DateTime.parse(toIso8601(
    year: year,
    month: month,
    day: day,
    hour: hour,
    minute: minute,
  )).isAfter(now.toUtc());

  /// Converts a UTC instant into Toronto wall-clock components. The returned
  /// DateTime is UTC-backed only to keep these components independent of the
  /// device zone; callers should use its fields for display.
  static DateTime toWallTime(DateTime instant) {
    final utc = instant.toUtc();
    final springDay = _nthSunday(utc.year, 3, 2);
    final fallDay = _nthSunday(utc.year, 11, 1);
    final springTransition = DateTime.utc(utc.year, 3, springDay, 7);
    final fallTransition = DateTime.utc(utc.year, 11, fallDay, 6);
    final daylight = !utc.isBefore(springTransition) && utc.isBefore(fallTransition);
    return utc.add(Duration(hours: daylight ? -4 : -5));
  }

  static int _nthSunday(int year, int month, int occurrence) {
    final firstWeekday = DateTime.utc(year, month, 1).weekday;
    final firstSunday = 1 + (DateTime.sunday - firstWeekday) % 7;
    return firstSunday + (occurrence - 1) * 7;
  }
}
