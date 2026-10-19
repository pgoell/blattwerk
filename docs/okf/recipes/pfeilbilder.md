---
type: How-to
title: "Pfeilbilder"
description: A heading, a name line, and four Pfeilbilder of four boxes with the start number and the operators given and the other boxes to fill in.
tags: [pfeilbild, zahlenraum-20, klasse-1]
covers: [text, name, pfeilbild]
generated: { by: "human:pgoell", at: 2026-10-19T06:45:00Z }
---

# Pfeilbilder

When a teacher asks for: "Ein Blatt mit Pfeilbildern bis 20, Plus und Minus, die Startzahl gegeben."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the pictures are the button "Pfeilbild" in the menu "Mathe-Blöcke" in the insert bar. A Pfeilbild is a row of boxes joined by arrows, each arrow labelled with an operator such as "+4" or ":2".
* `given` says what the pupil gets: "start" the first box and every operator (fill the boxes), "ends" the first and the last box (find the operators and the boxes between), "mixed" the first box and, per arrow, either its operator or the box after it.
* `ops` picks the Rechenarten: "+" and "-" from Zahlenraum 10, "*" and ":" from 20. `arrows` "both" adds a back arrow under each arrow with the inverse operator.
* See [pfeilbild](../blocks/pfeilbild.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new pictures.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "c5e3a9b2-7d4f-4b0c-9f82-3e1d6a8c0f01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Pfeilbilder",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "c5e3a9b2-7d4f-4b0c-9f82-3e1d6a8c0f02",
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
          "id": "c5e3a9b2-7d4f-4b0c-9f82-3e1d6a8c0f03",
          "type": "pfeilbild",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 53.9,
          "z": 3,
          "locked": false,
          "props": {
            "count": 4,
            "columns": 2,
            "boxes": 4,
            "max": 20,
            "ops": ["+", "-"],
            "arrows": "one",
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
