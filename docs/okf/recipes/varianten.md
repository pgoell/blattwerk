---
type: How-to
title: "Varianten zum Drucken"
description: A maths block and a suchsel with seeds, so each printed variant gets its own tasks and grid.
tags: [varianten, maths, suchsel, abschreiben, klasse-2]
covers: [text, name, maths, suchsel]
generated: { by: "human:pgoell", at: 2026-10-19T06:10:00Z }
---

# Varianten zum Drucken

When a teacher asks for: "Ein Blatt mit Plusaufgaben und einem Suchsel, mehrere Varianten, damit die Nachbarn nicht abschreiben können."

* Each block with a `seed` changes from letter to letter. Variant A is the stored sheet. Letters B to D get new tasks and a new grid from the same seed and the letter.
* A block without a `seed` prints the same on every variant. Give every block that should change a whole-number seed.
* The maths block takes its tasks from its limits and `seed`. Its `exercises` is what the server made for those limits, so keep them with the seed.
* The suchsel draws its grid from `seed`. Its `words` stay the same on every variant.
* Claude cannot print. The teacher presses the button "Varianten drucken", picks how many variants to print (letters A to D), and the solutions carry the letter. Nothing is stored.
* See [maths](../blocks/maths.md) and [suchsel](../blocks/suchsel.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seeds for new tasks.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "e2b7c9a4-6f13-4d5e-8a20-3c9f1d7b6e01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Plusaufgaben und Suchsel",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "e2b7c9a4-6f13-4d5e-8a20-3c9f1d7b6e02",
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
          "id": "e2b7c9a4-6f13-4d5e-8a20-3c9f1d7b6e03",
          "type": "maths",
          "x": 15,
          "y": 55,
          "w": 180,
          "h": 100,
          "z": 3,
          "locked": false,
          "props": {
            "ops": ["+"],
            "max": 20,
            "a": [[0, 9], [0, 9]],
            "b": [[0, 9], [0, 9]],
            "carry": "either",
            "rest": false,
            "format": "row",
            "count": 12,
            "seed": 42,
            "columns": 3,
            "size": 14,
            "exercises": [
              {"op": "+", "a": 9, "b": 10, "result": 19, "rest": 0},
              {"op": "+", "a": 1, "b": 7, "result": 8, "rest": 0},
              {"op": "+", "a": 0, "b": 6, "result": 6, "rest": 0},
              {"op": "+", "a": 12, "b": 3, "result": 15, "rest": 0},
              {"op": "+", "a": 3, "b": 10, "result": 13, "rest": 0},
              {"op": "+", "a": 3, "b": 2, "result": 5, "rest": 0},
              {"op": "+", "a": 2, "b": 16, "result": 18, "rest": 0},
              {"op": "+", "a": 1, "b": 14, "result": 15, "rest": 0},
              {"op": "+", "a": 12, "b": 2, "result": 14, "rest": 0},
              {"op": "+", "a": 1, "b": 5, "result": 6, "rest": 0},
              {"op": "+", "a": 10, "b": 8, "result": 18, "rest": 0},
              {"op": "+", "a": 19, "b": 0, "result": 19, "rest": 0}
            ],
            "loosen": null
          }
        },
        {
          "id": "e2b7c9a4-6f13-4d5e-8a20-3c9f1d7b6e04",
          "type": "suchsel",
          "x": 15,
          "y": 160,
          "w": 180,
          "h": 110,
          "z": 4,
          "locked": false,
          "props": {
            "words": ["HUND", "KATZE", "MAUS", "PFERD", "IGEL"],
            "cols": 10,
            "rows": 8,
            "ways": "down",
            "caps": true,
            "umlauts": true,
            "show": "words",
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
