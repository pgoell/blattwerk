---
type: How-to
title: "Zahlenmauern"
description: A heading, a name line, and four Zahlenmauern with the sums above the given foot stones to fill in.
tags: [zahlenmauer, zahlen, klasse-1]
covers: [text, name, zahlenmauer]
generated: { by: "human:pgoell", at: 2026-10-18T04:30:00Z }
---

# Zahlenmauern

When a teacher asks for: "Ein Blatt mit Zahlenmauern zum Rechnen, Zahlen bis 20."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* The zahlenmauer block draws four walls with three stones at the foot of each, every stone above is the sum of the two under it. The foot stones are given, the rest is for the pupil to fill in.
* In the editor the walls are the button "Zahlenmauer" in the menu "Mathe-Blöcke" in the insert bar, group "Mathe".
* See [zahlenmauer](../blocks/zahlenmauer.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new numbers.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "9a4f6b21-7c3d-4e5a-8b10-2d6e1f3c9a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Zahlenmauern",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "9a4f6b21-7c3d-4e5a-8b10-2d6e1f3c9a02",
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
          "id": "9a4f6b21-7c3d-4e5a-8b10-2d6e1f3c9a03",
          "type": "zahlenmauer",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 100,
          "z": 3,
          "locked": false,
          "props": {
            "base": 3,
            "count": 4,
            "columns": 2,
            "max": 20,
            "op": "+",
            "given": "base",
            "empty": false,
            "seed": 3
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
