---
type: How-to
title: "Namenszeile und Punkte"
description: A heading, a name line, a text task with its points box beside it, and a total points box at the foot.
tags: [punkte, namenszeile, klasse-1]
covers: [text, name, points]
generated: { by: "human:pgoell", at: 2026-10-17T16:00:00Z }
---

# Namenszeile und Punkte

When a teacher asks for: "Ein Blatt mit Namenszeile und Punkteangabe für eine Aufgabe."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the points box is the button "Punkte" in the insert bar, group "Schule". Its `max` is the most points the task gives. The total box has `total` set and adds up every task box on the sheet.
* See [points](../blocks/points.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the task text and the points for another task.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "b7d3e1a5-2c9f-4a6b-8e04-5f1d9c2a7b01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Rechnen mit Punkten",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "b7d3e1a5-2c9f-4a6b-8e04-5f1d9c2a7b02",
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
          "id": "b7d3e1a5-2c9f-4a6b-8e04-5f1d9c2a7b03",
          "type": "text",
          "x": 15,
          "y": 60,
          "w": 140,
          "h": 20,
          "z": 3,
          "locked": false,
          "props": {
            "text": "Rechne aus: 8 + 6 = ____ und 14 - 5 = ____.",
            "size": 14,
            "align": "left"
          }
        },
        {
          "id": "b7d3e1a5-2c9f-4a6b-8e04-5f1d9c2a7b04",
          "type": "points",
          "x": 160,
          "y": 60,
          "w": 35,
          "h": 12,
          "z": 4,
          "locked": false,
          "props": {
            "max": 10
          }
        },
        {
          "id": "b7d3e1a5-2c9f-4a6b-8e04-5f1d9c2a7b05",
          "type": "points",
          "x": 155,
          "y": 262,
          "w": 40,
          "h": 12,
          "z": 5,
          "locked": false,
          "props": {
            "max": 10,
            "total": true
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
