---
type: How-to
title: "Zeichen farbig markieren"
description: A text with vowels in red and a letter group such as "sch" in green. Punctuation stays uncoloured.
tags: [zeichen, vokale, umlaute, deutsch, klasse-1]
covers: [text, name]
generated: { by: "human:pgoell", at: 2026-11-03T05:45:00Z }
---

# Zeichen farbig markieren

When a teacher asks for: "Markiere die Vokale rot und sch am Wortanfang grün."

* `marks` colours letters. `vowels` is a, e, i, o, u. `umlauts` is ä, ö, ü, and they are not vowels here, so each can have its own colour. `consonants` is every other letter. `first` and `last` colour the first or last letter of each word.
* `groups` holds up to three groups. Each has `letters` (such as "sch", "ei" or "ie"), `where` (`any`, `start` or `end`) and `color`. A group wins over a place, and a place wins over a kind. A fourth group is left out.
* Punctuation, digits and spaces are not coloured. They keep the text's own colour.
* The same `marks` work on a text, a shape, a table and a Lineatur.
* In the editor the teacher sets this under "Zeichen" in the format panel.
* See [text](../blocks/text.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the text and the colours for other words.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "9d6f2b03-5a1e-4c78-b2d9-e4a0c7f81c01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Zeichen",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "9d6f2b03-5a1e-4c78-b2d9-e4a0c7f81c02",
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
          "id": "9d6f2b03-5a1e-4c78-b2d9-e4a0c7f81c03",
          "type": "text",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 30,
          "z": 3,
          "locked": false,
          "props": {
            "text": "Schule, Ei und die Maus!",
            "size": 20,
            "align": "left",
            "marks": {
              "vowels": "#e02424",
              "groups": [
                {"letters": "sch", "where": "start", "color": "#2f9e44"}
              ]
            }
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
