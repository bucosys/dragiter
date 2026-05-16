# Über dragiter (Deterministic RAG Iterator)

dragiter ist ein modulares Kommandozeilen-Werkzeug (CLI), das entwickelt wurde, um die Arbeit mit großen Sprachmodellen (LLMs) in automatisierte Workflows zu integrieren. Inspiriert von der Unix-Philosophie ("Do one thing and do it well"), ermöglicht es das Verketten von KI-Agenten ähnlich wie Pipes in einem Terminal.

## Kernfunktionen

*   **Modularität**: Agenten und Komponenten können flexibel kombiniert werden, um maßgeschneiderte Lösungen zu erstellen.
*   **Kontext-Management**: dragiter ermöglicht das dynamische Laden von Referenzmaterialien. Benutzer können spezifische Dateien oder Ordner angeben und Inhalte mithilfe von Regex-Mustern präzise filtern, um sie als Kontext in den KI-Prompt zu injizieren.
*   **Automatisierung**: Das Tool unterstützt Stapelverarbeitung (Loops), wodurch wiederkehrende Aufgaben effizient über mehrere Eingaben hinweg ausgeführt werden können.
*   **Flexibilität**: Es bietet eine einheitliche Schnittstelle für verschiedene KI-Backends, wie z.B. OpenAI oder Google Vertex AI.

## Anwendungsbereiche

dragiter eignet sich besonders für Entwickler und technische Nutzer, die:
*   Automatisierte Code-Analysen oder Dokumentationen erstellen möchten.
*   Inhalte basierend auf spezifischen Projekt-Kontexten generieren müssen.
*   Komplexe Abfrage-Szenarien automatisieren wollen, die strukturierte Daten oder Dateiinhalte als Wissensbasis benötigen.

## Technologie

Das Tool ist in Python (>= 3.11) geschrieben und setzt auf eine leichtgewichtige, erweiterbare Architektur. Es nutzt moderne Bibliotheken wie `tomllib` für die Konfiguration und SDKs der jeweiligen KI-Anbieter.