---
type: How-to
title: "Hunderterfeld"
description: A heading, a name line, and a Hundertertafel with twenty numbers hidden for the pupil to fill in.
tags: [hunderterfeld, zahlenraum-100, klasse-1]
covers: [text, name, hunderterfeld]
generated: { by: "human:pgoell", at: 2026-10-17T16:00:00Z }
---

# Hunderterfeld

When a teacher asks for: "Ein Blatt mit einem Hunderterfeld, einige Zahlen fehlen."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the field is the button "Hunderterfeld" in the menu "Mathe-Blöcke" under Einfügen. `look` "tafel" draws the numbers, "punkte" draws dots. `show` "random" hides `hide` numbers, picked from `seed`.
* See [hunderterfeld](../blocks/hunderterfeld.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for other hidden numbers.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "3f7b1d8e-5a2c-4e6f-9b49-8d0a6c3e5f01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Das Hunderterfeld",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "3f7b1d8e-5a2c-4e6f-9b49-8d0a6c3e5f02",
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
          "id": "3f7b1d8e-5a2c-4e6f-9b49-8d0a6c3e5f03",
          "type": "hunderterfeld",
          "x": 15,
          "y": 60,
          "w": 100,
          "h": 100,
          "z": 3,
          "locked": false,
          "props": {
            "look": "tafel",
            "from": 1,
            "show": "random",
            "hide": 20,
            "tint": "none",
            "times": 2,
            "line": 1,
            "color": 1,
            "cut": false,
            "given": 44,
            "fill": "count",
            "dots": 0,
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
