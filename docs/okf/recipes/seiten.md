---
type: How-to
title: "Ein Blatt mit zwei Seiten"
description: "Two pages: a heading, a name line and a text task on page 1, then a heading and a ruling on page 2."
tags: [seiten, mehrseitig, lineatur]
covers: [text, name, ruling]
generated: { by: "human:pgoell", at: 2026-10-17T17:00:00Z }
---

# Ein Blatt mit zwei Seiten

When a teacher asks for: "Ein Blatt mit zwei Seiten, auf der ersten Seite eine Aufgabe und auf der zweiten Linien."

* Page 1 holds the heading, the name line and the text task. Page 2 holds its own heading and a ruling.
* `pages` lists the pages in print order. Each page has its own `blocks`. Every `y` counts from the top of its own page, so page 2 starts again at 15 mm.
* Add a page with `add_page`. Its `after` is the number of the page to put it behind, so `after: 1` makes a new page 2.
* In the editor the button "Neue Seite" adds an empty page at the end. The button "Seite duplizieren" copies the page the teacher is on.
* See [text](../blocks/text.md) and [ruling](../blocks/ruling.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it page by page with `add_block` and `add_page`. Change the words for other sheets.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "3f1c8e20-7a4b-4d9e-8c15-2b6a9d0e4a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Der Igel",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "3f1c8e20-7a4b-4d9e-8c15-2b6a9d0e4a02",
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
          "id": "3f1c8e20-7a4b-4d9e-8c15-2b6a9d0e4a03",
          "type": "text",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 60,
          "z": 3,
          "locked": false,
          "props": {
            "text": "Schreibe drei Sätze über den Igel.",
            "size": 14,
            "align": "left"
          }
        }
      ]
    },
    {
      "blocks": [
        {
          "id": "3f1c8e20-7a4b-4d9e-8c15-2b6a9d0e4a04",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Mehr vom Igel",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "3f1c8e20-7a4b-4d9e-8c15-2b6a9d0e4a05",
          "type": "ruling",
          "x": 15,
          "y": 35,
          "w": 180,
          "h": 120,
          "z": 2,
          "locked": false,
          "props": {
            "kind": "l1",
            "color": "#222222"
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
