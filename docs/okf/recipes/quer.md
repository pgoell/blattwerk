---
type: How-to
title: "Ein Blatt quer"
description: A sheet turned landscape, with a heading and a table across its full width.
tags: [quer, tabelle, wochentage, klasse-1]
covers: [text, table]
generated: { by: "human:pgoell", at: 2026-10-18T04:30:00Z }
---

# Ein Blatt quer

When a teacher asks for: "Ein Blatt quer mit einer Tabelle über die ganze Breite."

* `landscape: true` on the doc turns every page to 297 by 210 mm. A page can turn alone with `landscape` on its own entry, or `set_page` with `landscape: true` on that page.
* The heading and the table run from x 15 to x 282 mm, so the width is 267 mm.
* The table's `cells` hold the text row by row, and `cols` the width share of each column. `head` true sets the first row in bold.
* In the editor the teacher turns the sheet with the button "Format und Ansicht": in the tab "Ansicht", under "Format, Raster und Hilfslinien für", she picks the sheet or one page, then "Hoch" or "Quer". A page on "Wie Blatt" follows the sheet.
* When a page turns Quer and already holds blocks, `set_page` warns of the blocks that leave the page. Move them with `move_block`.
* See [table](../blocks/table.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the cells for other words.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "7a0d3b52-c1e8-4f96-9b24-5e8f1a6c2d01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 267,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Die Wochentage",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "7a0d3b52-c1e8-4f96-9b24-5e8f1a6c2d02",
          "type": "table",
          "x": 15,
          "y": 40,
          "w": 267,
          "h": 50,
          "z": 2,
          "locked": false,
          "props": {
            "cells": [
              ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"],
              ["", "", "", "", ""],
              ["", "", "", "", ""]
            ],
            "cols": [1, 1, 1, 1, 1],
            "rows": [10, 20, 20],
            "size": 14,
            "align": "center",
            "line": "#222222",
            "head": true
          }
        }
      ],
      "landscape": true
    }
  ],
  "guides": {
    "x": [],
    "y": []
  },
  "grid": 0,
  "landscape": true
}
```
