---
type: How-to
title: "Uhrzeiten lesen"
description: A heading, a name line, and six clocks with full and half hours to read, the time written under each.
tags: [uhr, uhrzeit, klasse-1]
covers: [text, name, uhr]
generated: { by: "human:pgoell", at: 2026-10-16T17:55:00Z }
---

# Uhrzeiten lesen

When a teacher asks for: "Ein Blatt mit Uhrzeiten zum Lesen, volle und halbe Stunden."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* The uhr block draws six clocks in three columns, each with a time on the hour or the half hour, from the seed. The pupil writes the time in the box under each clock.
* See [uhr](../blocks/uhr.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new times.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "7c1d2e4a-3b5f-4e8a-9d61-2f0a8b6c1e01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Uhrzeiten lesen",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "7c1d2e4a-3b5f-4e8a-9d61-2f0a8b6c1e02",
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
          "id": "7c1d2e4a-3b5f-4e8a-9d61-2f0a8b6c1e03",
          "type": "uhr",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 200,
          "z": 3,
          "locked": false,
          "props": {
            "numbers": "all",
            "minutes": true,
            "ring": false,
            "task": "read",
            "answer": "box",
            "format": "12",
            "region": "nach",
            "count": 6,
            "cols": 3,
            "step": 30,
            "fill": "random",
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
