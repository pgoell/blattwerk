---
type: How-to
title: "Zahlenmauern bis 20"
description: A heading, a name line, and two walls of four stones each with the base row given, the sums up to 20 to fill in above.
tags: [mathe, zahlenmauer, klasse-2]
covers: [text, name, zahlenmauer]
generated: { by: "human:pgoell", at: 2026-10-16T17:55:00Z }
---

# Zahlenmauern bis 20

When a teacher asks for: "Zahlenmauern bis 20 zum Ausrechnen."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* The zahlenmauer block draws two walls side by side. Each has a base row of four stones with numbers, and the pupil adds the stones above, up to 20. The seed sets the walls, so the sheet prints the same way each time.
* See [zahlenmauer](../blocks/zahlenmauer.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new walls.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "3e9a6b20-5d1c-4f7e-8b2a-6c4d0e9f1a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Zahlenmauern bis 20",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "3e9a6b20-5d1c-4f7e-8b2a-6c4d0e9f1a02",
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
          "id": "3e9a6b20-5d1c-4f7e-8b2a-6c4d0e9f1a03",
          "type": "zahlenmauer",
          "x": 15,
          "y": 60,
          "w": 120,
          "h": 150,
          "z": 3,
          "locked": false,
          "props": {
            "base": 3,
            "count": 2,
            "columns": 2,
            "max": 20,
            "op": "+",
            "given": "base",
            "empty": false,
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
