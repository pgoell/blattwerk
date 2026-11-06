---
type: How-to
title: "Zahlzerlegung"
description: A heading, a name line, and six Zahlzerlegung tasks bis 1000 where the pupil splits each number into its Hunderter, Zehner and Einer (348 = 300 + 40 + 8).
tags: [zahlzerlegung, stellenwert, zahlen, klasse-2]
covers: [text, name, zahlzerlegung]
generated: { by: "human:pgoell", at: 2026-11-06T18:30:00Z }
---

# Zahlzerlegung

When a teacher asks for: "Ein Arbeitsblatt mit sechs Zerlegungsaufgaben bis 1000: die Kinder zerlegen die Zahl in Hunderter, Zehner und Einer."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the block is the button "Zahlzerlegung" in the menu "Mathe-Blöcke" in the insert bar.
* A Zahlzerlegung block shows each number and the pupil writes its place values in the gaps (348 = __ + __ + __).
* `count` is the number of tasks (1 to 12, default 6) and `columns` how many sit side by side (1 to 3, default 2).
* `max` is the Zahlenraum: 1000 (default for this recipe), 100 or 10000.
* `task` is "split" (Zerlegen, the default for this recipe). Other values are in [zahlzerlegung](../blocks/zahlzerlegung.md).
* `seed` gives the tasks. The same seed gives the same tasks. Change the seed to change them.
* See [zahlzerlegung](../blocks/zahlzerlegung.md) for the other props.

Do not type numbers into `typed` unless the teacher gave them. The Varianten B to D draw new tasks and drop the typed numbers.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new tasks.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "7e4b9c21-5a0d-4f3e-8b12-3c9d6a1f0e01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Zahlzerlegung",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "7e4b9c21-5a0d-4f3e-8b12-3c9d6a1f0e02",
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
          "id": "7e4b9c21-5a0d-4f3e-8b12-3c9d6a1f0e03",
          "type": "zahlzerlegung",
          "x": 15,
          "y": 60,
          "w": 145,
          "h": 35,
          "z": 3,
          "locked": false,
          "props": {
            "count": 6,
            "columns": 2,
            "max": 1000,
            "task": "split",
            "seed": 7
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
