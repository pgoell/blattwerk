---
type: How-to
title: "Lernwörter mit Lineatur und Silbenbögen"
description: Four Lernwörter on a two-line ruling, each word in grey to write over with a bow under each syllable.
tags: [lernwoerter, silben, lineatur, klasse-1]
covers: [text, name, ruling]
generated: { by: "human:pgoell", at: 2026-10-19T06:10:00Z }
---

# Lernwörter mit Lineatur und Silbenbögen

When a teacher asks for: "Ein Blatt mit Lernwörtern, Lineatur und Silbenbögen."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* The four words go in the doc's `words` list. The ruling block is kind `l2` and links to that list with `list: "trace"`, so each word gets its own row, printed in grey for the pupil to write over.
* `syllables: true` draws a bow under each syllable of each listed word.
* In the editor the ruling is the button "Lineatur" in the insert bar, group "Schule".
* See [ruling](../blocks/ruling.md) for the kinds.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or add the blocks with `add_block`. Change the words in the doc's `words` to change the sheet, or call `set_words`.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "d40a04b0-97b7-4f93-8277-d0ab462c06d2",
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
          "id": "6a49646a-8c26-49a8-9568-acdaa4a1cdd9",
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
          "id": "ad269260-d56f-4b7e-bf6b-2e5036d5a168",
          "type": "ruling",
          "x": 15,
          "y": 55,
          "w": 180,
          "h": 120,
          "z": 3,
          "locked": false,
          "props": {
            "kind": "l2",
            "color": "#222222",
            "list": "trace",
            "syllables": true
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
  "words": ["Hase", "Igel", "Maus", "Katze"]
}
```
