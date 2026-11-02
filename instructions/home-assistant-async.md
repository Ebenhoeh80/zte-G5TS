# AsyncIO und Home Assistant

## Home-Assistant-Lifecycle

- Ressourcen pro `ConfigEntry` erzeugen und in `entry.runtime_data` mit einem
  typisierten Config-Entry speichern. Beim Unload HTTP-Sessions und eigene
  Listener/Aufgaben zuverlässig schließen.
- Config Flow und Options Flow validieren Eingaben nachvollziehbar und
  verwenden lokalisierte Fehler-IDs statt interner Exceptions als UI-Text.
- `DataUpdateCoordinator`-Intervalle sind die Quelle für gepollte Daten.
  Entitäten abonnieren sie und führen keine eigenen Polling-Schleifen oder
  synchronen Routerzugriffe aus.
- Für entitätsbezogene Aktionen die passende Home-Assistant-Fehlerbehandlung
  verwenden. Ein fehlgeschlagener Routerbefehl darf nicht als Erfolg erscheinen.
- Stabile Unique IDs, `DeviceInfo`, Entity Categories und Übersetzungen
  erhalten. Registry-Identitäten bei Refactorings nicht unbeabsichtigt ändern.
- Diagnostics müssen redigiert sein. Repairs nur für klar erkennbare,
  vom Benutzer lösbare Zustände bereitstellen.

## Async und Synchronisation

- Netzwerkzugriffe ausschließlich asynchron ausführen, mit begrenzten
  Timeouts und kontrollierter Wiederverwendung/Schließung von `aiohttp`-Sessions.
- `asyncio.Lock` für Authentifizierungs- und Requestzustände gezielt verwenden.
  Lock-Reihenfolge dokumentieren und keine rekursiven Lock-Aufnahmen erzeugen.
- Polling und Schreibaktionen gegen Router-Races synchronisieren, wenn die
  Firmware dies erfordert. Unabhängige Lesevorgänge nur parallelisieren, wenn
  Routerlast und Sessionverhalten dies erlauben.
- Keine blockierenden I/O- oder CPU-intensiven Arbeiten im Event Loop.
- `CancelledError` nicht verschlucken; Abbruch und Unload müssen Ressourcen
  trotzdem sauber freigeben.
- Wiederholungen begrenzen und auf sichere, idempotente Operationen
  beschränken.
