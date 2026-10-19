---
type: How-to
title: "Magische Quadrate"
description: A heading, a name line, and two 3 × 3 Magische Quadrate bis 20 with the Zielzahl shown and four cells given.
tags: [magischesquadrat, zahlenquadrat, klasse-3]
covers: [text, name, magischesquadrat]
generated: { by: "human:pgoell", at: 2026-10-19T17:00:00Z }
---

# Magische Quadrate

When a teacher asks for: "Ein Arbeitsblatt mit zwei magischen Quadraten (3 × 3) bis 20, die Zielzahl soll dastehen."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the squares are the button "Magisches Quadrat" in the menu "Mathe-Blöcke" in the insert bar. A Magisches Quadrat is a square of cells where every row, every column and both diagonals have the same sum, the Zielzahl.
* `size` is 3 (3 × 3, the default) or 5 (5 × 5).
* `max` is the Zahlenraum: the largest number in a drawn square (20, 100, 1000 or any whole number from 9 for a 3 × 3 to 9999). A 5 × 5 needs at least 25.
* `given` is how many cells the pupil sees filled in. With 3 or more given cells in a 3 × 3 the square has one solution; with fewer the key says that other answers count too.
* `showSum` prints the Zielzahl above each square as "Zielzahl: 15".
* `count` is the number of squares (1 to 4) and `columns` how many sit side by side (1 to 3).
* The block's height follows its squares: two 3 × 3 squares side by side at 180 mm wide with the Zielzahl shown are 117.39 mm tall.
* See [magischesquadrat](../blocks/magischesquadrat.md) for the other props.

Do not type numbers into `typed` unless the teacher gave them. The Varianten B to D draw new squares and drop the typed numbers, and a square whose typed numbers do not fit is marked wrong.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new squares.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "3e8a5c21-7d4b-4f90-9b16-2a6c0d1e8f01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Magische Quadrate",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "3e8a5c21-7d4b-4f90-9b16-2a6c0d1e8f02",
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
          "id": "3e8a5c21-7d4b-4f90-9b16-2a6c0d1e8f03",
          "type": "magischesquadrat",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 117.39,
          "z": 3,
          "locked": false,
          "props": {
            "count": 2,
            "columns": 2,
            "size": 3,
            "max": 20,
            "given": 4,
            "showSum": true,
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
