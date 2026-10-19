---
type: How-to
title: "Rechenräder"
description: A heading, a name line, and four Rechenräder of two rings with the centre's number given and the outer ring to fill in.
tags: [rechenrad, zahlenraum-20, klasse-1]
covers: [text, name, rechenrad]
generated: { by: "human:pgoell", at: 2026-10-19T10:20:00Z }
---

# Rechenräder

When a teacher asks for: "Ein Blatt mit Rechenrädern bis 20, Plus, der äußere Ring zum Ausfüllen."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the wheels are the button "Rechenrad" in the menu "Mathe-Blöcke" in the insert bar. A Rechenrad is a wheel: a centre with an operator and a number such as "+7", and rings of boxes. Each ring's number, worked with the centre, gives the number of the next ring out in the same segment.
* `task` picks the empty ring: "outer" (the outer ring is empty), "inner" (the inner ring is empty, the pupil works back), "middle" (the middle ring is empty, with 3 rings only) or "mixed" (one empty box per segment).
* `op` picks the Rechenart: "+" and "-" at any Zahlenraum, "*" and ":" from Zahlenraum 20.
* `max` is the Zahlenraum: 10, 20, 100 or 1000.
* `rings` is 2 or 3. `segments` is the number of boxes per wheel, from 4 to 12.
* The block's height follows its rows: four wheels in two columns at 180 mm wide are 177.45 mm tall.
* See [rechenrad](../blocks/rechenrad.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new wheels.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "e8a2c5d4-9f3b-4d2e-b1c0-6a3f8d0e2b01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Rechenräder",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "e8a2c5d4-9f3b-4d2e-b1c0-6a3f8d0e2b02",
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
          "id": "e8a2c5d4-9f3b-4d2e-b1c0-6a3f8d0e2b03",
          "type": "rechenrad",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 177.45,
          "z": 3,
          "locked": false,
          "props": {
            "count": 4,
            "columns": 2,
            "rings": 2,
            "segments": 8,
            "max": 20,
            "op": "+",
            "task": "outer",
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
