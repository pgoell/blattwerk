---
type: How-to
title: "Textaufgaben"
description: A heading, a name line, and two Sachaufgaben bis 20 with the story and the question shown and the Rechnung and the Antwort left for the pupil.
tags: [textaufgabe, sachaufgaben, zahlenraum-20, klasse-2]
covers: [text, name, textaufgabe]
generated: { by: "human:pgoell", at: 2026-11-03T05:45:00Z }
---

# Textaufgaben

When a teacher asks for: "Ein Blatt mit Sachaufgaben bis 20, die Frage gezeigt, Rechnung und Antwort zum Ausfüllen."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the tasks are the button "Textaufgaben" in the menu "Mathe-Blöcke" in the insert bar. Each task is a short story, a question, a Rechnung on Karo and an Antwort line.
* `themes` picks the texts: "kurz", "sach", "raetsel", "zeit" (Zeitpunkte or Dauern, `zeit`) and "geld". `ops` picks the Rechenarten, `steps` is 1 or 2, `max` is the Zahlenraum.
* `numbers` "decimal" writes Kommazahlen. Geld is always in euros and cents. `carry` is the Übertrag: "any", "yes" or "no".
* `frage`, `rechnung` and `antwort` say whether that part is printed for the pupil. The Lösungen fill a part that is not. The story is always printed.
* `sketch` adds a drawing box above the Rechnung. `rows` "auto" gives one Karo row per step plus one, or a number of rows from 1 to 8.
* `manual` with `written` is the teacher's own Text, Frage, Rechnung and Antwort. Leave `written` out unless the teacher gave the words.
* See [textaufgabe](../blocks/textaufgabe.md) for the other props.

Neu würfeln, and variant letters B to D, pick another story and other numbers. A variant drops `written`.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new tasks.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "a7c2e4b1-6d08-4f3a-8c55-1b9e0d2a7c01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Sachaufgaben",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "a7c2e4b1-6d08-4f3a-8c55-1b9e0d2a7c02",
          "type": "name",
          "x": 15,
          "y": 35,
          "w": 180,
          "h": 18,
          "z": 2,
          "locked": false,
          "props": {}
        },
        {
          "id": "a7c2e4b1-6d08-4f3a-8c55-1b9e0d2a7c03",
          "type": "textaufgabe",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 83,
          "z": 3,
          "locked": false,
          "props": {
            "count": 2,
            "themes": ["sach"],
            "ops": ["+"],
            "steps": 1,
            "max": 20,
            "numbers": "whole",
            "carry": "any",
            "frage": true,
            "rechnung": false,
            "antwort": false,
            "sketch": false,
            "rows": "auto",
            "manual": false,
            "zeit": "both",
            "seed": 5
          }
        }
      ]
    }
  ],
  "guides": {
    "x": [],
    "y": []
  },
  "grid": 0
}
```
