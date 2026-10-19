---
type: How-to
title: "Lernwörter verknüpfen"
description: Five Lernwörter in the sheet's list, a ruling that copies them, and a text that blanks out their vowels.
tags: [lernwoerter, lineatur, luecken, verknuepft, klasse-1]
covers: [text, name, ruling]
generated: { by: "human:pgoell", at: 2026-10-19T06:10:00Z }
---

# Lernwörter verknüpfen

When a teacher asks for: "Ein Blatt mit fünf Lernwörtern zum Abschreiben und ein Lückentext mit denselben Wörtern."

* The five words go in the doc's `words` list, one entry per word. Every block that links to the list follows it.
* The ruling with `list: "copy"` prints each word on its own row, with the word to copy on the row.
* The text with `list: true` prints the words, one to a paragraph, in `listCols` columns. `holes: "vowels"` blanks out the vowels, and `holeSeed` picks the same gaps on every print.
* `set_words` with `sheet_id`, `version` and `words` changes the list. Every linked block changes with it, so the sheet needs no other edit.
* A second ruling on page 2 with `from: 5` shows the words from index 5 on, counted from 0. Use it when the list runs over more than one ruling.
* In the editor the list is the tab "Lernwörter" in the panel, and the teacher adds a ruling with the button "Lineatur".
* See [ruling](../blocks/ruling.md) and [text](../blocks/text.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or add the blocks with `add_block`. Change the `words` to change the sheet.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "c8a4d1f9-2e6b-4a37-8f05-9d3b7e1c4a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Lernwörter",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "c8a4d1f9-2e6b-4a37-8f05-9d3b7e1c4a02",
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
          "id": "c8a4d1f9-2e6b-4a37-8f05-9d3b7e1c4a03",
          "type": "ruling",
          "x": 15,
          "y": 55,
          "w": 180,
          "h": 100,
          "z": 3,
          "locked": false,
          "props": {
            "kind": "l2",
            "color": "#222222",
            "list": "copy"
          }
        },
        {
          "id": "c8a4d1f9-2e6b-4a37-8f05-9d3b7e1c4a04",
          "type": "text",
          "x": 15,
          "y": 160,
          "w": 180,
          "h": 60,
          "z": 4,
          "locked": false,
          "props": {
            "text": "Lernwörter",
            "size": 14,
            "align": "left",
            "list": true,
            "listCols": 2,
            "holes": "vowels",
            "holeSeed": 1
          }
        }
      ]
    }
  ],
  "guides": {
    "x": [],
    "y": []
  },
  "grid": 0,
  "words": ["Hase", "Igel", "Maus", "Katze", "Fisch"]
}
```
