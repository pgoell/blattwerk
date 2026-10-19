---
type: How-to
title: "Operatorfelder"
description: A heading, a name line, and four Operatorfelder of four boxes with the start number and the operators given and the other boxes to fill in.
tags: [operatorfeld, zahlenraum-20, klasse-1]
covers: [text, name, operatorfeld]
generated: { by: "human:pgoell", at: 2026-10-19T08:15:00Z }
---

# Operatorfelder

When a teacher asks for: "Ein Blatt mit Operatorfeldern bis 20, Plus und Minus, die Startzahl gegeben."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the fields are the button "Operatorfeld" in the menu "Mathe-Blöcke" in the insert bar. An Operatorfeld is a ring of boxes joined by operators such as "+4" or ":2", each pair of neighbours one task.
* `given` says what the pupil gets: "start" the first box and every operator (fill the boxes), "ops" every box and no operator (find the operators), "mixed" the first box and, per link, either its operator or the box after it.
* `ops` picks the Rechenarten: "+" and "-" from Zahlenraum 10, "*" and ":" from 20. `centre` true draws one number in the middle, linked to every outer box.
* `only` "tens" (from Zahlenraum 100) or "hundreds" (1000) keeps every number a multiple of 10 or 100.
* The block's height follows its rows: four fields in two columns at 180 mm wide are 177.71 mm tall.
* See [operatorfeld](../blocks/operatorfeld.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new fields.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "d7f1b4c3-8e2a-4c1d-a0b9-5f2e7c9d1a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Operatorfelder",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "d7f1b4c3-8e2a-4c1d-a0b9-5f2e7c9d1a02",
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
          "id": "d7f1b4c3-8e2a-4c1d-a0b9-5f2e7c9d1a03",
          "type": "operatorfeld",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 177.71,
          "z": 3,
          "locked": false,
          "props": {
            "centre": false,
            "count": 4,
            "columns": 2,
            "boxes": 4,
            "max": 20,
            "ops": ["+", "-"],
            "only": "none",
            "given": "start",
            "drawOps": true,
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
