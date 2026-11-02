# Tests und Codequalität

- Vor Änderungen Baseline und relevante bestehende Tests ausführen, danach die
  kleinstmögliche aussagekräftige Testauswahl und erforderliche Gesamtprüfungen.
- Tests dürfen Routerzugriffe nicht unabsichtlich ausführen. Verwende
  deterministische Mockantworten und prüfe Requestinhalt, Session-/Cookie-
  Verhalten, Error Mapping, Retry-Grenzen und Redaction.
- Login- und Sessiontests müssen mindestens Erfolg, ungültige Zugangsdaten,
  leere/falsche Antworten, HTML, Timeout, Verbindungs-/TLS-Fehler, abgelaufene
  Sitzung und API-Fallback abdecken.
- Regressionstests für jede behobene Root Cause ergänzen. Tests müssen das
  geforderte Verhalten direkt prüfen und nicht nur einen Proxy dafür.
- Timeout-, Status- und Payloadfälle sowie Firmwarevarianten mit eigenen
  Testfällen abdecken. Nebenwirkungsbehaftete Requests auf genau einen Aufruf
  bei unklarem Ausgang prüfen.
- Python-Änderungen an den unterstützten Laufzeiten testen und Ruff,
  Typprüfung sowie Home-Assistant-Validierung verwenden, sofern im Projekt
  eingerichtet.
- TypeScript-Änderungen mit dem vorhandenen TypeScript-/Vite-Build prüfen.
- Keine Toolchain oder Dependencies ohne Bedarf hinzufügen. Fehlende
  Entwicklungsabhängigkeiten transparent als Validierungshindernis angeben.
- Vor Abschluss Git-Diff und Status prüfen. Nur taskbezogene Dateien ändern;
  keine fremden oder vorher bestehenden Änderungen zurücksetzen.
