/// Reusable UI copy catalog. Add English keys and translations here as pages grow.
class AppStrings {
  AppStrings._();

  static const Map<String, Map<String, String>> _copy = {
    'fr': {
      'Connection settings': 'Paramètres de connexion',
      'Ready when you are': 'Prêt quand vous l’êtes',
      'Transcribing and translating your file…':
          'Transcription et traduction du fichier…',
      'Connecting to live translation…': 'Connexion à la traduction en direct…',
      'Listening · speak naturally': 'Écoute · parlez naturellement',
      'Finishing the last words…': 'Finalisation des derniers mots…',
      'Connected to your server': 'Connecté à votre serveur',
      'Connect your server to get started':
          'Connectez votre serveur pour commencer',
      'Connect server': 'Connecter le serveur',
      'WhatsApp inbox': 'Boîte de réception WhatsApp',
      'Your voice, in two languages.': 'Votre voix, en deux langues.',
      'Upload a voice note or speak into your microphone. Read the original words alongside their translation.':
          'Importez un mémo vocal ou parlez dans votre microphone. Lisez les mots originaux avec leur traduction.',
      'Translate into': 'Traduire en',
      'French / Français': 'Français',
      'English': 'Anglais',
      'French': 'Français',
      'English and French input · language detected automatically':
          'Entrée en anglais ou en français · langue détectée automatiquement',
      'Upload a voice note': 'Importer un mémo vocal',
      'WhatsApp .ogg / .opus, MP3, WAV, M4A or WebM. Up to {size} MB.':
          'WhatsApp .ogg / .opus, MP3, WAV, M4A ou WebM. Jusqu’à {size} Mo.',
      'Uploading saves the original audio and transcription on the machine running this backend. It is not automatically synced to your iPhone.':
          'L’importation enregistre l’audio original et la transcription sur l’ordinateur qui exécute ce serveur. Rien n’est synchronisé automatiquement avec votre iPhone.',
      'Choose audio file': 'Choisir un fichier audio',
      'No file selected': 'Aucun fichier sélectionné',
      'Upload & transcribe': 'Importer et transcrire',
      'Speak live': 'Parler en direct',
      'Allow microphone access, then speak in English or French. Text appears as you talk.':
          'Autorisez l’accès au microphone, puis parlez en anglais ou en français. Le texte apparaît pendant que vous parlez.',
      'Stop & finish': 'Arrêter et terminer',
      'Start speaking': 'Commencer à parler',
      'Live translated text · up to 10 minutes per session\nSmall delays are normal. Keep this page open.':
          'Traduction en direct · jusqu’à 10 minutes par session\nUn léger délai est normal. Gardez cette page ouverte.',
      'Original transcript': 'Transcription originale',
      '{language} translation': 'Traduction en {language}',
      'Your original words will appear here.':
          'Vos paroles originales apparaîtront ici.',
      'Your translated text will appear here.':
          'Votre texte traduit apparaîtra ici.',
      'Copy text': 'Copier le texte',
      'Copied': 'Copié',
      'Testing with WhatsApp? Save a voice note to your device, then choose it above. Live mode uses this microphone.':
          'Vous testez avec WhatsApp ? Enregistrez un mémo vocal sur votre appareil, puis choisissez-le ci-dessus. Le mode en direct utilise ce microphone.',
      'Audio is processed by OpenAI. Uploaded audio and transcripts are stored on the backend machine in its local data folder. WhatsApp inbox results also remain in the app queue.':
          'L’audio est traité par OpenAI. Les fichiers importés et les transcriptions sont stockés dans le dossier local de l’ordinateur serveur. Les résultats WhatsApp restent aussi dans la file de l’application.',
      'Save to Database': 'Enregistrer dans la base de données',
      'Applies to WhatsApp, uploads, and live sessions.':
          'S’applique à WhatsApp, aux imports et aux sessions en direct.',
      'When on, processed audio or text is saved on the backend machine.':
          'Lorsque cette option est activée, l’audio ou le texte traité est enregistré sur l’ordinateur serveur.',
      'Connect your app': 'Connecter votre application',
      'Enter your Voice Notes server address and app access token. Your OpenAI and WhatsApp keys stay on the server.':
          'Saisissez l’adresse du serveur Voice Notes et le jeton d’accès. Vos clés OpenAI et WhatsApp restent sur le serveur.',
      'Server address': 'Adresse du serveur',
      'App access token': 'Jeton d’accès à l’application',
      'For this personal prototype, the app keeps this token in memory until you disconnect or close the app.':
          'Dans ce prototype personnel, l’application conserve ce jeton en mémoire jusqu’à la déconnexion ou la fermeture.',
      'Connecting…': 'Connexion…',
      'Connect': 'Connecter',
      'Disconnect and clear results': 'Déconnecter et effacer les résultats',
      'Delete this result?': 'Supprimer ce résultat ?',
      'This removes the saved transcript and translation from your Voice Notes inbox.':
          'Cela supprime la transcription et la traduction enregistrées de votre boîte Voice Notes.',
      'Cancel': 'Annuler',
      'Delete': 'Supprimer',
      'Retry': 'Réessayer',
      'Refresh inbox': 'Actualiser la boîte de réception',
      'Voice messages, translated.': 'Messages vocaux traduits.',
      'Send a voice message to your connected WhatsApp business number. Your original words and translation will appear here.':
          'Envoyez un message vocal à votre numéro WhatsApp Business connecté. Vos paroles originales et leur traduction apparaîtront ici.',
      'Results are kept for 24 hours. Refreshes every 5 seconds while this screen is open. Translation: {language}.':
          'Les résultats sont conservés 24 heures. Actualisation toutes les 5 secondes pendant l’ouverture de cette page. Traduction : {language}.',
      'WhatsApp setup is still needed on your server. Complete the Meta configuration, then refresh.':
          'La configuration WhatsApp du serveur est incomplète. Terminez la configuration Meta, puis actualisez.',
      'No voice messages yet.': 'Aucun message vocal pour le moment.',
      'Waiting to process': 'En attente de traitement',
      'Transcribing and translating…': 'Transcription et traduction…',
      'Ready': 'Prêt',
      'Transcript ready · translation needs retry':
          'Transcription prête · traduction à réessayer',
      'Processing failed': 'Échec du traitement',
      'French translation': 'Traduction française',
      'English translation': 'Traduction anglaise',
      'From {sender} · {date}': 'De {sender} · {date}',
      'Could not update the database setting. Check the connection and try again.':
          'Impossible de modifier le réglage de la base de données. Vérifiez la connexion et réessayez.',
      'Enter a server address such as https://voice.example.com.':
          'Saisissez une adresse de serveur comme https://voice.example.com.',
      'Enter your app access token.':
          'Saisissez le jeton d’accès de l’application.',
      'Connect to the v3 backend. This server uses another version.':
          'Connectez-vous au serveur v3. Ce serveur utilise une autre version.',
      'Cannot connect. Check the server address, HTTPS certificate and network.':
          'Connexion impossible. Vérifiez l’adresse du serveur, le certificat HTTPS et le réseau.',
      'The server returned an unreadable response. Check its address.':
          'Le serveur a renvoyé une réponse illisible. Vérifiez son adresse.',
      'Could not refresh your inbox. Check the connection and try again.':
          'Impossible d’actualiser la boîte de réception. Vérifiez la connexion et réessayez.',
      'The message could not be updated. Refresh and try again.':
          'Impossible de mettre à jour le message. Actualisez et réessayez.',
      'The upload timed out. Try a shorter recording.':
          'L’importation a expiré. Essayez un enregistrement plus court.',
      'This audio file is empty or too large.':
          'Ce fichier audio est vide ou trop volumineux.',
      'Could not read the file. Try exporting the original voice note again.':
          'Impossible de lire le fichier. Essayez d’exporter à nouveau le mémo vocal original.',
      'Microphone permission was denied. Allow it in your browser or device settings.':
          'L’autorisation du microphone a été refusée. Autorisez-la dans les réglages du navigateur ou de l’appareil.',
      'Live translation failed.': 'La traduction en direct a échoué.',
      'Received an invalid live response. Please start again.':
          'Réponse en direct invalide. Veuillez recommencer.',
      'Live connection failed. Check the backend and start again.':
          'La connexion en direct a échoué. Vérifiez le serveur et recommencez.',
      'Could not finish the recording. Your displayed text is kept.':
          'Impossible de terminer l’enregistrement. Le texte affiché est conservé.',
    },
    'ar': {
      'Connection settings': 'إعدادات الاتصال',
      'Ready when you are': 'جاهز عندما تكون مستعدًا',
      'Transcribing and translating your file…': 'جارٍ نسخ ملفك وترجمته…',
      'Connecting to live translation…': 'جارٍ الاتصال بالترجمة المباشرة…',
      'Listening · speak naturally': 'أستمع · تحدث بشكل طبيعي',
      'Finishing the last words…': 'جارٍ إنهاء الكلمات الأخيرة…',
      'Connected to your server': 'متصل بالخادم',
      'Connect your server to get started': 'اتصل بالخادم للبدء',
      'Connect server': 'اتصال بالخادم',
      'WhatsApp inbox': 'رسائل واتساب',
      'Your voice, in two languages.': 'صوتك بلغتين.',
      'Upload a voice note or speak into your microphone. Read the original words alongside their translation.':
          'ارفع رسالة صوتية أو تحدث عبر الميكروفون. اعرض الكلمات الأصلية مع ترجمتها.',
      'Translate into': 'الترجمة إلى',
      'French / Français': 'الفرنسية',
      'English': 'الإنجليزية',
      'French': 'الفرنسية',
      'English and French input · language detected automatically':
          'الإدخال بالإنجليزية أو الفرنسية · يتم اكتشاف اللغة تلقائيًا',
      'Upload a voice note': 'رفع رسالة صوتية',
      'WhatsApp .ogg / .opus, MP3, WAV, M4A or WebM. Up to {size} MB.':
          'واتساب .ogg / .opus أو MP3 أو WAV أو M4A أو WebM. حتى {size} ميغابايت.',
      'Uploading saves the original audio and transcription on the machine running this backend. It is not automatically synced to your iPhone.':
          'يُحفظ الصوت الأصلي والنص المنسوخ على الجهاز الذي يشغّل الخادم. لا تتم مزامنتهما تلقائيًا مع iPhone.',
      'Choose audio file': 'اختر ملفًا صوتيًا',
      'No file selected': 'لم يتم اختيار ملف',
      'Upload & transcribe': 'رفع ونسخ صوتي',
      'Speak live': 'تحدث مباشرة',
      'Allow microphone access, then speak in English or French. Text appears as you talk.':
          'اسمح باستخدام الميكروفون، ثم تحدث بالإنجليزية أو الفرنسية. سيظهر النص أثناء التحدث.',
      'Stop & finish': 'إيقاف وإنهاء',
      'Start speaking': 'ابدأ التحدث',
      'Live translated text · up to 10 minutes per session\nSmall delays are normal. Keep this page open.':
          'ترجمة مباشرة · حتى ١٠ دقائق للجلسة\nالتأخير البسيط طبيعي. أبقِ الصفحة مفتوحة.',
      'Original transcript': 'النص الأصلي',
      '{language} translation': 'الترجمة إلى {language}',
      'Your original words will appear here.': 'ستظهر كلماتك الأصلية هنا.',
      'Your translated text will appear here.': 'سيظهر النص المترجم هنا.',
      'Copy text': 'نسخ النص',
      'Copied': 'تم النسخ',
      'Testing with WhatsApp? Save a voice note to your device, then choose it above. Live mode uses this microphone.':
          'للاختبار عبر واتساب، احفظ رسالة صوتية على جهازك ثم اخترها أعلاه. يستخدم الوضع المباشر هذا الميكروفون.',
      'Audio is processed by OpenAI. Uploaded audio and transcripts are stored on the backend machine in its local data folder. WhatsApp inbox results also remain in the app queue.':
          'يعالج OpenAI الصوت. تُحفظ الملفات المرفوعة والنصوص على جهاز الخادم في مجلد البيانات المحلي. وتبقى نتائج واتساب أيضًا في قائمة التطبيق.',
      'Save to Database': 'حفظ في قاعدة البيانات',
      'Applies to WhatsApp, uploads, and live sessions.':
          'ينطبق على واتساب والملفات المرفوعة والجلسات المباشرة.',
      'When on, processed audio or text is saved on the backend machine.':
          'عند التفعيل، يُحفظ الصوت أو النص المعالَج على جهاز الخادم.',
      'Connect your app': 'اتصال التطبيق',
      'Enter your Voice Notes server address and app access token. Your OpenAI and WhatsApp keys stay on the server.':
          'أدخل عنوان خادم Voice Notes ورمز الوصول. تبقى مفاتيح OpenAI وواتساب على الخادم.',
      'Server address': 'عنوان الخادم',
      'App access token': 'رمز وصول التطبيق',
      'For this personal prototype, the app keeps this token in memory until you disconnect or close the app.':
          'في هذا النموذج، يحتفظ التطبيق بالرمز في الذاكرة حتى قطع الاتصال أو إغلاق التطبيق.',
      'Connecting…': 'جارٍ الاتصال…',
      'Connect': 'اتصال',
      'Disconnect and clear results': 'قطع الاتصال ومسح النتائج',
      'Delete this result?': 'حذف هذه النتيجة؟',
      'This removes the saved transcript and translation from your Voice Notes inbox.':
          'سيؤدي ذلك إلى حذف النص والترجمة من صندوق Voice Notes.',
      'Cancel': 'إلغاء',
      'Delete': 'حذف',
      'Retry': 'إعادة المحاولة',
      'Refresh inbox': 'تحديث الرسائل',
      'Voice messages, translated.': 'رسائل صوتية مترجمة.',
      'Send a voice message to your connected WhatsApp business number. Your original words and translation will appear here.':
          'أرسل رسالة صوتية إلى رقم واتساب للأعمال المتصل. ستظهر كلماتك الأصلية وترجمتها هنا.',
      'Results are kept for 24 hours. Refreshes every 5 seconds while this screen is open. Translation: {language}.':
          'تُحفظ النتائج لمدة ٢٤ ساعة. يتم التحديث كل ٥ ثوانٍ أثناء فتح الصفحة. الترجمة: {language}.',
      'WhatsApp setup is still needed on your server. Complete the Meta configuration, then refresh.':
          'يلزم إعداد واتساب على الخادم. أكمل إعداد Meta ثم حدّث الصفحة.',
      'No voice messages yet.': 'لا توجد رسائل صوتية بعد.',
      'Waiting to process': 'بانتظار المعالجة',
      'Transcribing and translating…': 'جارٍ النسخ والترجمة…',
      'Ready': 'جاهز',
      'Transcript ready · translation needs retry':
          'النص جاهز · أعد محاولة الترجمة',
      'Processing failed': 'فشلت المعالجة',
      'French translation': 'الترجمة الفرنسية',
      'English translation': 'الترجمة الإنجليزية',
      'From {sender} · {date}': 'من {sender} · {date}',
      'Could not update the database setting. Check the connection and try again.':
          'تعذر تحديث إعداد قاعدة البيانات. تحقق من الاتصال وحاول مرة أخرى.',
      'Enter a server address such as https://voice.example.com.':
          'أدخل عنوان خادم مثل https://voice.example.com.',
      'Enter your app access token.': 'أدخل رمز وصول التطبيق.',
      'Connect to the v3 backend. This server uses another version.':
          'اتصل بخادم الإصدار 3. يستخدم هذا الخادم إصدارًا آخر.',
      'Cannot connect. Check the server address, HTTPS certificate and network.':
          'تعذر الاتصال. تحقق من عنوان الخادم وشهادة HTTPS والشبكة.',
      'The server returned an unreadable response. Check its address.':
          'أعاد الخادم استجابة غير مقروءة. تحقق من عنوانه.',
      'Could not refresh your inbox. Check the connection and try again.':
          'تعذر تحديث الرسائل. تحقق من الاتصال وحاول مرة أخرى.',
      'The message could not be updated. Refresh and try again.':
          'تعذر تحديث الرسالة. حدّث الصفحة وحاول مرة أخرى.',
      'The upload timed out. Try a shorter recording.':
          'انتهت مهلة الرفع. جرّب تسجيلًا أقصر.',
      'This audio file is empty or too large.': 'ملف الصوت فارغ أو كبير جدًا.',
      'Could not read the file. Try exporting the original voice note again.':
          'تعذرت قراءة الملف. حاول تصدير الرسالة الصوتية الأصلية مجددًا.',
      'Microphone permission was denied. Allow it in your browser or device settings.':
          'تم رفض إذن الميكروفون. اسمح به في إعدادات المتصفح أو الجهاز.',
      'Live translation failed.': 'فشلت الترجمة المباشرة.',
      'Received an invalid live response. Please start again.':
          'تم استلام رد مباشر غير صالح. ابدأ من جديد.',
      'Live connection failed. Check the backend and start again.':
          'فشل الاتصال المباشر. تحقق من الخادم وابدأ من جديد.',
      'Could not finish the recording. Your displayed text is kept.':
          'تعذر إنهاء التسجيل. تم الاحتفاظ بالنص المعروض.',
    },
  };

  static String translate(String locale, String english) =>
      _copy[locale]?[english] ?? english;
}
