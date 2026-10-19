---
type: How-to
title: "Suchsel mit Tieren"
description: A heading, a name line, and a word search of five animal words, running down, with the words printed under the grid.
tags: [deutsch, suchsel, tiere, klasse-2]
covers: [text, name, suchsel]
generated: { by: "human:pgoell", at: 2026-10-19T06:10:00Z }
---

# Suchsel mit Tieren

When a teacher asks for: "Ein Suchsel mit Tieren, die Wörter stehen darunter."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* The suchsel block hides five animal words in a grid of 12 by 10 squares. The words run down, and the list under the grid gives them in capitals. The seed sets the letters, so the sheet prints the same way each time.
* In the editor the word search is the button "Suchsel" in the insert bar, group "Schule".
* See [suchsel](../blocks/suchsel.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the words or the seed for new tasks.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "b04f1d82-6e3a-4c9b-a517-9d2e8f3c4b01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Suchsel mit Tieren",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "b04f1d82-6e3a-4c9b-a517-9d2e8f3c4b02",
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
          "id": "b04f1d82-6e3a-4c9b-a517-9d2e8f3c4b03",
          "type": "suchsel",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 200,
          "z": 3,
          "locked": false,
          "props": {
            "words": ["HUND", "KATZE", "MAUS", "PFERD", "IGEL"],
            "cols": 12,
            "rows": 10,
            "ways": "down",
            "caps": true,
            "umlauts": true,
            "show": "words",
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
