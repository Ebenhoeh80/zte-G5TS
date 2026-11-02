# Sicherheit und Transport

## Zugangsdaten und Sitzungen

- Zugangsdaten ausschließlich über Home-Assistant-Config-Entries und dessen
  Secret-Handling speichern. Passwörter niemals in Klartext-Logs, Ausnahmen,
  Diagnostics oder Testausgaben aufnehmen.
- Tokens, Cookies, Session-IDs, Hashes und Schlüssel dürfen nicht vollständig
  protokolliert oder in Diagnosedaten ausgegeben werden. Falls ein Debugwert
  nötig ist, nur eine ausdrücklich sichere, begrenzte Maskierung verwenden.
- Keine Zugangsdaten in URL-Userinfo, Query-Strings oder Fehlermeldungen
  transportieren.
- Sitzungen und Cookies pro Router kontrolliert verwalten. Erneuerung,
  Invalidierung und parallele Authentifizierung müssen synchronisiert sein.

## TLS und HTTP

- HTTPS mit Zertifikatsprüfung ist der sichere Standard.
- Selbstsignierte oder anderweitig nicht vertrauenswürdige Zertifikate dürfen
  nur über eine klare, bewusste Benutzeroption akzeptiert werden.
- Unverschlüsseltes HTTP muss für neue Konfigurationen eine explizite,
  verständlich erklärte Ausnahme sein. Bestehende Konfigurationen nur mit
  dokumentierter, rückwärtskompatibler Migration behandeln.
- Keine automatische HTTPS-zu-HTTP-Rückstufung und kein unsicheres TLS-Fallback.
- Fehlermeldungen müssen Transportprobleme erklären, ohne URL-Zugangsdaten,
  Tokens oder Routerantworten mit sensiblen Inhalten offenzulegen.

## Sicherer Umgang mit Routerdaten

- UBUS-/GoForm-Antworten sind nicht vertrauenswürdig. Struktur, Feldtypen und
  Größen vor Verarbeitung prüfen.
- SMS, WLAN-Konfiguration, GNSS-Koordinaten und Client-Identifikatoren sind
  sensible Daten; sie dürfen nicht ungefiltert in Logs oder Diagnostics
  erscheinen.
- Aktionen mit Nebenwirkungen (SMS, Neustart, Funkzellen-Sperre,
  Firmware-Update) nur explizit auslösen. Bei unklarem Ausgang keine Aktion
  automatisch wiederholen, sofern sie nicht nachweislich idempotent ist.
- Kein dynamisches Ausführen von Routerantworten und keine unnötigen Rechte
  oder API-Aufrufe.

## Sicherheitsprüfung

- Prüfe Änderungen auf Secret Leakage, Session-Hijacking, unsichere Defaults,
  Exception Leakage, Redirect-/Downgrade-Risiken und Information Disclosure.
- Sicherheitsbefunde müssen reproduzierbar und mit präziser Stelle,
  Auswirkung, Schweregrad und Konfidenz belegt sein.
