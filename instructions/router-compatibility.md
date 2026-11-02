# ZTE-APIs und Firmware-Kompatibilität

- Niemals annehmen, dass ZTE-Modelle, API-Versionen oder Firmwarestände
  identische Endpunkte, Header, Cookies, Antwortfelder oder Loginabläufe
  besitzen.
- UBUS und GoForm als getrennte Protokollvarianten behandeln. Gemeinsamkeiten
  können über einen klar definierten Normalisierungsschritt geteilt werden;
  Protokolldetails nicht in Entity-Code duplizieren.
- Erkenne API-Varianten anhand belegter Merkmale aus Firmware-/Routerantworten.
  Keine Version, Feldbedeutung oder Hashformel aus Modellnamen erraten.
- Unterstütze alternative JSON-Strukturen und bekannte Feldaliasse nur mit
  konkreten Routerantworten oder Regressionstests.
- Prüfe JSON-RPC-Envelope, Status, Content-Type und Payloadtyp vor Zugriff auf
  Felder. Leere JSON-, HTML-, Text- und fehlerhafte Antworten dürfen nicht als
  erfolgreiche Login- oder Polling-Antwort gelten.
- Halte Login-Challenge, Passwort-Hashing, Session-Cookie, Token und
  Verschlüsselungs-Key als getrennte Schritte mit klaren Vorbedingungen.
- Authentifizierungsfehler müssen von Netzwerk-, TLS-, HTTP- und
  Firmware-/API-Fehlern unterscheidbar sein.
- Vermeide parallele Session-Erzeugung und Requests, wenn die Router-Firmware
  nur eine aktive WebUI-Sitzung oder serialisierte Aktionen unterstützt.
- Schreibende Requests dürfen nach Timeout oder Verbindungsabbruch nicht blind
  wiederholt werden. Prüfe den Zustand neu oder melde den Ausgang als unklar.
- Neue Kompatibilitätspfade brauchen Tests für Erfolgsantworten,
  abweichende Firmwareantworten und Fehler-/Grenzfälle.
