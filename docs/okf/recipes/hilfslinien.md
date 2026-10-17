---
type: How-to
title: "Hilfslinien setzen"
description: Two columns of text that line up on the sheet's guides at 15, 105 and 195 mm.
tags: [hilfslinien, spalten, layout]
covers: [text]
generated: { by: "human:pgoell", at: 2026-10-17T17:00:00Z }
---

# Hilfslinien setzen

When a teacher asks for: "Ein Blatt mit zwei Spalten, die sauber untereinander stehen."

* `guides` holds the guide lines in mm. `x: [15, 105, 195]` puts a line at the left margin, in the middle of the gutter, and at the right margin. The guides show in the editor and never print.
* The left column runs from x 15 to x 100 (w 85). The right column runs from x 110 to x 195 (w 85), so both sit on the guides.
* Doc guides apply to every page. A page can hold its own guides with `set_page`, and `guides` there only changes that page.
* In the editor the teacher sets the guides in the panel of the button "Format und Ansicht", tab "Ansicht", under the heading "Hilfslinien". Dragging a guide's number off the sheet removes it.
* See [text](../blocks/text.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the guides to set other columns.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "b5e2f7a1-9d30-4c8b-a6e4-1f7d2c9b0e01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Zwei Spalten",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "b5e2f7a1-9d30-4c8b-a6e4-1f7d2c9b0e02",
          "type": "text",
          "x": 15,
          "y": 35,
          "w": 85,
          "h": 60,
          "z": 2,
          "locked": false,
          "props": {
            "text": "Links schreiben.",
            "size": 14,
            "align": "left"
          }
        },
        {
          "id": "b5e2f7a1-9d30-4c8b-a6e4-1f7d2c9b0e03",
          "type": "text",
          "x": 110,
          "y": 35,
          "w": 85,
          "h": 60,
          "z": 3,
          "locked": false,
          "props": {
            "text": "Rechts schreiben.",
            "size": 14,
            "align": "left"
          }
        }
      ]
    }
  ],
  "guides": {
    "x": [15, 105, 195],
    "y": []
  },
  "grid": 0
}
```
