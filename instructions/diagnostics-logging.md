# Fehlerbehandlung, Logging und Diagnose

- Fehler explizit klassifizieren: DNS/Verbindung, Timeout, TLS, HTTP-Status,
  Redirect/HTML, ungültiges JSON, RPC-Fehler, Authentifizierung und
  Firmware-/API-Inkompatibilität.
- Leere Routerantworten sowie falsche Statuscodes oder Datentypen sind Fehler,
  keine Erfolgssignale und keine stillen Defaults.
- Exceptions nicht breit abfangen und verwerfen. Wo ein optionaler Teilfehler
  den restlichen Poll nicht abbrechen soll, den Fehlerzustand sichtbar und
  sicher protokollieren und den Teilerfolg eindeutig kennzeichnen.
- Config-Flow-Fehler nutzerverständlich und lokalisiert darstellen; technische
  Details ausschließlich in redigierten Logs belassen.
- Debuglogs sollen Methode/API-Typ, Endpoint, Statuscode, Firmwarehinweise und
  Sessionzustand nachvollziehbar machen, ohne Response-Bodies oder Secrets
  auszugeben.
- URLs vor dem Loggen normalisieren: Userinfo, Query-Parameter mit möglichen
  Tokens sowie sensible Pfadsegmente entfernen.
- Routerantworten und Exceptions nicht ungeprüft vollständig loggen. Inhalte
  können WLAN-Schlüssel, SMS, GNSS-Daten, Telefonnummern oder Sessiontokens
  enthalten.
- Sessionzustände nur als sichere Zustandsklassen (z. B. vorhanden/fehlend/
  abgelaufen) protokollieren. Session-IDs, Cookies und Tokens nicht loggen.
- Diagnosewerkzeuge müssen standardmäßig sicher sein, keine Zugangsdaten
  ausgeben und einen möglichen Einfluss auf bestehende Router-WebUI-Sitzungen
  kenntlich machen.
- Keine Diagnosewerte als bestätigt ausgeben, wenn kein echter Router-Request
  erfolgt ist.
