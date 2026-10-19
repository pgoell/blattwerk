---
type: How-to
title: "Zahlenketten"
description: A heading, a name line, and four Zahlenketten of six rings with the first two rings given and the rest to fill in.
tags: [zahlenkette, zahlenraum-20, klasse-1]
covers: [text, name, zahlenkette]
generated: { by: "human:pgoell", at: 2026-10-19T04:00:00Z }
---

# Zahlenketten

When a teacher asks for: "Ein Blatt mit Zahlenketten bis 20, die ersten Ringe gegeben."

* The heading is a text block at 20 pt. The name line is a name block for the pupil.
* In the editor the chains are the button "Zahlenkette" in the menu "Mathe-Blöcke" in the insert bar. `given` says which rings show their number: "start" gives the first two rings, "ends" the first and the last ring, "random" a few rings at random places, and "free" the rings flagged in `free`.
* `step` fixes the Schrittweite. Leave it out for a random step per chain.
* See [zahlenkette](../blocks/zahlenkette.md) for the other props.

# Doc

Pass this to `replace_doc` (after `create_sheet`), or build it block by block with `add_block`. Change the seed for new chains.

```json
{
  "pages": [
    {
      "blocks": [
        {
          "id": "b4d2f8a1-6c3e-4a9b-8e71-2d0c5f7b9e01",
          "type": "text",
          "x": 15,
          "y": 15,
          "w": 180,
          "h": 14,
          "z": 1,
          "locked": false,
          "props": {
            "text": "Zahlenketten",
            "size": 20,
            "align": "left"
          }
        },
        {
          "id": "b4d2f8a1-6c3e-4a9b-8e71-2d0c5f7b9e02",
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
          "id": "b4d2f8a1-6c3e-4a9b-8e71-2d0c5f7b9e03",
          "type": "zahlenkette",
          "x": 15,
          "y": 60,
          "w": 180,
          "h": 39,
          "z": 3,
          "locked": false,
          "props": {
            "count": 4,
            "columns": 2,
            "rings": 6,
            "max": 20,
            "op": "+",
            "showStep": false,
            "given": "start",
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
