---
type: How-to
title: "Zahlenstrahl bis 100"
description: A heading, a name line, and a Zahlenstrahl from 0 to 100 with boxes to fill in.
tags: [zahlenstrahl, zahlenraum-100, klasse-2]
covers: [text, name, zahlenstrahl]
generated: { by: "human:pgoell", at: 2026-10-17T16:00:00Z }
---

# Zahlenstrahl bis 100

When a teacher asks for: "Ein Blatt mit einem Zahlenstrahl bis 100, mit Kästchen zum Ausfüllen."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the line is the button "Zahlenstrahl" in the menu "Mathe-Blöcke" in the insert bar, group "Mathe". `tasks` "random" puts the boxes and arrows on ticks chosen from `seed`. `major` sets the long ticks, and `labels` "major" prints their numbers.
* See [zahlenstrahl](../blocks/zahlenstrahl.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new boxes.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "a6c2e9f4-3b8d-4f1a-9e5c-2d7b0a8f6e01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Zahlenstrahl bis 100",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "a6c2e9f4-3b8d-4f1a-9e5c-2d7b0a8f6e02",
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
          "id": "a6c2e9f4-3b8d-4f1a-9e5c-2d7b0a8f6e03",
          "type": "zahlenstrahl",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 30,
          "z": 3,
          "locked": false,
          "props": {
            "start": 0,
            "end": 100,
            "minor": 1,
            "major": 10,
            "labels": "major",
            "size": 12,
            "cut": false,
            "tasks": "random",
            "boxes": 3,
            "arrows": 1,
            "jumps": false,
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
