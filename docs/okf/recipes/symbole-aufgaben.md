---
type: How-to
title: "Symbole mit Aufgaben"
description: A heading, a name line, and three OpenMoji symbols, each next to a short task.
tags: [symbol, bild, klasse-1]
covers: [text, name, symbol]
generated: { by: "human:pgoell", at: 2026-10-17T16:00:00Z }
---

# Symbole mit Aufgaben

When a teacher asks for: "Ein Blatt mit Symbolen und einer kurzen Aufgabe daneben."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the symbol is the button "Symbol" under Einfügen. Its `code` is the OpenMoji code of the symbol: "270F" Bleistift, "1F3E0" Haus, "2B50" Stern. The teacher finds others in the panel's field "Symbol suchen".
* See [symbol](../blocks/symbol.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the codes and the tasks for other symbols.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "0c8e4f72-9b1a-4d3c-a5e6-7f2b8d0c3e01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Symbole und Aufgaben",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "0c8e4f72-9b1a-4d3c-a5e6-7f2b8d0c3e02",
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
          "id": "0c8e4f72-9b1a-4d3c-a5e6-7f2b8d0c3e03",
          "type": "symbol",
          "x": 15,
          "y": 60,
          "w": 20,
          "h": 20,
          "z": 3,
          "locked": false,
          "props": {
            "code": "270F"
          }
        },
        {
          "id": "0c8e4f72-9b1a-4d3c-a5e6-7f2b8d0c3e04",
          "type": "text",
          "x": 45,
          "y": 63,
          "w": 150,
          "h": 14,
          "z": 4,
          "locked": false,
          "props": {
            "text": "Schreibe drei Wörter mit dem Bleistift auf.",
            "size": 14,
            "align": "left"
          }
        },
        {
          "id": "0c8e4f72-9b1a-4d3c-a5e6-7f2b8d0c3e05",
          "type": "symbol",
          "x": 15,
          "y": 95,
          "w": 20,
          "h": 20,
          "z": 5,
          "locked": false,
          "props": {
            "code": "1F3E0"
          }
        },
        {
          "id": "0c8e4f72-9b1a-4d3c-a5e6-7f2b8d0c3e06",
          "type": "text",
          "x": 45,
          "y": 98,
          "w": 150,
          "h": 14,
          "z": 6,
          "locked": false,
          "props": {
            "text": "Schreibe ein Wort auf, das zum Haus passt.",
            "size": 14,
            "align": "left"
          }
        },
        {
          "id": "0c8e4f72-9b1a-4d3c-a5e6-7f2b8d0c3e07",
          "type": "symbol",
          "x": 15,
          "y": 130,
          "w": 20,
          "h": 20,
          "z": 7,
          "locked": false,
          "props": {
            "code": "2B50"
          }
        },
        {
          "id": "0c8e4f72-9b1a-4d3c-a5e6-7f2b8d0c3e08",
          "type": "text",
          "x": 45,
          "y": 133,
          "w": 150,
          "h": 14,
          "z": 8,
          "locked": false,
          "props": {
            "text": "Male fünf Sterne in die Zeile.",
            "size": 14,
            "align": "left"
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
