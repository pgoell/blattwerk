---
type: How-to
title: "Zahlenhäuser"
description: A heading, a name line, and four Zahlenhäuser with the left box of each floor given and the rest to fill in.
tags: [zahlenhaus, zahlenraum-10, klasse-1]
covers: [text, name, zahlenhaus]
generated: { by: "human:pgoell", at: 2026-10-19T06:10:00Z }
---

# Zahlenhäuser

When a teacher asks for: "Ein Blatt mit Zahlenhäusern bis 10, einige Zahlen gegeben."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the houses are the button "Zahlenhaus" in the menu "Mathe-Blöcke" in the insert bar. `given` says which boxes show their number: "side" gives the roof and the left box of each floor, "roof" gives the roof only, "mix" gives the roof and one box of each floor, and "free" shows the boxes flagged in `free`.
* See [zahlenhaus](../blocks/zahlenhaus.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new houses.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "a7c3e1d0-4b8f-4e2a-9d61-5f0b2c8e3a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Zahlenhäuser",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "a7c3e1d0-4b8f-4e2a-9d61-5f0b2c8e3a02",
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
          "id": "a7c3e1d0-4b8f-4e2a-9d61-5f0b2c8e3a03",
          "type": "zahlenhaus",
          "x": 15,
          "y": 60,
          "w": 120,
          "h": 55,
          "z": 3,
          "locked": false,
          "props": {
            "count": 4,
            "columns": 4,
            "floors": 4,
            "max": 10,
            "given": "side",
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
