---
type: How-to
title: "Lernwörter mit Lineatur und Silbenbögen"
description: Four Lernwörter on a two-line ruling, each word in grey to copy with a bow under each syllable.
tags: [lernwoerter, silben, lineatur, klasse-1]
covers: [text, name, ruling]
generated: { by: "human:pgoell", at: 2026-10-16T00:00:00Z }
---

# Lernwörter mit Lineatur und Silbenbögen

When a teacher asks for: "Ein Blatt mit Lernwörtern, Lineatur und Silbenbögen."

* The words live in `doc.words`. Set them with `set_words`, or put them in the doc of `replace_doc`.
* The ruling block takes its words from that list (`list: "copy"`), one to a row, and it has the kind `l2` ruling.
* `syllables: true` draws a bow under each syllable. `trace: true` prints the word in grey for the pupil to write over.
* See [ruling](../blocks/ruling.md) for the kinds and the list modes.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or set the words with `set_words` and add the blocks with `add_block`. Change the words to change the sheet.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "7b8896a0-7fba-41d4-8879-203e071fdee1",
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
          "id": "1f41e01f-d2ee-4a76-b14e-8b4c3f90eef8",
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
          "id": "eed41d0e-ccdf-4090-924d-36e216ed112a",
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
            "list": "copy",
            "syllables": true,
            "trace": true
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
  "words": [
    "Hase",
    "Igel",
    "Maus",
    "Katze"
  ]
}
```
