---
type: How-to
title: "Plusaufgaben bis 20 mit Selbstkontrolle"
description: A heading, a name line, twelve addition sums to 20 with a fixed seed, and a self-check that lists the results shuffled.
tags: [maths, selbstkontrolle, klasse-1]
covers: [text, name, maths, selbstkontrolle]
generated: { by: "human:pgoell", at: 2026-10-16T00:00:00Z }
---

# Plusaufgaben bis 20 mit Selbstkontrolle

When a teacher asks for: "Ein Blatt mit Plusaufgaben bis 20 und Selbstkontrolle."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* The maths block makes twelve `+` sums with results up to 20, in three columns. The seed fixes the sums, so the sheet prints the same way each time.
* The selbstkontrolle block lists the results in a shuffled order, each with a box to tick. Its `links` holds the id of the maths block, so it checks those sums.
* See [maths](../blocks/maths.md) and [selbstkontrolle](../blocks/selbstkontrolle.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new tasks.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "bf141883-d388-4fdc-bb4d-6fc6bfc2c02e",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Plusaufgaben bis 20",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "55225855-8c75-4bbc-b679-38bb27ac6308",
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
          "id": "e7e9140b-2099-428c-a34d-cc62bfd560dd",
          "type": "maths",
          "x": 15,
          "y": 55,
          "w": 180,
          "h": 120,
          "z": 3,
          "locked": false,
          "props": {
            "ops": [
              "+"
            ],
            "max": 20,
            "a": [
              [
                0,
                9
              ],
              [
                0,
                9
              ]
            ],
            "b": [
              [
                0,
                9
              ],
              [
                0,
                9
              ]
            ],
            "carry": "either",
            "rest": false,
            "format": "row",
            "count": 12,
            "seed": 42,
            "columns": 3,
            "size": 14,
            "exercises": [
              {
                "op": "+",
                "a": 9,
                "b": 10,
                "result": 19,
                "rest": 0
              },
              {
                "op": "+",
                "a": 1,
                "b": 7,
                "result": 8,
                "rest": 0
              },
              {
                "op": "+",
                "a": 0,
                "b": 6,
                "result": 6,
                "rest": 0
              },
              {
                "op": "+",
                "a": 12,
                "b": 3,
                "result": 15,
                "rest": 0
              },
              {
                "op": "+",
                "a": 3,
                "b": 10,
                "result": 13,
                "rest": 0
              },
              {
                "op": "+",
                "a": 3,
                "b": 2,
                "result": 5,
                "rest": 0
              },
              {
                "op": "+",
                "a": 2,
                "b": 16,
                "result": 18,
                "rest": 0
              },
              {
                "op": "+",
                "a": 1,
                "b": 14,
                "result": 15,
                "rest": 0
              },
              {
                "op": "+",
                "a": 12,
                "b": 2,
                "result": 14,
                "rest": 0
              },
              {
                "op": "+",
                "a": 1,
                "b": 5,
                "result": 6,
                "rest": 0
              },
              {
                "op": "+",
                "a": 10,
                "b": 8,
                "result": 18,
                "rest": 0
              },
              {
                "op": "+",
                "a": 19,
                "b": 0,
                "result": 19,
                "rest": 0
              }
            ],
            "loosen": null
          }
        },
        {
          "id": "a91a2498-1351-47c3-ae47-19b3c0eb27e0",
          "type": "selbstkontrolle",
          "x": 15,
          "y": 185,
          "w": 180,
          "h": 60,
          "z": 4,
          "locked": false,
          "props": {
            "form": "mixed",
            "links": [
              "e7e9140b-2099-428c-a34d-cc62bfd560dd"
            ],
            "word": "",
            "title": "Selbstkontrolle",
            "size": 14,
            "turn": "none",
            "seed": 42
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
