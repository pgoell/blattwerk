---
type: How-to
title: "Silbenbögen und Silbenfarbe"
description: A text with a bow under each syllable, the syllables in two colours.
tags: [silben, silbenboegen, silbenfarbe, deutsch, klasse-1]
covers: [text, name]
generated: { by: "human:pgoell", at: 2026-10-19T06:10:00Z }
---

# Silbenbögen und Silbenfarbe

When a teacher asks for: "Ein Text mit Silbenbögen, die Silben in Blau und Rot."

* `syllables: true` draws a bow under each syllable of each word.
* `tints` holds two hex colours. The syllables take them in turn, the first and then the second. `tintsAcross: true` carries the turn on from word to word. Without it, each word starts again with the first colour.
* In the editor the teacher sets the same on a text with the checkboxes "Silbenbögen" and "Silbenfarbe" in the format panel of the button "Text".
* `breaks` sets a word's syllables by hand when the program splits it wrong. Leave it out otherwise.
* See [text](../blocks/text.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the text for other words.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "9d6f2b03-5a1e-4c78-b2d9-e4a0c7f81b01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Silben",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "9d6f2b03-5a1e-4c78-b2d9-e4a0c7f81b02",
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
          "id": "9d6f2b03-5a1e-4c78-b2d9-e4a0c7f81b03",
          "type": "text",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 60,
          "z": 3,
          "locked": false,
          "props": {
            "text": "Hase Igel Maus Katze Fisch Banane Sonne Tiger",
            "size": 20,
            "align": "left",
            "syllables": true,
            "tints": ["#1a56db", "#e02424"]
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
