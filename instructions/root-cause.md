# Root-Cause-Analyse und Änderungen

## Vor jeder Änderung

1. Lies das gesamte Repository einschließlich Tests, Konfiguration,
   Übersetzungen und Dokumentation. Berücksichtige außerdem den Git-Status und
   integriere vorhandene Änderungen, statt sie zu überschreiben.
2. Erstelle zuerst eine aktuelle Architekturübersicht. Benenne darin
   Komponenten, Datenflüsse, Abhängigkeiten und Zuständigkeiten.
3. Verfolge den betroffenen Ablauf vom Einstiegspunkt bis zur beobachteten
   Ausgabe oder zum Fehler. Nutze Code, Tests, Logs und reproduzierbare
   Laufzeitdaten als Belege.
4. Formuliere die Root Cause mit den konkreten betroffenen Funktionen und
   Bedingungen. Trenne bewiesene Tatsachen von Hypothesen.
5. Wenn die Ursache ohne Laufzeitdaten nicht eindeutig bestimmbar ist, ändere
   das betroffene Verhalten nicht spekulativ. Erkläre, welche sichere Diagnose
   oder welcher reproduzierbare Test noch fehlt.

## Umsetzung

- Behebe die Ursache und nicht lediglich das sichtbare Symptom.
- Bevorzuge eine nachhaltige, nachvollziehbare Architekturverbesserung vor
  einem lokalen Workaround. Ändere aber keine unabhängigen Bereiche.
- Lies vor jeder weiteren Änderung den vollständigen Kontext der betroffenen
  Dateien erneut, einschließlich bereits vorgenommenen Änderungen.
- Halte Änderungen chirurgisch, typisiert und mit bestehenden Mustern
  konsistent. Entferne oder ersetze Verhalten nur, wenn der beabsichtigte
  Verhaltenswechsel klar begründet und getestet ist.
- Dokumentiere direkt betroffene Benutzer- und Entwicklungsabläufe.
- Berichte für jeden behobenen Fehler Root Cause, technische Erklärung,
  Risiko, betroffene Dateien/Funktionen, Patch und Begründung.
