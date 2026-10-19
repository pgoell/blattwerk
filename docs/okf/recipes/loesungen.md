---
type: How-to
title: "Lückentext mit Lösungen"
description: A text with four gaps for the pupil, a word box under it, and the answer key shown for the teacher.
tags: [luecken, loesungen, lueckentext, deutsch, klasse-2]
covers: [text, name]
generated: { by: "human:pgoell", at: 2026-10-19T06:10:00Z }
---

# Lückentext mit Lösungen

When a teacher asks for: "Ein Lückentext mit einer Wortbox darunter und den Lösungen für mich."

* A gap is a run in `rich` with `gap: true`. Its words are the answer, and the pupil sees a line in their place.
* `text` holds the same words as one plain string. Keep the two in step.
* `gapWidth: 25` makes every gap at least 25 mm wide, so the pupil has room to write.
* `bank: 3` prints a box of the hidden words under the text, shuffled. The number is the seed for the order.
* The teacher sees the answers with the button "Lösungen zeigen". To print them, the teacher downloads the PDF "Lösungen". The plain PDF has no answers.
* See [text](../blocks/text.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the runs and the `text` for other gaps.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "a4f9e6c2-8b07-4e3d-9c51-7d2b0f8e3a01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Tiere im Haus",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "a4f9e6c2-8b07-4e3d-9c51-7d2b0f8e3a02",
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
          "id": "a4f9e6c2-8b07-4e3d-9c51-7d2b0f8e3a03",
          "type": "text",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 90,
          "z": 3,
          "locked": false,
          "props": {
            "text": "Der Hund bellt laut, die Katze schläft im Korb.",
            "rich": [
              {
                "runs": [
                  {"text": "Der "},
                  {"text": "Hund", "gap": true},
                  {"text": " bellt "},
                  {"text": "laut", "gap": true},
                  {"text": ", die "},
                  {"text": "Katze", "gap": true},
                  {"text": " schläft im "},
                  {"text": "Korb", "gap": true},
                  {"text": "."}
                ]
              }
            ],
            "size": 14,
            "align": "left",
            "gapWidth": 25,
            "bank": 3
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
