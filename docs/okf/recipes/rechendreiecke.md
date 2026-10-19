---
type: How-to
title: "Rechendreiecke"
description: A heading, a name line, and four Rechendreiecke with some fields given and the rest to fill in.
tags: [rechendreieck, zahlenraum-20, klasse-1]
covers: [text, name, rechendreieck]
generated: { by: "human:pgoell", at: 2026-10-19T06:10:00Z }
---

# Rechendreiecke

When a teacher asks for: "Ein Blatt mit Rechendreiecken bis 20, einige Zahlen gegeben."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the triangles are the button "Rechendreieck" in the menu "Mathe-Blöcke" in the insert bar, group "Mathe". `given` says which fields show their number: "mix" gives two inner fields and one outer field.
* See [rechendreieck](../blocks/rechendreieck.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new triangles.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "e1f5a8b3-6d2c-4b9e-8f70-3a4c1e6b2d01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Rechendreiecke",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "e1f5a8b3-6d2c-4b9e-8f70-3a4c1e6b2d02",
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
          "id": "e1f5a8b3-6d2c-4b9e-8f70-3a4c1e6b2d03",
          "type": "rechendreieck",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 50,
          "z": 3,
          "locked": false,
          "props": {
            "count": 4,
            "columns": 4,
            "max": 20,
            "given": "mix",
            "empty": false,
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
