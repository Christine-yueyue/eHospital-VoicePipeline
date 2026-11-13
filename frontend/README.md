# Voice Notes frontend

This Flutter app provides Upload, Speak Live, and the WhatsApp inbox. For complete backend, Meta, database, iOS, and verification instructions, see the [project README](../README.md).

## Run locally

Use Flutter with Dart 3.10 or newer. From this directory:

```bash
flutter pub get
flutter run -d chrome --web-port 5174
```

If Chrome is not available as a Flutter device, run `flutter run -d web-server --web-port 5174 --web-hostname 127.0.0.1` and open `http://127.0.0.1:5174`. **Connection settings** defaults to the deployed backend at `https://ehospitalbackend.com/voice`; the `/voice` path is supported for API and WebSocket requests. For local development, replace it with `http://127.0.0.1:8003` and enter the local `APP_ACCESS_TOKEN` from `backend/.env`.
