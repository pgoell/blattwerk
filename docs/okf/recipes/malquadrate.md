---
type: How-to
title: "Malquadrate"
description: A heading, a name line, and two Malquadrate for the Einmaleins with the factors given at the edges and the products to fill in.
tags: [malquadrat, einmaleins, klasse-3]
covers: [text, name, malquadrat]
generated: { by: "human:pgoell", at: 2026-10-19T19:47:30Z }
---

# Malquadrate

When a teacher asks for: "Ein Arbeitsblatt mit zwei Malquadraten zum Einmaleins."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the squares are the button "Malquadrat" in the menu "Mathe-Blöcke" in the insert bar. A Malquadrat is a square of products: the row numbers stand down the left, the column numbers along the top, and each inner cell is the row number times (or plus) the column number. The sum of each row and column sits outside, and the total in the corner.
* `op` is "*" (Mal, the default) or "+" (Plus, the addition version).
* `reihen` are the Einmaleins-Reihen the column numbers come from (default 2 to 9). With Mal the factors stay in these rows.
* `size` is the number of inner cells per side, 2 to 4 (default 3).
* `task` says what the pupil fills in: "factors" (default) gives every row and column number, and the pupil fills the rest. "mixed" hides some of the row and column numbers and gives a cell for each. "knobel" does the same, and one hidden row is found only through its sum.
* `max` is the Zahlenraum for Plus, 20, 100 or 1000 (default 20).
* `count` is the number of squares (1 to 4) and `columns` how many sit side by side (1 to 3).
* The block's height follows its squares. Two 3 × 3 squares side by side at 180 mm wide are 93.98 mm tall.
* See [malquadrat](../blocks/malquadrat.md) for the other props.

Do not type numbers into `typed` unless the teacher gave them. The Varianten B to D draw new squares and drop the typed numbers, and a square whose typed numbers do not fit is marked wrong.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new squares.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "5b1d7e04-2c9a-4f63-8e21-9a3c6f0b7d01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Malquadrate",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "5b1d7e04-2c9a-4f63-8e21-9a3c6f0b7d02",
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
          "id": "5b1d7e04-2c9a-4f63-8e21-9a3c6f0b7d03",
          "type": "malquadrat",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 93.98,
          "z": 3,
          "locked": false,
          "props": {
            "count": 2,
            "columns": 2,
            "size": 3,
            "op": "*",
            "reihen": [2, 3, 4, 5, 6, 7, 8, 9],
            "max": 20,
            "task": "factors",
            "seed": 4
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
