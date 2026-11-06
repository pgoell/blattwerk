---
type: How-to
title: "Stellenwerttafel"
description: A heading, a name line, and four Stellenwerttafeln bis 1000 with Plättchen shown, the number to write in each table.
tags: [stellenwerttafel, stellenwert, plaettchen, zahlen, klasse-3]
covers: [text, name, stellenwerttafel]
generated: { by: "human:pgoell", at: 2026-11-06T19:45:00Z }
---

# Stellenwerttafel

When a teacher asks for: "Ein Arbeitsblatt mit vier Stellenwerttafeln bis 1000 mit Plättchen: die Kinder lesen die Plättchen und schreiben die Zahl."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the block is the button "Stellenwerttafel" in the menu "Mathe-Blöcke" in the insert bar.
* A Stellenwerttafel block shows a table with the places H, Z and E. The Plättchen (dots) lie in the columns. Right of the table, after "=", the pupil writes the number in a box.
* `count` is the number of tables (1 to 12, default 4) and `columns` how many sit side by side (1 to 4, default 2).
* `max` is the Zahlenraum: 1000 (default for this recipe) or 10000.
* `task` is "read" (Plättchen gegeben, Zahl schreiben, the default for this recipe). "lay" gives the number and the pupil draws the Plättchen in the empty table. "move" gives the Plättchen and the pupil moves one Plättchen to another column and writes each new number.
* `dots` is the most Plättchen in one task (1 to 36, default 9). `zero` set to false (default) gives every column at least one Plättchen, so no 0 digit. `zero` set to true lets a column stay empty.
* `seed` gives the tasks. The same seed gives the same tasks. Change the seed to change them.
* See [stellenwerttafel](../blocks/stellenwerttafel.md) for the other props.
* For the answers, the teacher presses the button "Lösungen zeigen" herself ([what she does herself](../teacher-does.md)).

Do not type numbers into `typed` unless the teacher gave them. The Varianten B to D draw new tasks and drop the typed numbers.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new tasks.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "3b8f6d2e-9c1a-4e7b-a5d0-6f2e8c4b9a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Stellenwerttafel",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "3b8f6d2e-9c1a-4e7b-a5d0-6f2e8c4b9a02",
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
          "id": "3b8f6d2e-9c1a-4e7b-a5d0-6f2e8c4b9a03",
          "type": "stellenwerttafel",
          "x": 15,
          "y": 60,
          "w": 147,
          "h": 47,
          "z": 3,
          "locked": false,
          "props": {
            "count": 4,
            "columns": 2,
            "max": 1000,
            "task": "read",
            "dots": 9,
            "zero": false,
            "seed": 1
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
