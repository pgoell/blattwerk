---
type: Tutorial
title: Dein erstes Blatt mit Claude
description: For teachers, in German. From a Blattomat account to a first worksheet that Claude makes, in short steps.
tags: [tutorial, lehrkraft, claude-desktop]
covers: [text, name, ruling]
generated: { by: "human:pgoell", at: 2026-10-16T00:00:00Z }
---

# Dein erstes Blatt mit Claude

Claude ist ein Assistent, dem du in ganzen Sätzen schreibst. Mit Blattomat verbunden, legt Claude Arbeitsblätter in deinem Konto an. Du öffnest sie danach im Editor, änderst, was dir nicht passt, und druckst sie.

Das brauchst du: einen Computer mit Windows oder macOS, dein Blattomat-Konto und etwa 20 Minuten.

## Schritt 1: Claude Desktop holen

1. Geh auf [claude.ai/download](https://claude.ai/download).
2. Lade Claude Desktop für deinen Computer herunter und installiere es.
3. Öffne Claude Desktop und melde dich an. Hast du noch kein Konto bei Claude, legst du hier eins an.

## Schritt 2: Einen Schlüssel für Claude machen

Der Schlüssel erlaubt Claude, in deinem Blattomat-Konto Blätter anzulegen und zu ändern. Nur in deinem, und nur, solange du ihn nicht widerrufst.

1. Melde dich bei [Blattomat](https://blattwerk.pgoell.com) an.
2. Klick oben auf **Konto**.
3. Unter **Zugang für Claude** steht schon „Claude Desktop“ als Name. Klick auf **Schlüssel erstellen**.
4. Klick auf **Kopieren** und leg den Schlüssel kurz in eine Notiz. Blattomat zeigt ihn nur dieses eine Mal.

Gib den Schlüssel niemandem weiter. Ist er weg oder in falschen Händen, klick daneben auf **Widerrufen** und mach einen neuen.

## Schritt 3: Blattomat in Claude Desktop eintragen

Diesen Schritt kannst du noch nicht allein mit einem Klick machen. Das Einrichten braucht heute eine Person mit etwas Technikwissen und Zugriff auf deinen Computer. Gib ihr deinen Schlüssel aus Schritt 2 und diese Seite.

> Für die Person, die einrichtet: Der Server liegt im Repository unter `frontend/mcp/stdio.ts` und braucht Node 22 und `npm ci --prefix frontend`. In Claude Desktop unter Einstellungen, Entwickler, Konfiguration bearbeiten:
>
> ```json
> {"mcpServers": {"blattomat": {"command": "node", "args": ["<Pfad zum Repository>/frontend/mcp/stdio.ts"], "env": {"BLATTWERK_TOKEN": "<Schlüssel>"}}}}
> ```
>
> Danach Claude Desktop ganz beenden und neu öffnen.

Wenn es geklappt hat, siehst du in Claude Desktop unter dem Eingabefeld bei den Werkzeugen den Eintrag **blattomat**.

## Schritt 4: Dein erstes Blatt

1. Schreib in Claude Desktop zum Beispiel: „Mach mir ein Arbeitsblatt mit Lernwörtern auf Lineatur und Silbenbögen für die Wörter Hase, Igel, Maus, Katze.“
2. Claude fragt beim ersten Mal, ob es die Werkzeuge von Blattomat benutzen darf. Erlaube es.
3. Warte, bis Claude schreibt, dass das Blatt fertig ist. Claude sagt dir den Titel.
4. Öffne Blattomat. Das neue Blatt steht in deiner Liste. Öffne es.
5. Ändere, was du ändern willst, so wie bei jedem anderen Blatt. Dann druck es.

Gefällt dir etwas nicht, sag es Claude in einem Satz: „Mach die Schrift größer“ oder „Nimm noch das Wort Fuchs dazu“. Lade das Blatt in Blattomat danach neu.

## Gut zu wissen

- Was du Claude schreibst und was auf dem Blatt steht, geht an Anthropic, die Firma hinter Claude. Schreib keine Namen oder anderen Angaben von Kindern hinein.
- Schließ ein Blatt im Editor, solange Claude daran arbeitet. Ändert ihr beide zugleich, kommt eine der beiden Änderungen nicht durch.
